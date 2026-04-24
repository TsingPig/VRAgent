using System.Collections.Generic;
using UnityEngine;

// =============================================================================
// MiniGame_TowerDefense — All controllers (10 injected bugs)
// 8-step flow: PowerOn → GoldEarned → TowerSelected → TowerPlaced →
//   TowerUpgraded → WaveStarted → AllWavesDefeated → GameComplete
// =============================================================================

namespace MiniGame.TowerDefense
{

public class TowerDefenseStateController : MonoBehaviour
{
    public static TowerDefenseStateController Instance;
    public bool PowerOn, TowerSelected, TowerPlaced, TowerUpgraded, WaveStarted, AllWavesDefeated, GameComplete;
    public int  WavesCompleted;
    public int  WavesRequired = 5;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)        { PowerOn = v;       TowerDefenseOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetTowerSelected(bool v)  { TowerSelected = v; }
    public void SetTowerPlaced(bool v)    { TowerPlaced = v;   TowerDefenseOracleRegistry.StateAssert("Build", $"Placed={v}"); }
    public void SetTowerUpgraded(bool v)  { TowerUpgraded = v; }
    public void SetWaveStarted(bool v)    { WaveStarted = v; }
    public void RegisterWaveCompleted()   { WavesCompleted++; TowerDefenseOracleRegistry.StateAssert("Wave", $"Done={WavesCompleted}/{WavesRequired}"); }

    public void TryDeclareVictory()
    {
        // BUG-006: skips WavesCompleted >= WavesRequired check.
        TowerDefenseOracleRegistry.Check("BUG-006",
            WavesCompleted < WavesRequired,
            $"Victory with only {WavesCompleted}/{WavesRequired} waves completed");
        AllWavesDefeated = true;
        GameComplete = true;
    }

    public void ResetAllState()
    {
        PowerOn = TowerSelected = TowerPlaced = TowerUpgraded = WaveStarted = AllWavesDefeated = GameComplete = false;
        WavesCompleted = 0;
        // BUG-010: doesn't refund spent gold.
        TowerDefenseOracleRegistry.Check("BUG-010",
            ResourceManager.Instance != null && ResourceManager.Instance.Gold < ResourceManager.Instance.StartingGold,
            "ResetAllState didn't refund gold");
    }
}

/// <summary>Tower placer (player tool). Hosts BUG-001 (NRE) and BUG-009 (place before cost validation).</summary>
public class TowerPlacer : MonoBehaviour
{
    public int towerCost = 50;

    public void PlaceTower()
    {
        // BUG-009: applies side effect (TowerPlaced=true) BEFORE checking cost.
        TowerDefenseStateController.Instance?.SetTowerPlaced(true);
        var rm = ResourceManager.Instance;
        if (rm == null || rm.Gold < towerCost)
        {
            TowerDefenseOracleRegistry.Trigger("BUG-009",
                "Tower placed before validating gold cost");
            return;
        }
        rm.Spend(towerCost);

        // BUG-001: NRE — no AudioSource on placer.
        GetComponent<AudioSource>().Play();
    }
}

/// <summary>A placed tower. Hosts BUG-002 (fires without enemies) and BUG-005 (turret rotates wrong direction).</summary>
public class Tower : MonoBehaviour
{
    public List<EnemyController> enemiesInRange = new();

    public void Fire()
    {
        // BUG-002: skips enemiesInRange.Count > 0 check.
        TowerDefenseOracleRegistry.Check("BUG-002",
            enemiesInRange.Count == 0,
            "Tower fired with zero enemies in range");
        foreach (var e in enemiesInRange) if (e != null) e.TakeDamage(10);
    }

    public void RotateTurret(EnemyController target)
    {
        if (target == null) return;
        var dir = target.transform.position - transform.position;
        // BUG-005: rotates AWAY from target (negated direction).
        transform.rotation = Quaternion.LookRotation(-dir);
        TowerDefenseOracleRegistry.Check("BUG-005", true, "Turret rotated away from target");
    }
}

/// <summary>Wave spawner. Hosts BUG-003 (Stop doesn't reset Active) and BUG-004 (spawn timer not reset).</summary>
public class WaveSpawner : MonoBehaviour
{
    public bool IsActive { get; private set; }
    public float spawnInterval = 1f;
    private float _spawnTimer = 0f;

    public void StartWave()
    {
        // BUG-004: _spawnTimer not reset on retry.
        IsActive = true;
        TowerDefenseStateController.Instance?.SetWaveStarted(true);
        TowerDefenseOracleRegistry.Check("BUG-004",
            _spawnTimer > 0.01f,
            $"Spawn timer carried over: {_spawnTimer:F2}s");
    }

    public void StopWave()
    {
        // BUG-003: only sets state controller flag false; IsActive stays true.
        TowerDefenseStateController.Instance?.SetWaveStarted(false);
        TowerDefenseOracleRegistry.Check("BUG-003",
            IsActive == true,
            "StopWave() left IsActive=true");
    }

    private void Update()
    {
        if (!IsActive) return;
        _spawnTimer += Time.deltaTime;
        if (_spawnTimer >= spawnInterval) _spawnTimer = 0f;
    }
}

/// <summary>Enemy with health bar. Hosts BUG-008 (HP bar stuck red after heal).</summary>
public class EnemyController : MonoBehaviour
{
    public GameObject redHealthOverlay;
    public int Health { get; private set; } = 100;

    public void TakeDamage(int amt)
    {
        Health = Mathf.Max(0, Health - amt);
        if (Health < 30 && redHealthOverlay != null) redHealthOverlay.SetActive(true);
    }

    public void Heal(int amt)
    {
        Health = Mathf.Min(100, Health + amt);
        // BUG-008: missing redHealthOverlay.SetActive(false).
        TowerDefenseOracleRegistry.Check("BUG-008",
            Health >= 30 && redHealthOverlay != null && redHealthOverlay.activeSelf,
            "Enemy red HP overlay stuck after Heal restored health");
    }
}

/// <summary>Resource manager (gold). Hosts BUG-007 (build without enough gold).</summary>
public class ResourceManager : MonoBehaviour
{
    public static ResourceManager Instance;
    public int StartingGold = 100;
    public int Gold { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        Gold = StartingGold;
    }

    public void Spend(int amt) { Gold = Mathf.Max(0, Gold - amt); }

    public void TryBuildExpensive(int cost)
    {
        // BUG-007: should require Gold >= cost; allows any cost.
        TowerDefenseOracleRegistry.Check("BUG-007",
            Gold < cost,
            $"Build allowed with insufficient gold ({Gold}/{cost})");
        Gold = Mathf.Max(0, Gold - cost);
    }

} // namespace MiniGame.TowerDefense
}
