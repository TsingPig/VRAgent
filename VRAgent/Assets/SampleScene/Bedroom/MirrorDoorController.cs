using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Wardrobe_Mirror sliding door (or hinged door variant).
/// Supports two modes: Slide (X-axis) or Hinge (Y-rotation).
/// Wire XRSimpleInteractable.selectEntered on Handle_Wardrobe → MirrorDoorController.Toggle().
/// </summary>
[RequireComponent(typeof(XRSimpleInteractable))]
public class MirrorDoorController : MonoBehaviour
{
    public enum DoorMode { Slide, Hinge }

    [Header("Mode")]
    [SerializeField] private DoorMode mode = DoorMode.Slide;

    [Header("Slide Settings")]
    [SerializeField] private float slideDistance = 0.9f;

    [Header("Hinge Settings")]
    [SerializeField] private float openAngle = 85f;

    [Header("Animation")]
    [SerializeField] private float speed = 5f;

    public bool IsOpen { get; private set; } = false;

    private Vector3    _closedPos;
    private Vector3    _openPos;
    private Quaternion _closedRot;
    private Quaternion _openRot;

    private void Start()
    {
        _closedPos = transform.localPosition;
        _openPos   = _closedPos + Vector3.right * slideDistance;
        _closedRot = transform.localRotation;
        _openRot   = Quaternion.Euler(0f, openAngle, 0f) * _closedRot;
    }

    private void Update()
    {
        if (mode == DoorMode.Slide)
        {
            Vector3 target = IsOpen ? _openPos : _closedPos;
            transform.localPosition = Vector3.Lerp(transform.localPosition, target, Time.deltaTime * speed);
        }
        else
        {
            Quaternion target = IsOpen ? _openRot : _closedRot;
            transform.localRotation = Quaternion.Slerp(transform.localRotation, target, Time.deltaTime * speed);
        }
    }

    /// <summary>Toggle the door. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        IsOpen = !IsOpen;
        Debug.Log($"[MirrorDoorController] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
