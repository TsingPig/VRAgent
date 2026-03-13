using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Socket receiver for the kitchen door badge scanner.
/// Only unlocks when RecipeController reports power is enabled.
/// Provides clear feedback on failure.
/// Attach to the XRSocketInteractor on the kitchen door badge panel.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class KitchenBadgeUnlockReceiver : MonoBehaviour
{
    [SerializeField] private DoorController kitchenDoorController;
    [SerializeField] private Renderer panelRenderer;
    [SerializeField] private Material materialUnlocked;
    [SerializeField] private Material materialNoPower;

    private XRSocketInteractor _socket;
    private bool _hasUnlocked = false;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnBadgeInserted);
    }

    private void OnBadgeInserted(SelectEnterEventArgs args)
    {
        if (_hasUnlocked) return;

        if (RecipeController.Instance == null || !RecipeController.Instance.PowerEnabled)
        {
            Debug.LogWarning("[KitchenBadgeUnlockReceiver] FAIL — badge scanned but no power. Panel flashes red.");
            if (panelRenderer != null && materialNoPower != null)
                panelRenderer.sharedMaterial = materialNoPower;
            return;
        }

        _hasUnlocked = true;
        RecipeController.Instance.SetKitchenDoorUnlocked();
        kitchenDoorController?.Unlock();

        if (panelRenderer != null && materialUnlocked != null)
            panelRenderer.sharedMaterial = materialUnlocked;

        Debug.Log("[KitchenBadgeUnlockReceiver] Badge accepted — kitchen door unlocked.");
    }

    private void OnDestroy()
    {
        if (_socket != null)
            _socket.selectEntered.RemoveListener(OnBadgeInserted);
    }
}
