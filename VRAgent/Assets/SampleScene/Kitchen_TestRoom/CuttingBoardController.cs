using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Board_Cutting — players must interact with this while Tool_Knife is present
/// in the adjacent KnifeSlot socket. Fails clearly when knife is missing or
/// ingredient has not been washed yet.
/// Wire XRSimpleInteractable.selectEntered -> CuttingBoardController.TryCut().
/// </summary>
public class CuttingBoardController : MonoBehaviour
{
    [SerializeField] private KnifeSlotDetector knifeSlot;
    [SerializeField] private Renderer boardRenderer;
    [SerializeField] private Material materialCut;
    [SerializeField] private Material materialUncut;

    private bool _hasBeenCut = false;

    public bool HasBeenCut => _hasBeenCut;

    private void Start()
    {
        UpdateVisual();
    }

    /// <summary>
    /// Attempt to cut the ingredient.
    /// Wire to XRSimpleInteractable.selectEntered on Board_Cutting.
    /// </summary>
    public void TryCut()
    {
        if (_hasBeenCut) return;

        bool knifePresent = knifeSlot != null && knifeSlot.IsKnifePresent;

        // BUG-009: SetIngredientCut called BEFORE knifePresent/wash validation.
        // Even with knifePresent=false, this hits RecipeController producing a
        // spurious FAIL warning. Fix: move this call AFTER all validation passes.
        RecipeController.Instance?.SetIngredientCut(knifePresent);
        if (!knifePresent)
            OracleRegistry.Trigger("BUG-009", "SetIngredientCut(false) called before validation");

        if (!knifePresent)
        {
            Debug.LogWarning("[CuttingBoardController] FAIL — no knife in slot. Place Tool_Knife on the board first.");
            return;
        }

        if (RecipeController.Instance != null && !RecipeController.Instance.IngredientWashed)
        {
            Debug.LogWarning("[CuttingBoardController] FAIL — ingredient not yet washed.");
            return;
        }

        _hasBeenCut = true;
        UpdateVisual();
        Debug.Log("[CuttingBoardController] Ingredient successfully cut.");
    }

    private void UpdateVisual()
    {
        if (boardRenderer == null) return;
        boardRenderer.sharedMaterial = _hasBeenCut ? materialCut : materialUncut;
    }
}
