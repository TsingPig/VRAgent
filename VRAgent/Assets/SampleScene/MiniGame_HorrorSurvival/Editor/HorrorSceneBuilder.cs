#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGameBuild;

/// <summary>
/// Abandoned hospital corridor: 8×12 m L-shape, peeling-wall material, cracked
/// tile floor, dim green fluorescent ceiling, gurney/IV-stand/wheelchair decor,
/// flashlight prop with disabled SpotLight LightCone child, battery on gurney,
/// 3 keys distributed, enemy capsule at z=+9 with disabled RedOverlay child.
/// </summary>
public static class HorrorSceneBuilder
{
    [MenuItem("Tools/MiniGame HorrorSurvival/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Horror_Root") ?? new GameObject("Horror_Root");
        root.transform.position = Vector3.zero;

        var matFloor   = H.Mat("HR_TileCracked",   new Color(0.30f, 0.32f, 0.30f), 0f, 0.30f);
        var matWall    = H.Mat("HR_WallPeeling",   new Color(0.40f, 0.42f, 0.36f), 0f, 0.10f);
        var matCeiling = H.Mat("HR_CeilingStained",new Color(0.30f, 0.32f, 0.28f), 0f, 0.10f);
        var matMetal   = H.Mat("HR_RustMetal",     new Color(0.40f, 0.30f, 0.22f), 0.6f, 0.40f);
        var matSteel   = H.Mat("HR_DullSteel",     new Color(0.45f, 0.45f, 0.45f), 0.7f, 0.55f);
        var matFlash   = H.Mat("HR_FlashlightBlk", new Color(0.05f, 0.05f, 0.05f), 0.5f, 0.55f);
        var matGreen   = H.Mat("HR_FluorGreen",    new Color(0.6f, 1.0f, 0.6f), 0f, 0.5f, new Color(0.4f, 0.9f, 0.4f));
        var matCone    = H.Mat("HR_LightCone",     new Color(1f, 0.95f, 0.7f, 0.4f), 0f, 0.9f, new Color(1.5f, 1.4f, 1.0f));
        var matEnemy   = H.Mat("HR_EnemyFlesh",    new Color(0.30f, 0.10f, 0.10f), 0f, 0.30f);
        var matRed     = H.Mat("HR_RedOverlay",    new Color(0.85f, 0.05f, 0.05f, 0.5f), 0f, 0.6f, new Color(1.5f, 0.0f, 0.0f));
        var matKey     = H.Mat("HR_KeyRust",       new Color(0.55f, 0.40f, 0.20f), 0.6f, 0.40f);
        var matBattery = H.Mat("HR_Battery",       new Color(0.10f, 0.50f, 0.20f), 0.4f, 0.55f);
        var matDoor    = H.Mat("HR_DoorRust",      new Color(0.35f, 0.20f, 0.15f), 0.4f, 0.30f);
        var matSheet   = H.Mat("HR_GurneySheet",   new Color(0.75f, 0.72f, 0.66f), 0f, 0.20f);

        H.Atmosphere(new Color(0.08f, 0.10f, 0.08f), 0.30f);

        // Main corridor: 4 m wide × 14 m long centered on z=4 (covers player at -2..enemy at z=9)
        H.BuildRoom(root, new Vector3(0, 0, 4), new Vector3(4f, 3f, 14f), matFloor, matWall, matCeiling);
        // Side branch (L-shape) at +X extending +X by 4m at z=6..10
        H.Prim(root, "Env_BranchFloor", PrimitiveType.Cube, new Vector3(3.5f, -0.05f, 8f), new Vector3(4f, 0.1f, 4f), matFloor);
        H.Prim(root, "Env_BranchCeiling", PrimitiveType.Cube, new Vector3(3.5f, 3.05f, 8f), new Vector3(4f, 0.1f, 4f), matCeiling);
        H.Prim(root, "Env_BranchWallN", PrimitiveType.Cube, new Vector3(3.5f, 1.5f, 10f), new Vector3(4f, 3f, 0.15f), matWall);
        H.Prim(root, "Env_BranchWallS", PrimitiveType.Cube, new Vector3(3.5f, 1.5f, 6f), new Vector3(4f, 3f, 0.15f), matWall);
        H.Prim(root, "Env_BranchWallE", PrimitiveType.Cube, new Vector3(5.5f, 1.5f, 8f), new Vector3(0.15f, 3f, 4f), matWall);

        // Dim green fluorescent ceiling lights (3 along corridor)
        for (int i = 0; i < 3; i++)
        {
            var fix = H.Prim(root, $"Env_FluorTube_{i}", PrimitiveType.Cube,
                new Vector3(0, 2.95f, -1 + i * 4f), new Vector3(1.4f, 0.10f, 0.20f), matGreen);
            H.StripCollider(fix);
            H.AddLight(fix, "Bulb", LightType.Point, Vector3.zero, new Color(0.6f, 1.0f, 0.6f), 0.6f, 5);
        }

        // Decor: gurney with sheet (battery sits on top)
        var gurney = H.Empty(root, "Decor_Gurney", new Vector3(-1.2f, 0.5f, 2.0f));
        H.Prim(gurney, "Frame", PrimitiveType.Cube, Vector3.zero, new Vector3(0.7f, 0.05f, 1.8f), matSteel);
        H.Prim(gurney, "Legs1", PrimitiveType.Cylinder, new Vector3(-0.30f, -0.25f, -0.80f), new Vector3(0.05f, 0.50f, 0.05f), matSteel);
        H.Prim(gurney, "Legs2", PrimitiveType.Cylinder, new Vector3( 0.30f, -0.25f, -0.80f), new Vector3(0.05f, 0.50f, 0.05f), matSteel);
        H.Prim(gurney, "Legs3", PrimitiveType.Cylinder, new Vector3(-0.30f, -0.25f,  0.80f), new Vector3(0.05f, 0.50f, 0.05f), matSteel);
        H.Prim(gurney, "Legs4", PrimitiveType.Cylinder, new Vector3( 0.30f, -0.25f,  0.80f), new Vector3(0.05f, 0.50f, 0.05f), matSteel);
        H.Prim(gurney, "Sheet", PrimitiveType.Cube, new Vector3(0, 0.04f, 0), new Vector3(0.65f, 0.04f, 1.7f), matSheet);

        // IV stand
        var iv = H.Empty(root, "Decor_IVStand", new Vector3(-1.6f, 0.0f, 3.5f));
        H.Prim(iv, "Pole", PrimitiveType.Cylinder, new Vector3(0, 0.9f, 0), new Vector3(0.04f, 0.9f, 0.04f), matSteel);
        H.Prim(iv, "Bag", PrimitiveType.Capsule, new Vector3(0.10f, 1.6f, 0), new Vector3(0.10f, 0.15f, 0.10f), matCone);
        H.Prim(iv, "Base", PrimitiveType.Cylinder, new Vector3(0, 0.02f, 0), new Vector3(0.30f, 0.04f, 0.30f), matSteel);

        // Wheelchair (in branch corridor)
        var wc = H.Empty(root, "Decor_Wheelchair", new Vector3(4.0f, 0.0f, 8.0f));
        H.Prim(wc, "Seat", PrimitiveType.Cube, new Vector3(0, 0.5f, 0), new Vector3(0.5f, 0.06f, 0.5f), matMetal);
        H.Prim(wc, "Back", PrimitiveType.Cube, new Vector3(0, 0.85f, -0.22f), new Vector3(0.5f, 0.7f, 0.05f), matMetal);
        H.Prim(wc, "WheelL", PrimitiveType.Cylinder, new Vector3(-0.30f, 0.30f, 0), new Vector3(0.55f, 0.04f, 0.55f), matSteel, new Vector3(0, 0, 90));
        H.Prim(wc, "WheelR", PrimitiveType.Cylinder, new Vector3( 0.30f, 0.30f, 0), new Vector3(0.55f, 0.04f, 0.55f), matSteel, new Vector3(0, 0, 90));

        // Controllers
        H.EnsureComp<HorrorStateController>(H.Empty(root, "StateController"));

        // Flashlight on gurney sheet (no AudioSource per oracle)
        var fl = H.Prim(root, "Flashlight", PrimitiveType.Cylinder, new Vector3(-1.1f, 0.62f, 1.6f), new Vector3(0.06f, 0.18f, 0.06f), matFlash, new Vector3(90, 0, 0));
        H.KinematicRb(fl);
        var flash = H.EnsureComp<FlashlightController>(fl);
        var coneGo = H.Empty(fl, "LightCone", new Vector3(0, 0.20f, 0));
        var coneVis = H.Prim(coneGo, "ConeMesh", PrimitiveType.Cylinder, new Vector3(0, 0.5f, 0), new Vector3(0.4f, 0.5f, 0.4f), matCone);
        H.StripCollider(coneVis);
        H.AddLight(coneGo, "SpotLight", LightType.Spot, Vector3.zero, new Color(1f, 0.95f, 0.7f), 4.0f, 8, 35f, new Vector3(-90, 0, 0));
        coneGo.SetActive(false);
        flash.lightCone = coneGo;

        // Battery on gurney
        var bat = H.Prim(root, "Battery", PrimitiveType.Cube, new Vector3(-1.3f, 0.62f, 1.4f), new Vector3(0.10f, 0.06f, 0.18f), matBattery);
        H.KinematicRb(bat);
        var battery = H.EnsureComp<BatteryItem>(bat);
        flash.battery = battery;

        // ExitDoor at +Z corridor end (z=10.9)
        var door = H.Prim(root, "ExitDoor", PrimitiveType.Cube, new Vector3(0, 1.10f, 10.90f), new Vector3(1.2f, 2.20f, 0.10f), matDoor);
        H.Prim(door, "Handle", PrimitiveType.Sphere, new Vector3(0.45f, 0, -0.06f), new Vector3(0.08f, 0.08f, 0.08f), matSteel);
        H.EnsureComp<DoorLockController>(door);

        // EnemyAI capsule at z=+9
        var enemy = H.Prim(root, "EnemyAI", PrimitiveType.Capsule, new Vector3(0.5f, 0.9f, 9.0f), new Vector3(0.6f, 0.9f, 0.6f), matEnemy);
        H.EnsureComp<EnemyAI>(enemy);
        // Enemy red highlight overlay (must NOT be the HealthSystem's RedOverlay, but an enemy decoration child)
        var enemyRed = H.Prim(enemy, "EnemyRedHalo", PrimitiveType.Capsule, Vector3.zero, new Vector3(1.05f, 1.05f, 1.05f), matRed);
        H.StripCollider(enemyRed);
        enemyRed.SetActive(false);

        // HealthSystem (logical) with RedOverlay disabled child (UI placeholder quad)
        var hpGo = H.Empty(root, "HealthSystem", new Vector3(0, 1.7f, -1.5f));
        var hp = H.EnsureComp<HealthSystem>(hpGo);
        var red = H.Prim(hpGo, "RedOverlay", PrimitiveType.Quad, new Vector3(0, 0, 0.3f), new Vector3(2.0f, 1.2f, 1f), matRed);
        H.StripCollider(red);
        red.SetActive(false);
        hp.redBarOverlay = red;

        // 3 keys: 1 on desk-area floor, 1 in branch, 1 by enemy
        Vector3[] keyPos = { new Vector3(-1.6f, 0.05f, 4.5f), new Vector3(4.5f, 0.05f, 9.0f), new Vector3(0.8f, 0.05f, 8.5f) };
        for (int i = 0; i < 3; i++)
        {
            var k = H.Prim(root, $"Key_{i:00}", PrimitiveType.Cube, keyPos[i], new Vector3(0.06f, 0.02f, 0.20f), matKey);
            H.KinematicRb(k);
            H.EnsureComp<KeyItem>(k);
        }

        // Playable test player at the corridor entrance, facing the enemy (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -2.5f), 0f);

        Debug.Log("[Horror] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame HorrorSurvival/Print Oracle Summary")]
    public static void PrintSummary() => HorrorOracleRegistry.PrintSummary();
}
#endif
