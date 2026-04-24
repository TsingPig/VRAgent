using UnityEngine;

// =============================================================================
// MiniGame_EscapeRoom — All controllers (10 injected bugs)
// 9-step flow: PowerOn → CombinationDialed → SafeUnlocked → KeyGrabbed →
//   KeyInserted → DoorUnlocked → DoorOpened → ExitReached → GameComplete
// =============================================================================

public class EscapeRoomStateController : MonoBehaviour
{
    public static EscapeRoomStateController Instance;
    public bool PowerOn, CombinationDialed, SafeUnlocked, KeyGrabbed, KeyInserted, DoorUnlocked, DoorOpened, ExitReached, GameComplete;
    public int  PuzzlesSolved;
    public int  PuzzlesRequired = 3;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)            { PowerOn = v;            EscapeRoomOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetCombinationDialed(bool v)  { CombinationDialed = v;  EscapeRoomOracleRegistry.StateAssert("Combo", $"Dialed={v}"); }
    public void SetSafeUnlocked(bool v)       { SafeUnlocked = v;       EscapeRoomOracleRegistry.StateAssert("Safe", $"Unlocked={v}"); }
    public void SetKeyGrabbed(bool v)         { KeyGrabbed = v; }
    public void SetKeyInserted(bool v)        { KeyInserted = v; }
    public void SetDoorUnlocked(bool v)       { DoorUnlocked = v; }
    public void SetDoorOpened(bool v)         { DoorOpened = v; }
    public void RegisterPuzzleSolved()        { PuzzlesSolved++; EscapeRoomOracleRegistry.StateAssert("Puzzle", $"Solved={PuzzlesSolved}/{PuzzlesRequired}"); }

    public void TryEscape()
    {
        // BUG-006: skips PuzzlesSolved >= PuzzlesRequired check.
        EscapeRoomOracleRegistry.Check("BUG-006",
            PuzzlesSolved < PuzzlesRequired,
            $"Escape with only {PuzzlesSolved}/{PuzzlesRequired} puzzles");
        ExitReached = true;
        GameComplete = true;
    }

    public void ResetAllState()
    {
        PowerOn = CombinationDialed = SafeUnlocked = KeyGrabbed = KeyInserted = DoorUnlocked = DoorOpened = ExitReached = GameComplete = false;
        PuzzlesSolved = 0;
        // BUG-010: forgets to cascade to HintLight / DoorController / KeySafe.
        EscapeRoomOracleRegistry.Check("BUG-010",
            HintLight.Instance != null && HintLight.Instance.IsOn,
            "ResetAllState left HintLight on");
    }
}

/// <summary>Combination dial. Hosts BUG-005 (wrong dial direction).</summary>
public class CombinationLock : MonoBehaviour
{
    public int correctDigit = 7;
    public int CurrentDigit { get; private set; }
    public bool IsDialed { get; private set; }

    /// <summary>Rotate dial — direction +1 (clockwise) or -1 (counter).</summary>
    public void RotateDial(int direction)
    {
        // BUG-005: applies -direction (sign error) — visual dial moves opposite of input.
        // CORRECT: CurrentDigit = (CurrentDigit + direction + 10) % 10;
        CurrentDigit = (CurrentDigit - direction + 10) % 10;
        EscapeRoomOracleRegistry.Check("BUG-005",
            direction != 0,
            $"RotateDial used negated direction (in={direction})");
    }

    public void TryDial()
    {
        IsDialed = (CurrentDigit == correctDigit);
        if (IsDialed) EscapeRoomStateController.Instance?.SetCombinationDialed(true);
    }

    public void ForceDialCorrect() { CurrentDigit = correctDigit; TryDial(); }
}

/// <summary>Locked safe. Hosts BUG-001 (NRE) and BUG-009 (unlock before validation).</summary>
public class KeySafeController : MonoBehaviour
{
    public CombinationLock combo;

    public bool IsOpen { get; private set; }

