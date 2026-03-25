using HenryLab.VRExplorer;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Unity.Plastic.Newtonsoft.Json;
using UnityEditor;
using UnityEngine;

namespace HenryLab.VRAgent
{
    public class VRAgent : BaseExplorer
    {
        private class TestPlanCounter
        {
            public int taskUnitCount = 0, actionUnitCount = 0;
            public int grabCount = 0, transformCount = 0, triggerCount = 0;
            public int objCount = 0, hitObjCount = 0;
            public int componentCount = 0, hitComponentCount = 0;

            public void Log()
            {
                // ====== Debug ��� ======
                Debug.Log(
                    $"{Str.Tags.LogsTag} Test Plan Metrics:\n" +
                    new RichText().Add($"Tasks: {taskUnitCount}, Actions: {actionUnitCount}\n", color: Color.yellow, bold: true) +
                    new RichText().Add($"Grab: {grabCount}, Trigger: {triggerCount}, Transform: {transformCount}\n", color: Color.yellow, bold: true) +
                    new RichText().Add($"Objects: {objCount}, HitObjects: {hitObjCount}\n", color: Color.yellow, bold: true) +
                    new RichText().Add($"Components: {componentCount}, HitComponents: {hitComponentCount}", color: Color.yellow, bold: true)
                );
            }
        }

        private int _index = 0;
        private TestPlanCounter _testPlanCounter;
        private List<TaskUnit> _taskUnits = new List<TaskUnit>();
        private int _totalActionCount = 0;
        private int _syntaxRejectedActionCount = 0;
        private int _semanticRejectedActionCount = 0;
        private int _legalActionCount = 0;
        private int _declaredGrabActionCount = 0;
        private int _declaredTriggerActionCount = 0;
        private int _declaredTransformActionCount = 0;
        private int _declaredMoveActionCount = 0;
        private int _declaredUnknownActionCount = 0;
        private int _legalGrabActionCount = 0;
        private int _legalTriggerActionCount = 0;
        private int _legalTransformActionCount = 0;
        private int _legalMoveActionCount = 0;
        private int _runtimeActionAttemptCount = 0;
        private int _runtimeActionSuccessCount = 0;
        private int _runtimeActionExceptionCount = 0;
        private DateTime _testStartTime;
        private bool _legalRateLogged = false;

        [Header("Show for Debug")]
        [SerializeField] private GameObject objA;

        [SerializeField] private GameObject objB;

        public bool useFileID = true;

        private static FileIDContainer GetOrCreateManager()
        {
            FileIDContainer manager = FindObjectOfType<FileIDContainer>();
            if(manager == null)
            {
                GameObject go = new GameObject("FileIdManager");
                manager = go.AddComponent<FileIDContainer>();
                Debug.Log("Created FileIdManager in scene");
            }
            return manager;
        }

        protected TaskUnit NextTask => _taskUnits[_index++];

        #region ������Ϊִ�еĳ���̽����Scene Exploration with Behaviour Executation��

        /// <summary>
        /// �ظ�ִ�г���̽����
        /// ��ʼʱ��¼������Ϣ������������ʱ�Զ������첽����
        /// </summary>
        /// <returns></returns>
        protected override async Task RepeatSceneExplore()
        {
            ExperimentManager.Instance.StartRecording();
            //StoreMonoPos();
            while(!_applicationQuitting)
            {
                await SceneExplore();
                //ExperimentManager.Instance.ShowMetrics();
                for(int i = 0; i < 30; i++)
                {
                    await Task.Yield();
                }
                if(TestFinished)
                {
                    if(!_legalRateLogged)
                    {
                        LogLegalActionRate();
                        ExportFinalAnalysisReport();
                        _legalRateLogged = true;
                    }

                    //ExperimentManager.Instance.ExperimentFinish();
                    if(exitAfterTesting)
                    {
                        UnityEditor.EditorApplication.isPlaying = false;
                    }
                    else
                    {
                        // ʵ������� ��ѡ���˳�����������״̬ѭ��ʵ��
                        ResetExploration();
                    }
                }
            }
        }

