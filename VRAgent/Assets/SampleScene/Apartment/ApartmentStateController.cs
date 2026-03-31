using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Central state machine for the Apartment morning routine.
/// Singleton that tracks 10 sequential progress flags and enforces ordering.
/// Mimics RecipeController from Kitchen_TestRoom.
/// Attach to a persistent manager GameObject in the scene.
/// </summary>
public class ApartmentStateController : MonoBehaviour
{
    public static ApartmentStateController Instance { get; private set; }

    // ── Progress flags (in sequence order) ───────────────────────
    [Header("Progress Flags (read-only at runtime)")]
    [SerializeField] private bool hasMailKey;
    [SerializeField] private bool mailboxUnlocked;
    [SerializeField] private bool powerOn;
    [SerializeField] private bool blindsOpened;
    [SerializeField] private bool cupPlaced;
    [SerializeField] private bool coffeeBrewed;
    [SerializeField] private bool toastMade;
    [SerializeField] private bool breakfastServed;
    [SerializeField] private bool tvNewsWatched;
    [SerializeField] private bool routineComplete;

    // ── Public read-only accessors ───────────────────────────────
    public bool HasMailKey       => hasMailKey;
    public bool MailboxUnlocked  => mailboxUnlocked;
    public bool PowerOn          => powerOn;
    public bool BlindsOpened     => blindsOpened;
    public bool CupPlaced        => cupPlaced;
    public bool CoffeeBrewed     => coffeeBrewed;
    public bool ToastMade        => toastMade;
    public bool BreakfastServed  => breakfastServed;
    public bool TvNewsWatched    => tvNewsWatched;
    public bool RoutineComplete  => routineComplete;

    // ── Events ───────────────────────────────────────────────────
    [Header("Events")]
    public UnityEvent onPowerOn;
    public UnityEvent onPowerOff;
    public UnityEvent onRoutineComplete;

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    // ── Step 1 ───────────────────────────────────────────────────
    public void SetHasMailKey()
    {
        if (hasMailKey) return;
        hasMailKey = true;
        Debug.Log("[ApartmentState] Step 1 ✓ hasMailKey");
    }

