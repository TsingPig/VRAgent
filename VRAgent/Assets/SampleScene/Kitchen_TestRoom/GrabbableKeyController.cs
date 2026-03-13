using BNG;
using HenryLab;
using UnityEngine;

/// <summary>
/// Attached to Key_Pantry. Extends XRGrabbable to notify RecipeController
/// the moment the key is grabbed for the first time.
/// </summary>
public class GrabbableKeyController : XRGrabbable
{
    private bool _hasBeenPickedUp = false;

    /// <summary>Whether the key has ever been picked up.</summary>
    public bool HasBeenPickedUp => _hasBeenPickedUp;

    public new void OnGrabbed()
    {
        base.OnGrabbed();
        if (_hasBeenPickedUp) return;
        _hasBeenPickedUp = true;
        RecipeController.Instance?.SetHasPantryKey();
        Debug.Log($"[GrabbableKeyController] {gameObject.name} grabbed for the first time.");
    }
}
