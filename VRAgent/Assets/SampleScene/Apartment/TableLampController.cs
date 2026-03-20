using UnityEngine;

/// <summary>
/// Controls a table/floor lamp: toggle on/off with point light and shade emission.
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class TableLampController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer shadeRenderer;
    [SerializeField] private Light lampLight;

    [Header("Materials")]
    [SerializeField] private Material materialOn;
    [SerializeField] private Material materialOff;

    [Header("Settings")]
    [SerializeField] private bool startOn = false;

    /// <summary>Whether the lamp is currently on.</summary>
    public bool IsOn { get; private set; }

    private void Start()
    {
        IsOn = startOn;
        ApplyState();
    }

    /// <summary>Toggle the lamp on/off.</summary>
    public void Toggle()
    {
        IsOn = !IsOn;
        ApplyState();
        Debug.Log($"[TableLampController] {gameObject.name} → {(IsOn ? "ON" : "OFF")}");
    }

    private void ApplyState()
    {
        if (shadeRenderer != null)
        {
            shadeRenderer.sharedMaterial = IsOn ? materialOn : materialOff;
        }

        if (lampLight != null)
        {
            lampLight.enabled = IsOn;
        }
    }
}
