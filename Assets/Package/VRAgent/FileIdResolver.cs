#if UNITY_EDITOR
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEditor.Events;
using UnityEngine;
using UnityEngine.Events;

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

                MonoBehaviour mono = FindMonoByFileID(methodCallUnit.script);
                MethodInfo method = mono.GetType().GetMethod(methodCallUnit.methodName,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if(method == null)
                {
                    Debug.LogWarning($"{Str.Tags.Logs}Method {methodCallUnit.methodName} not found on {mono.name}");
                    continue;
                }

                // 方法无参数
                if(method.GetParameters().Length == 0)
                {
#if UNITY_EDITOR
                    // 创建 UnityAction
                    UnityAction action = System.Delegate.CreateDelegate(typeof(UnityAction), mono, method) as UnityAction;
                    if(action != null)
                        UnityEventTools.AddPersistentListener(evt, action);
                    else
                        Debug.LogWarning($"Cannot create UnityAction for method {method.Name}");
#endif
                }
                else
                {
                    // 目前无法解决将带有参数的方法加入到event的问题
                }
            }

            return evt;
        }


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


        public static long GetObjectFileID(UnityEngine.Object obj)
        {
            if(obj == null)
            {
                Debug.LogWarning("Object is null!");
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
        /// <param name="go"></param>
        /// <returns></returns>
        public static string GetObjectGuid(GameObject go)
        {
            if(go == null) return null;

            // 1. 如果是预制体资源
            if(PrefabUtility.IsPartOfPrefabAsset(go))
            {
                return AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(go));
            }
            // 2. 如果是场景中的物体（且是在Editor中）
            else if(Application.isEditor)
            {
                // 使用GlobalObjectId获取稳定的场景对象ID
                GlobalObjectId globalId = GlobalObjectId.GetGlobalObjectIdSlow(go);
                return globalId.ToString(); // 格式如："Scene:GlobalObjectId_V1-2-xxxx-64330974-0"
            }
            // 3. 运行时回退方案
            else
            {
                return go.GetInstanceID().ToString();
            }
        }

        public static GameObject FindGameObjectByFileID(long fileId)
        {
            if(fileId == 0)
            {
                Debug.LogWarning("FileID is 0");
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

            Debug.LogWarning($"Cannot find GameObject with FileID: {fileId}");
            return null;
        }

        public static MonoBehaviour FindMonoByFileID(string fileId)
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
                    if(GetObjectFileID(mono) == id) // 也是用 mono 自身
                        return mono;
                }
            }

            Debug.LogWarning($"Cannot find MonoBehaviour with FileID: {id}");
            return null;
        }


        /// <summary>
        /// 通过 GUID 获取物体
        /// </summary>
        /// <param name="guid"></param>
        /// <returns></returns>
        public static GameObject FindGameObjectByGuid(string guid)
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

        public static GameObject FindGameObject(string id, bool useFileID)
        {
            if(useFileID)
            {
                if(long.TryParse(id, out long fileID))
                {
                    return FindGameObjectByFileID(fileID);
                }
                else
                {
                    Debug.LogError($"Invalid FileID: {id}");
                    return null;
                }
            }
            else
            {
                return FindGameObjectByGuid(id);
            }
        }



    }
}
#endif
