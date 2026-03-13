using UnityEngine;

/// <summary>
/// Lightweight editor-mode keyboard + mouse player controller for scene validation.
/// Attach to Player_KitchenTest. Disable when running with actual VR hardware.
///
/// Controls:
///   WASD / Arrow Keys  — move horizontally
///   Q / E             — descend / ascend
///   Hold Right Mouse  — rotate camera (drag)
///   Space             — jump (single step up)
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class EditorPlayerController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 4.0f;
    [SerializeField] private float verticalSpeed = 2.0f;
    [SerializeField] private float gravity = -9.81f;

    [Header("Look")]
    [SerializeField] private Transform cameraRig;
    [SerializeField] private float lookSensitivity = 2.0f;
    [SerializeField] private float lookPitchMin = -80f;
    [SerializeField] private float lookPitchMax = 80f;

    [Header("Editor Only")]
    [Tooltip("Disable this script when running with real VR hardware.")]
    [SerializeField] private bool enableInEditor = true;

    private CharacterController _cc;
    private float _yaw = 0f;
    private float _pitch = 0f;
    private float _verticalVelocity = 0f;

    private void Awake()
    {
        _cc = GetComponent<CharacterController>();
        if (cameraRig == null)
        {
            // Auto-find CameraRig under TrackingSpace
            Transform ts = transform.Find("TrackingSpace");
            if (ts != null) cameraRig = ts.Find("CameraRig");
        }
    }

    private void Update()
    {
        if (!enableInEditor) return;

        HandleRotation();
        HandleMovement();
    }

    private void HandleRotation()
    {
        if (!Input.GetMouseButton(1)) return;

        _yaw   += Input.GetAxisRaw("Mouse X") * lookSensitivity;
        _pitch -= Input.GetAxisRaw("Mouse Y") * lookSensitivity;
        _pitch  = Mathf.Clamp(_pitch, lookPitchMin, lookPitchMax);

        transform.localRotation = Quaternion.Euler(0f, _yaw, 0f);
        if (cameraRig != null)
            cameraRig.localRotation = Quaternion.Euler(_pitch, 0f, 0f);
    }

    private void HandleMovement()
    {
        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        float vertical = (Input.GetKey(KeyCode.E) ? 1f : 0f) - (Input.GetKey(KeyCode.Q) ? 1f : 0f);

        Vector3 move = transform.right * h + transform.forward * v;
        move = move.normalized * moveSpeed;

        if (_cc.isGrounded)
        {
            _verticalVelocity = -0.5f;
            if (Input.GetKeyDown(KeyCode.Space))
                _verticalVelocity = Mathf.Sqrt(-2f * gravity * 0.8f);
        }
        else
        {
            _verticalVelocity += gravity * Time.deltaTime;
        }

        move.y = _verticalVelocity + vertical * verticalSpeed;
        _cc.Move(move * Time.deltaTime);
    }
}
