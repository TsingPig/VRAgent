using System.Collections.Generic;
using UnityEngine;

namespace HenryLab.VRAgent.Online
{
    // =====================================================================
    //  StateCollector — Captures Unity runtime state for Observer feedback
    //
    //  Responsibilities:
    //    1. Snapshot object state (position, rotation, active, components)
    //    2. Intercept Console logs (Application.logMessageReceived)
    //    3. Track events fired during action execution
    // =====================================================================

    public class StateCollector : MonoBehaviour
    {
        // --- Console Log Buffer ---
        private readonly List<LogEntry> _logs = new();
        private int _logIndex = 0;

        // --- Event Tracker ---
        private readonly List<string> _pendingEvents = new();

        // =================================================================
        // Lifecycle
        // =================================================================

        private void OnEnable()
        {
            Application.logMessageReceived += OnLogMessage;
        }

        private void OnDisable()
        {
            Application.logMessageReceived -= OnLogMessage;
        }

        // =================================================================
        // Object State Snapshots
        // =================================================================

        /// <summary>
        /// Capture state of a specific GameObject.
        /// </summary>
        public ObjectStateSnapshot CaptureState(GameObject go, string fileId = "")
        {
            return ObjectStateSnapshot.Capture(go, fileId);
        }

        /// <summary>
        /// Capture state of multiple objects by FileID.
        /// </summary>
        public Dictionary<string, ObjectStateSnapshot> CaptureStates(
            IEnumerable<string> fileIds, FileIDContainer container)
        {
            var result = new Dictionary<string, ObjectStateSnapshot>();
            foreach(string fid in fileIds)
            {
                GameObject go = container.GetObject(fid);
                if(go != null)
                {
                    result[fid] = CaptureState(go, fid);
                }
            }
            return result;
        }

        // =================================================================
        // Console Logs
        // =================================================================

        /// <summary>
        /// Get all logs since the given index.
        /// </summary>
        public List<LogEntry> GetLogsSince(int sinceIndex)
        {
            var result = new List<LogEntry>();
            lock(_logs)
            {
                for(int i = sinceIndex; i < _logs.Count; i++)
                {
                    result.Add(_logs[i]);
                }
            }
            return result;
        }

        /// <summary>Current log count (next index to query from).</summary>
        public int LogCount
        {
            get { lock(_logs) return _logs.Count; }
        }

        /// <summary>Clear all captured logs.</summary>
        public void ClearLogs()
        {
            lock(_logs) _logs.Clear();
        }

        private void OnLogMessage(string condition, string stackTrace, LogType type)
        {
            string level = type switch
            {
                LogType.Error => "Error",
                LogType.Exception => "Exception",
                LogType.Warning => "Warning",
                LogType.Assert => "Assert",
                _ => "Log",
            };

            // Filter out our own bridge logs to avoid feedback loop
            if(condition.StartsWith("[AgentBridge]") || condition.StartsWith("[AgentOnline]"))
                return;

            lock(_logs)
            {
                _logs.Add(new LogEntry
                {
                    index = _logIndex++,
                    level = level,
                    message = condition,
                    timestamp = System.DateTime.Now.ToString("HH:mm:ss.fff"),
                });
            }
        }

        // =================================================================
        // Event Tracking (used during action execution)
        // =================================================================

        /// <summary>Record an event that occurred during execution.</summary>
        public void RecordEvent(string eventDescription)
        {
            _pendingEvents.Add(eventDescription);
        }

        /// <summary>Drain and return all pending events.</summary>
        public List<string> DrainEvents()
        {
            var result = new List<string>(_pendingEvents);
            _pendingEvents.Clear();
            return result;
        }
    }
}