        protected override async Task SceneExplore()
        {
            if(!TestFinished)
            {
                await TaskExecutation();
            }
        }

        protected override async Task TaskExecutation()
        {
            _curTask = TaskGenerator(NextTask);

            if(_curTask == null || _curTask.Count == 0)
            {
                return;
            }

            foreach(var action in _curTask)
            {
                _runtimeActionAttemptCount++;
                try
                {
                    await action.Execute();
                    _runtimeActionSuccessCount++;
                }
                catch(Exception ex)
                {
                    _runtimeActionExceptionCount++;
                    Debug.LogException(ex);
                }
            }
        }

        protected override void ResetExploration()
        {
        }

        protected override bool TestFinished => _index >= _taskUnits.Count;

        #endregion ������Ϊִ�еĳ���̽����Scene Exploration with Behaviour Executation��

        private static TaskList GetTaskListFromJson()
        {
            string filePath = PlayerPrefs.GetString("TestPlanPath", Str.TestPlanPath);
            if(!File.Exists(filePath))
            {
                Debug.LogError($"Test plan file not found at: {filePath}");
                return null;
            }

            try
            {
                string jsonContent = File.ReadAllText(filePath);
                // TaskList taskList = JsonUtility.FromJson<TaskList>(jsonContent);  ��֧�ֶ�̬
                TaskList taskList = JsonConvert.DeserializeObject<TaskList>(jsonContent);
                if(taskList == null)
                {
                    Debug.LogError("Failed to parse test plan JSON");
                }
                return taskList;
            }
            catch(Exception e)
            {
                Debug.LogError($"Failed to import test plan: {e.Message}\n{e.StackTrace}");
            }
            return null;
        }

        /// <summary>
        /// ������Լƻ�
        /// </summary>
        /// <param name="useFileID"></param>
        public static void ImportTestPlan(bool useFileID = true)
        {
            TaskList tasklist = GetTaskListFromJson();
            if(tasklist == null) return;

            FileIDContainer manager = GetOrCreateManager();
            manager.Clear();

            // ====== ͳ����Ϣ ======
            TestPlanCounter counter = new TestPlanCounter();
            counter.taskUnitCount = tasklist.taskUnits.Count;

            foreach(var taskUnit in tasklist.taskUnits)
            {
                foreach(var action in taskUnit.actionUnits)
                {
                    counter.actionUnitCount++;
                    if(!string.IsNullOrEmpty(action.objectA)) counter.objCount++;



                    switch(action.type)
                    {
                        case "Grab":
                        {
                            GameObject objA = FileIDResolver.FindGameObject(action.objectA, useFileID);
                            if(objA != null)
                            {
                                counter.hitObjCount++;
                                manager.Add(action.objectA, objA);
                            }

                            counter.grabCount++;
                            GrabActionUnit grabAction = action as GrabActionUnit;
                            if(grabAction != null && !string.IsNullOrEmpty(grabAction.objectB))
                            {
                                counter.objCount++;
                                GameObject objB = FileIDResolver.FindGameObject(grabAction.objectB, useFileID);
                                if(objB != null)
                                {
                                    counter.hitObjCount++;
                                    manager.Add(grabAction.objectB, objB);
                                }
                            }
                        }
                        break;


                        case "Trigger":
                        {
                            GameObject objA = FileIDResolver.FindGameObject(action.objectA, useFileID);
                            if(objA != null)
                            {
                                counter.hitObjCount++;
                                manager.Add(action.objectA, objA);
                            }

                            counter.triggerCount++;
                            TriggerActionUnit triggerAction = action as TriggerActionUnit;
                            if(triggerAction != null)
                            {
                                manager.AddComponents(triggerAction.triggerringEvents, ref counter.componentCount, ref counter.hitComponentCount);
                                manager.AddComponents(triggerAction.triggerredEvents, ref counter.componentCount, ref counter.hitComponentCount);
                            }
                        }
                        break;

                        case "Transform":
                        counter.transformCount++;
                        break;


                        case "Move":
                        MoveActionUnit moveAction = action as MoveActionUnit;
                        if(!string.IsNullOrEmpty(moveAction.objectB))
                        {
                            counter.objCount++;
                            GameObject objB = FileIDResolver.FindGameObject(moveAction.objectB, useFileID);
                            if(objB != null)
                            {
                                counter.hitObjCount++;
                                manager.Add(moveAction.objectB, objB);
                            }
                        }
                        break;
                    }
                }
            }

            // ====== Debug ��� ======
            counter.Log();
        }

