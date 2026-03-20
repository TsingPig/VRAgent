using UnityEngine;

/// <summary>
/// Controls a fridge door with hinge animation and an interior light.
/// Attach to the door pivot GameObject (empty at hinge edge).
/// The door panel should be a child offset by half its width.
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class FridgeDoorController : MonoBehaviour
{
    private const float DEFAULT_OPEN_ANGLE = 100f;
    private const float DEFAULT_SPEED = 4f;

    [Header("Hinge Settings")]
    [SerializeField] private float openAngle = DEFAULT_OPEN_ANGLE;
    [SerializeField] private float speed = DEFAULT_SPEED;

    [Header("Interior Light")]
    [SerializeField] private Light interiorLight;

    /// <summary>Whether the fridge door is currently open.</summary>
    public bool IsOpen { get; private set; }

    private Quaternion closedRotation;
    private Quaternion openRotation;

    private void Start()
    {
        closedRotation = transform.localRotation;
        openRotation = Quaternion.Euler(0f, openAngle, 0f) * closedRotation;
        IsOpen = false;

        if (interiorLight != null)
        {
            interiorLight.enabled = false;
        }
    }

    private void Update()
    {
        Quaternion target = IsOpen ? openRotation : closedRotation;
        transform.localRotation = Quaternion.Slerp(
            transform.localRotation, target, Time.deltaTime * speed
        );
    }

    /// <summary>Toggle fridge door open/closed.</summary>
    public void Toggle()
    {
        IsOpen = !IsOpen;

        if (interiorLight != null)
        {
            interiorLight.enabled = IsOpen;
        }

        Debug.Log($"[FridgeDoorController] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
