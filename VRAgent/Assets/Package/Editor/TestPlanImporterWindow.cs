#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System;
using Object = UnityEngine.Object;
namespace HenryLab.VRAgent
{
    /// <summary>
    /// TestPlanImporterWindow 是一个 Unity 编辑器窗口，
    /// 用于导入和管理 VRExplorer 的 Test Plan JSON 文件。
    /// 功能包括：
    /// 1. 选择场景对象并打印 GUID 或 FileID
    /// 2. 选择 Test Plan 文件路径
    /// 3. 导入或移除 Test Plan 对象及其组件
    /// </summary>
    public class TestPlanImporterWindow : EditorWindow
    {
        public static string filePath = null;

        private Object selectedObject;  // 用于选择场景中的物体

        [MenuItem("Tools/VR Explorer/Import Test Plan")]
        public static void ShowWindow()
        {
            GetWindow<TestPlanImporterWindow>("Test Plan Importer");
        }

        private void OnGUI()
        {
            GUILayout.Label("Test Plan Importer", EditorStyles.boldLabel);

            // 物体选择器
            selectedObject = EditorGUILayout.ObjectField("Select Object", selectedObject, typeof(UnityEngine.Object), true);

            // 打印GUID按钮
            if(GUILayout.Button("Print Object GUID") && selectedObject != null)
            {
                string guid = FileIDResolver.GetObjectGuid(selectedObject as GameObject);
                Debug.Log($"GUID for {selectedObject.name}: {guid}");
                EditorGUIUtility.systemCopyBuffer = guid;  // 复制到剪贴板
                ShowNotification(new GUIContent($"GUID copied to clipboard: {guid}"));
            }

            if(GUILayout.Button("Print Object FileID") && selectedObject != null)
            {
                try
                {
                    long fileId = FileIDResolver.GetObjectFileID(selectedObject);
                    if(fileId != 0)
                    {
                        Debug.Log($"FileID for {selectedObject.name}: {fileId}");
                        EditorGUIUtility.systemCopyBuffer = fileId.ToString();
                        ShowNotification(new GUIContent($"FileID copied to clipboard: {fileId}"));
                    }
                    else
                    {
                        Debug.LogError($"Failed to get FileID for {selectedObject.name}. Is it a scene object?");
                    }
                }
                catch(Exception e)
                {
                    Debug.LogError($"Failed to get FileID: {e.Message}");
                }
            }

            GUILayout.Space(30);

            // TestPlan文件路径选择
            GUILayout.BeginHorizontal();
            filePath = EditorGUILayout.TextField("Test Plan Path", filePath);
            if(GUILayout.Button("Browse", GUILayout.Width(80)))
            {
                filePath = EditorUtility.OpenFilePanel("Select Test Plan", "Assets", "json");
                PlayerPrefs.SetString("TestPlanPath", filePath);
            }
            GUILayout.EndHorizontal();


            // 导入按钮
            if(GUILayout.Button("Import Test Plan"))
            {
                VRAgent.RemoveTestPlan();
                VRAgent.ImportTestPlan();
            }

            if(GUILayout.Button("Remove Test Plan"))
            {
                if(EditorUtility.DisplayDialog("Remove Test Plan",
                   "This will remove all components added by the test plan. Continue?",
                   "Yes", "No"))
                {
                    VRAgent.RemoveTestPlan();
                }
            }
        }
    }

}
#endif
