#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGame.EscapeRoom;
using MiniGameBuild;

/// <summary>
/// Victorian study escape room: 5×5 m parquet floor, dark wood walls, brass
/// CombinationLock on -X wall, KeySafe on +X wall, ExitDoor on +Z wall.
/// Warm 2700K chandelier (point light), bookshelf/desk/armchair/rug decor.
/// HintLight bulb starts ON; oracle bug-007 toggles it (default visible).
/// </summary>
public static class EscapeRoomSceneBuilder
{
    [MenuItem("Tools/MiniGame EscapeRoom/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("EscapeRoom_Root") ?? new GameObject("EscapeRoom_Root");
        root.transform.position = Vector3.zero;

        var matFloor   = H.Mat("ER_Parquet",      new Color(0.42f, 0.26f, 0.14f), 0f, 0.55f);
        var matWall    = H.Mat("ER_DarkWoodWall", new Color(0.22f, 0.14f, 0.10f), 0f, 0.30f);
        var matCeiling = H.Mat("ER_Plaster",      new Color(0.85f, 0.80f, 0.70f), 0f, 0.10f);
        var matRug     = H.Mat("ER_RugRed",       new Color(0.55f, 0.10f, 0.12f), 0f, 0.20f);
        var matBrass   = H.Mat("ER_Brass",        new Color(0.85f, 0.70f, 0.30f), 0.85f, 0.70f, new Color(0.05f, 0.04f, 0.0f));
        var matSafe    = H.Mat("ER_SafeMetal",    new Color(0.18f, 0.18f, 0.18f), 0.7f, 0.55f);
        var matDoor    = H.Mat("ER_DoorWood",     new Color(0.30f, 0.18f, 0.10f), 0.1f, 0.40f);
        var matKey     = H.Mat("ER_KeyGold",      new Color(0.95f, 0.78f, 0.30f), 0.95f, 0.85f, new Color(0.10f, 0.07f, 0.0f));
        var matBulb    = H.Mat("ER_BulbWarm",     new Color(1f, 0.9f, 0.7f), 0f, 0.5f, new Color(2.0f, 1.6f, 0.9f));
        var matBook    = H.Mat("ER_BookshelfWood",new Color(0.28f, 0.16f, 0.10f), 0f, 0.4f);
        var matBookA   = H.Mat("ER_BookRed",      new Color(0.55f, 0.10f, 0.10f), 0f, 0.4f);
        var matBookB   = H.Mat("ER_BookGreen",    new Color(0.10f, 0.40f, 0.20f), 0f, 0.4f);
        var matBookC   = H.Mat("ER_BookBlue",     new Color(0.10f, 0.20f, 0.55f), 0f, 0.4f);
        var matDesk    = H.Mat("ER_DeskMahogany", new Color(0.35f, 0.18f, 0.12f), 0.1f, 0.55f);
        var matChair   = H.Mat("ER_ChairLeather", new Color(0.20f, 0.10f, 0.08f), 0f, 0.40f);
        var matPanel   = H.Mat("ER_PanelDark",    new Color(0.10f, 0.10f, 0.12f), 0.5f, 0.5f);

        H.Atmosphere(new Color(0.18f, 0.14f, 0.10f), 0.5f);
        H.BuildRoom(root, new Vector3(0, 0, 0), new Vector3(5, 3, 5), matFloor, matWall, matCeiling);

        // Rug
        H.Prim(root, "Decor_Rug", PrimitiveType.Cube, new Vector3(0, 0.01f, 0), new Vector3(3.0f, 0.02f, 2.0f), matRug);

        // Bookshelf on +X back-corner area
        var shelf = H.Prim(root, "Decor_Bookshelf", PrimitiveType.Cube, new Vector3(2.20f, 1.20f, -1.5f), new Vector3(0.30f, 2.4f, 1.6f), matBook);
        for (int s = 0; s < 4; s++)
        {
            H.Prim(shelf, $"Books_Row{s}_A", PrimitiveType.Cube, new Vector3(-0.6f, -0.9f + s * 0.6f, -0.5f), new Vector3(2.0f, 0.04f, 1.4f), matBook);
            H.Prim(shelf, $"Books_Row{s}_R", PrimitiveType.Cube, new Vector3(-0.6f, -0.7f + s * 0.6f, -0.3f), new Vector3(1.6f, 0.30f, 0.20f), matBookA);
            H.Prim(shelf, $"Books_Row{s}_G", PrimitiveType.Cube, new Vector3(-0.6f, -0.7f + s * 0.6f,  0.0f), new Vector3(1.6f, 0.30f, 0.20f), matBookB);
            H.Prim(shelf, $"Books_Row{s}_B", PrimitiveType.Cube, new Vector3(-0.6f, -0.7f + s * 0.6f,  0.3f), new Vector3(1.6f, 0.30f, 0.20f), matBookC);
        }

        // Desk + armchair on -X side
        H.Prim(root, "Decor_Desk", PrimitiveType.Cube, new Vector3(-1.6f, 0.40f, 1.5f), new Vector3(1.4f, 0.80f, 0.7f), matDesk);
        H.Prim(root, "Decor_Armchair", PrimitiveType.Cube, new Vector3(-1.5f, 0.45f, 0.5f), new Vector3(0.8f, 0.9f, 0.8f), matChair);

        // Chandelier (warm point light at ceiling center)
        var chandStem = H.Prim(root, "Decor_Chandelier", PrimitiveType.Cylinder, new Vector3(0, 2.6f, 0), new Vector3(0.05f, 0.20f, 0.05f), matBrass);
        H.StripCollider(chandStem);
        var chandBulb = H.Prim(chandStem, "Bulb", PrimitiveType.Sphere, new Vector3(0, -0.6f, 0), new Vector3(0.20f, 0.20f, 0.20f), matBulb);
        H.StripCollider(chandBulb);
        H.AddLight(chandStem, "PointLight", LightType.Point, new Vector3(0, -0.6f, 0), new Color(1f, 0.85f, 0.65f), 1.6f, 8);

        // Controllers
        H.EnsureComp<EscapeRoomStateController>(H.Empty(root, "StateController"));

        // CombinationLock on -X wall, brass
        var combo = H.Prim(root, "CombinationLock", PrimitiveType.Cube, new Vector3(-2.40f, 1.4f, -0.3f), new Vector3(0.30f, 0.40f, 0.25f), matBrass);
        H.Prim(combo, "Dial", PrimitiveType.Cylinder, new Vector3(0, 0, -0.16f), new Vector3(0.18f, 0.04f, 0.18f), matBrass, new Vector3(90, 0, 0));
        var clComp = H.EnsureComp<CombinationLock>(combo); clComp.correctDigit = 7;

        // KeySafe on +X wall (steel box)
        var safe = H.Prim(root, "KeySafe", PrimitiveType.Cube, new Vector3(2.40f, 1.20f, 0.8f), new Vector3(0.20f, 0.50f, 0.50f), matSafe);
        H.Prim(safe, "Handle", PrimitiveType.Cylinder, new Vector3(-0.12f, 0.0f, 0.10f), new Vector3(0.06f, 0.10f, 0.06f), matBrass, new Vector3(0, 0, 90));
        var safeComp = H.EnsureComp<KeySafeController>(safe); safeComp.combo = clComp;

        // Key (gold, on the desk)
        var key = H.Prim(root, "Key", PrimitiveType.Cube, new Vector3(-1.6f, 0.85f, 1.5f), new Vector3(0.06f, 0.02f, 0.20f), matKey);
        H.KinematicRb(key);
        H.EnsureComp<KeyController>(key);

        // ExitDoor on +Z wall (centered, taller)
        var door = H.Prim(root, "ExitDoor", PrimitiveType.Cube, new Vector3(0, 1.10f, 2.45f), new Vector3(1.0f, 2.20f, 0.10f), matDoor);
        H.Prim(door, "Handle", PrimitiveType.Sphere, new Vector3(0.40f, 0, -0.06f), new Vector3(0.08f, 0.08f, 0.08f), matBrass);
        H.EnsureComp<DoorController>(door);

        // HintLight (small wall sconce above CombinationLock); bulb visible by default
        var hintGo = H.Empty(root, "HintLight", new Vector3(-2.40f, 2.1f, -0.3f));
        var hintFix = H.Prim(hintGo, "Fixture", PrimitiveType.Cube, Vector3.zero, new Vector3(0.18f, 0.10f, 0.20f), matBrass);
        H.StripCollider(hintFix);
        var hintBulb = H.Prim(hintGo, "Bulb", PrimitiveType.Sphere, new Vector3(0, -0.10f, 0), new Vector3(0.10f, 0.10f, 0.10f), matBulb);
        H.StripCollider(hintBulb);
        hintBulb.SetActive(true);
        var hint = H.EnsureComp<HintLight>(hintGo); hint.lightBulb = hintBulb;

        // Puzzle panel near desk (red emissive label)
        var puzzle = H.Prim(root, "PuzzlePanel", PrimitiveType.Cube, new Vector3(-1.6f, 1.30f, 1.85f), new Vector3(0.6f, 0.8f, 0.05f), matPanel);
        H.Prim(puzzle, "ColorLabel", PrimitiveType.Quad, new Vector3(0, 0, -0.03f), new Vector3(0.5f, 0.5f, 1f),
            H.Mat("ER_PuzzleRed", new Color(0.7f, 0.1f, 0.1f), 0f, 0.7f, new Color(1.5f, 0.2f, 0.2f)), new Vector3(0, 180f, 0));
        var pp = H.EnsureComp<PuzzlePanelController>(puzzle); pp.correctAnswer = "RED";

        // Playable test player in the centre, facing the exit door (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -1.5f), 0f);

        Debug.Log("[EscapeRoom] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame EscapeRoom/Print Oracle Summary")]
    public static void PrintSummary() => EscapeRoomOracleRegistry.PrintSummary();
}
#endif
