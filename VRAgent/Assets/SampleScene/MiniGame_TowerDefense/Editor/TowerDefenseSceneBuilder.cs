#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGame.TowerDefense;
using MiniGameBuild;

/// <summary>
/// Tower defense map: 12×12 m grass field with stone path winding from gate
/// (+Z, z=+5.5) to balcony (-Z, z=-5.5). 4 towers (cylinder + sphere top, mix
/// stone-gray and wood-brown) flanking path. 3 enemy capsules (green) marching
/// at z=+4 with disabled RedHP child quads. WaveSpawner gate. ResourceManager
/// gold panel on balcony rail. TowerPlacer hand tool at player position.
/// </summary>
public static class TowerDefenseSceneBuilder
{
    [MenuItem("Tools/MiniGame TowerDefense/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("TowerDefense_Root") ?? new GameObject("TowerDefense_Root");
        root.transform.position = Vector3.zero;

        var matGrass    = H.Mat("TD_Grass",         new Color(0.30f, 0.55f, 0.20f), 0f, 0.20f);
        var matPath     = H.Mat("TD_StonePath",     new Color(0.60f, 0.55f, 0.50f), 0f, 0.30f);
        var matSky      = H.Mat("TD_SkyBackdrop",   new Color(0.50f, 0.70f, 0.85f), 0f, 0.10f);
        var matTowerStn = H.Mat("TD_TowerStone",    new Color(0.55f, 0.55f, 0.55f), 0.1f, 0.40f);
        var matTowerWd  = H.Mat("TD_TowerWood",     new Color(0.55f, 0.30f, 0.15f), 0.1f, 0.45f);
        var matTowerTop = H.Mat("TD_TowerTopBlue",  new Color(0.10f, 0.35f, 0.65f), 0.3f, 0.60f);
        var matEnemy    = H.Mat("TD_EnemyGreen",    new Color(0.20f, 0.65f, 0.20f), 0f, 0.40f);
        var matRed      = H.Mat("TD_EnemyRed",      new Color(0.85f, 0.05f, 0.05f, 0.6f), 0f, 0.7f, new Color(1.5f, 0.0f, 0.0f));
        var matGate     = H.Mat("TD_Gate",          new Color(0.30f, 0.20f, 0.10f), 0.2f, 0.40f);
        var matBalc     = H.Mat("TD_BalconyStone",  new Color(0.65f, 0.60f, 0.55f), 0f, 0.30f);
        var matRail     = H.Mat("TD_Rail",          new Color(0.30f, 0.30f, 0.30f), 0.7f, 0.55f);
        var matResPan   = H.Mat("TD_ResPanel",      new Color(0.10f, 0.10f, 0.12f), 0.6f, 0.5f);
        var matGold     = H.Mat("TD_Gold",          new Color(1f, 0.85f, 0.30f), 0.9f, 0.85f, new Color(0.8f, 0.6f, 0.1f));
        var matPlacer   = H.Mat("TD_Placer",        new Color(0.20f, 0.55f, 0.95f), 0.4f, 0.6f, new Color(0.0f, 0.4f, 1.4f));

        H.Atmosphere(new Color(0.45f, 0.50f, 0.55f), 1.0f);

        // 12×12 grass field (open sky)
        H.Prim(root, "Env_Ground", PrimitiveType.Cube, new Vector3(0, -0.05f, 0), new Vector3(12f, 0.10f, 12f), matGrass);

        // Stone path winding from +Z gate to -Z balcony (3 segments forming an S)
        H.Prim(root, "Env_PathSeg_A", PrimitiveType.Cube, new Vector3(-1.5f, 0.005f,  4f), new Vector3(1.4f, 0.02f, 4f), matPath);
        H.Prim(root, "Env_PathSeg_B", PrimitiveType.Cube, new Vector3( 0.0f, 0.005f,  1f), new Vector3(4.4f, 0.02f, 1.4f), matPath);
        H.Prim(root, "Env_PathSeg_C", PrimitiveType.Cube, new Vector3( 1.5f, 0.005f, -2f), new Vector3(1.4f, 0.02f, 5f), matPath);

        // Sun
        H.AddLight(root, "Env_Sun", LightType.Directional, new Vector3(0, 10, 0), new Color(1f, 0.96f, 0.85f), 1.2f, 50, 0, new Vector3(50, -30, 0));

        // Distant sky backdrop
        H.Prim(root, "Env_SkyBackdrop", PrimitiveType.Cube, new Vector3(0, 6f, 6.05f), new Vector3(12f, 12f, 0.05f), matSky);

        // Gate at +Z
        var gate = H.Empty(root, "Env_GateArch", new Vector3(-1.5f, 0, 5.8f));
        H.Prim(gate, "PostL", PrimitiveType.Cube, new Vector3(-1.0f, 1.2f, 0), new Vector3(0.30f, 2.4f, 0.30f), matGate);
        H.Prim(gate, "PostR", PrimitiveType.Cube, new Vector3( 1.0f, 1.2f, 0), new Vector3(0.30f, 2.4f, 0.30f), matGate);
        H.Prim(gate, "Top",   PrimitiveType.Cube, new Vector3( 0.0f, 2.5f, 0), new Vector3(2.2f, 0.30f, 0.30f), matGate);

        // Balcony at -Z (raised platform)
        var balc = H.Empty(root, "Env_Balcony", new Vector3(0, 0, -5.5f));
        H.Prim(balc, "Floor", PrimitiveType.Cube, new Vector3(0, 0.20f, 0), new Vector3(6.0f, 0.20f, 1.6f), matBalc);
        H.Prim(balc, "Rail",  PrimitiveType.Cube, new Vector3(0, 0.85f, 0.7f), new Vector3(6.0f, 0.10f, 0.10f), matRail);
        H.Prim(balc, "RailPostL", PrimitiveType.Cube, new Vector3(-2.5f, 0.55f, 0.7f), new Vector3(0.10f, 0.7f, 0.10f), matRail);
        H.Prim(balc, "RailPostC", PrimitiveType.Cube, new Vector3( 0.0f, 0.55f, 0.7f), new Vector3(0.10f, 0.7f, 0.10f), matRail);
        H.Prim(balc, "RailPostR", PrimitiveType.Cube, new Vector3( 2.5f, 0.55f, 0.7f), new Vector3(0.10f, 0.7f, 0.10f), matRail);

        // Controllers
        H.EnsureComp<TowerDefenseStateController>(H.Empty(root, "StateController"));

        // ResourceManager — gold panel on balcony rail
        var res = H.Prim(root, "ResourceManager", PrimitiveType.Cube, new Vector3(0, 1.30f, -4.7f), new Vector3(1.0f, 0.50f, 0.10f), matResPan);
        var gold = H.Prim(res, "GoldIcon", PrimitiveType.Cylinder, new Vector3(-0.30f, 0, -0.06f), new Vector3(0.20f, 0.04f, 0.20f), matGold, new Vector3(90, 0, 0));
        H.StripCollider(gold);
        H.EnsureComp<ResourceManager>(res);

        // TowerPlacer (blue hand tool, kinematic, on balcony)
        var placer = H.Prim(root, "TowerPlacer", PrimitiveType.Cube, new Vector3(-0.5f, 1.0f, -4.8f), new Vector3(0.18f, 0.14f, 0.30f), matPlacer);
        H.KinematicRb(placer);
        H.EnsureComp<TowerPlacer>(placer);

        // 4 towers flanking path (alternating stone/wood)
        Vector3[] towerPos = {
            new Vector3(-3.0f, 0, 4.0f),
            new Vector3( 3.0f, 0, 1.0f),
            new Vector3(-3.0f, 0,-1.5f),
            new Vector3( 3.5f, 0,-3.5f),
        };
        Material[] towerMats = { matTowerStn, matTowerWd, matTowerStn, matTowerWd };
        for (int i = 0; i < 4; i++)
        {
            var t = H.Empty(root, $"Tower_{i:00}", towerPos[i]);
            // Base
            H.Prim(t, "Base", PrimitiveType.Cylinder, new Vector3(0, 0.40f, 0), new Vector3(0.80f, 0.40f, 0.80f), towerMats[i]);
            // Shaft
            H.Prim(t, "Shaft", PrimitiveType.Cylinder, new Vector3(0, 1.30f, 0), new Vector3(0.55f, 0.50f, 0.55f), towerMats[i]);
            // Cannon top (sphere)
            H.Prim(t, "Top", PrimitiveType.Sphere, new Vector3(0, 1.95f, 0), new Vector3(0.55f, 0.55f, 0.55f), matTowerTop);
            // Barrel
            H.Prim(t, "Barrel", PrimitiveType.Cylinder, new Vector3(0, 1.95f, 0.40f), new Vector3(0.12f, 0.30f, 0.12f), matTowerTop, new Vector3(90, 0, 0));
            // Add Tower component on the root tower object itself (with collider)
            var col = H.EnsureComp<BoxCollider>(t);
            col.center = new Vector3(0, 1.0f, 0);
            col.size = new Vector3(0.9f, 2.2f, 0.9f);
            H.EnsureComp<Tower>(t);
        }

        // WaveSpawner — invisible logic node at gate
        var ws = H.Empty(root, "WaveSpawner", new Vector3(-1.5f, 0.5f, 5.8f));
        H.EnsureComp<WaveSpawner>(ws);

        // 3 enemy capsules marching along path at z=4
        Vector3[] enemyPos = {
            new Vector3(-1.5f, 0.5f, 4.5f),
            new Vector3(-1.5f, 0.5f, 3.5f),
            new Vector3(-1.5f, 0.5f, 2.5f),
        };
        for (int i = 0; i < 3; i++)
        {
            var e = H.Prim(root, $"Enemy_{i:00}", PrimitiveType.Capsule, enemyPos[i], new Vector3(0.5f, 0.5f, 0.5f), matEnemy);
            var ec = H.EnsureComp<EnemyController>(e);
            // RedHP overlay quad (faces camera direction, disabled)
            var red = H.Prim(e, "RedHP", PrimitiveType.Quad, new Vector3(0, 1.4f, 0), new Vector3(0.6f, 0.10f, 1f), matRed, new Vector3(0, 180f, 0));
            H.StripCollider(red);
            red.SetActive(false);
            ec.redHealthOverlay = red;
        }

        // Playable test player on the balcony, facing the gate (+Z)
        H.BuildPlayer(root, new Vector3(0.5f, 0.40f, -4.6f), 0f);

        Debug.Log("[TowerDefense] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame TowerDefense/Print Oracle Summary")]
    public static void PrintSummary() => TowerDefenseOracleRegistry.PrintSummary();
}
#endif
