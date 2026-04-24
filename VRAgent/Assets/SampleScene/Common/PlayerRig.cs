using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace MiniGameBuild
{
    /// <summary>
    /// Keyboard + mouse first-person rig for testing MiniGame scenes without VR.
    ///
    /// Controls
    ///   WASD       — walk (relative to camera yaw)
    ///   Mouse      — look (yaw on body, pitch on camera). RMB hold to look while keeping cursor.
    ///   Space      — jump
    ///   Shift      — sprint
    ///   E          — toggle cursor lock (so you can click GUI / IMGUI buttons)
    ///   F          — pick up / drop the targeted Rigidbody object (held in front of camera)
    ///   Mouse 0    — invoke a generic OnPlayerClick(this) on targeted object (SendMessage)
    ///   1..9       — call the Nth public zero-arg method discovered on the targeted object
    ///                via reflection (covers Trigger/Fire/Open/Toggle/Hit/Throw/Submit/...)
    ///   T          — call any method whose name starts with "Try" or "Test" first
    ///   R          — reset position to spawn
    ///
    /// On-screen IMGUI overlay shows the targeted object name + numbered method list.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class PlayerRig : MonoBehaviour
    {
        public float walkSpeed = 3.5f;
        public float sprintSpeed = 6.5f;
        public float jumpSpeed = 4.5f;
        public float gravity = -15f;
        public float mouseSensitivity = 2.2f;
        public float interactRange = 4.0f;
        public Camera cam;
        public Transform handAnchor;

        Vector3 _spawnPos;
        Quaternion _spawnRot;
        float _pitch;
        float _vy;
        bool _cursorLocked = true;
        Rigidbody _heldRb;
        Transform _heldOriginalParent;
        bool _heldHadGravity;
        bool _heldWasKinematic;
        Collider _heldCollider;

        // Cached method list of the targeted object
        GameObject _aimedGo;
        readonly List<MethodInfo> _aimedMethods = new();
        readonly List<Component> _aimedMethodOwners = new();
        readonly List<string> _aimedMethodLabels = new();

        void Start()
        {
            _spawnPos = transform.position;
            _spawnRot = transform.rotation;
            if (cam == null) cam = GetComponentInChildren<Camera>();
            if (cam != null) _pitch = cam.transform.localEulerAngles.x;
            SetCursor(true);
        }

        void Update()
        {
            HandleCursor();
            HandleLook();
            HandleMove();
            UpdateAim();
            HandleInteract();
        }

        // ------------- look / move -------------
        void HandleCursor()
        {
            if (Input.GetKeyDown(KeyCode.E)) SetCursor(!_cursorLocked);
        }

        void SetCursor(bool locked)
        {
            _cursorLocked = locked;
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }

        void HandleLook()
        {
            if (!_cursorLocked && !Input.GetMouseButton(1)) return;
            float mx = Input.GetAxis("Mouse X") * mouseSensitivity;
            float my = Input.GetAxis("Mouse Y") * mouseSensitivity;
            transform.Rotate(0, mx, 0, Space.Self);
            _pitch = Mathf.Clamp(_pitch - my, -85f, 85f);
            if (cam != null)
                cam.transform.localEulerAngles = new Vector3(_pitch, 0, 0);
        }

        void HandleMove()
        {
            var cc = GetComponent<CharacterController>();
            float speed = Input.GetKey(KeyCode.LeftShift) ? sprintSpeed : walkSpeed;
            Vector3 input = new Vector3(Input.GetAxisRaw("Horizontal"), 0, Input.GetAxisRaw("Vertical"));
            Vector3 dir = transform.TransformDirection(input.normalized) * speed;

            if (cc.isGrounded)
            {
                _vy = -1f;
                if (Input.GetKeyDown(KeyCode.Space)) _vy = jumpSpeed;
            }
            else _vy += gravity * Time.deltaTime;

            dir.y = _vy;
            cc.Move(dir * Time.deltaTime);

            if (Input.GetKeyDown(KeyCode.R))
            {
                cc.enabled = false;
                transform.SetPositionAndRotation(_spawnPos, _spawnRot);
                cc.enabled = true;
            }
        }

        // ------------- aim + interact -------------
        void UpdateAim()
        {
            _aimedGo = null;
            _aimedMethods.Clear();
            _aimedMethodOwners.Clear();
            _aimedMethodLabels.Clear();
            if (cam == null) return;

            var ray = new Ray(cam.transform.position, cam.transform.forward);
            if (Physics.Raycast(ray, out var hit, interactRange))
            {
                var go = hit.collider.attachedRigidbody != null
                    ? hit.collider.attachedRigidbody.gameObject
                    : hit.collider.gameObject;
                _aimedGo = go;
                CollectInvokableMethods(go);
            }
        }

        void CollectInvokableMethods(GameObject go)
        {
            foreach (var comp in go.GetComponents<MonoBehaviour>())
            {
                if (comp == null) continue;
                var t = comp.GetType();
                // Skip Unity built-ins and our rig itself
                if (t == typeof(PlayerRig)) continue;
                var asm = t.Assembly.GetName().Name;
                if (asm.StartsWith("UnityEngine") || asm.StartsWith("UnityEditor")) continue;

                foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                {
                    if (m.IsSpecialName) continue;
                    if (m.GetParameters().Length != 0) continue;
                    if (m.ReturnType != typeof(void)) continue;
                    _aimedMethods.Add(m);
                    _aimedMethodOwners.Add(comp);
                    _aimedMethodLabels.Add($"{t.Name}.{m.Name}()");
                    if (_aimedMethods.Count >= 9) return;
                }
            }
        }

        void HandleInteract()
        {
            // Pick up / drop
            if (Input.GetKeyDown(KeyCode.F))
            {
                if (_heldRb != null) DropHeld();
                else if (_aimedGo != null)
                {
                    var rb = _aimedGo.GetComponent<Rigidbody>();
                    if (rb != null) PickUp(rb);
                }
            }

            // OnPlayerClick broadcast
            if (Input.GetMouseButtonDown(0) && _aimedGo != null)
                _aimedGo.SendMessage("OnPlayerClick", this, SendMessageOptions.DontRequireReceiver);

            // Numbered method invocation
            for (int i = 0; i < _aimedMethods.Count && i < 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                    SafeInvoke(i);
            }

            // T = first method whose name starts with Try/Test
            if (Input.GetKeyDown(KeyCode.T))
            {
                for (int i = 0; i < _aimedMethods.Count; i++)
                {
                    var n = _aimedMethods[i].Name;
                    if (n.StartsWith("Try") || n.StartsWith("Test"))
                    { SafeInvoke(i); break; }
                }
            }
        }

        void SafeInvoke(int i)
        {
            try
            {
                _aimedMethods[i].Invoke(_aimedMethodOwners[i], null);
                Debug.Log($"[PlayerRig] Invoked {_aimedMethodLabels[i]} on {_aimedGo.name}");
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"[PlayerRig] {_aimedMethodLabels[i]} threw: {ex.InnerException?.Message ?? ex.Message}");
            }
        }

        void PickUp(Rigidbody rb)
        {
            _heldRb = rb;
            _heldOriginalParent = rb.transform.parent;
            _heldHadGravity = rb.useGravity;
            _heldWasKinematic = rb.isKinematic;
            _heldCollider = rb.GetComponent<Collider>();
            rb.useGravity = false;
            rb.isKinematic = true;
            if (_heldCollider != null) _heldCollider.enabled = false;
            rb.transform.SetParent(handAnchor != null ? handAnchor : (cam != null ? cam.transform : transform), true);
            rb.transform.localPosition = new Vector3(0.25f, -0.20f, 0.55f);
            rb.transform.localRotation = Quaternion.identity;
        }

        void DropHeld()
        {
            if (_heldRb == null) return;
            _heldRb.transform.SetParent(_heldOriginalParent, true);
            _heldRb.useGravity = _heldHadGravity;
            _heldRb.isKinematic = _heldWasKinematic;
            if (_heldCollider != null) _heldCollider.enabled = true;
            // small forward velocity if non-kinematic
            if (!_heldRb.isKinematic && cam != null)
                _heldRb.AddForce(cam.transform.forward * 4f, ForceMode.VelocityChange);
            _heldRb = null;
            _heldCollider = null;
        }

        // ------------- IMGUI overlay -------------
        void OnGUI()
        {
            // Crosshair
            float cx = Screen.width * 0.5f, cy = Screen.height * 0.5f;
            GUI.color = Color.white;
            GUI.Box(new Rect(cx - 4, cy - 1, 8, 2), GUIContent.none);
            GUI.Box(new Rect(cx - 1, cy - 4, 2, 8), GUIContent.none);

            // Help banner
            var help = "WASD move | Mouse look | Space jump | Shift sprint | E toggle cursor | F pick/drop | LMB OnPlayerClick | 1-9 invoke method | T Try* | R respawn";
            GUI.Label(new Rect(10, 10, Screen.width - 20, 22), help);

            if (_aimedGo == null) return;
            int line = 0;
            float y0 = 36;
            GUI.Box(new Rect(10, y0, 460, 22 + 18 * (_aimedMethods.Count + 1)), GUIContent.none);
            GUI.Label(new Rect(16, y0 + 2, 450, 20), $"Aimed: {_aimedGo.name}");
            line++;
            for (int i = 0; i < _aimedMethods.Count; i++)
            {
                GUI.Label(new Rect(16, y0 + 2 + line * 18, 450, 20), $"  [{i + 1}] {_aimedMethodLabels[i]}");
                line++;
            }
            if (_heldRb != null)
                GUI.Label(new Rect(10, Screen.height - 24, 400, 22), $"Holding: {_heldRb.name}  (F to drop)");
        }
    }
}
