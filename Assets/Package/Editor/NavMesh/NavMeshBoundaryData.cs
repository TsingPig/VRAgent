using UnityEngine;

[CreateAssetMenu(fileName = "NavMeshBoundaryData", menuName = "NavMesh/BoundaryData")]
public class NavMeshBoundaryData : ScriptableObject
{
    public Vector3[] vertices;  // NavMesh ¶¥µã
    public Bounds bounds;       // AABB ±ß½ç
}
