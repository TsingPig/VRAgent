using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Central recipe state machine. Tracks each cooking step in order and gates
/// every downstream interaction. Exposes individual bool fields so the test
/// framework can inspect state directly without reflection.
/// </summary>
public class RecipeController : MonoBehaviour
{
    // ── Gating flags (read by all other controllers) ──────────────────────
    [Header("State Flags (read-only in Inspector)")]
    [SerializeField] private bool hasPantryKey       = false;
    [SerializeField] private bool doorPantryUnlocked  = false;
    [SerializeField] private bool doorKitchenUnlocked = false;
    [SerializeField] private bool powerEnabled        = false;
    [SerializeField] private bool ingredientWashed    = false;
    [SerializeField] private bool ingredientCut       = false;
    [SerializeField] private bool ingredientsCombined = false;
    [SerializeField] private bool dishCooked          = false;
    [SerializeField] private bool dishPlated          = false;
    [SerializeField] private bool finalDoorUnlocked   = false;

    // ── Public accessors (used by other controllers) ───────────────────────
    public bool HasPantryKey        => hasPantryKey;
    public bool DoorPantryUnlocked  => doorPantryUnlocked;
    public bool DoorKitchenUnlocked => doorKitchenUnlocked;
    public bool PowerEnabled        => powerEnabled;
    public bool IngredientWashed    => ingredientWashed;
    public bool IngredientCut       => ingredientCut;
    public bool IngredientsCombined => ingredientsCombined;
    public bool DishCooked          => dishCooked;
    public bool DishPlated          => dishPlated;
    public bool FinalDoorUnlocked   => finalDoorUnlocked;

    // ── Events ─────────────────────────────────────────────────────────────
    [Header("Step Events")]
    public UnityEvent onPantryKeyPickedUp;
    public UnityEvent onPantryDoorUnlocked;
    public UnityEvent onKitchenDoorUnlocked;
    public UnityEvent onPowerEnabled;
    public UnityEvent onIngredientWashed;
    public UnityEvent onIngredientCut;
    public UnityEvent onIngredientsCombined;
    public UnityEvent onDishCooked;
    public UnityEvent onDishPlated;
    public UnityEvent onFinalDoorUnlocked;

    // ── Singleton-style accessor ───────────────────────────────────────────
    private static RecipeController _instance;
    public static RecipeController Instance
    {
        get
        {
            if (_instance == null)
                _instance = FindObjectOfType<RecipeController>();
            return _instance;
        }
    }

    private void Awake()
    {
        _instance = this;
    }

    // ─────────────────────────────────────────────────────────────────────
    //  Step setters — each validates prerequisites before advancing
    // ─────────────────────────────────────────────────────────────────────

    /// <summary>Called when player grabs Key_Pantry.</summary>
    public void SetHasPantryKey()
    {
        if (hasPantryKey) return;
        hasPantryKey = true;
        Debug.Log("[RecipeController] Step 1 PASSED — pantry key picked up.");
        onPantryKeyPickedUp?.Invoke();
    }