        /// <summary>
        /// ����ѵ���Ĳ��Լƻ�
        /// </summary>
        /// <param name="useFileID"></param>
        public static void RemoveTestPlan(bool useFileID = true)
        {
            // �Ƴ���ʱĿ������
            var tempTargets = GameObject.FindGameObjectsWithTag(Str.Tags.TempTargetTag);
            foreach(var t in tempTargets)
            {
                DestroyImmediate(t);
            }

            // �Ƴ������� FileIdManager
            FileIDContainer manager = FindObjectOfType<FileIDContainer>();
            if(manager != null)
                DestroyImmediate(manager.gameObject);

            TaskList tasklist = GetTaskListFromJson();
            if(tasklist == null) return;

            foreach(var taskUnit in tasklist.taskUnits)
            {
                foreach(var action in taskUnit.actionUnits)
                {
                    if(action.type == "Move") continue;     // �������


                    GameObject objA = FileIDResolver.FindGameObject(action.objectA, useFileID);
                    if(objA == null) continue;

                    if(action.type == "Grab")
                    {
                        XRGrabbable grabbable = objA.GetComponent<XRGrabbable>();
                        if(grabbable != null)
                        {
                            UnityEngine.Object.DestroyImmediate(grabbable, true);
                            Debug.Log($"Removed XRGrabbable from {objA.name}");
                        }
                    }
                    else if(action.type == "Trigger")
                    {
                        XRTriggerable triggerable = objA.GetComponent<XRTriggerable>();
                        if(triggerable != null)
                        {
                            // ����¼��б�
                            triggerable.triggerringEvents.Clear();
                            triggerable.triggerredEvents.Clear();

                            UnityEngine.Object.DestroyImmediate(triggerable, true);
                            Debug.Log($"Removed XRTriggerable from {objA.name}");
                        }
                    }
                    else if(action.type == "Transform")
                    {
                        XRTransformable transformable = objA.GetComponent<XRTransformable>();
                        if(transformable != null)
                        {
                            UnityEngine.Object.DestroyImmediate(transformable, true);
                            Debug.Log($"Removed XRTransformable from {objA.name}");
                        }

                        if(PrefabUtility.IsPartOfPrefabAsset(objA))
                        {
                            EditorUtility.SetDirty(objA);
                            AssetDatabase.SaveAssets();
                        }
                    }

                    if(PrefabUtility.IsPartOfPrefabAsset(objA))
                    {
                        EditorUtility.SetDirty(objA);
                        AssetDatabase.SaveAssets();
                    }
                }
            }
        }

