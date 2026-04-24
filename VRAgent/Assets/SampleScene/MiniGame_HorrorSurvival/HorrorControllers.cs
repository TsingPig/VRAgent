using System.Collections.Generic;
using UnityEngine;

// =============================================================================
// MiniGame_HorrorSurvival — All controllers (10 injected bugs)
// 9-step flow: PowerOn → FlashlightHeld → BatteryInserted → KeyFound →
//   DoorUnlocked → EnemyEscaped → SafeRoomReached → ExtractionCalled → GameComplete
// =============================================================================

public class HorrorStateController : MonoBehaviour
{
    public static HorrorStateController Instance;
    public bool PowerOn, FlashlightHeld, BatteryInserted, KeyFound, DoorUnlocked, EnemyEscaped, SafeRoomReached, ExtractionCalled, GameComplete;
    public int  KeysCollected;
    public int  KeysRequired = 3;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)         { PowerOn = v;        HorrorOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetFlashlightHeld(bool v)  { FlashlightHeld = v; }
    public void SetBatteryInserted(bool v) { BatteryInserted = v; HorrorOracleRegistry.StateAssert("Battery", $"Inserted={v}"); }
    public void SetKeyFound(bool v)        { KeyFound = v; }
    public void SetDoorUnlocked(bool v)    { DoorUnlocked = v; }
    public void RegisterKeyCollected()     { KeysCollected++; HorrorOracleRegistry.StateAssert("Key", $"Collected={KeysCollected}/{KeysRequired}"); }

    public void TryEscape()
    {
        // BUG-006: skips KeysCollected >= KeysRequired check.
        HorrorOracleRegistry.Check("BUG-006",
            KeysCollected < KeysRequired,
            $"Escape with only {KeysCollected}/{KeysRequired} keys");
        ExtractionCalled = true;
        GameComplete = true;
    }

    public void ResetAllState()
    {
        PowerOn = FlashlightHeld = BatteryInserted = KeyFound = DoorUnlocked = EnemyEscaped = SafeRoomReached = ExtractionCalled = GameComplete = false;
        KeysCollected = 0;
        // BUG-010: forgets to cascade to EnemyAI / Health / HUD.
        HorrorOracleRegistry.Check("BUG-010",
            EnemyAI.Instance != null && EnemyAI.Instance.AggroLevel > 0,
            "ResetAllState left EnemyAI aggro non-zero");
    }
}

/// <summary>VR flashlight. Hosts BUG-001 (NRE) and BUG-009 (toggle before battery check).</summary>
public class FlashlightController : MonoBehaviour
{
    public BatteryItem battery;
    public GameObject lightCone;

    public bool IsOn { get; private set; }
    public bool IsHeld { get; private set; }

    public void OnGrab()    { IsHeld = true;  HorrorStateController.Instance?.SetFlashlightHeld(true); }
    public void OnRelease() { IsHeld = false; HorrorStateController.Instance?.SetFlashlightHeld(false); }

    public void ToggleLight()
    {
        // BUG-009: toggles light state BEFORE checking battery.
        IsOn = !IsOn;
        if (lightCone != null) lightCone.SetActive(IsOn);
        if (battery == null || !battery.IsCharged)
        {
            HorrorOracleRegistry.Trigger("BUG-009",
                "Flashlight toggled before validating battery presence");
            return;
        }

        // BUG-001: NRE — flashlight has no AudioSource.
        GetComponent<AudioSource>().Play();
    }
}

/// <summary>Battery item, slotted into flashlight. Hosts BUG-002 (no grab check) and BUG-005 (wrong slot direction).</summary>
public class BatteryItem : MonoBehaviour
{
    public bool IsCharged = true;
    public bool WasGrabbed { get; private set; }

    public void OnGrab() { WasGrabbed = true; }

