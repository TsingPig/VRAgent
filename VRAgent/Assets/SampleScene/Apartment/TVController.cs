using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Controls a TV: power on/off and channel cycling.
/// Screen switches between a dark off-material and colored channel materials with emission.
/// Wire XRSimpleInteractable.selectEntered → TogglePower() on a power button,
/// and another XRSimpleInteractable.selectEntered → CycleChannel() on a channel button.
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

    /// <summary>Toggle TV power on/off.</summary>
    public void TogglePower()
    {
        IsPowered = !IsPowered;
        ApplyScreenState();
        Debug.Log($"[TVController] {gameObject.name} → {(IsPowered ? "ON" : "OFF")}");
    }

    /// <summary>Cycle to the next channel (only when powered on).</summary>
    public void CycleChannel()
    {
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
