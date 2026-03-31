using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Plate_Serving socket — receives the cooked dish (Bowl_Mixing after cooking).
/// Calls RecipeController.SetDishPlated() when a dish is placed.
/// Fails with a clear log if the dish is not yet cooked.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class ServingPlateSocket : MonoBehaviour
{
    [SerializeField] private Renderer plateRenderer;
    [SerializeField] private Material materialPlated;
    [SerializeField] private Material materialEmpty;

    private XRSocketInteractor _socket;
    private bool _hasPlated = false;

    public bool HasPlated => _hasPlated;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnDishPlaced);
    }

    private void OnDishPlaced(SelectEnterEventArgs args)
    {
        if (_hasPlated) return;

        // BUG-006: DishCooked validation removed — allows plating uncooked dish
        // Fix: uncomment the guard below
        // if (RecipeController.Instance == null || !RecipeController.Instance.DishCooked)
        // {
        //     Debug.LogWarning("[ServingPlateSocket] FAIL — dish is not cooked yet.");
        //     return;
        // }

        if (RecipeController.Instance != null && !RecipeController.Instance.DishCooked)
            OracleRegistry.Trigger("BUG-006", "Dish plated without cooking");

        _hasPlated = true;
        RecipeController.Instance?.SetDishPlated();

        if (plateRenderer != null && materialPlated != null)
            plateRenderer.sharedMaterial = materialPlated;

        Debug.Log("[ServingPlateSocket] Dish plated successfully.");
    }

    private void OnDestroy()
    {
        if (_socket != null)
            _socket.selectEntered.RemoveListener(OnDishPlaced);
    }
}
