#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class TowerDefenseSceneBuilder
{
    [MenuItem("Tools/MiniGame TowerDefense/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("TowerDefense_Root") ?? new GameObject("TowerDefense_Root");

        Add<TowerDefenseStateController>(root, "StateController");
        Add<ResourceManager>(root, "ResourceManager");

        var placer = Ensure(root, "TowerPlacer");
        if (placer.GetComponent<Rigidbody>() == null) { var rb = placer.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (placer.GetComponent<BoxCollider>() == null) placer.AddComponent<BoxCollider>();
        var tp = placer.GetComponent<TowerPlacer>(); if (tp == null) placer.AddComponent<TowerPlacer>();

        for (int i = 0; i < 4; i++)
        {
            var t = Ensure(root, $"Tower_{i:00}");
            t.transform.localPosition = new Vector3(i * 2f, 0.5f, 2);
            if (t.GetComponent<BoxCollider>() == null) t.AddComponent<BoxCollider>();
            if (t.GetComponent<Tower>() == null) t.AddComponent<Tower>();
        }

        Add<WaveSpawner>(root, "WaveSpawner");

        for (int i = 0; i < 3; i++)
        {
            var e = Ensure(root, $"Enemy_{i:00}");
            e.transform.localPosition = new Vector3(i * 1.2f, 0.5f, 6);
            if (e.GetComponent<BoxCollider>() == null) e.AddComponent<BoxCollider>();
            var ec = e.GetComponent<EnemyController>(); if (ec == null) ec = e.AddComponent<EnemyController>();
            var red = Ensure(e, "RedHP"); red.SetActive(false);
            ec.redHealthOverlay = red;
        }

        Debug.Log("[TowerDefense] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame TowerDefense/Print Oracle Summary")]
    public static void PrintSummary() => TowerDefenseOracleRegistry.PrintSummary();

    private static T Add<T>(GameObject parent, string name) where T : Component
    {
        var go = Ensure(parent, name);
        var c = go.GetComponent<T>(); if (c == null) c = go.AddComponent<T>();
        return c;
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
