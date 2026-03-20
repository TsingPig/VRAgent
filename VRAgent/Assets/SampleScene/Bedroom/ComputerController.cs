using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Computer_Desk — press the power button to boot/shutdown.
/// Has three states: Off → Booting (2s) → On → Off.
/// Monitor screen renderer switches emissive material per state.
/// Wire XRSimpleInteractable.selectEntered on Button_ComputerPower → ComputerController.PressButton().
/// </summary>
public class ComputerController : MonoBehaviour
{
    public enum ComputerState { Off, Booting, On }

    [Header("References")]
    [SerializeField] private Renderer monitorScreenRenderer;
    [SerializeField] private Renderer powerLedRenderer;
    [SerializeField] private Light    monitorGlow;

    [Header("Materials")]
    [SerializeField] private Material screenOff;
    [SerializeField] private Material screenBooting;
    [SerializeField] private Material screenOn;
    [SerializeField] private Material ledOff;
    [SerializeField] private Material ledOn;

    [Header("Timing")]
    [SerializeField] private float bootDuration = 2.0f;

    [Header("Events")]
    public UnityEvent onBooted;
    public UnityEvent onShutdown;

    public ComputerState CurrentState { get; private set; } = ComputerState.Off;
    public bool IsOn => CurrentState == ComputerState.On;

    private float _bootTimer;

    private void Start() => ApplyState();

    private void Update()
    {
        if (CurrentState != ComputerState.Booting) return;
        _bootTimer += Time.deltaTime;
        if (_bootTimer >= bootDuration)
            FinishBooting();
    }

    /// <summary>Press the power button. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void PressButton()
    {
        switch (CurrentState)
        {
            case ComputerState.Off:
                CurrentState = ComputerState.Booting;
                _bootTimer = 0f;
                Debug.Log("[ComputerController] Booting...");
                break;

            case ComputerState.Booting:
                Debug.Log("[ComputerController] Already booting — please wait.");
                return;

            case ComputerState.On:
                CurrentState = ComputerState.Off;
                onShutdown?.Invoke();
                Debug.Log("[ComputerController] Shutdown.");
                break;
        }
        ApplyState();
    }

    private void FinishBooting()
    {
        CurrentState = ComputerState.On;
        ApplyState();
        onBooted?.Invoke();
        Debug.Log("[ComputerController] Boot complete — computer is ON.");
    }

    private void ApplyState()
    {
        if (monitorScreenRenderer != null)
        {
            monitorScreenRenderer.sharedMaterial = CurrentState switch
            {
                ComputerState.Booting => screenBooting,
                ComputerState.On      => screenOn,
                _                    => screenOff
            };
        }
        if (powerLedRenderer != null)
            powerLedRenderer.sharedMaterial = CurrentState == ComputerState.Off ? ledOff : ledOn;
        if (monitorGlow != null)
            monitorGlow.enabled = CurrentState == ComputerState.On;
    }
}
