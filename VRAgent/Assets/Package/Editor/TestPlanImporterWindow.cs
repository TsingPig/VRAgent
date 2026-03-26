#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using System;
using System.IO;
using System.Linq;
using Object = UnityEngine.Object;
namespace HenryLab.VRAgent
{
    /// <summary>
    /// TestPlanImporterWindow 是一个 Unity 编辑器窗口，
    /// 用于导入和管理 VRExplorer 的 Test Plan JSON 文件。
    /// 功能包括：
    /// 1. 选择场景对象并打印 GUID 或 FileID
    /// 2. 选择 Test Plan 文件路径（手动浏览）
    /// 3. 根据当前打开的场景自动检测并选择 Test Plan
    /// 4. 导入或移除 Test Plan 对象及其组件
    /// </summary>
    public class TestPlanImporterWindow : EditorWindow
    {
        public static string filePath = null;

        private Object selectedObject;  // 用于选择场景中的物体

        // 自动检测相关
        private string[] _detectedTestPlans = Array.Empty<string>();
        private string[] _detectedTestPlanNames = Array.Empty<string>();
        private int _selectedTestPlanIndex = -1;
        private string _lastDetectedSceneName = null;

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

            GUILayout.Space(20);

            // ==================== 自动检测区域 ====================
            DrawAutoDetectSection();

            GUILayout.Space(10);

            // ==================== 手动选择区域 ====================
            DrawManualSelectSection();

            GUILayout.Space(10);

            // ==================== 导入/移除按钮 ====================
            DrawImportRemoveButtons();
        }

        /// <summary>
        /// 自动检测当前场景的 TestPlan 文件并提供一键导入
        /// </summary>
        private void DrawAutoDetectSection()
        {
            GUILayout.Label("Auto Detect (Current Scene)", EditorStyles.boldLabel);

            var activeScene = EditorSceneManager.GetActiveScene();
            string sceneName = activeScene.name;

            if(string.IsNullOrEmpty(sceneName) || !activeScene.IsValid())
            {
                EditorGUILayout.HelpBox("No active scene detected. Please open a scene first.", MessageType.Warning);
                return;
            }

            EditorGUILayout.LabelField("Current Scene", sceneName);

            // 场景切换时重新扫描
            if(_lastDetectedSceneName != sceneName)
            {
                RefreshTestPlanList(sceneName);
            }

            if(GUILayout.Button("Refresh Test Plans"))
            {
                RefreshTestPlanList(sceneName);
            }

            if(_detectedTestPlans.Length == 0)
            {
                EditorGUILayout.HelpBox($"No test plans found for scene \"{sceneName}\".\nExpected directory: Assets/SampleScene/{sceneName}/TestPlans/", MessageType.Info);
                return;
            }

            // 下拉列表选择
            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField("Test Plan", GUILayout.Width(70));
            _selectedTestPlanIndex = EditorGUILayout.Popup(_selectedTestPlanIndex, _detectedTestPlanNames);
            EditorGUILayout.EndHorizontal();

            if(_selectedTestPlanIndex >= 0 && _selectedTestPlanIndex < _detectedTestPlans.Length)
            {
                EditorGUILayout.LabelField("Path", _detectedTestPlans[_selectedTestPlanIndex], EditorStyles.miniLabel);
            }

            // 一键导入按钮
            GUI.backgroundColor = new Color(0.4f, 0.8f, 0.4f);
            if(GUILayout.Button("Auto Import Selected Test Plan", GUILayout.Height(28)))
            {
                if(_selectedTestPlanIndex >= 0 && _selectedTestPlanIndex < _detectedTestPlans.Length)
                {
                    string selectedPath = _detectedTestPlans[_selectedTestPlanIndex];
                    filePath = selectedPath;
                    PlayerPrefs.SetString("TestPlanPath", selectedPath);
                    VRAgent.RemoveTestPlan();
                    VRAgent.ImportTestPlan();
                    ShowNotification(new GUIContent($"Imported: {_detectedTestPlanNames[_selectedTestPlanIndex]}"));
                    Debug.Log($"[AutoImport] Test plan imported from: {selectedPath}");
                }
                else
                {
                    ShowNotification(new GUIContent("Please select a test plan from the dropdown."));
                }
            }
            GUI.backgroundColor = Color.white;
        }

        /// <summary>
        /// 扫描指定场景名对应的 TestPlans 目录
        /// </summary>
        private void RefreshTestPlanList(string sceneName)
        {
            _lastDetectedSceneName = sceneName;
            _selectedTestPlanIndex = -1;

            // 搜索策略：先在 Assets 下递归查找 <SceneName>/TestPlans 目录
            string testPlanDir = FindTestPlanDirectory(sceneName);

            if(testPlanDir == null || !Directory.Exists(testPlanDir))
            {
                _detectedTestPlans = Array.Empty<string>();
                _detectedTestPlanNames = Array.Empty<string>();
                return;
            }

            var jsonFiles = Directory.GetFiles(testPlanDir, "*.json", SearchOption.TopDirectoryOnly)
                .OrderBy(f => f)
                .ToArray();

            _detectedTestPlans = jsonFiles;
            _detectedTestPlanNames = jsonFiles.Select(Path.GetFileName).ToArray();

            if(jsonFiles.Length > 0)
            {
                _selectedTestPlanIndex = 0;
                Debug.Log($"[AutoDetect] Found {jsonFiles.Length} test plan(s) for scene \"{sceneName}\" in {testPlanDir}");
            }
        }

        /// <summary>
        /// 根据场景名查找 TestPlans 目录。
        /// 优先查找 Assets/SampleScene/{sceneName}/TestPlans/，
        /// 然后回退到 Assets 下任意匹配的 {sceneName}/TestPlans/。
        /// </summary>
        private static string FindTestPlanDirectory(string sceneName)
        {
            // 优先路径：SampleScene 下
            string primaryPath = Path.Combine(Application.dataPath, "SampleScene", sceneName, "TestPlans");
            if(Directory.Exists(primaryPath))
                return primaryPath;

            // 回退：在整个 Assets 下搜索 <sceneName>/TestPlans
            try
            {
                var matches = Directory.GetDirectories(Application.dataPath, "TestPlans", SearchOption.AllDirectories)
                    .Where(d => Path.GetFileName(Path.GetDirectoryName(d)) == sceneName)
                    .ToArray();
                if(matches.Length > 0)
                    return matches[0];
            }
            catch(Exception e)
            {
                Debug.LogWarning($"[AutoDetect] Error scanning for TestPlans directory: {e.Message}");
            }

            return null;
        }

        /// <summary>
        /// 手动浏览选择 TestPlan 文件
        /// </summary>
        private void DrawManualSelectSection()
        {
            GUILayout.Label("Manual Select", EditorStyles.boldLabel);

            GUILayout.BeginHorizontal();
            filePath = EditorGUILayout.TextField("Test Plan Path", filePath);
            if(GUILayout.Button("Browse", GUILayout.Width(80)))
            {
                filePath = EditorUtility.OpenFilePanel("Select Test Plan", "Assets", "json");
                PlayerPrefs.SetString("TestPlanPath", filePath);
            }
            GUILayout.EndHorizontal();
        }

        /// <summary>
        /// 导入/移除按钮
        /// </summary>
        private void DrawImportRemoveButtons()
        {
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
