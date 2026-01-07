using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace HenryLab.VRAgent
{
    public class FileIDContainer : MonoBehaviour
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
            Debug.LogWarning($"{Str.Tags.LogsTag} Missing object for FileID: {fileId}", this);
            return null;
        }

        public new MonoBehaviour GetComponent(string scriptFileId)
        {
            int index = scriptFileIds.IndexOf(scriptFileId);
            if(index >= 0 && index < scripts.Count)
                return scripts[index];
            Debug.LogWarning($"{Str.Tags.LogsTag} Missing script for FileID: {scriptFileId}", this);
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
                    MonoBehaviour component = FileIDResolver.FindComponentByFileID(methodCallUnit.script);
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
    
    
    /// <summary>
    /// 辅助组件，用于包装有返回值的方法调用，使其能在Inspector中序列化
    /// </summary>
    [System.Serializable]
    public class SerializableMethodWrapper : MonoBehaviour
    {
        [SerializeField] private MonoBehaviour targetComponent;
        [SerializeField] private string methodName;
        [SerializeField] private bool logReturnValue = true;

        /// <summary>
        /// 包装器方法，调用目标方法并处理返回值
        /// </summary>
        public void InvokeWrappedMethod()
        {
            if(targetComponent == null || string.IsNullOrEmpty(methodName))
            {
                Debug.LogWarning($"{Str.Tags.LogsTag} SerializableMethodWrapper: Invalid target or method name");
                return;
            }

            try
            {
                MethodInfo method = targetComponent.GetType().GetMethod(methodName,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

                if(method == null)
                {
                    Debug.LogError($"{Str.Tags.LogsTag} Method {methodName} not found on {targetComponent.GetType().Name}");
                    return;
                }

                object result = method.Invoke(targetComponent, null);

                if(logReturnValue && result != null)
                {
                    Debug.Log($"{Str.Tags.LogsTag} {targetComponent.name}.{methodName}() returned: {result}");
                }

                // 可以在这里添加额外的返回值处理逻辑
                HandleReturnValue(result, method.ReturnType);
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Error invoking {methodName}: {ex.Message}");
            }
        }

        /// <summary>
        /// 处理方法返回值
        /// </summary>
        private void HandleReturnValue(object returnValue, Type returnType)
        {
            // 这里可以根据需要处理不同类型的返回值
            // 例如：存储到变量、触发其他事件、发送消息等

            if(returnValue == null) return;

            // 示例：根据返回值类型进行不同处理
            switch(Type.GetTypeCode(returnType))
            {
                case TypeCode.Boolean:
                bool boolResult = (bool)returnValue;
                // 可以根据布尔结果触发不同行为
                break;

                case TypeCode.Int32:
                case TypeCode.Single:
                case TypeCode.Double:
                // 数值类型的处理
                break;

                case TypeCode.String:
                string stringResult = (string)returnValue;
                // 字符串类型的处理
                break;

                default:
                // 其他类型的处理
                break;
            }
        }

        /// <summary>
        /// 设置包装器参数
        /// </summary>
        public void Setup(MonoBehaviour target, string method, bool logReturn = true)
        {
            targetComponent = target;
            methodName = method;
            logReturnValue = logReturn;
        }
    }
}