using HenryLab.VRExplorer;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading.Tasks;
using Unity.Plastic.Newtonsoft.Json;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace HenryLab.VRAgent.Online
{
    // =====================================================================
    //  VRAgentOnline — Online closed-loop executor
    //
    //  Replaces VRAgent's batch "load all → execute all" model with:
    //    Python sends command → Unity executes 1 action → returns result
    //    → Python observes → sends next command → ...
    //
    //  Architecture:
    //    AgentBridge (TCP)  →  VRAgentOnline (command dispatch)
    //                           ├── Execute:      single action
    //                           ├── ExecuteBatch:  n actions
    //                           ├── QueryState:    snapshot objects
    //                           ├── QueryLogs:     console log drain
    //                           ├── ImportObjects: pre-resolve FileIDs
    //                           └── Reset:         cleanup
    //
    //  This class inherits from BaseExplorer to reuse GrabTask/TriggerTask/
    //  TransformTask helpers but overrides the exploration loop to be
    //  event-driven instead of sequential.
    // =====================================================================

    [RequireComponent(typeof(AgentBridge))]
    [RequireComponent(typeof(StateCollector))]
    public class VRAgentOnline : BaseExplorer
    {
        [Header("Online Settings")]
        [SerializeField] private bool useFileID = true;

        private AgentBridge _bridge;
        private StateCollector _stateCollector;
        private FileIDContainer _fileIdContainer;

        // Tracks whether we're currently executing an action (to prevent overlap)
        private bool _executing = false;

        [Header("Debug")]
        [SerializeField] private GameObject objA;
        [SerializeField] private GameObject objB;

        // =================================================================
        // Lifecycle
        // =================================================================

        private new void Start()
        {
            base.Start();

            _bridge = GetComponent<AgentBridge>();
            _stateCollector = GetComponent<StateCollector>();
            _fileIdContainer = GetOrCreateFileIDContainer();

            _bridge.OnCommandReceived += HandleCommand;

            Debug.Log($"[AgentOnline] Ready — listening on port {_bridge.Port}");
        }

        private void OnDestroy()
        {
            if(_bridge != null)
                _bridge.OnCommandReceived -= HandleCommand;
        }

        // =================================================================
        // BaseExplorer overrides (no-op — we don't use the sequential loop)
        // =================================================================

        protected override async Task RepeatSceneExplore() { await Task.CompletedTask; }
        protected override async Task SceneExplore() { await Task.CompletedTask; }
        protected override async Task TaskExecutation() { await Task.CompletedTask; }
        protected override void ResetExploration() { }
        protected override bool TestFinished => true; // Always "finished" — driven by commands

        // =================================================================
        // Command Dispatch (main thread, called from AgentBridge.Update)
        // =================================================================

        private async void HandleCommand(AgentCommand command)
        {
            if(command == null) return;

            try
            {
                switch(command.type)
                {
                    case "Execute":
                        await HandleExecute((ExecuteCommand)command);
                        break;

                    case "ExecuteBatch":
                        await HandleExecuteBatch((ExecuteBatchCommand)command);
                        break;

                    case "QueryState":
                        HandleQueryState((QueryStateCommand)command);
                        break;

                    case "QueryLogs":
                        HandleQueryLogs((QueryLogsCommand)command);
                        break;

                    case "ImportObjects":
                        HandleImportObjects((ImportObjectsCommand)command);
                        break;

                    case "Reset":
                        HandleReset(command);
                        break;

                    default:
                        _bridge.SendResponse(AgentResponse.MakeError(
                            command.requestId, $"Unknown command type: {command.type}"));
                        break;
                }
            }
            catch(Exception ex)
            {
                Debug.LogException(ex);
                _bridge.SendResponse(AgentResponse.MakeError(command.requestId, ex.ToString()));
            }
        }

        // =================================================================
        // Execute — Single Action
        // =================================================================

        private async Task HandleExecute(ExecuteCommand cmd)
        {
            if(_executing)
            {
                _bridge.SendResponse(AgentResponse.MakeError(
                    cmd.requestId, "Already executing an action. Wait for completion."));
                return;
            }

            _executing = true;
            var sw = Stopwatch.StartNew();

            try
            {
                var result = await ExecuteSingleAction(cmd.action, cmd.requestId);
                sw.Stop();
                result.durationMs = (float)sw.Elapsed.TotalMilliseconds;
                _bridge.SendResponse(result);
            }
            finally
            {
                _executing = false;
            }
        }

        // =================================================================
        // ExecuteBatch — Multiple Actions
        // =================================================================

        private async Task HandleExecuteBatch(ExecuteBatchCommand cmd)
        {
            if(_executing)
            {
                _bridge.SendResponse(AgentResponse.MakeError(
                    cmd.requestId, "Already executing. Wait for completion."));
                return;
            }

            _executing = true;
            var totalSw = Stopwatch.StartNew();
            var batchResult = new BatchResultResponse
            {
                type = ResponseType.BatchResult.ToString(),
                requestId = cmd.requestId,
                success = true,
            };

            try
            {
                foreach(var action in cmd.actions)
                {
                    var result = await ExecuteSingleAction(action, cmd.requestId);
                    batchResult.results.Add(result);

                    if(result.exceptions.Count > 0)
                        batchResult.success = false;
                }

                totalSw.Stop();
                batchResult.totalDurationMs = (float)totalSw.Elapsed.TotalMilliseconds;
                _bridge.SendResponse(batchResult);
            }
            finally
            {
                _executing = false;
            }
        }

        // =================================================================
        // Core: Execute a single ActionUnit → ExecutionResultResponse
        // =================================================================

        private async Task<ExecutionResultResponse> ExecuteSingleAction(
            ActionUnit actionUnit, string requestId)
        {
            var response = new ExecutionResultResponse
            {
                type = ResponseType.ExecutionResult.ToString(),
                requestId = requestId,
                actionType = actionUnit.type,
                sourceObject = actionUnit.objectA,
                success = true,
            };

            // Resolve source object
            GameObject sourceObj = _fileIdContainer.GetObject(actionUnit.objectA);
            if(sourceObj == null)
            {
                response.success = false;
                response.exceptions.Add($"Source object not found: fileID={actionUnit.objectA}");
                return response;
            }

            // Capture state BEFORE
            response.stateBefore = _stateCollector.CaptureState(sourceObj, actionUnit.objectA);
            _stateCollector.DrainEvents(); // Clear any stale events

            // For Trigger actions with explicit method calls, prefer direct event invocation.
            // This avoids XRTriggerable runtime assumptions that can cause NullReferenceException.
            if(actionUnit is TriggerActionUnit directTrigger && HasMethodCalls(directTrigger))
            {
                InvokeTriggerEventsDirectly(directTrigger, response);
                response.stateAfter = _stateCollector.CaptureState(sourceObj, actionUnit.objectA);
                response.events = _stateCollector.DrainEvents();
                return response;
            }

            // Build and execute task
            List<BaseAction> task = BuildTask(actionUnit, sourceObj, response);

            if(task != null)
            {
                foreach(var action in task)
                {
                    try
                    {
                        _stateCollector.RecordEvent($"execute:{action.GetType().Name}");
                        await action.Execute();
                        _stateCollector.RecordEvent($"completed:{action.GetType().Name}");
                    }
                    catch(Exception ex)
                    {
                        response.exceptions.Add($"{action.GetType().Name}: {ex.Message}");
                        _stateCollector.RecordEvent($"exception:{action.GetType().Name}:{ex.Message}");
                        Debug.LogException(ex);
                    }
                }
            }

            // Capture state AFTER
            response.stateAfter = _stateCollector.CaptureState(sourceObj, actionUnit.objectA);

            // Collect events
            response.events = _stateCollector.DrainEvents();

            return response;
        }

        private static bool HasMethodCalls(TriggerActionUnit trigger)
        {
            if(trigger == null) return false;

            bool HasCalls(List<eventUnit> events)
            {
                if(events == null) return false;
                foreach(var e in events)
                {
                    if(e?.methodCallUnits != null && e.methodCallUnits.Count > 0)
                        return true;
                }
                return false;
            }

            return HasCalls(trigger.triggerringEvents) || HasCalls(trigger.triggerredEvents);
        }

        private void InvokeTriggerEventsDirectly(TriggerActionUnit trigger, ExecutionResultResponse response)
        {
            void InvokeEventList(List<eventUnit> eventUnits, string phase)
            {
                if(eventUnits == null) return;
                for(int i = 0; i < eventUnits.Count; i++)
                {
                    try
                    {
                        UnityEngine.Events.UnityEvent evt = ParameterResolver.CreateUnityEvent(eventUnits[i]);
                        evt?.Invoke();
                        _stateCollector.RecordEvent($"direct_trigger:{phase}[{i}]");
                    }
                    catch(Exception ex)
                    {
                        response.exceptions.Add($"DirectTrigger:{phase}[{i}]: {ex.Message}");
                        _stateCollector.RecordEvent($"exception:DirectTrigger:{phase}[{i}]:{ex.Message}");
                        Debug.LogException(ex);
                    }
                }
            }

            InvokeEventList(trigger.triggerringEvents, "triggerring_events");
            InvokeEventList(trigger.triggerredEvents, "triggerred_events");
        }

        /// <summary>
        /// Build a BaseAction task list from an ActionUnit — mirrors VRAgent.TaskGenerator()
        /// but for a single action with state tracking.
        /// </summary>
        private List<BaseAction> BuildTask(ActionUnit actionUnit, GameObject sourceObj,
            ExecutionResultResponse response)
        {
            List<BaseAction> task = new();

            switch(actionUnit)
            {
                case GrabActionUnit grab:
                {
                    XRGrabbable grabbable = sourceObj.AddComponent<XRGrabbable>();
                    _stateCollector.RecordEvent($"component_added:XRGrabbable:{sourceObj.name}");

                    if(!string.IsNullOrEmpty(grab.objectB))
                    {
                        GameObject targetObj = _fileIdContainer.GetObject(grab.objectB);
                        if(targetObj != null)
                        {
                            grabbable.destination = targetObj.transform;
                        }
                        else
                        {
                            response.exceptions.Add($"Target object not found: fileID={grab.objectB}");
                            return null;
                        }
                    }
                    else if(grab.targetPosition.HasValue)
                    {
                        Vector3 targetPos = grab.targetPosition.Value;
                        string tempName = $"{sourceObj.name}_TargetPos_{Str.Tags.TempTargetTag}";
                        GameObject targetObj = GameObject.Find(tempName);
                        if(targetObj == null)
                        {
                            targetObj = new GameObject(tempName);
                            targetObj.tag = Str.Tags.TempTargetTag;
                        }
                        targetObj.transform.position = targetPos;
                        grabbable.destination = targetObj.transform;
                    }
                    else
                    {
                        response.exceptions.Add("Grab action missing target (objectB or targetPosition)");
                        return null;
                    }

                    task.AddRange(GrabTask(grabbable));
                    break;
                }

                case TransformActionUnit transformAU:
                {
                    XRTransformable transformable = sourceObj.AddComponent<XRTransformable>();
                    _stateCollector.RecordEvent($"component_added:XRTransformable:{sourceObj.name}");

                    transformable.deltaPosition = transformAU.deltaPosition;
                    transformable.deltaRotation = transformAU.deltaRotation;
                    transformable.deltaScale = transformAU.deltaScale;

                    if(transformAU.trigerringTime != null)
                        transformable.triggerringTime = (float)transformAU.trigerringTime;

                    ParameterResolver.BindEventList(transformAU.triggerringEvents, transformable.triggerringEvents);
                    ParameterResolver.BindEventList(transformAU.triggerredEvents, transformable.triggerredEvents);

                    task.AddRange(TransformTask(transformable));
                    break;
                }

                case TriggerActionUnit trigger:
                {
                    XRTriggerable triggerable = sourceObj.AddComponent<XRTriggerable>();
                    _stateCollector.RecordEvent($"component_added:XRTriggerable:{sourceObj.name}");

                    if(trigger.trigerringTime != null)
                        triggerable.triggeringTime = (float)trigger.trigerringTime;

                    ParameterResolver.BindEventList(trigger.triggerringEvents, triggerable.triggerringEvents);
                    ParameterResolver.BindEventList(trigger.triggerredEvents, triggerable.triggerredEvents);

                    task.AddRange(TriggerTask(triggerable));
                    break;
                }

                case MoveActionUnit move:
                {
                    Vector3 destination = transform.position;

                    if(!string.IsNullOrEmpty(move.objectB))
                    {
                        GameObject targetObj = _fileIdContainer.GetObject(move.objectB);
                        if(targetObj != null)
                            destination = targetObj.transform.position;
                        else
                            response.exceptions.Add($"Move target not found: fileID={move.objectB}");
                    }
                    else if(move.targetPosition.HasValue)
                    {
                        destination = move.targetPosition.Value;
                    }

                    task.Add(new MoveAction(_navMeshAgent, moveSpeed, destination));
                    break;
                }

                default:
                    response.exceptions.Add($"Unknown action type: {actionUnit.type}");
                    return null;
            }

            return task;
        }

        // =================================================================
        // QueryState
        // =================================================================

        private void HandleQueryState(QueryStateCommand cmd)
        {
            var result = new StateResultResponse
            {
                type = ResponseType.StateResult.ToString(),
                requestId = cmd.requestId,
                success = true,
            };

            result.states = _stateCollector.CaptureStates(cmd.objectFileIds, _fileIdContainer);
            _bridge.SendResponse(result);
        }

        // =================================================================
        // QueryLogs
        // =================================================================

        private void HandleQueryLogs(QueryLogsCommand cmd)
        {
            var logs = _stateCollector.GetLogsSince(cmd.sinceIndex);
            _bridge.SendResponse(new LogsResultResponse
            {
                type = ResponseType.LogsResult.ToString(),
                requestId = cmd.requestId,
                success = true,
                logs = logs,
                nextIndex = _stateCollector.LogCount,
            });
        }

        // =================================================================
        // ImportObjects — Pre-resolve FileIDs (same as VRAgent.ImportTestPlan)
        // =================================================================

        private void HandleImportObjects(ImportObjectsCommand cmd)
        {
            _fileIdContainer.Clear();

            int objTotal = 0, objFound = 0;
            int compTotal = 0, compFound = 0;

            TaskList taskList = cmd.taskList;
            if(taskList == null)
            {
                _bridge.SendResponse(AgentResponse.MakeError(cmd.requestId, "task_list is null"));
                return;
            }

            foreach(var taskUnit in taskList.taskUnits)
            {
                foreach(var action in taskUnit.actionUnits)
                {
                    // Resolve source object
                    if(!string.IsNullOrEmpty(action.objectA))
                    {
                        objTotal++;
                        GameObject go = FileIDResolver.FindGameObject(action.objectA, cmd.useFileId);
                        if(go != null)
                        {
                            objFound++;
                            _fileIdContainer.Add(action.objectA, go);
                        }
                    }

                    // Resolve target object for Grab
                    if(action is GrabActionUnit grab && !string.IsNullOrEmpty(grab.objectB))
                    {
                        objTotal++;
                        GameObject go = FileIDResolver.FindGameObject(grab.objectB, cmd.useFileId);
                        if(go != null)
                        {
                            objFound++;
                            _fileIdContainer.Add(grab.objectB, go);
                        }
                    }

                    // Resolve components for Trigger/Transform events
                    if(action is TriggerActionUnit trigger)
                    {
                        _fileIdContainer.AddComponents(trigger.triggerringEvents, ref compTotal, ref compFound);
                        _fileIdContainer.AddComponents(trigger.triggerredEvents, ref compTotal, ref compFound);
                    }
                }
            }

            Debug.Log($"[AgentOnline] Import: Objects {objFound}/{objTotal}, Components {compFound}/{compTotal}");

            _bridge.SendResponse(new ImportResultResponse
            {
                type = ResponseType.ImportResult.ToString(),
                requestId = cmd.requestId,
                success = true,
                objectsFound = objFound,
                objectsTotal = objTotal,
                componentsFound = compFound,
                componentsTotal = compTotal,
            });
        }

        // =================================================================
        // Reset
        // =================================================================

        private void HandleReset(AgentCommand cmd)
        {
            // Remove all temp target objects
            var tempTargets = GameObject.FindGameObjectsWithTag(Str.Tags.TempTargetTag);
            foreach(var t in tempTargets) DestroyImmediate(t);

            // Clear FileID container
            _fileIdContainer.Clear();

            // Clear logs
            _stateCollector.ClearLogs();

            _bridge.SendResponse(new AgentResponse
            {
                type = ResponseType.ResetResult.ToString(),
                requestId = cmd.requestId,
                success = true,
            });

            Debug.Log("[AgentOnline] Reset complete");
        }

        // =================================================================
        // Helpers
        // =================================================================

        private static FileIDContainer GetOrCreateFileIDContainer()
        {
            FileIDContainer container = FindObjectOfType<FileIDContainer>();
            if(container == null)
            {
                GameObject go = new GameObject("FileIdManager");
                container = go.AddComponent<FileIDContainer>();
                Debug.Log("[AgentOnline] Created FileIdManager");
            }
            return container;
        }
    }
}
