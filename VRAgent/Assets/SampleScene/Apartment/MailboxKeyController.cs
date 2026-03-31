using UnityEngine;

/// <summary>
/// Notifies ApartmentStateController when the mailbox key is first picked up.
/// Attach to the key GameObject.
/// Wire XRGrabInteractable.selectEntered → OnGrabbed().
/// </summary>
public class MailboxKeyController : MonoBehaviour
{
    private bool _hasBeenPickedUp;

    /// <summary>Called when the key is grabbed for the first time.</summary>
    public void OnGrabbed()
    {
        if (_hasBeenPickedUp) return;
        _hasBeenPickedUp = true;
        ApartmentStateController.Instance?.SetHasMailKey();
        Debug.Log("[MailboxKey] Key picked up for the first time");
    }
}