    public void TryUnlock()
    {
        // BUG-009: side effect (open) BEFORE validating combo.
        // CORRECT: validate first, then open.
        IsOpen = true;
        if (combo == null || !combo.IsDialed)
        {
            EscapeRoomOracleRegistry.Trigger("BUG-009",
                "KeySafe opened without correct combination");
            return;
        }
        EscapeRoomStateController.Instance?.SetSafeUnlocked(true);
        EscapeRoomStateController.Instance?.RegisterPuzzleSolved();

        // BUG-001: NRE — no AudioSource on this GameObject.
        GetComponent<AudioSource>().Play();
    }
}

/// <summary>Key item. Hosts BUG-004 (insert timer not reset).</summary>
public class KeyController : MonoBehaviour
{
    public float insertDuration = 1.0f;
    public bool IsInsertedFully { get; private set; }
    public bool IsInserting { get; private set; }
    private float _insertTimer = 0f;

    public void OnInsert()
    {
        // BUG-004: _insertTimer not reset. Previous interrupted insert carries over.
        // CORRECT: _insertTimer = 0f;
        IsInserting = true;
        EscapeRoomOracleRegistry.Check("BUG-004",
            _insertTimer > 0.01f,
            $"Insert timer carried over: {_insertTimer:F2}s");
    }

    public void OnRemove() { IsInserting = false; }

    private void Update()
    {
        if (!IsInserting) return;
        _insertTimer += Time.deltaTime;
        if (_insertTimer >= insertDuration)
        {
            IsInserting = false;
            IsInsertedFully = true;
            EscapeRoomStateController.Instance?.SetKeyInserted(true);
        }
    }
}

/// <summary>Exit door. Hosts BUG-003 (close not reset) and BUG-007 (open without key).</summary>
public class DoorController : MonoBehaviour
{
    public bool IsOpen { get; private set; }

    public void OpenDoor()
    {
        // BUG-007: should require KeyInserted; instead checks SafeUnlocked.
        var ctrl = EscapeRoomStateController.Instance;
        if (ctrl == null || !ctrl.SafeUnlocked) return;
        EscapeRoomOracleRegistry.Check("BUG-007",
            !ctrl.KeyInserted,
            "Door opened with SafeUnlocked but key NOT inserted");
        IsOpen = true;
        ctrl.SetDoorOpened(true);
    }

    public void CloseDoor()
    {
        // BUG-003: only does cosmetic close but IsOpen stays true.
        // CORRECT: IsOpen = false; ctrl.SetDoorOpened(false);
        EscapeRoomOracleRegistry.Check("BUG-003",
            IsOpen == true,
            "DoorController.CloseDoor() left IsOpen=true");
    }
}

/// <summary>Hint indicator (visual). Hosts BUG-008 (stays on after solve).</summary>
public class HintLight : MonoBehaviour
{
    public static HintLight Instance;
    public GameObject lightBulb;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public bool IsOn => lightBulb != null && lightBulb.activeSelf;

    public void TurnOn()  { if (lightBulb != null) lightBulb.SetActive(true); }
    public void OnSolved()
    {
        // BUG-008: NOT calling SetActive(false) — bulb remains lit after puzzle solved.
        // CORRECT: if (lightBulb != null) lightBulb.SetActive(false);
        EscapeRoomOracleRegistry.Check("BUG-008",
            lightBulb != null && lightBulb.activeSelf,
            "Hint light still on after OnSolved()");
    }
    public void ForceOff() { if (lightBulb != null) lightBulb.SetActive(false); }
}

/// <summary>Puzzle solver tracker. Hosts BUG-002 (puzzle solved without correct answer).</summary>
public class PuzzlePanelController : MonoBehaviour
{
    public string correctAnswer = "RED";

    public void SubmitAnswer(string answer)
    {
        // BUG-002: skips comparison — any answer counts as solved.
        // CORRECT: if (answer != correctAnswer) return;
        EscapeRoomOracleRegistry.Check("BUG-002",
            answer != correctAnswer,
            $"Puzzle marked solved with wrong answer: '{answer}' vs correct '{correctAnswer}'");
        EscapeRoomStateController.Instance?.RegisterPuzzleSolved();
        HintLight.Instance?.OnSolved();
    }
}
