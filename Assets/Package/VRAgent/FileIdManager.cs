using System.Collections.Generic;
using UnityEngine;

namespace HenryLab.VRAgent
{
    public class FileIdManager : MonoBehaviour
    {
        // 存 GameObject
        public List<string> fileIds = new List<string>();

        public List<GameObject> objects = new List<GameObject>();

        // 存 MonoBehaviour Component
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

        public GameObject GetObject(string fileId)
        {
            int index = fileIds.IndexOf(fileId);
            if(index >= 0 && index < objects.Count)
                return objects[index];
            return null;
        }

        public new MonoBehaviour GetComponent(string scriptFileId)
        {
            int index = scriptFileIds.IndexOf(scriptFileId);
            if(index >= 0 && index < scripts.Count)
                return scripts[index];
            return null;
        }

        /// <summary>
        /// 将一组 eventUnits 添加到 FileIdManager
        /// </summary>
        /// <param name="eventUnits">事件列表</param>
        /// <param name="methodCallCount">输出总methodCall数量</param>
        /// <param name="hitMethodCallCount">输出总有效methodCall数量</param>
        public void AddComponents(IEnumerable<eventUnit> eventUnits, ref int methodCallCount, ref int hitMethodCallCount)
        {
            if(eventUnits == null) return;

            foreach(var eventUnit in eventUnits)
            {
                if(eventUnit.methodCallUnits == null) continue;

                foreach(var methodCallUnit in eventUnit.methodCallUnits)
                {
                    methodCallCount++;
                    MonoBehaviour component = FileIdResolver.FindComponentByFileID(methodCallUnit.script);
                    if(component != null)
                    {
                        hitMethodCallCount++;
                        _AddComponent(methodCallUnit.script, component);
                    }
                    else
                    {
                        Debug.LogWarning($"{Str.Tags.LogsTag}{methodCallUnit}'s script is null");
                        continue;
                    }
                }
            }
        }

        /// <summary>
        /// 将一个 eventUnit 添加到 FileIdManager
        /// </summary>
        /// <param name="scriptFileId"></param>
        /// <param name="component"></param>
        internal void _AddComponent(string scriptFileId, MonoBehaviour component)
        {
            if(string.IsNullOrEmpty(scriptFileId) || component == null) return;
            if(!scriptFileIds.Contains(scriptFileId))
            {
                scriptFileIds.Add(scriptFileId);
                scripts.Add(component);
            }
        }
    }
}