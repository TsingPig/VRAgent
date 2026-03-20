using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Switch_MainLight — wall-mounted rocker switch near the door.
/// Controls the overhead ceiling light and optionally wakes connected devices.
/// Wire XRSimpleInteractable.selectEntered → MainLightSwitchController.Toggle().
/// </summary>
[RequireComponent(typeof(XRSimpleInteractable))]
public class MainLightSwitchController : MonoBehaviour
{
    [Header("Controlled Lights")]
    [SerializeField] private Light[] ceilingLights;

    [Header("Visuals")]
    [SerializeField] private Renderer switchRenderer;
    [SerializeField] private Material materialOn;
    [SerializeField] private Material materialOff;

    [Header("Start State")]
    [SerializeField] private bool startOn = false;

    public bool IsOn { get; private set; }

    private void Start()
    {
        IsOn = startOn;
        ApplyState();
    }

    /// <summary>Toggle the main light. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        IsOn = !IsOn;
        ApplyState();
        Debug.Log($"[MainLightSwitchController] {gameObject.name} → {(IsOn ? "ON" : "OFF")}");
    }

    private void ApplyState()
    {
        foreach (var l in ceilingLights)
            if (l != null) l.enabled = IsOn;

        if (switchRenderer != null)
            switchRenderer.sharedMaterial = IsOn ? materialOn : materialOff;
    }
}