        private List<BaseAction> TaskGenerator(TaskUnit taskUnit)
        {
            if(taskUnit == null || taskUnit.actionUnits == null || taskUnit.actionUnits.Count == 0)
            {
                Debug.LogError($"{Str.Tags.LogsTag} {taskUnit} is null");
                return null;
            }

            List<BaseAction> task = new List<BaseAction>();

            for(int actionIndex = 0; actionIndex < taskUnit.actionUnits.Count; actionIndex++)
            {
                var action = taskUnit.actionUnits[actionIndex];
                _totalActionCount++;

                if(action == null)
                {
                    _syntaxRejectedActionCount++;
                    Debug.LogWarning($"{Str.Tags.LogsTag} Skip action due to syntax mismatch: null action at task {_index}, action {actionIndex}");
                    continue;
                }

                CountDeclaredActionType(action.type);

                var debugText = new RichText()
                    .Add($"[Task {_index}][Action {actionIndex}] ", color: Color.yellow)
                    .Add("Type: ", color: Color.yellow)
                    .Add(action.type ?? "Unknown", color: Color.cyan)
                    .Add(" | Source: ", color: Color.white)
                    .Add(action.objectA ?? "null", color: Color.green);

                switch(action)
                {
                    case GrabActionUnit grab:
                    string targetInfo = grab.objectB ?? (grab.targetPosition?.ToString() ?? "null");
                    debugText.Add(" | Target: ", color: Color.white)
                             .Add(targetInfo, color: Color.cyan);
                    break;

                    case TransformActionUnit transform:
                    debugText.Add(" | ��Pos: ", color: Color.white)
                             .Add(transform.deltaPosition.ToString(), color: Color.cyan)
                             .Add(" | ��Rot: ", color: Color.white)
                             .Add(transform.deltaRotation.ToString(), color: Color.cyan)
                             .Add(" | ��Scale: ", color: Color.white)
                             .Add(transform.deltaScale.ToString(), color: Color.cyan);
                    break;

                    case TriggerActionUnit trigger:
                    int triggingCount = trigger.triggerringEvents?.Count ?? 0;
                    int trigredCount = trigger.triggerredEvents?.Count ?? 0;
                    debugText.Add(" | TriggerringEvents: ", color: Color.white)
                             .Add(triggingCount.ToString(), color: Color.magenta)
                             .Add(" | TriggerredEvents: ", color: Color.white)
                             .Add(trigredCount.ToString(), color: Color.magenta);
                    break;

                    case MoveActionUnit move:
                    targetInfo = move.objectB ?? (move.targetPosition?.ToString() ?? "null");
                    debugText.Add(" | Target: ", color: Color.white)
                             .Add(targetInfo, color: Color.cyan);
                    break;
                }
                Debug.Log(debugText);

                switch(action)
                {
                    case GrabActionUnit grabAction when action.type == "Grab":
                    {
                        if(string.IsNullOrEmpty(grabAction.objectA))
                        {
                            _syntaxRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Grab action due to syntax mismatch: source_object_fileID is empty");
                            continue;
                        }

                        objA = ResolveAndCacheObject(grabAction.objectA);
                        if(objA == null)
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Grab action due to semantic mismatch: source object not found ({grabAction.objectA})");
                            continue;
                        }

                        Transform destinationTransform = null;
                        if(!string.IsNullOrEmpty(grabAction.objectB))
                        {
                            objB = ResolveAndCacheObject(grabAction.objectB);
                            if(objB == null)
                            {
                                _semanticRejectedActionCount++;
                                Debug.LogWarning($"{Str.Tags.LogsTag} Skip Grab action due to semantic mismatch: target object not found ({grabAction.objectB})");
                                continue;
                            }
                            destinationTransform = objB.transform;
                        }
                        else if(grabAction.targetPosition != null)
                        {
                            Vector3 targetPos = (Vector3)grabAction.targetPosition;
                            GameObject targetObj = GameObject.Find($"{objA.name}_TargetPosition");
                            if(targetObj == null)
                            {
                                targetObj = new GameObject($"{objA.name}_TargetPosition_{Str.Tags.TempTargetTag}");
                                targetObj.tag = Str.Tags.TempTargetTag;
                            }
                            targetObj.transform.position = targetPos;
                            destinationTransform = targetObj.transform;
                            Debug.Log($"Set {objA.name}'s destination to position {targetPos}");
                        }
                        else
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Grab action due to semantic mismatch: lacking destination");
                            continue;
                        }

                        XRGrabbable grabbable = objA.AddComponent<XRGrabbable>();
                        grabbable.destination = destinationTransform;
                        Debug.Log($"Added XRGrabbable component to {objA.name}");
                        task.AddRange(GrabTask(grabbable));
                        _legalActionCount++;
                        _legalGrabActionCount++;
                        break;
                    }

                    case TriggerActionUnit triggerAction when action.type == "Trigger":
                    {
                        if(string.IsNullOrEmpty(triggerAction.objectA))
                        {
                            _syntaxRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Trigger action due to syntax mismatch: source_object_fileID is empty");
                            continue;
                        }

                        objA = ResolveAndCacheObject(triggerAction.objectA);
                        if(objA == null)
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Trigger action due to semantic mismatch: source object not found ({triggerAction.objectA})");
                            continue;
                        }

                        if(!ValidateAndCacheEventScripts(triggerAction.triggerringEvents) || !ValidateAndCacheEventScripts(triggerAction.triggerredEvents))
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Trigger action due to semantic mismatch: script_fileID cannot be resolved");
                            continue;
                        }

