using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// AlarmClock_Bedside — displays a cycling hour on a renderer material.
/// Player can:
///   1. Press Button_AlarmToggle  → start / stop alarm sound (light flash).
///   2. Press Button_Snooze       → snooze for snoozeSeconds.
///   3. Grab and shake the clock  → instant dismiss (velocity threshold).
///
/// All state is publicly readable for automated tests.
/// </summary>
public class AlarmClockController : MonoBehaviour
{
    public enum AlarmState { Silent, Ringing, Snoozed }

    [Header("References")]
    [SerializeField] private Renderer clockFaceRenderer;
    [SerializeField] private Light    alarmFlashLight;

    [Header("Materials — Clock Face")]
    [SerializeField] private Material faceNormal;
    [SerializeField] private Material faceRinging;
    [SerializeField] private Material faceSnoozed;

    [Header("Timing")]
    [SerializeField] private float snoozeDuration  = 5f;
    [SerializeField] private float flashInterval   = 0.4f;

    public AlarmState CurrentState { get; private set; } = AlarmState.Silent;
    public bool       IsRinging    => CurrentState == AlarmState.Ringing;
    public bool       IsSnoozed    => CurrentState == AlarmState.Snoozed;

    private float _snoozeTimer;
    private float _flashTimer;
    private bool  _flashOn;

    private void Update()
    {
        switch (CurrentState)
        {
            case AlarmState.Ringing:
                _flashTimer += Time.deltaTime;
                if (_flashTimer >= flashInterval)
                {
                    _flashTimer = 0f;
                    _flashOn    = !_flashOn;
                    if (alarmFlashLight != null) alarmFlashLight.enabled = _flashOn;
                }
                break;

            case AlarmState.Snoozed:
                _snoozeTimer += Time.deltaTime;
                if (_snoozeTimer >= snoozeDuration)
                    SetRinging();
                break;
        }
    }

    /// <summary>Toggle alarm on/off. Wire to Button_AlarmToggle XRSimpleInteractable.</summary>
    public void ToggleAlarm()
    {
        if (CurrentState == AlarmState.Silent)
            SetRinging();
        else
            SetSilent();
    }

    /// <summary>Snooze the alarm. Wire to Button_Snooze XRSimpleInteractable.</summary>
    public void Snooze()
    {
        if (CurrentState != AlarmState.Ringing)
        {
            Debug.Log("[AlarmClockController] Snooze pressed but alarm is not ringing.");
            return;
        }
        CurrentState = AlarmState.Snoozed;
        _snoozeTimer = 0f;
        if (alarmFlashLight != null) alarmFlashLight.enabled = false;
        ApplyFaceMaterial();
        Debug.Log($"[AlarmClockController] Snoozed for {snoozeDuration}s.");
    }

    /// <summary>Call from XRGrabbable velocity event or shake detection to dismiss.</summary>
    public void DismissAlarm()
    {
        SetSilent();
        Debug.Log("[AlarmClockController] Alarm dismissed by shake.");
    }

    private void SetRinging()
    {
        CurrentState = AlarmState.Ringing;
        _flashTimer  = 0f;
        ApplyFaceMaterial();
        Debug.Log("[AlarmClockController] RINGING!");
    }

    private void SetSilent()
    {
        CurrentState = AlarmState.Silent;
        if (alarmFlashLight != null) alarmFlashLight.enabled = false;
        ApplyFaceMaterial();
        Debug.Log("[AlarmClockController] Alarm stopped.");
    }

    private void ApplyFaceMaterial()
    {
        if (clockFaceRenderer == null) return;
        clockFaceRenderer.sharedMaterial = CurrentState switch
        {
            AlarmState.Ringing => faceRinging,
            AlarmState.Snoozed => faceSnoozed,
            _                  => faceNormal
        };
    }
}
