using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Generic sliding drawer / cabinet door.
/// Attach to the drawer panel GameObject itself.
/// Wire XRSimpleInteractable.selectEntered → DrawerController.Toggle().
///
/// Slide axis is configurable so the same script covers:
///   - Desk drawers (Z-axis pull)
///   - Wardrobe sliding doors (X-axis)
///   - Bedside table drawers (Z-axis)
/// </summary>
[RequireComponent(typeof(XRSimpleInteractable))]
public class BedroomDrawerController : MonoBehaviour
{
    public enum SlideAxis { X, Y, Z }

    [Header("Slide Settings")]
    [SerializeField] private SlideAxis axis       = SlideAxis.Z;
    [SerializeField] private float     openOffset  = 0.35f;
    [SerializeField] private float     speed       = 6f;

    [Header("Optional Visuals")]
    [SerializeField] private Renderer handleRenderer;
    [SerializeField] private Material materialOpen;
    [SerializeField] private Material materialClosed;

    public bool IsOpen { get; private set; } = false;

    private Vector3 _closedPos;
    private Vector3 _openPos;

    private void Start()
    {
        _closedPos = transform.localPosition;
        _openPos   = _closedPos + AxisVector() * openOffset;
        UpdateHandleVisual();
    }

    private void Update()
    {
        Vector3 target = IsOpen ? _openPos : _closedPos;
        transform.localPosition = Vector3.Lerp(transform.localPosition, target, Time.deltaTime * speed);
    }

    /// <summary>Toggle open/closed. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        IsOpen = !IsOpen;
        UpdateHandleVisual();
        Debug.Log($"[BedroomDrawerController] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }

    /// <summary>Force close (e.g. on scene reset).</summary>
    public void ForceClose()
    {
        IsOpen = false;
        transform.localPosition = _closedPos;
        UpdateHandleVisual();
    }

    private Vector3 AxisVector()
    {
        return axis switch
        {
            SlideAxis.X => Vector3.right,
            SlideAxis.Y => Vector3.up,
            _           => Vector3.forward
        };
    }

    private void UpdateHandleVisual()
    {
        if (handleRenderer == null) return;
        handleRenderer.sharedMaterial = IsOpen ? materialOpen : materialClosed;
    }
}
