using System.Collections.Generic;
using UnityEngine;

namespace HenryLab.VRAgent
{
    public class FileIdManager : MonoBehaviour
    {
        // ´æ GameObject
        public List<string> fileIds = new List<string>();

        public List<GameObject> objects = new List<GameObject>();

        // ´æ MonoBehaviour
        public List<string> scriptFileIds = new List<string>();

        public List<MonoBehaviour> scripts = new List<MonoBehaviour>();

        public void Clear()
        {
            fileIds.Clear();
            objects.Clear();
            scriptFileIds.Clear();
            scripts.Clear();
        }

        public void Add(string fileId, GameObject go)
        {
            if(string.IsNullOrEmpty(fileId) || go == null) return;
            if(!fileIds.Contains(fileId))
            {
                fileIds.Add(fileId);
                objects.Add(go);
            }
        }

        public void AddMono(string scriptFileId, MonoBehaviour mono)
        {
            if(string.IsNullOrEmpty(scriptFileId) || mono == null) return;
            if(!scriptFileIds.Contains(scriptFileId))
            {
                scriptFileIds.Add(scriptFileId);
                scripts.Add(mono);
            }
        }

        public void AddMonos(IEnumerable<eventUnit> eventUnits)
        {
            if(eventUnits == null) return;

            foreach(var eventUnit in eventUnits)
            {
                if(eventUnit.methodCallUnits == null) continue;

                foreach(var methodCallUnit in eventUnit.methodCallUnits)
                {
                    MonoBehaviour mono = FileIdResolver.FindMonoByFileID(methodCallUnit.script);
                    if(mono == null)
                    {
                        Debug.LogError($"{methodCallUnit}'s script is null");
                        continue;
                    }
                    AddMono(methodCallUnit.script, mono);
                }
            }
        }

        public GameObject GetObject(string fileId)
        {
            int index = fileIds.IndexOf(fileId);
            if(index >= 0 && index < objects.Count)
                return objects[index];
            return null;
        }

        public MonoBehaviour GetMono(string scriptFileId)
        {
            int index = scriptFileIds.IndexOf(scriptFileId);
            if(index >= 0 && index < scripts.Count)
                return scripts[index];
            return null;
        }
    }
}