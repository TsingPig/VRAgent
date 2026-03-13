using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Stove_Main — a stateful cooking device. Player activates it
/// (via XRSimpleInteractable.selectEntered -> TryStartCooking) after
/// placing Bowl_Mixing on the hob socket.
/// 
/// Gate checks (in order):
///   1. Power must be on.
///   2. Ingredients must be combined.
///   3. Cooking runs for cookDuration seconds.
///   4. Calls RecipeController.SetDishCooked() on completion.
///
/// Fails clearly at each gate without crashing.
/// </summary>
public class StoveController : MonoBehaviour
{
    public enum StoveState { Off, Cooking, Done }

    [Header("References")]
    [SerializeField] private MixingBowlSocket hobSocket;
    [SerializeField] private Renderer burnerRenderer;
    [SerializeField] private Material materialCooking;
    [SerializeField] private Material materialOff;
    [SerializeField] private Material materialDone;

    [Header("Cooking Settings")]
    [SerializeField] private float cookDuration = 3f;

    public StoveState CurrentState { get; private set; } = StoveState.Off;

    private float _cookTimer = 0f;

    private void Update()
    {
        if (CurrentState != StoveState.Cooking) return;

        _cookTimer += Time.deltaTime;
        if (_cookTimer >= cookDuration)
        {
            FinishCooking();
        }
    }

    /// <summary>
    /// Attempts to start cooking. Wire to XRSimpleInteractable.selectEntered on the stove knob.
    /// </summary>
    public void TryStartCooking()
    {
        if (CurrentState != StoveState.Off) return;

        RecipeController rc = RecipeController.Instance;

        if (rc == null || !rc.PowerEnabled)
        {
            Debug.LogWarning("[StoveController] FAIL — no power. Flip Switch_MainPower first.");
            return;
        }

        if (!rc.IngredientsCombined)
        {
            Debug.LogWarning("[StoveController] FAIL — ingredients not combined. Fill Bowl_Mixing first.");
            return;
        }

        CurrentState = StoveState.Cooking;
        _cookTimer = 0f;

        if (burnerRenderer != null && materialCooking != null)
            burnerRenderer.sharedMaterial = materialCooking;

        Debug.Log($"[StoveController] Cooking started — will finish in {cookDuration}s.");
    }

    private void FinishCooking()
    {
        CurrentState = StoveState.Done;

        if (burnerRenderer != null && materialDone != null)
            burnerRenderer.sharedMaterial = materialDone;

        RecipeController.Instance?.SetDishCooked();
        Debug.Log("[StoveController] Cooking complete — dish is ready.");
    }
}
