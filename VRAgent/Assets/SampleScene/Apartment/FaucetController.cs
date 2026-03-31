using UnityEngine;

/// <summary>
/// Controls a faucet with cold/hot water modes and dishwashing capability.
/// Cold water toggle always works; hot water dishwashing requires power.
/// Wire XRSimpleInteractable.selectEntered → Toggle() on the faucet handle,
/// and another XRSimpleInteractable.selectEntered → TryWashDishes() on the sink area.
/// </summary>
public class FaucetController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private GameObject waterStream;
    [SerializeField] private AudioSource waterAudio;
    [SerializeField] private Renderer sinkRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialClean;
    [SerializeField] private Material materialWashing;

    [Header("Settings")]
    [SerializeField] private float washDuration = 2f;

    /// <summary>Whether the faucet is currently running.</summary>
    public bool IsRunning { get; private set; }

    /// <summary>Whether dishes are currently being washed.</summary>
    public bool IsWashing { get; private set; }

    /// <summary>Whether dishes have been washed this session.</summary>
    public bool DishesWashed { get; private set; }

    private float _washTimer;

    private void Start()
    {
        IsRunning = false;
        if (waterStream != null) waterStream.SetActive(false);
    }

    private void Update()
    {
        if (!IsWashing) return;

        _washTimer += Time.deltaTime;
        if (_washTimer >= washDuration)
        {
            FinishWashing();
        }
    }

    /// <summary>Toggle water on/off (basic cold water).</summary>
    public void Toggle()
    {
        IsRunning = !IsRunning;

        if (waterStream != null)
        {
            waterStream.SetActive(IsRunning);
        }

        if (waterAudio != null)
        {
            if (IsRunning) waterAudio.Play();
            else waterAudio.Stop();
        }

        if (!IsRunning && IsWashing)
        {
            IsWashing = false;
            Debug.Log("[FaucetController] Water stopped — washing interrupted");
        }

        Debug.Log($"[FaucetController] {gameObject.name} → {(IsRunning ? "ON" : "OFF")}");
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-006: Missing power check for hot water dishwashing.
    //   Dishes can be washed with cold water (no power), bypassing
    //   the hot-water gate. Hot water heater requires CircuitBreaker.
    //   Correct: check ApartmentStateController.Instance.PowerOn
    //   Injected: power check removed → gate bypass
    // ══════════════════════════════════════════════════════════════
    /// <summary>Start washing dishes (requires running faucet + power for hot water).</summary>
    public void TryWashDishes()
    {
        if (!IsRunning)
        {
            Debug.LogWarning("[FaucetController] FAIL: Faucet not running");
            return;
        }

        if (DishesWashed)
        {
            Debug.LogWarning("[FaucetController] Dishes already washed");
            return;
        }

        // BUG-006: should check power for hot water
        // if (ApartmentStateController.Instance != null && !ApartmentStateController.Instance.PowerOn)
        // {
        //     Debug.LogWarning("[FaucetController] No power — hot water unavailable");
        //     return;
        // }

        ApartmentOracleRegistry.Check("BUG-006",
            ApartmentStateController.Instance != null && !ApartmentStateController.Instance.PowerOn,
            $"Dishes washed without power (cold water only). PowerOn={ApartmentStateController.Instance?.PowerOn}");

        IsWashing = true;
        _washTimer = 0f;
        if (sinkRenderer != null) sinkRenderer.sharedMaterial = materialWashing;
        Debug.Log("[FaucetController] Dish washing started...");
    }

    private void FinishWashing()
    {
        IsWashing = false;
        DishesWashed = true;
        if (sinkRenderer != null) sinkRenderer.sharedMaterial = materialClean;
        Debug.Log("[FaucetController] Dishes washed!");
    }
}
