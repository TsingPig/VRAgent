using UnityEngine;

/// <summary>
/// Motorized window blind: open (up) / close (down) with smooth animation.
/// Requires power from the circuit breaker.
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class WindowBlindController : MonoBehaviour
{
    private const float DEFAULT_OPEN_DISTANCE = 1.5f;
    private const float DEFAULT_SPEED = 2f;

    [Header("Settings")]
    [SerializeField] private float openDistance = DEFAULT_OPEN_DISTANCE;
    [SerializeField] private float speed = DEFAULT_SPEED;

    /// <summary>Whether the blind is currently open.</summary>
    public bool IsOpen { get; private set; }

    private Vector3 _closedLocalPosition;
    private Vector3 _openLocalPosition;

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-005: sign error on Y offset.
    //   Blinds should go UP (+Y) to open, but the vector uses
    //   NEGATIVE Y, causing them to slide downward / into floor.
    //   Correct: new Vector3(0f, openDistance, 0f)
    //   Injected: new Vector3(0f, -openDistance, 0f)
    // ══════════════════════════════════════════════════════════════
    private void Start()
    {
        _closedLocalPosition = transform.localPosition;
        // BUG-005: should be +openDistance (up), but uses -openDistance (down)
        _openLocalPosition = _closedLocalPosition + new Vector3(0f, -openDistance, 0f);

        var expectedDir = new Vector3(0f, openDistance, 0f).normalized;
        var actualDir = (_openLocalPosition - _closedLocalPosition).normalized;
        ApartmentOracleRegistry.Check("BUG-005",
            Vector3.Dot(expectedDir, actualDir) < 0f,
            $"Blind direction inverted: expected up, got {actualDir}");
    }

    private void Update()
    {
        Vector3 target = IsOpen ? _openLocalPosition : _closedLocalPosition;
        transform.localPosition = Vector3.Lerp(
            transform.localPosition, target, Time.deltaTime * speed
        );
    }

    /// <summary>Toggle blind open/closed (requires power).</summary>
    public void Toggle()
    {
        if (ApartmentStateController.Instance != null &&
            !ApartmentStateController.Instance.PowerOn)
        {
            Debug.LogWarning("[WindowBlind] No power — motorized blind cannot operate");
            return;
        }

        IsOpen = !IsOpen;

        if (IsOpen)
        {
            ApartmentStateController.Instance?.SetBlindsOpened();
        }

        Debug.Log($"[WindowBlind] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
