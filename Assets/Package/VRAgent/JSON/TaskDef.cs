using System;
using System.Collections.Generic;
using Unity.Plastic.Newtonsoft.Json;

namespace HenryLab.VRAgent
{
    [Serializable] public class TaskList { [JsonProperty("taskUnits")] public List<TaskUnit> taskUnits; }

    [Serializable] public class TaskUnit { [JsonProperty("actionUnits")] public List<ActionUnit> actionUnits; }

    [Serializable] public class eventUnit { [JsonProperty("methodCallUnits")] public List<methodCallUnit> methodCallUnits; }

    [Serializable]
    public class methodCallUnit
    {
        [JsonProperty("script_fileID")] public string script;
        [JsonProperty("method_name")] public string methodName;
        [JsonProperty("parameter_fileID")] public List<string>? parameters;
    }
}