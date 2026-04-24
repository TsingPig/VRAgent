using UnityEngine;

/// <summary>
/// Magazine that holds reload "charges". Hosts BUG-004 (timer not reset on retry).
/// </summary>
public class AmmoMagazine : MonoBehaviour
{
    public int  capacity = 3;
    public float reloadDuration = 1.5f;

    public bool  IsLoaded { get; private set; }
    public int   Charges  { get; private set; }
    public bool  IsReloading { get; private set; }

    private float _reloadTimer = 0f;

    private void Start()
    {
        Charges = capacity;
        IsLoaded = true;
    }

    public void ConsumeOne()
    {
        Charges = Mathf.Max(0, Charges - 1);
        IsLoaded = Charges > 0;
    }

    /// <summary>Begin a reload cycle — typically triggered by inserting magazine into socket.</summary>
    public void OnInsert()
    {
        // BUG-004: _reloadTimer is NOT reset to 0. If a previous reload was interrupted
        // (player removed mag mid-reload), accumulated time persists and the next
        // OnInsert completes "instantly".
        // CORRECT: _reloadTimer = 0f;
        IsReloading = true;
        ShootingRangeOracleRegistry.Check("BUG-004",
            _reloadTimer > 0.01f,
            $"Reload timer carried over: {_reloadTimer:F2}s of {reloadDuration:F2}s");
    }

    public void OnRemove()
    {
        IsReloading = false;
        // intentionally NOT zeroing the timer — that's the bug
    }

    private void Update()
    {
        if (!IsReloading) return;
        _reloadTimer += Time.deltaTime;
        if (_reloadTimer >= reloadDuration)
        {
            IsReloading = false;
            Charges = capacity;
            IsLoaded = true;
            ShootingRangeStateController.Instance?.SetMagazineLoaded(true);
        }
    }
}
