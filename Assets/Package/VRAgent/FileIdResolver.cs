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
    public static class FileIDResolver
    {

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
}
#endif
