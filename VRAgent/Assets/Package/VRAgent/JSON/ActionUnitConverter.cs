using System;
using Unity.Plastic.Newtonsoft.Json;
using Unity.Plastic.Newtonsoft.Json.Linq;

namespace HenryLab.VRAgent
{
    public class ActionUnitConverter : JsonConverter
    {
        public override bool CanConvert(Type objectType)
        {
            return objectType == typeof(ActionUnit);
        }

        public override object ReadJson(JsonReader reader, Type objectType, object existingValue, JsonSerializer serializer)
        {
            JObject jo = JObject.Load(reader);
            string type = jo["type"]?.ToString();

            ActionUnit action;

            switch(type)
            {
                case "Grab":
                action = new GrabActionUnit();
                break;

                case "Trigger":
                action = new TriggerActionUnit();
                break;

                case "Transform":
                action = new TransformActionUnit();
                break;

                case "Move":
                action = new MoveActionUnit();
                break;

                default:
                action = new ActionUnit();
                break;
            }

            serializer.Populate(jo.CreateReader(), action);
            return action;
        }

        public override void WriteJson(JsonWriter writer, object value, JsonSerializer serializer)
        {
            serializer.Serialize(writer, value);
        }
    }
}