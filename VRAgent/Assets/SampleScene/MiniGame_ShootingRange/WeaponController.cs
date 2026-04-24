using UnityEngine;

/// <summary>
/// Pistol weapon controller — handles fire / reload / safety toggle.
/// Hosts BUG-001 (crash) and BUG-009 (side-effect-before-validation).
/// </summary>
public class WeaponController : MonoBehaviour
{
    [Header("Refs")]
    public AmmoMagazine magazine;
    public MuzzleFlashController muzzleFlash;
    public Transform muzzlePoint;

    [Header("Config")]
    public float bulletRange = 50f;
    public LayerMask hitMask = ~0;

    public bool IsHeld { get; private set; }
    public int  ChamberRounds { get; private set; }

    public void OnGrab()
    {
        IsHeld = true;
        ShootingRangeStateController.Instance?.SetWeaponEquipped(true);
    }

    public void OnRelease()
    {
        IsHeld = false;
        ShootingRangeStateController.Instance?.SetWeaponEquipped(false);
    }

    /// <summary>Fire one round.</summary>
    public void Fire()
    {
        if (ChamberRounds <= 0) return;
        ChamberRounds--;

        if (muzzleFlash != null) muzzleFlash.Flash();

        // Raycast → notify any TargetController hit
        if (muzzlePoint != null && Physics.Raycast(muzzlePoint.position, muzzlePoint.forward, out var hit, bulletRange, hitMask))
        {
            var target = hit.collider.GetComponentInParent<TargetController>();
            if (target != null) target.OnHit(true);
        }

        // BUG-001: NullReferenceException — no AudioSource on this GameObject
        // CORRECT: var src = GetComponent<AudioSource>(); if (src != null) src.Play();
        GetComponent<AudioSource>().Play();
    }

    /// <summary>Reload weapon from magazine.</summary>
    public void Reload()
    {
        // BUG-009: Side effect (decrement) BEFORE validating magazine availability.
        // CORRECT order: validate → decrement → load chamber.
        ChamberRounds = 6;
        if (magazine == null || !magazine.IsLoaded)
        {
            ShootingRangeOracleRegistry.Trigger("BUG-009",
                "Reload incremented ChamberRounds without a loaded magazine");
            return;
        }
        magazine.ConsumeOne();
    }

    public void ToggleSafety()
    {
        var ctrl = ShootingRangeStateController.Instance;
        if (ctrl == null) return;
        ctrl.SetSafetyOff(!ctrl.SafetyOff);
    }
}