    /// <summary>Called by KeyUnlockReceiver when key is inserted into pantry socket.</summary>
    public void SetPantryDoorUnlocked()
    {
        if (!hasPantryKey)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to unlock pantry without key.");
            return;
        }
        if (doorPantryUnlocked) return;
        doorPantryUnlocked = true;
        Debug.Log("[RecipeController] Step 2 PASSED — pantry door unlocked.");
        onPantryDoorUnlocked?.Invoke();
    }

    /// <summary>Called by Switch_MainPower after pantry ingredients are collected.</summary>
    public void SetPowerEnabled()
    {
        if (!doorPantryUnlocked)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to enable power before opening pantry.");
            return;
        }
        if (powerEnabled) return;
        powerEnabled = true;
        Debug.Log("[RecipeController] Step 3 PASSED — main power enabled.");
        onPowerEnabled?.Invoke();
    }

    /// <summary>Called when power is on AND kitchen socket receives badge.</summary>
    public void SetKitchenDoorUnlocked()
    {
        if (!powerEnabled)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to unlock kitchen door without power.");
            return;
        }
        if (doorKitchenUnlocked) return;
        doorKitchenUnlocked = true;
        Debug.Log("[RecipeController] Step 4 PASSED — kitchen door unlocked.");
        onKitchenDoorUnlocked?.Invoke();
    }

    /// <summary>Called by Sink_WashStation interaction.</summary>
    public void SetIngredientWashed()
    {
        if (!doorKitchenUnlocked)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to wash ingredient before entering kitchen.");
            return;
        }
        if (ingredientWashed) return;
        ingredientWashed = true;
        Debug.Log("[RecipeController] Step 5 PASSED — ingredient washed.");
        onIngredientWashed?.Invoke();
    }

    /// <summary>Called by Board_Cutting interaction. Requires Tool_Knife to be held.</summary>
    public void SetIngredientCut(bool knifePresent)
    {
        if (!ingredientWashed)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to cut before washing.");
            return;
        }
        if (!knifePresent)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to cut without a knife.");
            return;
        }
        if (ingredientCut) return;
        ingredientCut = true;
        Debug.Log("[RecipeController] Step 6 PASSED — ingredient cut.");
        onIngredientCut?.Invoke();
    }

    /// <summary>Called when all ingredients are placed into Bowl_Mixing.</summary>
    public void SetIngredientsCombined()
    {
        if (!ingredientCut)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to combine before cutting.");
            return;
        }
        if (ingredientsCombined) return;
        ingredientsCombined = true;
        Debug.Log("[RecipeController] Step 7 PASSED — ingredients combined.");
        onIngredientsCombined?.Invoke();
    }

    /// <summary>Called by Stove_Main after cooking duration completes.</summary>
    public void SetDishCooked()
    {
        if (!powerEnabled)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to cook without power.");
            return;
        }
        if (!ingredientsCombined)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to cook without combined ingredients.");
            return;
        }
        if (dishCooked) return;
        dishCooked = true;
        Debug.Log("[RecipeController] Step 8 PASSED — dish cooked.");
        onDishCooked?.Invoke();
    }

    /// <summary>Called when cooked dish is placed onto Plate_Serving socket.</summary>
    public void SetDishPlated()
    {
        if (!dishCooked)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to plate an uncooked dish.");
            return;
        }
        if (dishPlated) return;
        dishPlated = true;
        Debug.Log("[RecipeController] Step 9 PASSED — dish plated.");
        onDishPlated?.Invoke();
    }

    /// <summary>Called when plated dish is placed on Counter_Serving, unlocking the final door.</summary>
    public void SetFinalDoorUnlocked()
    {
        if (!dishPlated)
        {
            Debug.LogWarning("[RecipeController] FAIL — tried to exit without plated dish.");
            return;
        }
        if (finalDoorUnlocked) return;
        finalDoorUnlocked = true;
        Debug.Log("[RecipeController] Step 10 PASSED — final door unlocked. Task complete!");
        onFinalDoorUnlocked?.Invoke();
    }

    // ── Debug helpers ──────────────────────────────────────────────────────

    /// <summary>Prints the full state snapshot to the console (useful for test assertions).</summary>
    public void PrintStateSnapshot()
    {
        Debug.Log($"[RecipeController][Snapshot] " +
                  $"hasPantryKey={hasPantryKey} | doorPantryUnlocked={doorPantryUnlocked} | " +
                  $"powerEnabled={powerEnabled} | doorKitchenUnlocked={doorKitchenUnlocked} | " +
                  $"ingredientWashed={ingredientWashed} | ingredientCut={ingredientCut} | " +
                  $"ingredientsCombined={ingredientsCombined} | dishCooked={dishCooked} | " +
                  $"dishPlated={dishPlated} | finalDoorUnlocked={finalDoorUnlocked}");
    }

    /// <summary>Resets all state to initial values (used between test iterations).</summary>
    public void ResetAllState()
    {
        hasPantryKey       = false;
        doorPantryUnlocked  = false;
        powerEnabled        = false;
        doorKitchenUnlocked = false;
        ingredientWashed    = false;
        ingredientCut       = false;
        ingredientsCombined = false;
        dishCooked          = false;
        dishPlated          = false;
        finalDoorUnlocked   = false;
        Debug.Log("[RecipeController] All state reset.");
    }
}
