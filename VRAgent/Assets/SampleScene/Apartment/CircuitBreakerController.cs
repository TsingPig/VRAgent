using UnityEngine;

/// <summary>
/// Main circuit breaker for the apartment.
/// Controls power to all electrical appliances (coffee machine, toaster, TV, blinds, lamp, burner).
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class CircuitBreakerController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer switchRenderer;
    [SerializeField] private Light indicatorLight;

    [Header("Materials")]
    [SerializeField] private Material materialOn;
    [SerializeField] private Material materialOff;

    /// <summary>Whether the breaker is currently on.</summary>
    public bool IsOn { get; private set; }

    private void Start()
    {
        IsOn = false;
        ApplyState();
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-003: Toggle OFF does not call SetPowerOff().
    //   When IsOn goes from true→false, the state controller's
    //   PowerOn flag stays true forever once set.
    //   Correct: add else { ApartmentStateController.Instance?.SetPowerOff(); }
    // ══════════════════════════════════════════════════════════════
    /// <summary>Toggle circuit breaker on/off.</summary>
    public void Toggle()
    {
        IsOn = !IsOn;
        ApplyState();

        if (IsOn)
        {
            ApartmentStateController.Instance?.SetPowerOn();
        }
        // BUG-003: missing else branch → SetPowerOff() never called
        // else { ApartmentStateController.Instance?.SetPowerOff(); }

        if (!IsOn)
        {
            ApartmentOracleRegistry.Check("BUG-003",
                ApartmentStateController.Instance != null && ApartmentStateController.Instance.PowerOn,
                $"Breaker OFF but PowerOn={ApartmentStateController.Instance?.PowerOn}");
        }

        Debug.Log($"[CircuitBreaker] {gameObject.name} → {(IsOn ? "ON" : "OFF")}");
    }

    private void ApplyState()
    {
        if (switchRenderer != null)
            switchRenderer.sharedMaterial = IsOn ? materialOn : materialOff;
        if (indicatorLight != null)
            indicatorLight.enabled = IsOn;
    }
}
