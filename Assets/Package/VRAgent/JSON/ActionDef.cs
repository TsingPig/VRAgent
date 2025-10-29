using System.Collections.Generic;
using Unity.Plastic.Newtonsoft.Json;
using UnityEngine;

namespace HenryLab.VRAgent
{
    [JsonConverter(typeof(ActionUnitConverter))] // 支持JSON多态
    public class ActionUnit
    {
        public string type;
        [JsonProperty("source_object_fileID")] public string objectA;
    }

    public class GrabActionUnit : ActionUnit
    {
        [JsonProperty("target_object_fileID")] public string? objectB;
        [JsonProperty("target_position")] public Vector3? targetPosition;
    }



    public class TriggerActionUnit : ActionUnit
    {
        [JsonProperty("triggerring_time")] public float? trigerringTime;
        [JsonProperty("triggerring_events")] public List<eventUnit> triggerringEvents;
        [JsonProperty("triggerred_events")] public List<eventUnit> triggerredEvents;
    }

    /// <summary>
    /// TransformActionUnit 用于描述物体的平移/旋转/缩放操作
    /// </summary>
    public class TransformActionUnit : TriggerActionUnit
    {
        [JsonProperty("delta_position")] public Vector3 deltaPosition;
        [JsonProperty("delta_rotation")] public Vector3 deltaRotation;
        [JsonProperty("delta_scale")] public Vector3 deltaScale;
    }

    public class MoveActionUnit : ActionUnit
    {
        [JsonProperty("target_object_fileID")] public string? objectB;
        [JsonProperty("target_position")] public Vector3? targetPosition;
    }
}