#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class SandboxSceneBuilder
{
    [MenuItem("Tools/MiniGame SandboxBuilder/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Sandbox_Root") ?? new GameObject("Sandbox_Root");

        Add<SandboxStateController>(root, "StateController");

        var placer = Ensure(root, "BlockPlacer");
        if (placer.GetComponent<Rigidbody>() == null) { var rb = placer.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (placer.GetComponent<BoxCollider>() == null) placer.AddComponent<BoxCollider>();
        placer.GetComponent<BlockPlacer>() ?? placer.AddComponent<BlockPlacer>();

        for (int i = 0; i < 6; i++)
        {
            var b = Ensure(root, $"Block_{i:00}");
            b.transform.localPosition = new Vector3(i * 1.1f, 0.5f, 0);
            if (b.GetComponent<Rigidbody>() == null) { var rb = b.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
            if (b.GetComponent<BoxCollider>() == null) b.AddComponent<BoxCollider>();
            b.GetComponent<BuildingBlock>() ?? b.AddComponent<BuildingBlock>();
        }

        Add<ToolboxController>(root, "Toolbox");
        Add<SaveLoadController>(root, "SaveLoad");

        var hl = Add<HighlightOutline>(root, "HighlightOutline");
        var mesh = Ensure(hl.gameObject, "OutlineMesh"); mesh.SetActive(false);
        hl.outlineMesh = mesh;

        Debug.Log("[Sandbox] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame SandboxBuilder/Print Oracle Summary")]
    public static void PrintSummary() => SandboxOracleRegistry.PrintSummary();

    private static T Add<T>(GameObject parent, string name) where T : Component
    {
        var go = Ensure(parent, name);
        return go.GetComponent<T>() ?? go.AddComponent<T>();
    }
    private static GameObject Ensure(GameObject parent, string name)
    {
        var t = parent.transform.Find(name);
        if (t != null) return t.gameObject;
        var go = new GameObject(name); go.transform.SetParent(parent.transform, false);
        return go;
    }
}
#endif
