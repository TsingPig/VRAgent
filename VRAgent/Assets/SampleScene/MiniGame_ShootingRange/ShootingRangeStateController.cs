using UnityEngine;

/// <summary>
/// Central state machine for the Shooting Range mini-game.
/// 8-step flow: PowerOn → MagazineLoaded → WeaponEquipped → SafetyOff →
///   WaveStarted → AllTargetsHit → ScoreSubmitted → GameComplete
/// </summary>
public class ShootingRangeStateController : MonoBehaviour
{
    public static ShootingRangeStateController Instance { get; private set; }

    public bool PowerOn { get; private set; }
    public bool MagazineLoaded { get; private set; }
    public bool WeaponEquipped { get; private set; }
    public bool SafetyOff { get; private set; }
    public bool WaveStarted { get; private set; }
    public int  TargetsHit { get; private set; }
    public int  TargetsRequired { get; set; } = 5;
    public bool ScoreSubmitted { get; private set; }
    public bool GameComplete { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    public void SetPowerOn(bool v)         { PowerOn = v;          ShootingRangeOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetMagazineLoaded(bool v)  { MagazineLoaded = v;   ShootingRangeOracleRegistry.StateAssert("Magazine", $"Loaded={v}"); }
    public void SetWeaponEquipped(bool v)  { WeaponEquipped = v; }
    public void SetSafetyOff(bool v)       { SafetyOff = v; }
    public void SetWaveStarted(bool v)     { WaveStarted = v; }
    public void RegisterHit()              { TargetsHit++; ShootingRangeOracleRegistry.StateAssert("Hit", $"TargetsHit={TargetsHit}/{TargetsRequired}"); }
    public void SetScoreSubmitted(bool v)  { ScoreSubmitted = v; }

    /// <summary>Marks game complete — REQUIRES all targets hit + score submitted.</summary>
    public void TryFinishGame()
    {
        // BUG-006: skips precondition — allows finish without hitting all targets
        // CORRECT: if (TargetsHit < TargetsRequired) { Debug.LogWarning("Not enough targets"); return; }
        // CORRECT: if (!ScoreSubmitted) { Debug.LogWarning("Score not submitted"); return; }
        ShootingRangeOracleRegistry.Check("BUG-006",
            TargetsHit < TargetsRequired,
            $"Game complete with only {TargetsHit}/{TargetsRequired} targets hit");
        GameComplete = true;
        ShootingRangeOracleRegistry.StateAssert("GameComplete", $"complete=true hits={TargetsHit}");
    }

    /// <summary>Reset all state — designed to cascade reset to all child controllers.</summary>
    public void ResetAllState()
    {
        PowerOn = false; MagazineLoaded = false; WeaponEquipped = false;
        SafetyOff = false; WaveStarted = false;
        TargetsHit = 0; ScoreSubmitted = false; GameComplete = false;

        // BUG-010: forgets to cascade reset to ComboCounter / WaveSpawner / MuzzleFlash
        // CORRECT: ScoreManager.Instance?.ResetCombo();
        // CORRECT: WaveSpawner.Instance?.StopWave();
        // CORRECT: MuzzleFlashController.Instance?.ForceHide();
        ShootingRangeOracleRegistry.Check("BUG-010",
            ScoreManager.Instance != null && ScoreManager.Instance.ComboStreak > 0,
            "ResetAllState left combo streak non-zero");
    }
}
