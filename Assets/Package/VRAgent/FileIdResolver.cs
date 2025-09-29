#if UNITY_EDITOR
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEditor.Events;
using UnityEngine;
using UnityEngine.Events;
using System;

namespace HenryLab.VRAgent
{
    /// <summary>
    /// 构建 FileID -> GameObject 的映射
    /// </summary>
    public static class FileIdResolver
    {
        /// <summary>
        /// 根据 eventUnit 创建 UnityEvent 并绑定所有 methodCallUnit
        /// </summary>
        public static UnityEvent CreateUnityEvent(eventUnit e, bool useFileID = true)
        {
            var manager = UnityEngine.Object.FindAnyObjectByType<FileIdManager>();
            UnityEvent evt = new UnityEvent();
            if(e.methodCallUnits == null) return evt;

            foreach(var methodCallUnit in e.methodCallUnits)
            {
                if(string.IsNullOrEmpty(methodCallUnit.script) || string.IsNullOrEmpty(methodCallUnit.methodName))
                    continue;

                // MonoBehaviour component = FindComponentByFileID(methodCallUnit.script);
                MonoBehaviour component = manager.GetComponent(methodCallUnit.script);
                if(component == null) continue;

                MethodInfo method = component.GetType().GetMethod(methodCallUnit.methodName,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if(method == null)
                {
                    Debug.LogWarning($"{Str.Tags.LogsTag}Method {methodCallUnit.methodName} not found on {component.name}");
                    continue;
                }

                // 方法无参数
                if(method.GetParameters().Length == 0)
                {
#if UNITY_EDITOR
                    if(method.ReturnType == typeof(void))
                    {
                        // 无返回值方法，直接创建 UnityAction
                        UnityAction action = System.Delegate.CreateDelegate(typeof(UnityAction), component, method) as UnityAction;
                        if(action != null)
                            UnityEventTools.AddPersistentListener(evt, action);
                        else
                            Debug.LogWarning($"{Str.Tags.LogsTag} Cannot create UnityAction for method {method.Name}");
                    }
                    else
                    {
                        // 有返回值的方法，创建包装器方法
                        CreateReturnValueWrapper(evt, component, method);
                    }
#endif
                }
                else
                {
                    Debug.LogError($"{Str.Tags.LogsTag} Method {method.Name} has parameters {method.GetParameters()}.");
                }
            }
            return evt;
        }

#if UNITY_EDITOR
        /// <summary>
        /// 为有返回值的方法创建包装器，使其能够在 Inspector 中序列化
        /// </summary>
        private static void CreateReturnValueWrapper(UnityEvent evt, MonoBehaviour component, MethodInfo method)
        {
            // 创建一个包装器方法，调用原方法但忽略返回值
            string wrapperMethodName = $"_Wrapper_{method.Name}_{method.GetHashCode()}";
            
            // 检查是否已经存在包装器方法
            MethodInfo existingWrapper = component.GetType().GetMethod(wrapperMethodName, 
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            
            if(existingWrapper == null)
            {
                // 动态创建包装器方法（运行时方案）
                UnityAction wrapperAction = () => {
                    try 
                    {
                        object result = method.Invoke(component, null);
                        Debug.Log($"{Str.Tags.LogsTag} Method {method.Name} returned: {result}");
                    }
                    catch(System.Exception ex)
                    {
                        Debug.LogError($"{Str.Tags.LogsTag} Error invoking {method.Name}: {ex.Message}");
                    }
                };
                
                // 使用 UnityEventTools.AddVoidPersistentListener 来添加可序列化的监听器
                // 这需要在目标组件上创建一个实际的void方法
                CreateAndAddVoidWrapper(evt, component, method);
            }
            else
            {
                UnityAction action = System.Delegate.CreateDelegate(typeof(UnityAction), component, existingWrapper) as UnityAction;
                if(action != null)
                    UnityEventTools.AddPersistentListener(evt, action);
            }
        }

        /// <summary>
        /// 创建并添加 void 包装器方法
        /// </summary>
        private static void CreateAndAddVoidWrapper(UnityEvent evt, MonoBehaviour component, MethodInfo originalMethod)
        {
            try
            {
                // 方案1: 尝试在同一个GameObject上找到或创建SerializableMethodWrapper
                GameObject targetGO = component.gameObject;
                SerializableMethodWrapper wrapper = targetGO.GetComponent<SerializableMethodWrapper>();
                
                if(wrapper == null)
                {
                    wrapper = targetGO.AddComponent<SerializableMethodWrapper>();
                    Debug.Log($"{Str.Tags.LogsTag} Added SerializableMethodWrapper to {targetGO.name}");
                }
                
                // 设置包装器参数
                wrapper.Setup(component, originalMethod.Name, true);
                
                // 添加可序列化的监听器
                UnityEventTools.AddPersistentListener(evt, wrapper.InvokeWrappedMethod);
                
                Debug.Log($"{Str.Tags.LogsTag} Successfully wrapped method {originalMethod.Name} with return type {originalMethod.ReturnType}");
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Failed to create wrapper for {originalMethod.Name}: {ex.Message}");
                
                // 备选方案：使用运行时调用（不可序列化）
                UnityAction fallbackAction = () => {
                    try 
                    {
                        object result = originalMethod.Invoke(component, null);
                        Debug.Log($"{Str.Tags.LogsTag} {component.name}.{originalMethod.Name}() returned: {result}");
                    }
                    catch(Exception invokeEx)
                    {
                        Debug.LogError($"{Str.Tags.LogsTag} Error invoking {originalMethod.Name}: {invokeEx.Message}");
                    }
                };
                
                UnityEventTools.AddPersistentListener(evt, fallbackAction);
            }
        }
#endif

        /// <summary>
        /// 绑定一组 eventUnit 到目标 UnityEvent 列表
        /// </summary>
        public static void BindEventList(List<eventUnit> eventUnits, List<UnityEvent> targetList, bool useFileID = true)
        {
            targetList.Clear();
            if(eventUnits == null) return;

            foreach(var e in eventUnits)
            {
                targetList.Add(CreateUnityEvent(e, useFileID));
            }
        }

        /// <summary>
        /// 获取 Object FileID
        /// </summary>
        /// <param name="obj"></param>
        /// <returns></returns>
        public static long GetObjectFileID(UnityEngine.Object obj)
        {
            if(obj == null)
            {
                Debug.LogWarning($"{Str.Tags.LogsTag} Object is null!");
                return 0;
            }

            // 获取 GlobalObjectId
            GlobalObjectId gid = GlobalObjectId.GetGlobalObjectIdSlow(obj);
            string gidString = gid.ToString(); // 例如 "GlobalObjectId_V1-2-GUID-Part1-Part2-Part3"

            // 分割字符串
            string[] parts = gidString.Split('-');

            if(parts.Length < 2)
            {
                Debug.LogWarning("GlobalObjectId format unexpected: " + gidString);
                return 0;
            }

            long fileID;

            if(obj is GameObject go)
            {
                // prefab instance: 取最后一段
                // 普通对象: 取倒数第二段
                if(go.scene.isLoaded && PrefabUtility.IsPartOfPrefabInstance(go))
                {
                    if(long.TryParse(parts[parts.Length - 1], out fileID))
                        return fileID;
                }
                else
                {
                    if(long.TryParse(parts[parts.Length - 2], out fileID))
                        return fileID;
                }
            }
            else if(obj is Component comp)
            {
                // MonoBehaviour 或其他组件
                GameObject goComp = comp.gameObject;

                // prefab instance: Component 的 FileID 在倒数第二段
                if(goComp.scene.isLoaded && PrefabUtility.IsPartOfPrefabInstance(goComp))
                {
                    if(long.TryParse(parts[parts.Length - 2], out fileID))
                        return fileID;
                }
                else
                {
                    // 普通对象，倒数第二段
                    if(long.TryParse(parts[parts.Length - 2], out fileID))
                        return fileID;
                }
            }

            Debug.LogWarning("Failed to parse FileID from GlobalObjectId: " + gidString);
            return 0;
        }

        /// <summary>
        /// 获取 Object GUID
        /// </summary>
        /// <param name="obj"></param>
        /// <returns></returns>
        public static string GetObjectGuid(GameObject obj)
        {
            if(obj == null)
            {
                Debug.LogWarning($"{Str.Tags.LogsTag} Object is null!");
                return null;
            }

            // 1. 如果是预制体资源
            if(PrefabUtility.IsPartOfPrefabAsset(obj))
            {
                return AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(obj));
            }
            // 2. 如果是场景中的物体（且是在Editor中）
            else if(Application.isEditor)
            {
                // 使用GlobalObjectId获取稳定的场景对象ID
                GlobalObjectId globalId = GlobalObjectId.GetGlobalObjectIdSlow(obj);
                return globalId.ToString(); // 格式如："Scene:GlobalObjectId_V1-2-xxxx-64330974-0"
            }
            // 3. 运行时回退方案
            else
            {
                return obj.GetInstanceID().ToString();
            }
        }

        /// <summary>
        /// 根据FileID 查找场景中的脚本组件实例
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        public static MonoBehaviour FindComponentByFileID(string fileId)
        {
            if(!long.TryParse(fileId, out long id) || id == 0)
            {
                Debug.LogWarning("FileID is invalid or 0");
                return null;
            }

            // 先在场景里找
            MonoBehaviour[] allMonos = GameObject.FindObjectsOfType<MonoBehaviour>(true);
            foreach(MonoBehaviour mono in allMonos)
            {
                if(GetObjectFileID(mono) == id) // 注意这里用 mono 自身
                    return mono;
            }

            // 再查 prefab
            string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab");
            foreach(string guid in prefabGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(prefab == null) continue;

                foreach(MonoBehaviour mono in prefab.GetComponentsInChildren<MonoBehaviour>(true))
                {
                    if(GetObjectFileID(mono) == id)
                        return mono;
                }
            }

            Debug.LogWarning($"{Str.Tags.LogsTag} Cannot find Component with FileID: {id}");
            return null;
        }

        /// <summary>
        /// 从场景中查找物体
        /// </summary>
        /// <param name="id"></param>
        /// <param name="useFileID"></param>
        /// <returns></returns>
        public static GameObject FindGameObject(string id, bool useFileID)
        {
            if(useFileID)
            {
                if(long.TryParse(id, out long fileID))
                {
                    return _FindGameObjectByFileID(fileID);
                }
                else
                {
                    Debug.LogError($"Invalid FileID: {id}");
                    return null;
                }
            }
            else
            {
                return _FindGameObjectByGuid(id);
            }
        }

        /// <summary>
        /// 根据FileID从场景中查找物体
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        internal static GameObject _FindGameObjectByFileID(long fileId)
        {
            if(fileId == 0)
            {
                Debug.LogWarning($"{Str.Tags.LogsTag} FileID is 0");
                return null;
            }

            // 遍历场景中所有 GameObject
            GameObject[] allObjects = GameObject.FindObjectsOfType<GameObject>();
            foreach(GameObject go in allObjects)
            {
                long goFileId = GetObjectFileID(go);
                if(goFileId == fileId)
                {
                    if(go.scene.isLoaded && PrefabUtility.IsPartOfPrefabInstance(go))
                    {
                        GameObject g = go;
                        while(g.transform.parent != null && GetObjectFileID(g.transform.parent.gameObject) == fileId)
                        {
                            g = g.transform.parent.gameObject;
                        }
                        return g;
                    }
                    else
                    {
                        return go;
                    }
                }
            }

            // 如果是Prefab资源（不是场景实例），可以扫描所有Prefab
            string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab");
            foreach(string guid in prefabGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(prefab != null)
                {
                    long prefabFileId = GetObjectFileID(prefab);
                    if(prefabFileId == fileId)
                    {
                        return prefab;
                    }
                }
            }

            Debug.LogWarning($"{Str.Tags.LogsTag} Cannot find GameObject with FileID: {fileId}");
            return null;
        }

        /// <summary>
        /// 根据GUID 从场景中查找物体
        /// </summary>
        /// <param name="guid"></param>
        /// <returns></returns>
        internal static GameObject _FindGameObjectByGuid(string guid)
        {
            if(string.IsNullOrEmpty(guid)) return null;

            // First try to find in scene objects
            GameObject[] allObjects = GameObject.FindObjectsOfType<GameObject>();
            foreach(GameObject go in allObjects)
            {
                if(GetObjectGuid(go) == guid)
                    return go;
            }

            // Then try to find in prefabs
            string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab");
            foreach(string prefabGuid in prefabGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(prefabGuid);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(prefab != null && GetObjectGuid(prefab) == guid)
                    return prefab;
            }

            return null;
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
#endif
