#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class EscapeRoomSceneBuilder
{
    [MenuItem("Tools/MiniGame EscapeRoom/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("EscapeRoom_Root") ?? new GameObject("EscapeRoom_Root");

        Add<EscapeRoomStateController>(root, "StateController");
        var combo = Add<CombinationLock>(root, "CombinationLock"); combo.correctDigit = 7;
        var safe = Add<KeySafeController>(root, "KeySafe"); safe.combo = combo;
        var key = Add<KeyController>(root, "Key");
        if (key.GetComponent<Rigidbody>() == null) { var rb = key.gameObject.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (key.GetComponent<BoxCollider>() == null) key.gameObject.AddComponent<BoxCollider>();
        Add<DoorController>(root, "ExitDoor");
        var hint = Add<HintLight>(root, "HintLight");
        var bulb = Ensure(hint.gameObject, "Bulb"); bulb.SetActive(true);
        hint.lightBulb = bulb;
        var puzzle = Add<PuzzlePanelController>(root, "PuzzlePanel"); puzzle.correctAnswer = "RED";

        Debug.Log("[EscapeRoom] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame EscapeRoom/Print Oracle Summary")]
    public static void PrintSummary() => EscapeRoomOracleRegistry.PrintSummary();

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
