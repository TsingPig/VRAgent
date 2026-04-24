#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

/// <summary>
/// Editor menu helper that programmatically builds the MiniGame_ShootingRange scene.
/// Avoids hand-written .unity YAML; click "Tools/MiniGame ShootingRange/Build Scene"
/// then File → Save.
/// </summary>
public static class ShootingRangeSceneBuilder
{
    [MenuItem("Tools/MiniGame ShootingRange/Build Scene")]
    public static void BuildScene()
    {
        // Root
        var root = GameObject.Find("ShootingRange_Root") ?? new GameObject("ShootingRange_Root");

        // State controller
        var stateGo = EnsureChild(root, "StateController");
        var state = stateGo.GetComponent<ShootingRangeStateController>() ?? stateGo.AddComponent<ShootingRangeStateController>();
        state.TargetsRequired = 5;

        // Floor
        var floor = EnsureChild(root, "Floor");
        floor.transform.localPosition = Vector3.zero;
        floor.transform.localScale = new Vector3(20, 1, 20);
        if (floor.GetComponent<MeshFilter>() == null)
        {
            var mf = floor.AddComponent<MeshFilter>();
            mf.sharedMesh = Resources.GetBuiltinResource<Mesh>("Cube.fbx");
            floor.AddComponent<MeshRenderer>();
            floor.AddComponent<BoxCollider>();
            floor.transform.localScale = new Vector3(20, 0.1f, 20);
        }

        // Score manager
        var scoreGo = EnsureChild(root, "ScoreManager");
        scoreGo.GetComponent<ScoreManager>(); _ = scoreGo.GetComponent<ScoreManager>() ?? scoreGo.AddComponent<ScoreManager>();

        // Power switch (placeholder)
        var power = EnsureChild(root, "PowerSwitch");
        power.transform.localPosition = new Vector3(-3, 1.2f, -2);

        // Weapon
        var weaponGo = EnsureChild(root, "Pistol");
        weaponGo.transform.localPosition = new Vector3(-1, 1, -3);
        var weapon = weaponGo.GetComponent<WeaponController>() ?? weaponGo.AddComponent<WeaponController>();
        if (weaponGo.GetComponent<Rigidbody>() == null) { var rb = weaponGo.AddComponent<Rigidbody>(); rb.useGravity = false; rb.isKinematic = true; }
        if (weaponGo.GetComponent<BoxCollider>() == null) weaponGo.AddComponent<BoxCollider>();

        var muzzlePoint = EnsureChild(weaponGo, "MuzzlePoint");
        muzzlePoint.transform.localPosition = new Vector3(0, 0, 0.3f);
        weapon.muzzlePoint = muzzlePoint.transform;

        // Magazine
        var magGo = EnsureChild(root, "Magazine");
        magGo.transform.localPosition = new Vector3(0, 1, -3);
        var mag = magGo.GetComponent<AmmoMagazine>() ?? magGo.AddComponent<AmmoMagazine>();
        weapon.magazine = mag;

        // Muzzle flash
        var flashGo = EnsureChild(root, "MuzzleFlash");
        var flash = flashGo.GetComponent<MuzzleFlashController>() ?? flashGo.AddComponent<MuzzleFlashController>();
        var quad = EnsureChild(flashGo, "FlashQuad");
        quad.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f);
        quad.SetActive(false);
        flash.flashQuad = quad;
        weapon.muzzleFlash = flash;

        // Wave spawner + 5 targets
        var waveGo = EnsureChild(root, "WaveSpawner");
        var wave = waveGo.GetComponent<WaveSpawner>() ?? waveGo.AddComponent<WaveSpawner>();
        wave.targets.Clear();
        for (int i = 0; i < 5; i++)
        {
            var tGo = EnsureChild(root, $"Target_{i:00}");
            tGo.transform.localPosition = new Vector3(-2 + i, 1.2f, 4);
            if (tGo.GetComponent<BoxCollider>() == null) tGo.AddComponent<BoxCollider>();
            var tc = tGo.GetComponent<TargetController>() ?? tGo.AddComponent<TargetController>();
            wave.targets.Add(tc);
        }

        Debug.Log("[ShootingRange] Scene built. Save scene with File→Save.");
        Selection.activeGameObject = root;
    }

    [MenuItem("Tools/MiniGame ShootingRange/Print Oracle Summary")]
    public static void PrintOracleSummary() => ShootingRangeOracleRegistry.PrintSummary();

    private static GameObject EnsureChild(GameObject parent, string name)
    {
        var t = parent.transform.Find(name);
        if (t != null) return t.gameObject;
        var go = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        return go;
    }
}
#endif