                        XRTriggerable triggerable = objA.AddComponent<XRTriggerable>();
                        Debug.Log($"Added XRTriggerable component to {objA.name}");

                        if(triggerAction.trigerringTime != null) triggerable.triggeringTime = (float)triggerAction.trigerringTime;
                        ParameterResolver.BindEventList(triggerAction.triggerringEvents, triggerable.triggerringEvents);
                        ParameterResolver.BindEventList(triggerAction.triggerredEvents, triggerable.triggerredEvents);

                        task.AddRange(TriggerTask(triggerable));
                        _legalActionCount++;
                        _legalTriggerActionCount++;
                        break;
                    }

                    case TransformActionUnit transformAction when action.type == "Transform":
                    {
                        if(string.IsNullOrEmpty(transformAction.objectA))
                        {
                            _syntaxRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Transform action due to syntax mismatch: source_object_fileID is empty");
                            continue;
                        }

                        objA = ResolveAndCacheObject(transformAction.objectA);
                        if(objA == null)
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Transform action due to semantic mismatch: source object not found ({transformAction.objectA})");
                            continue;
                        }

                        XRTransformable transformable = objA.AddComponent<XRTransformable>();
                        Debug.Log($"Added XRTransformable component to {objA.name}");

                        if(transformAction.trigerringTime != null) transformable.triggerringTime = (float)transformAction.trigerringTime;
                        transformable.deltaPosition = transformAction.deltaPosition;
                        transformable.deltaRotation = transformAction.deltaRotation;
                        transformable.deltaScale = transformAction.deltaScale;

