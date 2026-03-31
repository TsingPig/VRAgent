using UnityEngine;

/// <summary>
/// Mailbox lock socket: insert key to unlock the mailbox.
/// Attach to the same GameObject as the XRSocketInteractor on the mailbox.
/// Wire selectEntered → OnKeyInserted().
/// </summary>
public class MailboxLockReceiver : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer lockRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialLocked;
    [SerializeField] private Material materialUnlocked;

    /// <summary>Whether the mailbox is currently unlocked.</summary>
    public bool IsUnlocked { get; private set; }

    private void Start()
    {
        IsUnlocked = false;
        if (lockRenderer != null)
            lockRenderer.sharedMaterial = materialLocked;
    }

    /// <summary>Called when the key is inserted into the lock socket.</summary>
    public void OnKeyInserted()
    {
        if (IsUnlocked) return;
        IsUnlocked = true;

        if (lockRenderer != null)
            lockRenderer.sharedMaterial = materialUnlocked;

        ApartmentStateController.Instance?.SetMailboxUnlocked();
        Debug.Log("[MailboxLock] Mailbox unlocked");
    }
}
