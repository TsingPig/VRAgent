using UnityEngine;

/// <summary>
/// Dining table socket for serving breakfast.
/// Checks that coffee is brewed and toast is made before accepting.
/// Wire XRSocketInteractor.selectEntered → OnBreakfastPlaced().
/// </summary>
public class DiningTableSocket : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer plateRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialEmpty;
    [SerializeField] private Material materialServed;

    /// <summary>Whether breakfast has been served.</summary>
    public bool IsServed { get; private set; }

    private void Start()
    {
        IsServed = false;
        if (plateRenderer != null)
            plateRenderer.sharedMaterial = materialEmpty;
    }

    /// <summary>Called when a breakfast item is placed on the dining table.</summary>
    public void OnBreakfastPlaced()
    {
        if (IsServed) return;

        var state = ApartmentStateController.Instance;
        if (state != null && !state.CoffeeBrewed)
        {
            Debug.LogWarning("[DiningTable] Coffee not ready yet");
            return;
        }
        if (state != null && !state.ToastMade)
        {
            Debug.LogWarning("[DiningTable] Toast not ready yet");
            return;
        }

        IsServed = true;
        if (plateRenderer != null)
            plateRenderer.sharedMaterial = materialServed;

        state?.SetBreakfastServed();
        Debug.Log("[DiningTable] Breakfast served!");
    }
}
