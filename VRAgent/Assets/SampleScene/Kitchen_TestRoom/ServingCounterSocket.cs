using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Counter_Serving socket — the final delivery point in Room D.
/// When the plated dish is placed here, calls RecipeController.SetFinalDoorUnlocked()
/// which opens Door_FinalExit.
/// Fails clearly if dish is not yet plated.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class ServingCounterSocket : MonoBehaviour
{
    [SerializeField] private DoorController finalExitDoor;
    [SerializeField] private Renderer counterRenderer;
    [SerializeField] private Material materialComplete;
    [SerializeField] private Material materialWaiting;

    private XRSocketInteractor _socket;
    private bool _hasCompleted = false;

    public bool HasCompleted => _hasCompleted;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnDishDelivered);
    }

    private void OnDishDelivered(SelectEnterEventArgs args)
    {
        if (_hasCompleted) return;

        if (RecipeController.Instance == null || !RecipeController.Instance.DishPlated)
        {
            Debug.LogWarning("[ServingCounterSocket] FAIL — dish is not plated. Plate the dish first.");
            return;
        }

        _hasCompleted = true;
        RecipeController.Instance.SetFinalDoorUnlocked();
        finalExitDoor?.Unlock();

        if (counterRenderer != null && materialComplete != null)
            counterRenderer.sharedMaterial = materialComplete;

        Debug.Log("[ServingCounterSocket] Delivery complete — Door_FinalExit is now open!");
    }

    private void OnDestroy()
    {
        if (_socket != null)
            _socket.selectEntered.RemoveListener(OnDishDelivered);
    }
}
