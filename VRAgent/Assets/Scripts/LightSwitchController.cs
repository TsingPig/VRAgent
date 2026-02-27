using UnityEngine;

/// <summary>
/// Toggles a target Light on/off and swaps the switch's visual material.
/// Wire XRSimpleInteractable.selectEntered -> LightSwitchController.Toggle().
/// </summary>
public class LightSwitchController : MonoBehaviour
{
    [SerializeField] private Light controlledLight;
    [SerializeField] private Renderer switchRenderer;
    [SerializeField] private Material litMaterial;
    [SerializeField] private Material unlitMaterial;

    private bool isOn;

    private void Start()
    {
        isOn = controlledLight != null && controlledLight.enabled;
        UpdateVisual();
    }

    /// <summary>Toggles the controlled light and updates the switch visual.</summary>
    public void Toggle()
    {
        isOn = !isOn;

        if (controlledLight != null)
            controlledLight.enabled = isOn;

        UpdateVisual();
        Debug.Log($"[LightSwitch] {gameObject.name} → {(isOn ? "ON" : "OFF")}");
    }

    private void UpdateVisual()
    {
        if (switchRenderer == null) return;
        switchRenderer.sharedMaterial = isOn ? litMaterial : unlitMaterial;
    }
}
