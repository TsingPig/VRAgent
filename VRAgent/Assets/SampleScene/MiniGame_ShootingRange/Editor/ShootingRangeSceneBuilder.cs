#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGameBuild;

/// <summary>
/// Builds MiniGame_ShootingRange with full visuals: indoor range, floor + walls
/// + ceiling + lighting, side table, control panel, 5 numbered targets on stands,
/// pistol with muzzle flash. Controllers are bound by name.
/// </summary>
public static class ShootingRangeSceneBuilder
{
    [MenuItem("Tools/MiniGame ShootingRange/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("ShootingRange_Root") ?? new GameObject("ShootingRange_Root");
        root.transform.position = Vector3.zero;

        var matFloor   = H.Mat("SR_FloorConcrete", new Color(0.45f, 0.45f, 0.47f), 0.1f, 0.2f);
        var matWall    = H.Mat("SR_Drywall",       new Color(0.78f, 0.74f, 0.65f), 0.0f, 0.15f);
        var matCeiling = H.Mat("SR_Ceiling",       new Color(0.86f, 0.86f, 0.88f), 0.0f, 0.10f);
        var matLane    = H.Mat("SR_RedLane",       new Color(0.62f, 0.12f, 0.12f), 0.0f, 0.40f);
        var matTable   = H.Mat("SR_Table",         new Color(0.30f, 0.20f, 0.12f), 0.0f, 0.30f);
        var matPanel   = H.Mat("SR_PanelDark",     new Color(0.12f, 0.12f, 0.14f), 0.6f, 0.40f);
        var matScreen  = H.Mat("SR_Screen",        new Color(0.05f, 0.55f, 0.85f), 0f, 0.9f, new Color(0.0f, 1.0f, 1.5f));
        var matGun     = H.Mat("SR_GunMetal",      new Color(0.18f, 0.18f, 0.20f), 0.85f, 0.55f);
        var matMag     = H.Mat("SR_Magazine",      new Color(0.10f, 0.10f, 0.12f), 0.7f, 0.40f);
        var matFlash   = H.Mat("SR_FlashYellow",   Color.yellow, 0f, 0.9f, new Color(2f, 1.6f, 0.2f));
        var matTarget  = H.Mat("SR_Target",        new Color(0.93f, 0.93f, 0.93f), 0f, 0.20f);
        var matRing    = H.Mat("SR_TargetRing",    new Color(0.85f, 0.10f, 0.10f), 0f, 0.30f);
        var matStand   = H.Mat("SR_Stand",         new Color(0.30f, 0.30f, 0.32f), 0.5f, 0.40f);

        H.Atmosphere(new Color(0.45f, 0.46f, 0.50f), 0.9f);
        H.BuildRoom(root, new Vector3(0, 0, 4), new Vector3(12, 4, 16), matFloor, matWall, matCeiling);

        // Red lane carpet
        H.Prim(root, "Env_LaneCarpet", PrimitiveType.Cube, new Vector3(0, 0.005f, 4), new Vector3(2.4f, 0.02f, 14), matLane);

        // 4 ceiling lights
        for (int i = 0; i < 4; i++)
            H.AddLight(root, $"Env_CeilLight_{i}", LightType.Point,
                new Vector3(0, 3.6f, -2 + i * 4f), new Color(1f, 0.96f, 0.85f), 1.6f, 12);

        // Side table
        H.Prim(root, "SideTable", PrimitiveType.Cube, new Vector3(-1.4f, 0.45f, -2.5f), new Vector3(1.6f, 0.9f, 0.7f), matTable);

        // Control panel + emissive screen
        var panel = H.Prim(root, "ControlPanel", PrimitiveType.Cube, new Vector3(2.4f, 1.1f, -2f), new Vector3(0.9f, 1.4f, 0.25f), matPanel);
        H.Prim(panel, "Screen", PrimitiveType.Quad, new Vector3(0, 0.15f, -0.51f), new Vector3(0.7f, 0.45f, 1f), matScreen, new Vector3(0, 180f, 0));

        // Controllers
        var stateGo = H.Empty(root, "StateController");
        H.EnsureComp<ShootingRangeStateController>(stateGo).TargetsRequired = 5;
        H.EnsureComp<ScoreManager>(H.Empty(root, "ScoreManager"));

        H.Prim(root, "PowerSwitch", PrimitiveType.Cube, new Vector3(-3, 1.2f, -2), new Vector3(0.15f, 0.25f, 0.05f), matPanel);

        // Pistol
        var weaponGo = H.Prim(root, "Pistol", PrimitiveType.Cube, new Vector3(-1f, 0.95f, -2.5f), new Vector3(0.18f, 0.14f, 0.32f), matGun);
        H.KinematicRb(weaponGo);
        var weapon = H.EnsureComp<WeaponController>(weaponGo);
        var muzzle = H.Empty(weaponGo, "MuzzlePoint", new Vector3(0, 0, 0.55f));
        weapon.muzzlePoint = muzzle.transform;

        // Magazine
        var magGo = H.Prim(root, "Magazine", PrimitiveType.Cube, new Vector3(-1.7f, 0.95f, -2.5f), new Vector3(0.12f, 0.18f, 0.10f), matMag);
        H.KinematicRb(magGo);
        weapon.magazine = H.EnsureComp<AmmoMagazine>(magGo);

        // Muzzle flash (top-level for naming contract; positioned near weapon)
        var flashGo = H.Empty(root, "MuzzleFlash", new Vector3(-1f, 0.95f, -2.0f));
        var flash = H.EnsureComp<MuzzleFlashController>(flashGo);
        var flashQuad = H.Prim(flashGo, "FlashQuad", PrimitiveType.Quad, Vector3.zero, new Vector3(0.25f, 0.25f, 1f), matFlash);
        H.StripCollider(flashQuad);
        flashQuad.SetActive(false);
        flash.flashQuad = flashQuad;
        weapon.muzzleFlash = flash;

        // 5 targets at z=8 with stands
        var waveGo = H.Empty(root, "WaveSpawner");
        var wave = H.EnsureComp<WaveSpawner>(waveGo);
        wave.targets.Clear();
        for (int i = 0; i < 5; i++)
        {
            float x = -3.2f + i * 1.6f;
            H.Prim(root, $"TargetStand_{i:00}", PrimitiveType.Cylinder, new Vector3(x, 0.6f, 8f), new Vector3(0.08f, 0.6f, 0.08f), matStand);
            var tGo = H.Prim(root, $"Target_{i:00}", PrimitiveType.Cylinder, new Vector3(x, 1.4f, 8f), new Vector3(0.55f, 0.05f, 0.55f), matTarget, new Vector3(90f, 0, 0));
            var ring = H.Prim(tGo, "RedRing", PrimitiveType.Cylinder, new Vector3(0, -0.05f, 0), new Vector3(0.7f, 0.04f, 0.7f), matRing);
            H.StripCollider(ring);
            wave.targets.Add(H.EnsureComp<TargetController>(tGo));
        }

        // Playable test player at the firing line, facing the targets (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -2.8f), 0f);

        Debug.Log("[ShootingRange] Scene built. Save scene with File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame ShootingRange/Print Oracle Summary")]
    public static void PrintOracleSummary() => ShootingRangeOracleRegistry.PrintSummary();
}
#endif
