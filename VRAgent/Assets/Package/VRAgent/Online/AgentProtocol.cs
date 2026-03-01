using System;
using System.Collections.Generic;
using Unity.Plastic.Newtonsoft.Json;
using Unity.Plastic.Newtonsoft.Json.Linq;
using UnityEngine;

namespace HenryLab.VRAgent.Online
{
    // =====================================================================
    //  VRAgent 2.0 — Communication Protocol
    //  Python (Client) ↔ Unity (Server) via TCP + JSON messages
    //
    //  Message format:  4-byte little-endian length prefix + UTF-8 JSON body
    //  Every message has: { "type": "...", ... }
    // =====================================================================

    #region Enums

    /// <summary>
    /// Python → Unity 命令类型
    /// </summary>
    public enum CommandType
    {
        /// <summary>执行单个 ActionUnit</summary>
        Execute,
        /// <summary>批量执行多个 ActionUnit</summary>
        ExecuteBatch,
        /// <summary>查询场景对象状态</summary>
        QueryState,
        /// <summary>查询Console日志</summary>
        QueryLogs,
        /// <summary>导入并解析FileID（预热阶段）</summary>
        ImportObjects,
        /// <summary>重置当前场景/清理组件</summary>
        Reset,
        /// <summary>Ping心跳</summary>
        Ping,
        /// <summary>关闭连接</summary>
        Shutdown,
    }

    /// <summary>
    /// Unity → Python 响应类型
    /// </summary>
    public enum ResponseType
    {
        /// <summary>动作执行结果</summary>
        ExecutionResult,
        /// <summary>批量执行结果</summary>
        BatchResult,
        /// <summary>对象状态查询结果</summary>
        StateResult,
        /// <summary>Console日志</summary>
        LogsResult,
        /// <summary>导入完成</summary>
        ImportResult,
        /// <summary>重置完成</summary>
        ResetResult,
        /// <summary>Pong心跳回复</summary>
        Pong,
        /// <summary>错误</summary>
        Error,
    }

    #endregion

    #region Command Messages (Python → Unity)

    /// <summary>
    /// Python → Unity 的基础命令
    /// </summary>
    [Serializable]
    public class AgentCommand
    {
        [JsonProperty("type")] public string type;
        [JsonProperty("request_id")] public string requestId;

        /// <summary>反序列化命令</summary>
        public static AgentCommand Deserialize(string json)
        {
            try
            {
                JObject jo = JObject.Parse(json);
                string cmdType = jo["type"]?.ToString();

                return cmdType switch
                {
                    "Execute" => JsonConvert.DeserializeObject<ExecuteCommand>(json),
                    "ExecuteBatch" => JsonConvert.DeserializeObject<ExecuteBatchCommand>(json),
                    "QueryState" => JsonConvert.DeserializeObject<QueryStateCommand>(json),
                    "QueryLogs" => JsonConvert.DeserializeObject<QueryLogsCommand>(json),
                    "ImportObjects" => JsonConvert.DeserializeObject<ImportObjectsCommand>(json),
                    "Reset" => JsonConvert.DeserializeObject<AgentCommand>(json),
                    "Ping" => JsonConvert.DeserializeObject<AgentCommand>(json),
                    "Shutdown" => JsonConvert.DeserializeObject<AgentCommand>(json),
                    _ => JsonConvert.DeserializeObject<AgentCommand>(json),
                };
            }
            catch(Exception e)
            {
                Debug.LogError($"[AgentProtocol] Failed to deserialize command: {e.Message}");
                return null;
            }
        }
    }

    /// <summary>执行单个 ActionUnit</summary>
    [Serializable]
    public class ExecuteCommand : AgentCommand
    {
        [JsonProperty("action")] public ActionUnit action;
    }

    /// <summary>批量执行多个 ActionUnit</summary>
    [Serializable]
    public class ExecuteBatchCommand : AgentCommand
    {
        [JsonProperty("actions")] public List<ActionUnit> actions;
    }

    /// <summary>查询对象状态</summary>
    [Serializable]
    public class QueryStateCommand : AgentCommand
    {
        [JsonProperty("object_fileids")] public List<string> objectFileIds;
    }

    /// <summary>查询Console日志</summary>
    [Serializable]
    public class QueryLogsCommand : AgentCommand
    {
        [JsonProperty("since_index")] public int sinceIndex;
    }

    /// <summary>批量导入FileID→GameObject映射</summary>
    [Serializable]
    public class ImportObjectsCommand : AgentCommand
    {
        [JsonProperty("task_list")] public TaskList taskList;
        [JsonProperty("use_file_id")] public bool useFileId = true;
    }

