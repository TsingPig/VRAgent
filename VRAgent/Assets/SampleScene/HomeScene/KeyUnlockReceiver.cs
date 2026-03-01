using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Attached to an XRSocketInteractor. When any interactable is inserted,
/// it calls DoorController.Unlock() and updates the socket's visual indicator.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class KeyUnlockReceiver : MonoBehaviour
{
    [SerializeField] private DoorController doorController;
    [SerializeField] private Renderer socketIndicatorRenderer;
    [SerializeField] private Material unlockedMaterial;

    private XRSocketInteractor socketInteractor;
    private bool hasUnlocked = false;

    private void Awake()
    {
        socketInteractor = GetComponent<XRSocketInteractor>();
        socketInteractor.selectEntered.AddListener(OnItemInserted);
    }

    private void OnItemInserted(SelectEnterEventArgs args)
    {
        if (hasUnlocked) return;

        hasUnlocked = true;
        doorController?.Unlock();

        if (socketIndicatorRenderer != null && unlockedMaterial != null)
            socketIndicatorRenderer.sharedMaterial = unlockedMaterial;

        Debug.Log("[KeyUnlockReceiver] Item inserted — door unlocked!");
    }

    private void OnDestroy()
    {
        if (socketInteractor != null)
            socketInteractor.selectEntered.RemoveListener(OnItemInserted);
    }
}
