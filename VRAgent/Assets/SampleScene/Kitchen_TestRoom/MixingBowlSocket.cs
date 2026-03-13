using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Socket on Stove_Main's hob surface. StoveController reads HasBowl to
/// confirm a bowl is present before cooking. Separated from MixingBowlController
/// so the bowl remains a grabbable object and the hob is a distinct socket.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class MixingBowlSocket : MonoBehaviour
{
    private XRSocketInteractor _socket;

    public bool HasBowl { get; private set; } = false;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnBowlPlaced);
        _socket.selectExited.AddListener(OnBowlRemoved);
    }

    private void OnBowlPlaced(SelectEnterEventArgs args)
    {
        HasBowl = true;
        Debug.Log("[MixingBowlSocket] Bowl_Mixing placed on stove hob.");
    }

    private void OnBowlRemoved(SelectExitEventArgs args)
    {
        HasBowl = false;
        Debug.Log("[MixingBowlSocket] Bowl_Mixing removed from stove hob.");
    }

    private void OnDestroy()
    {
        if (_socket == null) return;
        _socket.selectEntered.RemoveListener(OnBowlPlaced);
        _socket.selectExited.RemoveListener(OnBowlRemoved);
    }
}