    // ── Step 2 ───────────────────────────────────────────────────
    public void SetMailboxUnlocked()
    {
        if (!hasMailKey)
        {
            Debug.LogWarning("[ApartmentState] FAIL: mailbox key not picked up");
            return;
        }
        if (mailboxUnlocked) return;
        mailboxUnlocked = true;
        Debug.Log("[ApartmentState] Step 2 ✓ mailboxUnlocked");
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-007: checks hasMailKey instead of mailboxUnlocked.
    //   Correct precondition: if (!mailboxUnlocked) return;
    //   Injected:             if (!hasMailKey)       return;
    //   Effect: power can turn on just by picking up the key,
    //   without inserting it into the mailbox lock socket.
    // ══════════════════════════════════════════════════════════════

    // ── Step 3 ───────────────────────────────────────────────────
    public void SetPowerOn()
    {
        if (!hasMailKey) // BUG-007: should be !mailboxUnlocked
        {
            Debug.LogWarning("[ApartmentState] FAIL: Cannot enable power — prerequisite not met");
            return;
        }
        ApartmentOracleRegistry.Check("BUG-007", !mailboxUnlocked,
            $"Power enabled: hasMailKey={hasMailKey}, mailboxUnlocked={mailboxUnlocked}");

        if (powerOn) return;
        powerOn = true;
        onPowerOn?.Invoke();
        Debug.Log("[ApartmentState] Step 3 ✓ powerOn");
    }

    public void SetPowerOff()
    {
        if (!powerOn) return;
        powerOn = false;
        onPowerOff?.Invoke();
        Debug.Log("[ApartmentState] powerOn → false");
    }

    // ── Step 4 ───────────────────────────────────────────────────
    public void SetBlindsOpened()
    {
        if (!powerOn)
        {
            Debug.LogWarning("[ApartmentState] FAIL: power off — cannot open blinds");
            return;
        }
        if (blindsOpened) return;
        blindsOpened = true;
        Debug.Log("[ApartmentState] Step 4 ✓ blindsOpened");
    }

    // ── Step 5 ───────────────────────────────────────────────────
    public void SetCupPlaced()
    {
        if (cupPlaced) return;
        cupPlaced = true;
        Debug.Log("[ApartmentState] Step 5 ✓ cupPlaced");
    }

    // ── Step 6 ───────────────────────────────────────────────────
    public void SetCoffeeBrewed()
    {
        if (!powerOn)
        {
            Debug.LogWarning("[ApartmentState] FAIL: power off — cannot brew");
            return;
        }
        if (!cupPlaced)
        {
            Debug.LogWarning("[ApartmentState] FAIL: no cup placed");
            return;
        }
        if (coffeeBrewed) return;
        coffeeBrewed = true;
        Debug.Log("[ApartmentState] Step 6 ✓ coffeeBrewed");
    }

    // ── Step 7 ───────────────────────────────────────────────────
    public void SetToastMade()
    {
        if (!powerOn)
        {
            Debug.LogWarning("[ApartmentState] FAIL: power off — cannot toast");
            return;
        }
        if (toastMade) return;
        toastMade = true;
        Debug.Log("[ApartmentState] Step 7 ✓ toastMade");
    }

    // ── Step 8 ───────────────────────────────────────────────────
    public void SetBreakfastServed()
    {
        if (!coffeeBrewed)
        {
            Debug.LogWarning("[ApartmentState] FAIL: coffee not brewed");
            return;
        }
        if (!toastMade)
        {
            Debug.LogWarning("[ApartmentState] FAIL: toast not made");
            return;
        }
        if (breakfastServed) return;
        breakfastServed = true;
        Debug.Log("[ApartmentState] Step 8 ✓ breakfastServed");
    }

    // ── Step 9 ───────────────────────────────────────────────────
    public void SetTvNewsWatched(bool powered)
    {
        if (!powered)
        {
            Debug.LogWarning("[ApartmentState] FAIL: TV not powered — cannot register news watching");
            ApartmentOracleRegistry.Trigger("BUG-009",
                "SetTvNewsWatched(false) called before power validation in CycleChannel");
            return;
        }
        if (tvNewsWatched) return;
        tvNewsWatched = true;
        Debug.Log("[ApartmentState] Step 9 ✓ tvNewsWatched");
    }

    // ── Step 10 (auto) ───────────────────────────────────────────
    public void CheckRoutineComplete()
    {
        if (routineComplete) return;
        if (breakfastServed && tvNewsWatched)
        {
            routineComplete = true;
            onRoutineComplete?.Invoke();
            Debug.Log("[ApartmentState] Step 10 ✓ routineComplete — Morning routine done!");
        }
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-010: ResetAllState clears own flags but does NOT
    //   notify downstream controllers (CircuitBreakerController,
    //   CoffeeMachineController, ToasterController, etc.).
    //   After reset, controllers retain stale local state.
    // ══════════════════════════════════════════════════════════════
    public void ResetAllState()
    {
        hasMailKey = false;
        mailboxUnlocked = false;
        powerOn = false;
        blindsOpened = false;
        cupPlaced = false;
        coffeeBrewed = false;
        toastMade = false;
        breakfastServed = false;
        tvNewsWatched = false;
        routineComplete = false;

        // BUG-010: Missing downstream controller resets
        // Should call: CircuitBreakerController.Reset(), CoffeeMachineController.Reset(), etc.
        ApartmentOracleRegistry.Trigger("BUG-010",
            "ResetAllState called — downstream controllers not notified");

        Debug.Log("[ApartmentState] All flags reset (downstream controllers NOT reset)");
    }
}
