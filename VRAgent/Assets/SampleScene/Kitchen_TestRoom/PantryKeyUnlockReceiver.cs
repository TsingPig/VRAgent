using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Socket receiver for the pantry door lock.
/// When Key_Pantry is inserted, notifies RecipeController to advance the
/// pantry-unlock step, then calls DoorController.Unlock().
/// Attach to the XRSocketInteractor on the pantry door lock socket.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class PantryKeyUnlockReceiver : MonoBehaviour
{
    [SerializeField] private DoorController pantryDoorController;
    [SerializeField] private Renderer socketIndicatorRenderer;
    [SerializeField] private Material unlockedMaterial;

    private XRSocketInteractor _socket;
    private bool _hasUnlocked = false;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnItemInserted);
    }

    private void OnItemInserted(SelectEnterEventArgs args)
    {
        if (_hasUnlocked) return;
        _hasUnlocked = true;

        RecipeController.Instance?.SetPantryDoorUnlocked();
        pantryDoorController?.Unlock();

        if (socketIndicatorRenderer != null && unlockedMaterial != null)
            socketIndicatorRenderer.sharedMaterial = unlockedMaterial;

        Debug.Log("[PantryKeyUnlockReceiver] Key inserted — pantry door unlocked.");
    }

    private void OnDestroy()
    {
        if (_socket != null)
            _socket.selectEntered.RemoveListener(OnItemInserted);
    }
}
