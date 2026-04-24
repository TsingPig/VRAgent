using UnityEngine;

/// <summary>
/// Score / combo tracker. Hosts BUG-007 (wrong precondition field).
/// </summary>
public class ScoreManager : MonoBehaviour
{
    public static ScoreManager Instance { get; private set; }

    public int Score { get; private set; }
    public int ComboStreak { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    public void AwardPoints(TargetController target, int amount)
    {
        if (target == null) return;

        // BUG-007: Wrong precondition — checks target.IsActive (still true at hit time)
        // when the intent is "only award if target.IsHit". Both happen to be true in
        // happy-path, but if someone calls AwardPoints externally on an active-but-
        // not-hit target, points are still awarded.
        // CORRECT: if (!target.IsHit) return;
        if (!target.IsActive)
        {
            ShootingRangeOracleRegistry.Trigger("BUG-007",
                "AwardPoints used wrong precondition (IsActive vs IsHit)");
            return;
        }

        Score += amount;
        ComboStreak++;
    }

    public void SubmitScore()
    {
        ShootingRangeStateController.Instance?.SetScoreSubmitted(true);
        ShootingRangeOracleRegistry.StateAssert("Submit", $"score={Score} combo={ComboStreak}");
    }

    public void ResetCombo() { ComboStreak = 0; }
}
