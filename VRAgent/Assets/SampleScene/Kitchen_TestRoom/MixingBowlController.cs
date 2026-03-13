using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Bowl_Mixing — an XRSocketInteractor that receives the cut ingredient.
/// Once the ingredient is seated, calls RecipeController.SetIngredientsCombined().
/// Fails with a log if the ingredient has not been cut yet.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class MixingBowlController : MonoBehaviour
{
    private XRSocketInteractor _socket;
    private bool _hasReceived = false;

    public bool HasReceived => _hasReceived;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnIngredientPlaced);
    }

    private void OnIngredientPlaced(SelectEnterEventArgs args)
    {
        if (_hasReceived) return;

        if (RecipeController.Instance == null || !RecipeController.Instance.IngredientCut)
        {
            Debug.LogWarning("[MixingBowlController] FAIL — ingredient not cut yet. Cut ingredient first.");
            return;
        }

        _hasReceived = true;
        RecipeController.Instance.SetIngredientsCombined();
        Debug.Log("[MixingBowlController] Ingredient added to bowl — combination complete.");
    }

    private void OnDestroy()
    {
        if (_socket != null)
            _socket.selectEntered.RemoveListener(OnIngredientPlaced);
    }
}
