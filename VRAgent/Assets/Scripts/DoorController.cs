using UnityEngine;

/// <summary>
/// Controls door open/close animation with optional locked state.
/// Unlock() must be called before Toggle()/Open() have any effect.
/// </summary>
public class DoorController : MonoBehaviour
{
    [SerializeField] private float openAngle = 90f;
    [SerializeField] private float animationSpeed = 3f;
    [SerializeField] private bool startLocked = true;

    private bool isLocked;
    private bool isOpen = false;
    private Quaternion closedRotation;
    private Quaternion targetOpenRotation;

    public bool IsLocked => isLocked;

    private void Awake()
    {
        isLocked = startLocked;
    }

    private void Start()
    {
        closedRotation = transform.localRotation;
        targetOpenRotation = Quaternion.Euler(0f, openAngle, 0f) * closedRotation;
    }

    private void Update()
    {
        Quaternion target = isOpen ? targetOpenRotation : closedRotation;
        transform.localRotation = Quaternion.Lerp(transform.localRotation, target, Time.deltaTime * animationSpeed);
    }

    /// <summary>Opens the door. No effect if locked.</summary>
    public void Open()
    {
        if (!isLocked) isOpen = true;
    }

    /// <summary>Closes the door regardless of lock state.</summary>
    public void Close()
    {
        isOpen = false;
    }

    /// <summary>Toggles the door. No effect if locked. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        if (!isLocked) isOpen = !isOpen;
    }

    /// <summary>Removes the lock so the door can be opened. Called by KeyUnlockReceiver.</summary>
    public void Unlock()
    {
        isLocked = false;
        Debug.Log($"[DoorController] {gameObject.name} unlocked.");
    }
}
