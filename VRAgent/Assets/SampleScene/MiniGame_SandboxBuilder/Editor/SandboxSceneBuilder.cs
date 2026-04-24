#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGameBuild;

/// <summary>
/// Outdoor sandbox: 16×16 m grass field with stone grid lines, 6 colored 1m³
/// material blocks (stone/wood/glass/grass/brick/sand) on a side rack, Toolbox
/// panel with 6 slots, SaveLoad terminal with green emissive screen, BlockPlacer
/// gun, HighlightOutline yellow wireframe (mesh disabled).
/// </summary>
public static class SandboxSceneBuilder
{
    [MenuItem("Tools/MiniGame SandboxBuilder/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("Sandbox_Root") ?? new GameObject("Sandbox_Root");
        root.transform.position = Vector3.zero;

        var matGrass   = H.Mat("SB_Grass",        new Color(0.30f, 0.55f, 0.20f), 0f, 0.20f);
        var matStone   = H.Mat("SB_StoneLine",    new Color(0.55f, 0.55f, 0.55f), 0f, 0.30f);
        var matSky     = H.Mat("SB_SkyBlue",      new Color(0.55f, 0.75f, 0.90f), 0f, 0.10f);
        var matBlkStn  = H.Mat("SB_BlockStone",   new Color(0.55f, 0.55f, 0.55f), 0f, 0.30f);
        var matBlkWd   = H.Mat("SB_BlockWood",    new Color(0.55f, 0.35f, 0.18f), 0f, 0.40f);
        var matBlkGl   = H.Mat("SB_BlockGlass",   new Color(0.6f, 0.85f, 0.95f, 0.6f), 0.1f, 0.95f);
        var matBlkGr   = H.Mat("SB_BlockGrass",   new Color(0.30f, 0.65f, 0.20f), 0f, 0.30f);
        var matBlkBr   = H.Mat("SB_BlockBrick",   new Color(0.65f, 0.25f, 0.18f), 0f, 0.40f);
        var matBlkSd   = H.Mat("SB_BlockSand",    new Color(0.85f, 0.78f, 0.55f), 0f, 0.30f);
        var matRack    = H.Mat("SB_Rack",         new Color(0.30f, 0.30f, 0.32f), 0.7f, 0.55f);
        var matPanel   = H.Mat("SB_Panel",        new Color(0.10f, 0.10f, 0.12f), 0.6f, 0.5f);
        var matSlot    = H.Mat("SB_Slot",         new Color(0.20f, 0.20f, 0.25f), 0.4f, 0.5f);
        var matTerm    = H.Mat("SB_Terminal",     new Color(0.18f, 0.18f, 0.20f), 0.5f, 0.5f);
        var matScreenG = H.Mat("SB_TermScreenGr", new Color(0.05f, 0.10f, 0.05f), 0f, 0.9f, new Color(0.0f, 1.4f, 0.3f));
        var matPlacer  = H.Mat("SB_PlacerOrange", new Color(0.95f, 0.45f, 0.10f), 0.4f, 0.55f, new Color(0.5f, 0.2f, 0.0f));
        var matOutline = H.Mat("SB_OutlineYellow",new Color(1f, 1f, 0.0f, 0.5f), 0f, 0.9f, new Color(1.5f, 1.5f, 0.0f));

        H.Atmosphere(new Color(0.50f, 0.55f, 0.60f), 1.1f);

        // 16×16 m grass field, no walls/ceiling — open sky
        H.Prim(root, "Env_Ground", PrimitiveType.Cube, new Vector3(0, -0.05f, 0), new Vector3(16f, 0.10f, 16f), matGrass);

        // Sky dome (large inverted sphere — visual only). Use cube backdrop instead for simplicity:
        H.Prim(root, "Env_SkyBackdrop_N", PrimitiveType.Cube, new Vector3(0, 8f, 8.05f), new Vector3(16f, 16f, 0.05f), matSky);

        // Stone grid lines every 2 m (X and Z)
        for (int i = -3; i <= 3; i++)
        {
            H.Prim(root, $"Env_GridX_{i}", PrimitiveType.Cube, new Vector3(i * 2f, 0.005f, 0), new Vector3(0.04f, 0.01f, 16f), matStone);
            H.Prim(root, $"Env_GridZ_{i}", PrimitiveType.Cube, new Vector3(0, 0.005f, i * 2f), new Vector3(16f, 0.01f, 0.04f), matStone);
        }

        // Sun (directional) for outdoor look
        H.AddLight(root, "Env_Sun", LightType.Directional, new Vector3(0, 10, 0), new Color(1f, 0.95f, 0.85f), 1.2f, 50, 0, new Vector3(50, -30, 0));

        // Controllers
        H.EnsureComp<SandboxStateController>(H.Empty(root, "StateController"));

        // BlockPlacer (orange ray gun) at player position
        var placer = H.Prim(root, "BlockPlacer", PrimitiveType.Cube, new Vector3(-0.3f, 1.0f, -1.5f), new Vector3(0.18f, 0.14f, 0.40f), matPlacer);
        H.KinematicRb(placer);
        H.Prim(placer, "Barrel", PrimitiveType.Cylinder, new Vector3(0, 0, 0.30f), new Vector3(0.05f, 0.10f, 0.05f), matStone, new Vector3(90, 0, 0));
        H.EnsureComp<BlockPlacer>(placer);

        // 6 colored 1m³ blocks lined up on a rack (z=2..7, x=-6 wall side)
        Material[] blkMats = { matBlkStn, matBlkWd, matBlkGl, matBlkGr, matBlkBr, matBlkSd };
        // Rack
        H.Prim(root, "Decor_BlockRack", PrimitiveType.Cube, new Vector3(-6f, 0.5f, 4.5f), new Vector3(1.4f, 1.0f, 7.0f), matRack);
        for (int i = 0; i < 6; i++)
        {
            var b = H.Prim(root, $"Block_{i:00}", PrimitiveType.Cube,
                new Vector3(-6f, 1.5f, 1.5f + i * 1.2f), new Vector3(1.0f, 1.0f, 1.0f), blkMats[i]);
            H.KinematicRb(b);
            H.EnsureComp<BuildingBlock>(b);
        }

        // Toolbox panel (6 slots) on +X wall area, mounted on a stand
        var tbStand = H.Prim(root, "Decor_ToolboxStand", PrimitiveType.Cube, new Vector3(5.5f, 0.6f, -1.5f), new Vector3(0.20f, 1.2f, 1.0f), matRack);
        var tb = H.Prim(root, "Toolbox", PrimitiveType.Cube, new Vector3(5.4f, 1.30f, -1.5f), new Vector3(0.10f, 0.7f, 1.4f), matPanel);
        for (int s = 0; s < 6; s++)
        {
            var slot = H.Prim(tb, $"Slot_{s}", PrimitiveType.Cube, new Vector3(-0.06f, 0.0f, -0.55f + s * 0.22f), new Vector3(1.0f, 0.6f, 0.18f), matSlot);
            H.StripCollider(slot);
            // mini cube preview inside slot, colored after the matching block
            var preview = H.Prim(slot, "Preview", PrimitiveType.Cube, new Vector3(0, 0, 0.0f), new Vector3(0.3f, 0.45f, 0.3f), blkMats[s]);
            H.StripCollider(preview);
        }
        H.EnsureComp<ToolboxController>(tb);

        // SaveLoad terminal at +Z
        var term = H.Prim(root, "SaveLoad", PrimitiveType.Cube, new Vector3(2.5f, 0.7f, 5.0f), new Vector3(0.7f, 1.4f, 0.4f), matTerm);
        var screen = H.Prim(term, "Screen", PrimitiveType.Quad, new Vector3(0, 0.20f, -0.21f), new Vector3(0.55f, 0.40f, 1f), matScreenG, new Vector3(0, 180f, 0));
        H.StripCollider(screen);
        H.EnsureComp<SaveLoadController>(term);

        // HighlightOutline (logical) with disabled wireframe child
        var hlGo = H.Empty(root, "HighlightOutline", new Vector3(0, 0.6f, 0));
        var mesh = H.Prim(hlGo, "OutlineMesh", PrimitiveType.Cube, Vector3.zero, new Vector3(1.05f, 1.05f, 1.05f), matOutline);
        H.StripCollider(mesh);
        mesh.SetActive(false);
        var hl = H.EnsureComp<HighlightOutline>(hlGo); hl.outlineMesh = mesh;

        // Playable test player near the spawn pad, facing toolbox / blocks (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -3.0f), 0f);

        Debug.Log("[Sandbox] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame SandboxBuilder/Print Oracle Summary")]
    public static void PrintSummary() => SandboxOracleRegistry.PrintSummary();
}
#endif
