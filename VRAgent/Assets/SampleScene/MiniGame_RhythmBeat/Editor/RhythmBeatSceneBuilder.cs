#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class RhythmBeatSceneBuilder
{
    [MenuItem("Tools/MiniGame RhythmBeat/Build Scene")]
    public static void BuildScene()
    {
        var root = GameObject.Find("RhythmBeat_Root") ?? new GameObject("RhythmBeat_Root");

        var stateGo = Ensure(root, "StateController");
        stateGo.GetComponent<RhythmBeatStateController>() ?? stateGo.AddComponent<RhythmBeatStateController>();

        var combo = Ensure(root, "ComboCounter");
        combo.GetComponent<ComboCounter>() ?? combo.AddComponent<ComboCounter>();

        var song = Ensure(root, "SongController");
        song.GetComponent<SongController>() ?? song.AddComponent<SongController>();

        var score = Ensure(root, "ScoreBoard");
        score.GetComponent<ScoreBoard>() ?? score.AddComponent<ScoreBoard>();

        var diff = Ensure(root, "DifficultySelector");
        var diffSel = diff.GetComponent<DifficultySelector>() ?? diff.AddComponent<DifficultySelector>();
        var indicator = Ensure(diff, "SelectedIndicator");
        indicator.SetActive(false);
        diffSel.selectedIndicator = indicator;

        // Sabers (blue + red)
        for (int i = 0; i < 2; i++)
        {
            var sg = Ensure(root, i == 0 ? "Saber_Blue" : "Saber_Red");
            sg.transform.localPosition = new Vector3(i == 0 ? -0.4f : 0.4f, 1, -2);
            if (sg.GetComponent<Rigidbody>() == null) { var rb = sg.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
            if (sg.GetComponent<BoxCollider>() == null) sg.AddComponent<BoxCollider>();
            var saber = sg.GetComponent<BeatSaberWeapon>() ?? sg.AddComponent<BeatSaberWeapon>();
            saber.saberColor = i == 0 ? "blue" : "red";
        }

        // 8 beat blocks (down direction)
        for (int i = 0; i < 8; i++)
        {
            var bg = Ensure(root, $"BeatBlock_{i:00}");
            bg.transform.localPosition = new Vector3(i % 2 == 0 ? -0.5f : 0.5f, 1.4f, 5 + i * 1.5f);
            if (bg.GetComponent<BoxCollider>() == null) bg.AddComponent<BoxCollider>();
            var block = bg.GetComponent<BeatBlock>() ?? bg.AddComponent<BeatBlock>();
            block.requiredDirection = "down";
        }

        Debug.Log("[RhythmBeat] Scene built. File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame RhythmBeat/Print Oracle Summary")]
    public static void PrintSummary() => RhythmBeatOracleRegistry.PrintSummary();

    private static GameObject Ensure(GameObject parent, string name)
    {
        var t = parent.transform.Find(name);
        if (t != null) return t.gameObject;
        var go = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        return go;
    }
}
#endif
