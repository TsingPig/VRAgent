using UnityEngine;
using UnityEditor;
using UnityEngine.AI;

public class NavMeshBoundaryEditor : EditorWindow
{
    private NavMeshBoundaryData boundaryData;

    [MenuItem("Tools/VR Explorer/Generate Boundary")]
    public static void ShowWindow()
    {
        GetWindow<NavMeshBoundaryEditor>("NavMesh Boundary Generator");
    }

    private void OnGUI()
    {
        GUILayout.Label("NavMesh Boundary Generator", EditorStyles.boldLabel);

        boundaryData = (NavMeshBoundaryData)EditorGUILayout.ObjectField(
            "Boundary Data", boundaryData, typeof(NavMeshBoundaryData), false);

        if (GUILayout.Button("Generate NavMesh Boundary"))
        {
            if (boundaryData == null)
            {
                Debug.LogWarning("请先创建并选择一个 NavMeshBoundaryData 对象！");
                return;
            }

            GenerateBoundary(boundaryData);
        }

        if (boundaryData != null && boundaryData.vertices != null)
        {
            GUILayout.Label($"Vertices Count: {boundaryData.vertices.Length}");
            GUILayout.Label($"Bounds Center: {boundaryData.bounds.center}");
            GUILayout.Label($"Bounds Size: {boundaryData.bounds.size}");
        }
    }

    private void GenerateBoundary(NavMeshBoundaryData data)
    {
        // 直接从当前场景 NavMesh 获取顶点
        var triangulation = NavMesh.CalculateTriangulation();

        if (triangulation.vertices.Length == 0)
        {
            Debug.LogWarning("场景中没有 NavMesh 或尚未 Bake！");
            return;
        }

        data.vertices = triangulation.vertices;

        // 计算 AABB 边界
        Bounds bounds = new Bounds(triangulation.vertices[0], Vector3.zero);
        foreach (var v in triangulation.vertices)
            bounds.Encapsulate(v);

        data.bounds = bounds;

        EditorUtility.SetDirty(data);
        AssetDatabase.SaveAssets();

        Debug.Log($"NavMesh 边界生成完成！顶点数：{triangulation.vertices.Length}, Bounds Center={bounds.center}, Size={bounds.size}");
    }

    // Scene 视图可视化
    [DrawGizmo(GizmoType.NonSelected | GizmoType.Selected)]
    static void DrawNavMeshGizmos(NavMeshBoundaryData data, GizmoType gizmoType)
    {
        if (data == null || data.vertices == null || data.vertices.Length == 0)
            return;

        Gizmos.color = Color.green;
        Gizmos.DrawWireCube(data.bounds.center, data.bounds.size);

        // 可选：绘制顶点
        foreach (var v in data.vertices)
        {
            Gizmos.DrawSphere(v, 0.05f);
        }
    }
}
