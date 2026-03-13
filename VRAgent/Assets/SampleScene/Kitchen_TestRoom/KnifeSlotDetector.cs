using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// KnifeSlot — XRSocketInteractor placed on Board_Cutting surface.
/// Detects whether Tool_Knife is currently seated in the slot.
/// CuttingBoardController queries IsKnifePresent before allowing a cut.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class KnifeSlotDetector : MonoBehaviour
{
    private XRSocketInteractor _socket;

    public bool IsKnifePresent { get; private set; } = false;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnKnifeInserted);
        _socket.selectExited.AddListener(OnKnifeRemoved);
    }

    private void OnKnifeInserted(SelectEnterEventArgs args)
    {
        IsKnifePresent = true;
        Debug.Log("[KnifeSlotDetector] Tool_Knife placed on cutting board.");
    }

    private void OnKnifeRemoved(SelectExitEventArgs args)
    {
        IsKnifePresent = false;
        Debug.Log("[KnifeSlotDetector] Tool_Knife removed from cutting board.");
    }

    private void OnDestroy()
    {
        if (_socket == null) return;
        _socket.selectEntered.RemoveListener(OnKnifeInserted);
        _socket.selectExited.RemoveListener(OnKnifeRemoved);
    }
}
