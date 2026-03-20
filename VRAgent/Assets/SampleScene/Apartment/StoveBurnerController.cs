using UnityEngine;

/// <summary>
/// Controls a stove burner: toggle on/off with visual glow effect.
/// Swaps between idle material and a glowing emission material.
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class StoveBurnerController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Renderer burnerRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialOff;
    [SerializeField] private Material materialOn;

    /// <summary>Whether the burner is currently on.</summary>
    public bool IsOn { get; private set; }

    private void Start()
    {
        IsOn = false;
        ApplyState();
    }

    /// <summary>Toggle the burner on/off.</summary>
    public void Toggle()
    {
        IsOn = !IsOn;
        ApplyState();
        Debug.Log($"[StoveBurnerController] {gameObject.name} → {(IsOn ? "ON" : "OFF")}");
    }

    private void ApplyState()
    {
        if (burnerRenderer == null) return;
        burnerRenderer.sharedMaterial = IsOn ? materialOn : materialOff;
    }
}
