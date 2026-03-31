using UnityEngine;

/// <summary>
/// Toaster: insert bread → push lever → wait for toast.
/// Wire XRSocketInteractor.selectEntered → OnBreadInserted(),
///       XRSocketInteractor.selectExited  → OnBreadRemoved(),
///       XRSimpleInteractable.selectEntered → PushLever().
/// </summary>
public class ToasterController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer bodyRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialIdle;
    [SerializeField] private Material materialToasting;
    [SerializeField] private Material materialDone;

    [Header("Settings")]
    [SerializeField] private float toastDuration = 3f;

    /// <summary>Whether bread is in the slot.</summary>
    public bool HasBread { get; private set; }

    /// <summary>Whether toasting is in progress.</summary>
    public bool IsToasting { get; private set; }

    /// <summary>Whether toast is done.</summary>
    public bool IsDone { get; private set; }

    private float _toastTimer;

    private void Start()
    {
        ApplyMaterial();
    }

    private void Update()
    {
        if (!IsToasting) return;

        _toastTimer += Time.deltaTime;
        if (_toastTimer >= toastDuration)
        {
            FinishToast();
        }
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-004: _toastTimer is NOT reset to 0 on re-insert.
    //   If bread is removed mid-toast and re-inserted, accumulated
    //   time carries over, causing instant or premature toasting.
    //   Correct: add _toastTimer = 0f;
    // ══════════════════════════════════════════════════════════════
    /// <summary>Called when bread is inserted into the toaster slot.</summary>
    public void OnBreadInserted()
    {
        HasBread = true;
        // BUG-004: missing _toastTimer = 0f;
        ApartmentOracleRegistry.Check("BUG-004", _toastTimer > 0f,
            $"Bread re-inserted with residual timer={_toastTimer:F2}s");
        Debug.Log("[Toaster] Bread inserted");
    }

    /// <summary>Called when bread is removed from the toaster slot.</summary>
    public void OnBreadRemoved()
    {
        HasBread = false;
        IsToasting = false;
        // Note: _toastTimer is NOT reset here either — that's part of BUG-004
        ApplyMaterial();
        Debug.Log("[Toaster] Bread removed");
    }

    /// <summary>Push the toaster lever to start toasting.</summary>
    public void PushLever()
    {
        if (!HasBread)
        {
            Debug.LogWarning("[Toaster] No bread in slot");
            return;
        }

        if (ApartmentStateController.Instance != null &&
            !ApartmentStateController.Instance.PowerOn)
        {
            Debug.LogWarning("[Toaster] No power");
            return;
        }

        if (IsToasting || IsDone)
        {
            Debug.LogWarning("[Toaster] Already toasting or done");
            return;
        }

        IsToasting = true;
        ApplyMaterial();
        Debug.Log("[Toaster] Toasting started...");
    }

    private void FinishToast()
    {
        IsToasting = false;
        IsDone = true;
        ApartmentStateController.Instance?.SetToastMade();
        ApplyMaterial();
        Debug.Log("[Toaster] Toast ready!");
    }

    private void ApplyMaterial()
    {
        if (bodyRenderer == null) return;
        if (IsToasting) bodyRenderer.sharedMaterial = materialToasting;
        else if (IsDone) bodyRenderer.sharedMaterial = materialDone;
        else bodyRenderer.sharedMaterial = materialIdle;
    }
}
