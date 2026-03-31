using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// TV controller with power dependency and state reporting.
/// Requires power from CircuitBreaker to operate.
/// Wire XRSimpleInteractable.selectEntered → TogglePower() on power button,
/// and another XRSimpleInteractable.selectEntered → CycleChannel() on channel button.
/// </summary>
public class TVController : MonoBehaviour
{
    private const float EMISSION_INTENSITY = 1.5f;

    [Header("References")]
    [SerializeField] private Renderer screenRenderer;
    [SerializeField] private Light screenGlow;

    [Header("Materials")]
    [SerializeField] private Material materialOff;
    [SerializeField] private List<Material> channelMaterials = new List<Material>();

    /// <summary>Whether the TV is currently powered on.</summary>
    public bool IsPowered { get; private set; }

    /// <summary>Index of the current channel (0-based).</summary>
    public int CurrentChannel { get; private set; }

    private void Start()
    {
        IsPowered = false;
        CurrentChannel = 0;
        ApplyScreenState();
    }

    /// <summary>Toggle TV power on/off (requires circuit breaker power).</summary>
    public void TogglePower()
    {
        if (ApartmentStateController.Instance != null &&
            !ApartmentStateController.Instance.PowerOn)
        {
            Debug.LogWarning("[TVController] No power from circuit breaker");
            return;
        }

        IsPowered = !IsPowered;
        ApplyScreenState();
        Debug.Log($"[TVController] {gameObject.name} → {(IsPowered ? "ON" : "OFF")}");
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-009: Calls SetTvNewsWatched(IsPowered) BEFORE the
    //   IsPowered early-return check. When TV is off, this passes
    //   IsPowered=false to the state controller, producing a
    //   spurious FAIL warning log that pollutes test analysis.
    //   Correct: move SetTvNewsWatched after the IsPowered guard.
    // ══════════════════════════════════════════════════════════════
    /// <summary>Cycle to the next channel.</summary>
    public void CycleChannel()
    {
        // BUG-009: side effect before validation
        ApartmentStateController.Instance?.SetTvNewsWatched(IsPowered);

        if (!IsPowered || channelMaterials.Count == 0) return;

        CurrentChannel = (CurrentChannel + 1) % channelMaterials.Count;
        ApplyScreenState();
        Debug.Log($"[TVController] Channel → {CurrentChannel}");
    }

    private void ApplyScreenState()
    {
        if (screenRenderer == null) return;

        if (!IsPowered)
        {
            screenRenderer.sharedMaterial = materialOff;
            if (screenGlow != null) screenGlow.enabled = false;
        }
        else if (channelMaterials.Count > 0)
        {
            screenRenderer.sharedMaterial = channelMaterials[CurrentChannel];
            if (screenGlow != null)
            {
                screenGlow.enabled = true;
                screenGlow.color = channelMaterials[CurrentChannel].GetColor("_EmissionColor");
            }
        }
    }
}