    #endregion

    #region Response Messages (Unity → Python)

    /// <summary>
    /// Unity → Python 的基础响应
    /// </summary>
    [Serializable]
    public class AgentResponse
    {
        [JsonProperty("type")] public string type;
        [JsonProperty("request_id")] public string requestId;
        [JsonProperty("success")] public bool success = true;
        [JsonProperty("error_message")] public string errorMessage;

        public string Serialize()
        {
            return JsonConvert.SerializeObject(this, Formatting.None,
                new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });
        }

        public static AgentResponse MakeError(string requestId, string message)
        {
            return new AgentResponse
            {
                type = ResponseType.Error.ToString(),
                requestId = requestId,
                success = false,
                errorMessage = message,
            };
        }
    }

    /// <summary>单次动作执行结果</summary>
    [Serializable]
    public class ExecutionResultResponse : AgentResponse
    {
        [JsonProperty("action_type")] public string actionType;
        [JsonProperty("source_object")] public string sourceObject;
        [JsonProperty("state_before")] public ObjectStateSnapshot stateBefore;
        [JsonProperty("state_after")] public ObjectStateSnapshot stateAfter;
        [JsonProperty("events")] public List<string> events = new();
        [JsonProperty("exceptions")] public List<string> exceptions = new();
        [JsonProperty("duration_ms")] public float durationMs;
    }

    /// <summary>批量执行结果</summary>
    [Serializable]
    public class BatchResultResponse : AgentResponse
    {
        [JsonProperty("results")] public List<ExecutionResultResponse> results = new();
        [JsonProperty("total_duration_ms")] public float totalDurationMs;
    }

    /// <summary>对象状态查询结果</summary>
    [Serializable]
    public class StateResultResponse : AgentResponse
    {
        [JsonProperty("states")] public Dictionary<string, ObjectStateSnapshot> states = new();
    }

    /// <summary>Console日志查询结果</summary>
    [Serializable]
    public class LogsResultResponse : AgentResponse
    {
        [JsonProperty("logs")] public List<LogEntry> logs = new();
        [JsonProperty("next_index")] public int nextIndex;
    }

    /// <summary>导入结果</summary>
    [Serializable]
    public class ImportResultResponse : AgentResponse
    {
        [JsonProperty("objects_found")] public int objectsFound;
        [JsonProperty("objects_total")] public int objectsTotal;
        [JsonProperty("components_found")] public int componentsFound;
        [JsonProperty("components_total")] public int componentsTotal;
    }

    #endregion

    #region Shared Data Structures

    /// <summary>
    /// 对象状态快照 — 执行前后各采集一次用于对比
    /// </summary>
    [Serializable]
    public class ObjectStateSnapshot
    {
        [JsonProperty("fileid")] public string fileId;
        [JsonProperty("name")] public string name;
        [JsonProperty("active")] public bool active;
        [JsonProperty("position")] public SerializableVector3 position;
        [JsonProperty("rotation")] public SerializableVector3 rotation;
        [JsonProperty("scale")] public SerializableVector3 scale;
        [JsonProperty("components")] public List<string> components;

        public static ObjectStateSnapshot Capture(GameObject go, string fileId = "")
        {
            if(go == null) return null;
            return new ObjectStateSnapshot
            {
                fileId = fileId,
                name = go.name,
                active = go.activeInHierarchy,
                position = new SerializableVector3(go.transform.position),
                rotation = new SerializableVector3(go.transform.eulerAngles),
                scale = new SerializableVector3(go.transform.localScale),
                components = GetComponentNames(go),
            };
        }

        private static List<string> GetComponentNames(GameObject go)
        {
            var list = new List<string>();
            foreach(var c in go.GetComponents<Component>())
            {
                if(c != null) list.Add(c.GetType().Name);
            }
            return list;
        }
    }

    [Serializable]
    public class SerializableVector3
    {
        [JsonProperty("x")] public float x;
        [JsonProperty("y")] public float y;
        [JsonProperty("z")] public float z;

        public SerializableVector3() { }
        public SerializableVector3(Vector3 v) { x = v.x; y = v.y; z = v.z; }
        public Vector3 ToVector3() => new Vector3(x, y, z);
    }

    [Serializable]
    public class LogEntry
    {
        [JsonProperty("index")] public int index;
        [JsonProperty("level")] public string level;   // Log, Warning, Error, Exception
        [JsonProperty("message")] public string message;
        [JsonProperty("timestamp")] public string timestamp;
    }

    #endregion
}
