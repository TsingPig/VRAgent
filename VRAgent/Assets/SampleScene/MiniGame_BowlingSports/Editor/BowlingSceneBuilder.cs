#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class BowlingSceneBuilder
{
    [MenuItem("Tools/MiniGame BowlingSports/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Bowling_Root") ?? new GameObject("Bowling_Root");

        Add<BowlingStateController>(root, "StateController");
        Add<FrameScoreboard>(root, "Scoreboard");

        var laneGo = Ensure(root, "Lane");
        var lane = laneGo.GetComponent<LaneController>() ?? laneGo.AddComponent<LaneController>();

        var ballGo = Ensure(root, "BowlingBall");
        ballGo.transform.localPosition = new Vector3(0, 0.5f, -3);
        if (ballGo.GetComponent<Rigidbody>() == null) { var rb = ballGo.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (ballGo.GetComponent<SphereCollider>() == null) ballGo.AddComponent<SphereCollider>();
        var ball = ballGo.GetComponent<BowlingBall>() ?? ballGo.AddComponent<BowlingBall>();
        ball.lane = lane;

        // 10 pins
        lane.pins.Clear();
        for (int i = 0; i < 10; i++)
        {
            var pg = Ensure(root, $"Pin_{i:00}");
            pg.transform.localPosition = new Vector3(-1.5f + (i % 4) * 1f, 0.5f, 5 + (i / 4));
            if (pg.GetComponent<CapsuleCollider>() == null) pg.AddComponent<CapsuleCollider>();
            var pin = pg.GetComponent<BowlingPin>() ?? pg.AddComponent<BowlingPin>();
            pin.lane = lane;
            lane.pins.Add(pin);
        }

        var lightGo = Ensure(root, "PinResetLight");
        var prl = lightGo.GetComponent<PinResetLight>() ?? lightGo.AddComponent<PinResetLight>();
        var bulb = Ensure(lightGo, "Bulb"); bulb.SetActive(false);
        prl.lightBulb = bulb;

        Debug.Log("[Bowling] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame BowlingSports/Print Oracle Summary")]
    public static void PrintSummary() => BowlingOracleRegistry.PrintSummary();

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
