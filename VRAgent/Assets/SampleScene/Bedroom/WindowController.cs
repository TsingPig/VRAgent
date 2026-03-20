using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Window_Main — a hinged window that opens inward.
/// Also has a latch that must be turned before the window can be pushed open.
/// Wire:
///   Latch_Window XRSimpleInteractable.selectEntered → WindowController.TurnLatch()
///   Handle_Window XRSimpleInteractable.selectEntered → WindowController.ToggleWindow()
/// </summary>
public class WindowController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Transform windowPanel;
    [SerializeField] private Transform latch;

    [Header("Open Rotation")]
    [SerializeField] private float openAngle = 70f;
    [SerializeField] private float speed     = 4f;

    [Header("Latch Rotation")]
    [SerializeField] private float latchOpenAngle = 90f;

    public bool IsLatched { get; private set; } = true;
    public bool IsOpen    { get; private set; } = false;

    private Quaternion _closedRot;
    private Quaternion _openRot;
    private Quaternion _latchClosedRot;
    private Quaternion _latchOpenRot;

    private void Start()
    {
        if (windowPanel != null)
        {
            _closedRot = windowPanel.localRotation;
            _openRot   = Quaternion.Euler(0f, -openAngle, 0f) * _closedRot;
        }
        if (latch != null)
        {
            _latchClosedRot = latch.localRotation;
            _latchOpenRot   = Quaternion.Euler(latchOpenAngle, 0f, 0f) * _latchClosedRot;
        }
    }

    private void Update()
    {
        if (windowPanel != null)
        {
            Quaternion target = IsOpen ? _openRot : _closedRot;
            windowPanel.localRotation = Quaternion.Slerp(windowPanel.localRotation, target, Time.deltaTime * speed);
        }
        if (latch != null)
        {
            Quaternion target = IsLatched ? _latchClosedRot : _latchOpenRot;
            latch.localRotation = Quaternion.Slerp(latch.localRotation, target, Time.deltaTime * speed * 2f);
        }
    }

    /// <summary>Turn / un-turn the latch. Wire to Latch_Window.</summary>
    public void TurnLatch()
    {
        IsLatched = !IsLatched;
        Debug.Log($"[WindowController] Latch → {(IsLatched ? "LOCKED" : "UNLOCKED")}");
    }

    /// <summary>Open / close the window. Wire to Handle_Window.</summary>
    public void ToggleWindow()
    {
        if (IsLatched)
        {
            Debug.LogWarning("[WindowController] FAIL — window is latched. Turn Latch_Window first.");
            return;
        }
        IsOpen = !IsOpen;
        Debug.Log($"[WindowController] Window → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
