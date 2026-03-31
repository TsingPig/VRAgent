using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Controls the main power switch (Switch_MainPower).
/// Toggles power state and notifies RecipeController.
/// Wire XRSimpleInteractable.selectEntered -> PowerSwitchController.Toggle().
/// </summary>
[RequireComponent(typeof(XRSimpleInteractable))]
public class PowerSwitchController : MonoBehaviour
{
    [SerializeField] private Renderer switchRenderer;
    [SerializeField] private Material materialOn;
    [SerializeField] private Material materialOff;
    [SerializeField] private Light[] controlledLights;

    public bool IsOn { get; private set; } = false;

    private void Start()
    {
        UpdateVisual();
    }

    /// <summary>Toggles the power. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        IsOn = !IsOn;
        UpdateVisual();

        if (IsOn)
            RecipeController.Instance?.SetPowerEnabled();
        // BUG-003: Toggling OFF does not reset RecipeController.PowerEnabled
        // Expected: else RecipeController.Instance?.SetPowerDisabled();
        // Result: PowerEnabled stays true even after switch is turned off
        if (!IsOn && RecipeController.Instance != null && RecipeController.Instance.PowerEnabled)
            OracleRegistry.Trigger("BUG-003", "IsOn=false but PowerEnabled=true");
        Debug.Log($"[PowerSwitchController] {gameObject.name} → {(IsOn ? "ON" : "OFF")}");
    }

    private void UpdateVisual()
    {
        if (switchRenderer != null)
            switchRenderer.sharedMaterial = IsOn ? materialOn : materialOff;

        foreach (var light in controlledLights)
        {
            if (light != null)
                light.enabled = IsOn;
        }
    }
}
