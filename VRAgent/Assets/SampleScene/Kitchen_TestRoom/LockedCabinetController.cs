using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Cabinet_Ingredients — slides open only after the pantry door is unlocked
/// (container gate). Extends DrawerController's pattern with a gating check
/// against RecipeController.
/// Wire XRSimpleInteractable.selectEntered -> LockedCabinetController.TryOpen().
/// </summary>
public class LockedCabinetController : MonoBehaviour
{
    [SerializeField] private float openDistance = 0.42f;
    [SerializeField] private float animationSpeed = 5f;
    [SerializeField] private Renderer lockIndicatorRenderer;
    [SerializeField] private Material materialLocked;
    [SerializeField] private Material materialUnlocked;

    private bool _isOpen = false;
    private bool _isUnlocked = false;
    private Vector3 _closedLocalPosition;
    private Vector3 _openLocalPosition;

    public bool IsOpen => _isOpen;
    public bool IsUnlocked => _isUnlocked;

    private void Start()
    {
        _closedLocalPosition = transform.localPosition;
        _openLocalPosition = _closedLocalPosition + new Vector3(0f, 0f, -openDistance);
        UpdateLockVisual();
    }

    private void Update()
    {
        Vector3 target = _isOpen ? _openLocalPosition : _closedLocalPosition;
        transform.localPosition = Vector3.Lerp(transform.localPosition, target, Time.deltaTime * animationSpeed);
    }

    /// <summary>
    /// Attempts to open the cabinet. Blocked until RecipeController confirms pantry is open.
    /// Wire to XRSimpleInteractable.selectEntered.
    /// </summary>
    public void TryOpen()
    {
        if (!_isUnlocked)
        {
            // Auto-check if the gate condition is now met.
            if (RecipeController.Instance != null && RecipeController.Instance.DoorPantryUnlocked)
            {
                Unlock();
            }
            else
            {
                Debug.LogWarning($"[LockedCabinetController] FAIL — {gameObject.name} is locked. Open pantry door first.");
                return;
            }
        }

        _isOpen = !_isOpen;
        Debug.Log($"[LockedCabinetController] {gameObject.name} → {(_isOpen ? "OPEN" : "CLOSED")}");
    }

    /// <summary>Unlocks the cabinet, allowing it to be opened.</summary>
    public void Unlock()
    {
        if (_isUnlocked) return;
        _isUnlocked = true;
        UpdateLockVisual();
        Debug.Log($"[LockedCabinetController] {gameObject.name} unlocked.");
    }

    private void UpdateLockVisual()
    {
        if (lockIndicatorRenderer == null) return;
        lockIndicatorRenderer.sharedMaterial = _isUnlocked ? materialUnlocked : materialLocked;
    }
}
