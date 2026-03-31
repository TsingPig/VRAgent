using UnityEngine;

/// <summary>
/// Controls a fridge door with hinge animation, interior light, and door-open alarm.
/// If the door stays open longer than alarmDelay seconds, an alarm indicator activates.
/// Attach to the door pivot GameObject (empty at hinge edge).
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class FridgeDoorController : MonoBehaviour
{
    private const float DEFAULT_OPEN_ANGLE = 100f;
    private const float DEFAULT_SPEED = 4f;
    private const float DEFAULT_ALARM_DELAY = 5f;

    [Header("Hinge Settings")]
    [SerializeField] private float openAngle = DEFAULT_OPEN_ANGLE;
    [SerializeField] private float speed = DEFAULT_SPEED;

    [Header("Interior Light")]
    [SerializeField] private Light interiorLight;

    [Header("Door Alarm")]
    [SerializeField] private float alarmDelay = DEFAULT_ALARM_DELAY;
    [SerializeField] private Renderer alarmRenderer;
    [SerializeField] private Material materialNormal;
    [SerializeField] private Material materialAlarm;

    /// <summary>Whether the fridge door is currently open.</summary>
    public bool IsOpen { get; private set; }

    private Quaternion closedRotation;
    private Quaternion openRotation;
    private float _doorOpenTimer;
    private bool _alarmActive;

    private void Start()
    {
        closedRotation = transform.localRotation;
        openRotation = Quaternion.Euler(0f, openAngle, 0f) * closedRotation;
        IsOpen = false;

        if (interiorLight != null) interiorLight.enabled = false;
        if (alarmRenderer != null) alarmRenderer.sharedMaterial = materialNormal;
    }

    private void Update()
    {
        // Hinge animation
        Quaternion target = IsOpen ? openRotation : closedRotation;
        transform.localRotation = Quaternion.Slerp(
            transform.localRotation, target, Time.deltaTime * speed
        );

        // Door alarm timer
        if (IsOpen)
        {
            _doorOpenTimer += Time.deltaTime;
            if (_doorOpenTimer >= alarmDelay && !_alarmActive)
            {
                _alarmActive = true;
                if (alarmRenderer != null)
                    alarmRenderer.sharedMaterial = materialAlarm;
                Debug.LogWarning("[FridgeDoor] ALARM: door open too long!");
            }
        }
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-008: Alarm indicator (Renderer material) not reset
    //   when door closes after alarm was triggered.
    //   _alarmActive flag is cleared but the material stays red.
    //   Correct: add alarmRenderer.sharedMaterial = materialNormal;
    // ══════════════════════════════════════════════════════════════
    /// <summary>Toggle fridge door open/closed.</summary>
    public void Toggle()
    {
        IsOpen = !IsOpen;

        if (interiorLight != null)
        {
            interiorLight.enabled = IsOpen;
        }

        if (!IsOpen)
        {
            if (_alarmActive)
            {
                // BUG-008: flag reset but visual NOT reset
                // Missing: if (alarmRenderer != null) alarmRenderer.sharedMaterial = materialNormal;
                ApartmentOracleRegistry.Trigger("BUG-008",
                    "Alarm indicator material not reset after door closed");
                _alarmActive = false;
            }
            _doorOpenTimer = 0f;
        }

        Debug.Log($"[FridgeDoorController] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
