using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Globe_Desk — a decorative spinning globe on the desk.
/// Grab and release it to set a spin velocity; it gradually slows down.
/// Also has a push mode: tap it (XRSimpleInteractable) for a fixed impulse spin.
/// </summary>
public class GlobeController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Transform globeSphere;

    [Header("Physics")]
    [SerializeField] private float tapImpulse      = 180f;   // deg/s added per tap
    [SerializeField] private float maxSpeed        = 540f;
    [SerializeField] private float damping         = 30f;    // deg/s² deceleration

    public float CurrentSpeed { get; private set; } = 0f;

    private void Update()
    {
        if (globeSphere == null) return;
        if (Mathf.Abs(CurrentSpeed) > 0f)
        {
            globeSphere.Rotate(Vector3.up, CurrentSpeed * Time.deltaTime, Space.Self);
            float decel = damping * Time.deltaTime * Mathf.Sign(CurrentSpeed);
            if (Mathf.Abs(decel) > Mathf.Abs(CurrentSpeed))
                CurrentSpeed = 0f;
            else
                CurrentSpeed -= decel;
        }
    }

    /// <summary>Tap the globe for a spin impulse. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void TapSpin()
    {
        CurrentSpeed = Mathf.Clamp(CurrentSpeed + tapImpulse, -maxSpeed, maxSpeed);
        Debug.Log($"[GlobeController] Globe tapped → speed {CurrentSpeed:F0}°/s");
    }

    /// <summary>Stop the globe immediately.</summary>
    public void Stop() => CurrentSpeed = 0f;
}