                        task.AddRange(TransformTask(transformable));
                        _legalActionCount++;
                        _legalTransformActionCount++;
                        break;
                    }

                    case MoveActionUnit moveAction when action.type == "Move":
                    {
                        Vector3 destination = transform.position;

                        if(!string.IsNullOrEmpty(moveAction.objectB))
                        {
                            objB = ResolveAndCacheObject(moveAction.objectB);
                            if(objB == null)
                            {
                                _semanticRejectedActionCount++;
                                Debug.LogWarning($"{Str.Tags.LogsTag} Skip Move action due to semantic mismatch: target object not found ({moveAction.objectB})");
                                continue;
                            }
                            destination = objB.transform.position;
                        }
                        else if(moveAction.targetPosition != null)
                        {
                            destination = (Vector3)moveAction.targetPosition;
                        }
                        else
                        {
                            _semanticRejectedActionCount++;
                            Debug.LogWarning($"{Str.Tags.LogsTag} Skip Move action due to semantic mismatch: lacking destination");
                            continue;
                        }

                        task.Add(new MoveAction(_navMeshAgent, moveSpeed, destination));
                        _legalActionCount++;
                        _legalMoveActionCount++;
                        break;
                    }

                    default:
                    {
                        _syntaxRejectedActionCount++;
                        Debug.LogWarning($"{Str.Tags.LogsTag} Skip action due to syntax mismatch: unsupported type '{action.type}' or type-body mismatch");
                        break;
                    }
                }
            }
            return task;
        }

        private GameObject ResolveAndCacheObject(string fileId)
        {
            if(string.IsNullOrEmpty(fileId)) return null;

            GameObject go = FileIDResolver.FindGameObject(fileId, useFileID);
            if(go != null)
            {
                GetOrCreateManager().Add(fileId, go);
            }
            return go;
        }

        private bool ValidateAndCacheEventScripts(IEnumerable<eventUnit> eventUnits)
        {
            if(eventUnits == null) return true;

            foreach(var eventUnit in eventUnits)
            {
                if(eventUnit?.methodCallUnits == null) continue;

                foreach(var methodCallUnit in eventUnit.methodCallUnits)
                {
                    if(methodCallUnit == null || string.IsNullOrEmpty(methodCallUnit.script))
                    {
                        return false;
                    }

                    MonoBehaviour component = FileIDResolver.FindComponentByFileID(methodCallUnit.script);
                    if(component == null)
                    {
                        return false;
                    }

                    GetOrCreateManager()._AddComponent(methodCallUnit.script, component);
                }
            }

            return true;
        }

        private void LogLegalActionRate()
        {
            int illegalCount = _syntaxRejectedActionCount + _semanticRejectedActionCount;
            float legalRate = _totalActionCount > 0
                ? (float)_legalActionCount / _totalActionCount * 100f
                : 0f;

            Debug.Log(
                $"{Str.Tags.LogsTag} Legal Action Summary:\n" +
                new RichText().Add($"Total Actions: {_totalActionCount}\n", color: Color.yellow, bold: true) +
                new RichText().Add($"Legal Actions: {_legalActionCount}\n", color: Color.green, bold: true) +
                new RichText().Add($"Syntax Rejected: {_syntaxRejectedActionCount}\n", color: Color.red, bold: true) +
                new RichText().Add($"Semantic Rejected: {_semanticRejectedActionCount}\n", color: Color.red, bold: true) +
                new RichText().Add($"Skipped Total: {illegalCount}\n", color: Color.red, bold: true) +
                new RichText().Add($"Legal Action Rate: {legalRate:F2}%", color: Color.cyan, bold: true)
            );
        }

        private void CountDeclaredActionType(string actionType)
        {
            switch(actionType)
            {
                case "Grab":
                _declaredGrabActionCount++;
                break;
                case "Trigger":
                _declaredTriggerActionCount++;
                break;
                case "Transform":
                _declaredTransformActionCount++;
                break;
                case "Move":
                _declaredMoveActionCount++;
                break;
                default:
                _declaredUnknownActionCount++;
                break;
            }
        }

        private void ExportFinalAnalysisReport()
        {
            string testPlanPath = PlayerPrefs.GetString("TestPlanPath", Str.TestPlanPath);
            DateTime testEndTime = DateTime.Now;
            TimeSpan duration = testEndTime - _testStartTime;

            int illegalCount = _syntaxRejectedActionCount + _semanticRejectedActionCount;
            float legalRate = _totalActionCount > 0 ? (float)_legalActionCount / _totalActionCount * 100f : 0f;
            float runtimeSuccessRate = _runtimeActionAttemptCount > 0 ? (float)_runtimeActionSuccessCount / _runtimeActionAttemptCount * 100f : 0f;

            string verdict;
            if(legalRate >= 80f) verdict = "Healthy";
            else if(legalRate >= 50f) verdict = "Needs Improvement";
            else verdict = "High Rejection Risk";

            string reportDir = Path.Combine(Path.GetDirectoryName(testPlanPath) ?? Application.dataPath, "Reports");
            Directory.CreateDirectory(reportDir);

            string planName = Path.GetFileNameWithoutExtension(testPlanPath);
            if(string.IsNullOrEmpty(planName)) planName = "test_plan";

            string reportPath = Path.Combine(reportDir, $"{planName}_analysis_{testEndTime:yyyyMMdd_HHmmss}.md");

            StringBuilder sb = new StringBuilder();
            sb.AppendLine("# VRAgent Final Analysis Report");
            sb.AppendLine();
            sb.AppendLine("## Overview");
            sb.AppendLine($"- Generated at: {testEndTime:yyyy-MM-dd HH:mm:ss}");
            sb.AppendLine($"- Test plan: {testPlanPath}");
            sb.AppendLine($"- Duration: {duration:c}");
            sb.AppendLine($"- Verdict: {verdict}");
            sb.AppendLine();

            sb.AppendLine("## Action Legality Summary");
            sb.AppendLine("| Metric | Value |");
            sb.AppendLine("| --- | ---: |");
            sb.AppendLine($"| Total Actions | {_totalActionCount} |");
            sb.AppendLine($"| Legal Actions | {_legalActionCount} |");
            sb.AppendLine($"| Syntax Rejected | {_syntaxRejectedActionCount} |");
            sb.AppendLine($"| Semantic Rejected | {_semanticRejectedActionCount} |");
            sb.AppendLine($"| Skipped Total | {illegalCount} |");
            sb.AppendLine($"| Legal Action Rate | {legalRate:F2}% |");
            sb.AppendLine();

            sb.AppendLine("## Declared vs Legal by Type");
            sb.AppendLine("| Action Type | Declared | Legal |");
            sb.AppendLine("| --- | ---: | ---: |");
            sb.AppendLine($"| Grab | {_declaredGrabActionCount} | {_legalGrabActionCount} |");
            sb.AppendLine($"| Trigger | {_declaredTriggerActionCount} | {_legalTriggerActionCount} |");
            sb.AppendLine($"| Transform | {_declaredTransformActionCount} | {_legalTransformActionCount} |");
            sb.AppendLine($"| Move | {_declaredMoveActionCount} | {_legalMoveActionCount} |");
            sb.AppendLine($"| Unknown Type | {_declaredUnknownActionCount} | 0 |");
            sb.AppendLine();

            sb.AppendLine("## Runtime Execution Summary");
            sb.AppendLine("| Metric | Value |");
            sb.AppendLine("| --- | ---: |");
            sb.AppendLine($"| Attempted Runtime Actions | {_runtimeActionAttemptCount} |");
            sb.AppendLine($"| Runtime Success | {_runtimeActionSuccessCount} |");
            sb.AppendLine($"| Runtime Exceptions | {_runtimeActionExceptionCount} |");
            sb.AppendLine($"| Runtime Success Rate | {runtimeSuccessRate:F2}% |");
            sb.AppendLine();

            sb.AppendLine("## Interpretation");
            sb.AppendLine("- Syntax rejections usually indicate malformed JSON fields, unsupported type names, or type-body mismatch.");
            sb.AppendLine("- Semantic rejections usually indicate unresolved object/script FileID or missing action destination.");
            sb.AppendLine("- Runtime exceptions indicate execution-time failures after action legality checks passed.");

            try
            {
                File.WriteAllText(reportPath, sb.ToString());
                Debug.Log($"{Str.Tags.LogsTag} Final analysis report exported: {reportPath}");
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Failed to export final analysis report: {ex.Message}");
            }
        }

        private new void Start()
        {
            base.Start();
            _testStartTime = DateTime.Now;
            TaskList taskList = GetTaskListFromJson();
            _taskUnits = taskList?.taskUnits ?? new List<TaskUnit>();
        }
    }
}