    /// <summary>Apply battery into flashlight socket. shouldRequireGrab is the precondition.</summary>
    public void ApplyToFlashlight(bool shouldRequireGrab)
    {
        // BUG-002: skips WasGrabbed check.
        HorrorOracleRegistry.Check("BUG-002",
            shouldRequireGrab && !WasGrabbed,
            "Battery applied without being grabbed first");

        HorrorStateController.Instance?.SetBatteryInserted(true);

        // BUG-005: physical orientation rotated -90 (battery upside-down in socket)
        // CORRECT: transform.localRotation = Quaternion.Euler(90, 0, 0);
        transform.localRotation = Quaternion.Euler(-90, 0, 0);
        HorrorOracleRegistry.Check("BUG-005", true, "Battery socket orientation upside-down");
    }

    public void ForceApplyWithoutGrab() => ApplyToFlashlight(true);
}

/// <summary>Locked door. Hosts BUG-003 (lock toggle no reset) and BUG-007 (unlock without key).</summary>
public class DoorLockController : MonoBehaviour
{
    public bool IsLocked = true;

    public void TryUnlock()
    {
        // BUG-007: should require KeysCollected >= KeysRequired; checks KeyFound.
        var ctrl = HorrorStateController.Instance;
        if (ctrl == null || !ctrl.KeyFound) return;
        HorrorOracleRegistry.Check("BUG-007",
            ctrl.KeysCollected < ctrl.KeysRequired,
            $"Door unlocked with only {ctrl.KeysCollected}/{ctrl.KeysRequired} keys");
        IsLocked = false;
        ctrl.SetDoorUnlocked(true);
    }

    public void ToggleLockOff()
    {
        // BUG-003: cosmetic toggle but IsLocked field stays true.
        HorrorOracleRegistry.Check("BUG-003",
            IsLocked == true,
            "ToggleLockOff() left IsLocked=true");
    }
}

/// <summary>Enemy AI. Hosts BUG-004 (chase timer not reset).</summary>
public class EnemyAI : MonoBehaviour
{
    public static EnemyAI Instance;
    public float chaseDuration = 5f;
    public int   AggroLevel { get; private set; }
    public bool  IsChasing { get; private set; }
    private float _chaseTimer = 0f;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void StartChase()
    {
        // BUG-004: _chaseTimer not reset on retry.
        IsChasing = true;
        AggroLevel++;
        HorrorOracleRegistry.Check("BUG-004",
            _chaseTimer > 0.01f && AggroLevel == 1,
            $"Chase timer carried over from previous chase: {_chaseTimer:F2}s");
    }

    public void StopChase() { IsChasing = false; }

    private void Update()
    {
        if (!IsChasing) return;
        _chaseTimer += Time.deltaTime;
        if (_chaseTimer >= chaseDuration) IsChasing = false;
    }

    public void ResetAggro() { AggroLevel = 0; _chaseTimer = 0f; IsChasing = false; }
}

/// <summary>Health bar with visual indicator. Hosts BUG-008 (bar stays red after heal).</summary>
public class HealthSystem : MonoBehaviour
{
    public GameObject redBarOverlay;
    public int Health { get; private set; } = 100;

    public void TakeDamage(int amt)
    {
        Health = Mathf.Max(0, Health - amt);
        if (Health < 30 && redBarOverlay != null) redBarOverlay.SetActive(true);
    }

    public void Heal(int amt)
    {
        Health = Mathf.Min(100, Health + amt);
        // BUG-008: when Health restored above 30, redBarOverlay is NOT deactivated.
        // CORRECT: if (Health >= 30 && redBarOverlay != null) redBarOverlay.SetActive(false);
        HorrorOracleRegistry.Check("BUG-008",
            Health >= 30 && redBarOverlay != null && redBarOverlay.activeSelf,
            "Red HP bar still active after Heal restored health above threshold");
    }
}

/// <summary>Key item collected from rooms.</summary>
public class KeyItem : MonoBehaviour
{
    public void OnGrab()
    {
        HorrorStateController.Instance?.SetKeyFound(true);
        HorrorStateController.Instance?.RegisterKeyCollected();
    }
}
