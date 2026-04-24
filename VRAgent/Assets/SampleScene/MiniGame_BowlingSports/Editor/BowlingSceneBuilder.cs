#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGameBuild;

/// <summary>
/// Bowling alley: 1m wide × 10m long lacquered wood lane with side gutters,
/// 10 white pins in classic triangle at z=5..6.8, glossy black ball at z=-3,
/// scoreboard at +Z wall, pin reset spotlight overhead (bulb disabled), warm
/// alley ambient + 4 ceiling spots.
/// </summary>
public static class BowlingSceneBuilder
{
    [MenuItem("Tools/MiniGame BowlingSports/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Bowling_Root") ?? new GameObject("Bowling_Root");
        root.transform.position = Vector3.zero;

        var matFloor    = H.Mat("BO_FloorCarpet",   new Color(0.20f, 0.10f, 0.10f), 0f, 0.1f);
        var matWall     = H.Mat("BO_WallPanel",     new Color(0.35f, 0.30f, 0.28f), 0f, 0.2f);
        var matCeiling  = H.Mat("BO_Ceiling",       new Color(0.18f, 0.18f, 0.20f), 0f, 0.1f);
        var matLane     = H.Mat("BO_LaneWood",      new Color(0.78f, 0.55f, 0.28f), 0.1f, 0.85f);
        var matGutter   = H.Mat("BO_Gutter",        new Color(0.10f, 0.10f, 0.12f), 0.6f, 0.55f);
        var matPin      = H.Mat("BO_PinWhite",      new Color(0.98f, 0.98f, 0.98f), 0f, 0.6f);
        var matPinStripe= H.Mat("BO_PinStripe",     new Color(0.85f, 0.10f, 0.10f), 0f, 0.55f);
        var matBall     = H.Mat("BO_BallBlack",     new Color(0.04f, 0.04f, 0.05f), 0.2f, 0.95f);
        var matBoard    = H.Mat("BO_BoardFrame",    new Color(0.10f, 0.10f, 0.10f), 0.7f, 0.4f);
        var matScreen   = H.Mat("BO_Scoreboard",    new Color(0.05f, 0.05f, 0.10f), 0f, 0.9f, new Color(0.1f, 0.6f, 1.4f));
        var matBulb     = H.Mat("BO_BulbOff",       new Color(0.6f, 0.6f, 0.6f), 0.2f, 0.5f);
        var matRack     = H.Mat("BO_BallRack",      new Color(0.18f, 0.18f, 0.18f), 0.85f, 0.6f);
        var matApproach = H.Mat("BO_Approach",      new Color(0.55f, 0.40f, 0.22f), 0f, 0.55f);

        H.Atmosphere(new Color(0.30f, 0.25f, 0.30f), 0.7f);

        // Long alley room (3m wide × 16m long), centered on z=4 (covers ball z=-3..pins z=+7..board z=+9)
        H.BuildRoom(root, new Vector3(0, 0, 4), new Vector3(4f, 4f, 16f), matFloor, matWall, matCeiling);

        // Approach (player area) -5..-1 z
        H.Prim(root, "Env_Approach", PrimitiveType.Cube, new Vector3(0, 0.01f, -3f), new Vector3(2.0f, 0.02f, 4f), matApproach);

        // Wood lane (1m wide × 10m long): z=-1..9
        H.Prim(root, "Env_Lane", PrimitiveType.Cube, new Vector3(0, 0.02f, 4f), new Vector3(1.0f, 0.04f, 10f), matLane);
        // Side gutters
        H.Prim(root, "Env_GutterL", PrimitiveType.Cube, new Vector3(-0.65f, 0.015f, 4f), new Vector3(0.30f, 0.03f, 10f), matGutter);
        H.Prim(root, "Env_GutterR", PrimitiveType.Cube, new Vector3( 0.65f, 0.015f, 4f), new Vector3(0.30f, 0.03f, 10f), matGutter);
        // Pin deck wall (back stop)
        H.Prim(root, "Env_PinDeck", PrimitiveType.Cube, new Vector3(0, 0.5f, 7.4f), new Vector3(2.0f, 1.0f, 0.1f), matBoard);

        // 4 overhead lane spots
        for (int i = 0; i < 4; i++)
            H.AddLight(root, $"Env_LaneSpot_{i}", LightType.Spot,
                new Vector3(0, 3.7f, -1 + i * 3f), new Color(1f, 0.95f, 0.78f), 3.0f, 14, 60f, new Vector3(90, 0, 0));

        // Ball rack (left side of approach)
        H.Prim(root, "Env_BallRack", PrimitiveType.Cube, new Vector3(-1.4f, 0.5f, -3f), new Vector3(0.4f, 1.0f, 1.2f), matRack);

        // Controllers
        H.EnsureComp<BowlingStateController>(H.Empty(root, "StateController"));

        // Scoreboard at far +Z wall
        var board = H.Prim(root, "Scoreboard", PrimitiveType.Cube, new Vector3(0, 2.4f, 9.0f), new Vector3(2.0f, 1.0f, 0.15f), matBoard);
        H.EnsureComp<FrameScoreboard>(board);
        var screen = H.Prim(board, "Screen", PrimitiveType.Quad, new Vector3(0, 0, -0.55f), new Vector3(1.8f, 0.85f, 1f), matScreen, new Vector3(0, 180f, 0));
        H.StripCollider(screen);

        // Lane controller (logical, on lane env or empty)
        var laneCtrl = H.Empty(root, "Lane");
        var lane = H.EnsureComp<LaneController>(laneCtrl);

        // Ball (glossy black sphere, z=-3, sphere collider radius=0.11)
        var ball = H.Prim(root, "BowlingBall", PrimitiveType.Sphere, new Vector3(0, 0.22f, -3f), new Vector3(0.22f, 0.22f, 0.22f), matBall);
        H.KinematicRb(ball);
        // ensure sphere collider exists (CreatePrimitive already adds one)
        var bc = H.EnsureComp<BowlingBall>(ball);
        bc.lane = lane;

        // 10 pins in classic triangle (apex at z=5.0, back row z=6.6)
        lane.pins.Clear();
        Vector2[] pinXZ = new Vector2[]
        {
            new Vector2( 0.00f, 5.0f),                                    // row 1 (1 pin)
            new Vector2(-0.15f, 5.40f), new Vector2( 0.15f, 5.40f),       // row 2 (2)
            new Vector2(-0.30f, 5.80f), new Vector2( 0.00f, 5.80f), new Vector2( 0.30f, 5.80f), // row 3 (3)
            new Vector2(-0.45f, 6.20f), new Vector2(-0.15f, 6.20f), new Vector2( 0.15f, 6.20f), new Vector2( 0.45f, 6.20f) // row 4 (4)
        };
        for (int i = 0; i < 10; i++)
        {
            var pin = H.Prim(root, $"Pin_{i:00}", PrimitiveType.Capsule,
                new Vector3(pinXZ[i].x, 0.20f, pinXZ[i].y), new Vector3(0.13f, 0.20f, 0.13f), matPin);
            // Red stripe ring
            var stripe = H.Prim(pin, "Stripe", PrimitiveType.Cylinder, new Vector3(0, 0.55f, 0), new Vector3(1.05f, 0.05f, 1.05f), matPinStripe);
            H.StripCollider(stripe);
            var bp = H.EnsureComp<BowlingPin>(pin);
            bp.lane = lane;
            lane.pins.Add(bp);
        }

        // Pin reset light: spot fixture above pins, bulb disabled per oracle
        var prlGo = H.Empty(root, "PinResetLight", new Vector3(0, 3.5f, 6.0f));
        var fixture = H.Prim(prlGo, "Fixture", PrimitiveType.Cylinder, new Vector3(0, 0.0f, 0), new Vector3(0.30f, 0.10f, 0.30f), matBoard);
        H.StripCollider(fixture);
        var bulb = H.Prim(prlGo, "Bulb", PrimitiveType.Sphere, new Vector3(0, -0.15f, 0), new Vector3(0.18f, 0.18f, 0.18f), matBulb);
        H.StripCollider(bulb);
        bulb.SetActive(false);
        var prl = H.EnsureComp<PinResetLight>(prlGo);
        prl.lightBulb = bulb;

        // Playable test player on the approach behind the ball, facing the pins (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -4.5f), 0f);

        Debug.Log("[Bowling] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame BowlingSports/Print Oracle Summary")]
    public static void PrintSummary() => BowlingOracleRegistry.PrintSummary();
}
#endif
