using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Spawns waves of TargetController activations. Hosts BUG-003 (Stop doesn't reset IsActive).
/// </summary>
public class WaveSpawner : MonoBehaviour
{
    public static WaveSpawner Instance { get; private set; }

    public List<TargetController> targets = new();
    public float interval = 1.2f;

    public bool IsActive { get; private set; }
    private float _timer = 0f;
    private int _idx = 0;

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    public void StartWave()
    {
        IsActive = true;
        _timer = 0f;
        _idx = 0;
        ShootingRangeStateController.Instance?.SetWaveStarted(true);
    }

    public void StopWave()
    {
        // BUG-003: physical stop happens but IsActive is NOT reset to false.
        // Downstream systems (StateController) still believe the wave is running.
        // CORRECT: IsActive = false; ShootingRangeStateController.Instance?.SetWaveStarted(false);
        _timer = 0f;
        ShootingRangeOracleRegistry.Check("BUG-003",
            IsActive == true,
            "StopWave() left IsActive=true");
    }

    private void Update()
    {
        if (!IsActive || targets == null || targets.Count == 0) return;
        _timer += Time.deltaTime;
        if (_timer >= interval)
        {
            _timer = 0f;
            var t = targets[_idx % targets.Count];
            if (t != null) t.Activate();
            _idx++;
        }
    }
}
