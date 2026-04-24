#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class HorrorSceneBuilder
{
    [MenuItem("Tools/MiniGame HorrorSurvival/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Horror_Root") ?? new GameObject("Horror_Root");

        Add<HorrorStateController>(root, "StateController");

        var fl = Ensure(root, "Flashlight");
        if (fl.GetComponent<Rigidbody>() == null) { var rb = fl.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (fl.GetComponent<BoxCollider>() == null) fl.AddComponent<BoxCollider>();
        var flash = fl.GetComponent<FlashlightController>() ?? fl.AddComponent<FlashlightController>();
        var cone = Ensure(fl, "LightCone"); cone.SetActive(false);
        flash.lightCone = cone;

        var bat = Ensure(root, "Battery");
        if (bat.GetComponent<Rigidbody>() == null) { var rb = bat.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (bat.GetComponent<BoxCollider>() == null) bat.AddComponent<BoxCollider>();
        var battery = bat.GetComponent<BatteryItem>() ?? bat.AddComponent<BatteryItem>();
        flash.battery = battery;

        Add<DoorLockController>(root, "ExitDoor");
        Add<EnemyAI>(root, "EnemyAI");

        var hp = Add<HealthSystem>(root, "HealthSystem");
        var red = Ensure(hp.gameObject, "RedOverlay"); red.SetActive(false);
        hp.redBarOverlay = red;

        for (int i = 0; i < 3; i++)
        {
            var k = Ensure(root, $"Key_{i:00}");
            if (k.GetComponent<Rigidbody>() == null) { var rb = k.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
            if (k.GetComponent<BoxCollider>() == null) k.AddComponent<BoxCollider>();
            k.GetComponent<KeyItem>() ?? k.AddComponent<KeyItem>();
        }

        Debug.Log("[Horror] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame HorrorSurvival/Print Oracle Summary")]
    public static void PrintSummary() => HorrorOracleRegistry.PrintSummary();

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
