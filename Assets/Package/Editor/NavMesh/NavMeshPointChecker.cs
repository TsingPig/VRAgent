using UnityEngine;
using UnityEditor;
using UnityEngine.AI;

public class NavMeshPointChecker : EditorWindow
{
    private Vector3 pointToCheck = Vector3.zero; // 输入点
    private bool? isOnNavMesh = null;            // 判断结果
    private float maxDistance = 0.1f;            // 搜索半径

    [MenuItem("Tools/NavMesh/Check Point")]
    public static void ShowWindow()
    {
        GetWindow<NavMeshPointChecker>("NavMesh Point Checker");
    }

    private void OnGUI()
    {
        GUILayout.Label("Check if a point is on NavMesh", EditorStyles.boldLabel);

        pointToCheck = EditorGUILayout.Vector3Field("World Position", pointToCheck);
        maxDistance = EditorGUILayout.FloatField("Max Distance", maxDistance);

        if (GUILayout.Button("Check Point"))
        {
            isOnNavMesh = IsPointOnNavMesh(pointToCheck, maxDistance);
        }

        if (isOnNavMesh.HasValue)
        {
            EditorGUILayout.LabelField("Result:", isOnNavMesh.Value ? "On NavMesh ✅" : "Off NavMesh ❌");
        }
    }

    private bool IsPointOnNavMesh(Vector3 worldPos, float maxDist)
    {
        NavMeshHit hit;
        return NavMesh.SamplePosition(worldPos, out hit, maxDist, NavMesh.AllAreas);
    }

    // 在 Scene 视图可视化
    private void OnSceneGUI(SceneView sceneView)
    {
        if (isOnNavMesh.HasValue)
        {
            Handles.color = isOnNavMesh.Value ? Color.green : Color.red;
            Handles.SphereHandleCap(0, pointToCheck, Quaternion.identity, 0.3f, EventType.Repaint);
        }
    }

    private void OnEnable()
    {
        SceneView.duringSceneGui += OnSceneGUI;
    }

    private void OnDisable()
    {
        SceneView.duringSceneGui -= OnSceneGUI;
    }
}
