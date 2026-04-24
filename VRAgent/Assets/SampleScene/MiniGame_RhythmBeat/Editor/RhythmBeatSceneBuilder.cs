#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using MiniGameBuild;

/// <summary>
/// Rhythm beat stage: 6×8 m black floor, 2 colored lane strips (cyan/magenta),
/// 8 alternating beat blocks at z=5..15.5, 4 stage spot lights, score board on
/// back wall, difficulty selector tilted toward player. Sabers (blue/red) at
/// player position. Beat blocks "down" arrow direction.
/// </summary>
public static class RhythmBeatSceneBuilder
{
    [MenuItem("Tools/MiniGame RhythmBeat/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("RhythmBeat_Root") ?? new GameObject("RhythmBeat_Root");
        root.transform.position = Vector3.zero;

        var matFloor   = H.Mat("RB_StageBlack",   new Color(0.04f, 0.04f, 0.05f), 0.2f, 0.85f);
        var matWall    = H.Mat("RB_StageWall",    new Color(0.06f, 0.06f, 0.08f), 0f, 0.30f);
        var matCeiling = H.Mat("RB_StageCeiling", new Color(0.05f, 0.05f, 0.06f), 0f, 0.10f);
        var matLaneC   = H.Mat("RB_LaneCyan",     new Color(0.0f, 0.6f, 0.9f), 0f, 0.85f, new Color(0.0f, 0.7f, 1.4f));
        var matLaneM   = H.Mat("RB_LaneMagenta",  new Color(0.85f, 0.05f, 0.85f), 0f, 0.85f, new Color(1.4f, 0.0f, 1.4f));
        var matBlockC  = H.Mat("RB_BlockCyan",    new Color(0.05f, 0.55f, 0.85f), 0f, 0.7f, new Color(0.0f, 0.7f, 1.6f));
        var matBlockM  = H.Mat("RB_BlockMagenta", new Color(0.85f, 0.05f, 0.85f), 0f, 0.7f, new Color(1.6f, 0.0f, 1.6f));
        var matArrow   = H.Mat("RB_ArrowWhite",   Color.white, 0f, 0.6f, new Color(1.5f, 1.5f, 1.5f));
        var matSaberB  = H.Mat("RB_SaberBlue",    new Color(0.05f, 0.20f, 0.85f), 0.2f, 0.9f, new Color(0.0f, 0.4f, 2.0f));
        var matSaberR  = H.Mat("RB_SaberRed",     new Color(0.85f, 0.05f, 0.05f), 0.2f, 0.9f, new Color(2.0f, 0.0f, 0.0f));
        var matHilt    = H.Mat("RB_SaberHilt",    new Color(0.10f, 0.10f, 0.10f), 0.85f, 0.55f);
        var matBoard   = H.Mat("RB_BoardFrame",   new Color(0.10f, 0.10f, 0.12f), 0.6f, 0.5f);
        var matScreen  = H.Mat("RB_BoardScreen",  new Color(0.05f, 0.55f, 0.85f), 0f, 0.9f, new Color(0.1f, 0.7f, 1.4f));
        var matDiff    = H.Mat("RB_DiffPanel",    new Color(0.10f, 0.10f, 0.15f), 0.5f, 0.6f);
        var matIndic   = H.Mat("RB_DiffIndicator",new Color(0.0f, 1.0f, 0.4f), 0f, 0.8f, new Color(0.0f, 1.6f, 0.6f));

        H.Atmosphere(new Color(0.05f, 0.05f, 0.10f), 0.4f);

        // Stage room: 6 wide × 4 high × 18 long, centered z=8 (covers player at -2 to far block at +15.5)
        H.BuildRoom(root, new Vector3(0, 0, 8), new Vector3(6f, 4f, 18f), matFloor, matWall, matCeiling);

        // Two lane strips (cyan/magenta) running z=0..16, x=±0.5
        H.Prim(root, "Env_LaneCyan",    PrimitiveType.Cube, new Vector3(-0.5f, 0.015f, 8f), new Vector3(0.6f, 0.03f, 16f), matLaneC);
        H.Prim(root, "Env_LaneMagenta", PrimitiveType.Cube, new Vector3( 0.5f, 0.015f, 8f), new Vector3(0.6f, 0.03f, 16f), matLaneM);

        // 4 stage spot lights (2 cyan + 2 magenta) — angled toward stage
        H.AddLight(root, "Env_Spot_CL", LightType.Spot, new Vector3(-2.5f, 3.7f, 4f),  new Color(0.2f, 0.7f, 1f), 4.0f, 14, 50f, new Vector3(60, 30, 0));
        H.AddLight(root, "Env_Spot_ML", LightType.Spot, new Vector3( 2.5f, 3.7f, 4f),  new Color(1f, 0.2f, 1f),   4.0f, 14, 50f, new Vector3(60, -30, 0));
        H.AddLight(root, "Env_Spot_CR", LightType.Spot, new Vector3(-2.5f, 3.7f, 12f), new Color(0.2f, 0.7f, 1f), 3.0f, 14, 50f, new Vector3(60, 30, 0));
        H.AddLight(root, "Env_Spot_MR", LightType.Spot, new Vector3( 2.5f, 3.7f, 12f), new Color(1f, 0.2f, 1f),   3.0f, 14, 50f, new Vector3(60, -30, 0));

        // Controllers
        H.EnsureComp<RhythmBeatStateController>(H.Empty(root, "StateController"));
        H.EnsureComp<ComboCounter>(H.Empty(root, "ComboCounter"));
        H.EnsureComp<SongController>(H.Empty(root, "SongController"));

        // ScoreBoard at +Z back wall
        var board = H.Prim(root, "ScoreBoard", PrimitiveType.Cube, new Vector3(0, 2.4f, 16.9f), new Vector3(2.5f, 1.2f, 0.15f), matBoard);
        H.EnsureComp<ScoreBoard>(board);
        var bsc = H.Prim(board, "Screen", PrimitiveType.Quad, new Vector3(0, 0, -0.55f), new Vector3(2.3f, 1.0f, 1f), matScreen, new Vector3(0, 180f, 0));
        H.StripCollider(bsc);

        // Difficulty selector — tilted panel facing player at z=-1
        var diff = H.Prim(root, "DifficultySelector", PrimitiveType.Cube, new Vector3(1.5f, 1.10f, -1.0f), new Vector3(0.7f, 0.5f, 0.05f), matDiff, new Vector3(-25, 0, 0));
        var diffSel = H.EnsureComp<DifficultySelector>(diff);
        var indicator = H.Prim(diff, "SelectedIndicator", PrimitiveType.Quad, new Vector3(0, 0, -0.04f), new Vector3(0.6f, 0.4f, 1f), matIndic, new Vector3(0, 180f, 0));
        H.StripCollider(indicator);
        indicator.SetActive(false);
        diffSel.selectedIndicator = indicator;

        // Sabers (blue + red) on a side rack — pick up with F (no AudioSource per oracle)
        H.Prim(root, "Decor_SaberRack", PrimitiveType.Cube, new Vector3(-2.0f, 0.55f, -1.5f), new Vector3(0.6f, 1.1f, 0.4f), matBoard);
        for (int i = 0; i < 2; i++)
        {
            string n = i == 0 ? "Saber_Blue" : "Saber_Red";
            var hilt = H.Prim(root, n, PrimitiveType.Cylinder, new Vector3(-2.0f + (i == 0 ? -0.18f : 0.18f), 1.20f, -1.5f),
                new Vector3(0.05f, 0.12f, 0.05f), matHilt);
            H.KinematicRb(hilt);
            // blade child (not SerializeField; visual only)
            var blade = H.Prim(hilt, "Blade", PrimitiveType.Cylinder, new Vector3(0, 0.55f, 0), new Vector3(0.04f, 0.45f, 0.04f), i == 0 ? matSaberB : matSaberR);
            H.StripCollider(blade);
            var saber = H.EnsureComp<BeatSaberWeapon>(hilt);
            saber.saberColor = i == 0 ? "blue" : "red";
        }

        // 8 beat blocks (alternating cyan/magenta lanes), arrow visual
        for (int i = 0; i < 8; i++)
        {
            float x = i % 2 == 0 ? -0.5f : 0.5f;
            float z = 5f + i * 1.5f;
            var blk = H.Prim(root, $"BeatBlock_{i:00}", PrimitiveType.Cube, new Vector3(x, 1.4f, z),
                new Vector3(0.55f, 0.55f, 0.55f), i % 2 == 0 ? matBlockC : matBlockM);
            // down arrow quad (faces player)
            var arrow = H.Prim(blk, "ArrowDown", PrimitiveType.Quad, new Vector3(0, 0, -0.30f), new Vector3(0.35f, 0.35f, 1f), matArrow, new Vector3(0, 180f, 0));
            H.StripCollider(arrow);
            var block = H.EnsureComp<BeatBlock>(blk);
            block.requiredDirection = "down";
        }

        // Playable test player on the platform, facing the lanes (+Z)
        H.BuildPlayer(root, new Vector3(0, 0, -2.6f), 0f);

        Debug.Log("[RhythmBeat] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame RhythmBeat/Print Oracle Summary")]
    public static void PrintSummary() => RhythmBeatOracleRegistry.PrintSummary();
}
#endif
