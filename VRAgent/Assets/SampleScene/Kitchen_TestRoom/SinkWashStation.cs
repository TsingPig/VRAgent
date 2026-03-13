using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Sink_WashStation — an XRSocketInteractor zone.
/// When Ingredient_Tomato (or any tagged ingredient) is placed here,
/// triggers a brief wash animation and advances the wash step.
/// Fails gracefully if kitchen is not yet unlocked.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class SinkWashStation : MonoBehaviour
{
    private const string IngredientTag = "Ingredient";

    [SerializeField] private Renderer waterFXRenderer;
    [SerializeField] private Material materialWashing;
    [SerializeField] private Material materialIdle;
    [SerializeField] private float washDuration = 1.5f;

    private XRSocketInteractor _socket;
    private bool _hasWashed = false;
    private float _washTimer = 0f;
    private bool _isWashing = false;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnIngredientPlaced);
        _socket.selectExited.AddListener(OnIngredientRemoved);
    }

    private void Update()
    {
        if (!_isWashing) return;
        _washTimer += Time.deltaTime;
        if (_washTimer >= washDuration)
        {
            _isWashing = false;
            CompleteWash();
        }
    }

    private void OnIngredientPlaced(SelectEnterEventArgs args)
    {
        if (_hasWashed) return;

        if (RecipeController.Instance == null || !RecipeController.Instance.DoorKitchenUnlocked)
        {
            Debug.LogWarning("[SinkWashStation] FAIL — kitchen not yet accessible.");
            return;
        }

        _isWashing = true;
        _washTimer = 0f;

        if (waterFXRenderer != null && materialWashing != null)
            waterFXRenderer.sharedMaterial = materialWashing;

        Debug.Log("[SinkWashStation] Washing ingredient...");
    }

    private void OnIngredientRemoved(SelectExitEventArgs args)
    {
        if (_isWashing)
        {
            _isWashing = false;
            Debug.LogWarning("[SinkWashStation] WARN — ingredient removed before wash completed.");
        }

        if (waterFXRenderer != null && materialIdle != null)
            waterFXRenderer.sharedMaterial = materialIdle;
    }

    private void CompleteWash()
    {
        if (_hasWashed) return;
        _hasWashed = true;
        RecipeController.Instance?.SetIngredientWashed();
        Debug.Log("[SinkWashStation] Wash complete.");
    }

    private void OnDestroy()
    {
        if (_socket == null) return;
        _socket.selectEntered.RemoveListener(OnIngredientPlaced);
        _socket.selectExited.RemoveListener(OnIngredientRemoved);
    }
}
