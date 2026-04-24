using UnityEngine;

/// <summary>
/// Pop-up target. Hosts BUG-002 (no hit validation) and BUG-005 (wrong rotation direction).
/// </summary>
public class TargetController : MonoBehaviour
{
    public float popupAngle = 90f;
    public float popupDuration = 0.4f;

    public bool IsActive { get; private set; }
    public bool IsHit    { get; private set; }

    private Quaternion _startRot;

    private void Awake() { _startRot = transform.localRotation; }

    public void Activate()
    {
        IsActive = true;
        IsHit = false;
        // BUG-005: Negative angle → target rotates AWAY from player instead of facing them.
        // CORRECT: Quaternion.Euler(popupAngle, 0, 0)
        transform.localRotation = _startRot * Quaternion.Euler(-popupAngle, 0, 0);
        ShootingRangeOracleRegistry.Check("BUG-005",
            popupAngle > 0,
            "Target rotated with negated angle (away from player)");
    }

    public void Deactivate()
    {
        IsActive = false;
        transform.localRotation = _startRot;
    }

    /// <summary>Called when bullet hits target. The bool indicates whether a real bullet collision happened.</summary>
    public void OnHit(bool wasRealBulletHit)
    {
        // BUG-002: skips wasRealBulletHit check — score awarded even if called without a bullet.
        // CORRECT: if (!wasRealBulletHit) return;
        if (!IsActive) return;
        IsHit = true;

        ShootingRangeOracleRegistry.Check("BUG-002",
            !wasRealBulletHit,
            "Target hit registered without bullet collision");

        ScoreManager.Instance?.AwardPoints(this, 10);
        ShootingRangeStateController.Instance?.RegisterHit();
        Deactivate();
    }

    /// <summary>Force-trigger hit without bullet (used by VRAgent to test BUG-002).</summary>
    public void ForceTriggerHitWithoutBullet() => OnHit(false);
}
