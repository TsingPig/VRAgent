using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// CeilingFan_Main — wall switch pulls the fan through 3 speeds then off.
/// The fan blades GameObject rotates each Update when active.
/// Wire XRSimpleInteractable.selectEntered on Switch_FanSpeed → CeilingFanController.CycleSpeed().
/// </summary>
public class CeilingFanController : MonoBehaviour
{
    public enum FanSpeed { Off, Low, Medium, High }

    [Header("References")]
    [SerializeField] private Transform bladesRoot;           // rotates
    [SerializeField] private Renderer  speedIndicatorRenderer;

    [Header("Rotation speeds (deg/s)")]
    [SerializeField] private float speedLow    = 60f;
    [SerializeField] private float speedMedium = 180f;
    [SerializeField] private float speedHigh   = 360f;

    [Header("Materials")]
    [SerializeField] private Material matOff;
    [SerializeField] private Material matLow;
    [SerializeField] private Material matMedium;
    [SerializeField] private Material matHigh;

    public FanSpeed CurrentSpeed { get; private set; } = FanSpeed.Off;
    public bool IsOn => CurrentSpeed != FanSpeed.Off;

    private void Update()
    {
        if (bladesRoot == null || CurrentSpeed == FanSpeed.Off) return;
        float rpm = CurrentSpeed switch
        {
            FanSpeed.Low    => speedLow,
            FanSpeed.Medium => speedMedium,
            FanSpeed.High   => speedHigh,
            _               => 0f
        };
        bladesRoot.Rotate(Vector3.up, rpm * Time.deltaTime, Space.Self);
    }

    /// <summary>Cycle through Off → Low → Medium → High → Off. Wire to Switch_FanSpeed.</summary>
    public void CycleSpeed()
    {
        CurrentSpeed = CurrentSpeed switch
        {
            FanSpeed.Off    => FanSpeed.Low,
            FanSpeed.Low    => FanSpeed.Medium,
            FanSpeed.Medium => FanSpeed.High,
            FanSpeed.High   => FanSpeed.Off,
            _               => FanSpeed.Off
        };
        ApplyIndicator();
        Debug.Log($"[CeilingFanController] Fan speed → {CurrentSpeed}");
    }

    private void ApplyIndicator()
    {
        if (speedIndicatorRenderer == null) return;
        speedIndicatorRenderer.sharedMaterial = CurrentSpeed switch
        {
            FanSpeed.Low    => matLow,
            FanSpeed.Medium => matMedium,
            FanSpeed.High   => matHigh,
            _               => matOff
        };
    }
}
