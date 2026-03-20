using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// DeskLamp_Study / DeskLamp_Bedside — touch the lamp shade or base to toggle.
/// Supports dimming via repeated interactions (Off → Dim → Bright → Off).
/// Wire XRSimpleInteractable.selectEntered → DeskLampController.CycleState().
/// </summary>
[RequireComponent(typeof(XRSimpleInteractable))]
public class DeskLampController : MonoBehaviour
{
    public enum LampState { Off, Dim, Bright }

    [Header("Light")]
    [SerializeField] private Light lampLight;
    [SerializeField] private float dimIntensity   = 0.6f;
    [SerializeField] private float brightIntensity = 2.0f;

    [Header("Visuals")]
    [SerializeField] private Renderer shadeRenderer;
    [SerializeField] private Material materialOff;
    [SerializeField] private Material materialDim;
    [SerializeField] private Material materialBright;

    [Header("Events")]
    public UnityEvent onTurnedOn;
    public UnityEvent onTurnedOff;

    public LampState CurrentState { get; private set; } = LampState.Off;
    public bool IsOn => CurrentState != LampState.Off;

    private void Start() => ApplyState();

    /// <summary>Cycles Off → Dim → Bright → Off. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void CycleState()
    {
        CurrentState = CurrentState switch
        {
            LampState.Off    => LampState.Dim,
            LampState.Dim    => LampState.Bright,
            LampState.Bright => LampState.Off,
            _                => LampState.Off
        };
        ApplyState();
        Debug.Log($"[DeskLampController] {gameObject.name} → {CurrentState}");

        if (CurrentState != LampState.Off) onTurnedOn?.Invoke();
        else                               onTurnedOff?.Invoke();
    }

    private void ApplyState()
    {
        if (lampLight != null)
        {
            lampLight.enabled = CurrentState != LampState.Off;
            lampLight.intensity = CurrentState == LampState.Bright ? brightIntensity : dimIntensity;
        }

        if (shadeRenderer == null) return;
        shadeRenderer.sharedMaterial = CurrentState switch
        {
            LampState.Dim    => materialDim,
            LampState.Bright => materialBright,
            _                => materialOff
        };
    }
}
