using System.Collections.Generic;
using UnityEngine;

// =============================================================================
// MiniGame_BowlingSports — All controllers (10 injected bugs)
// 8-step flow: PowerOn → BallGrabbed → BallReleased → BallRolled →
//   PinsKnocked → FrameScored → LaneReset → GameComplete
// =============================================================================

public class BowlingStateController : MonoBehaviour
{
    public static BowlingStateController Instance;
    public bool PowerOn, BallGrabbed, BallReleased, BallRolled, FrameScored, LaneReset, GameComplete;
    public int  PinsKnocked;
    public int  PinsRequired = 10;
    public int  CurrentFrame;
    public int  FramesRequired = 10;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)        { PowerOn = v;        BowlingOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetBallGrabbed(bool v)    { BallGrabbed = v; }
    public void SetBallReleased(bool v)   { BallReleased = v; }
    public void SetBallRolled(bool v)     { BallRolled = v; }
    public void RegisterPinKnocked()      { PinsKnocked++; BowlingOracleRegistry.StateAssert("Pins", $"Knocked={PinsKnocked}/{PinsRequired}"); }

    public void TryFinishGame()
    {
        // BUG-006: skips required frames AND pins check.
        BowlingOracleRegistry.Check("BUG-006",
            CurrentFrame < FramesRequired,
            $"Game complete after only frame {CurrentFrame}/{FramesRequired}");
        GameComplete = true;
    }

    public void ResetAllState()
    {
        PowerOn = BallGrabbed = BallReleased = BallRolled = FrameScored = LaneReset = GameComplete = false;
        PinsKnocked = 0; CurrentFrame = 0;
        // BUG-010: forgets to cascade to Scoreboard / PinSetter / LaneController.
        BowlingOracleRegistry.Check("BUG-010",
            FrameScoreboard.Instance != null && FrameScoreboard.Instance.TotalScore > 0,
            "ResetAllState left scoreboard non-zero");
    }
}

/// <summary>Bowling ball. Hosts BUG-001 (NRE) and BUG-009 (score before pin validation).</summary>
public class BowlingBall : MonoBehaviour
{
    public LaneController lane;

    public void OnGrab()    { BowlingStateController.Instance?.SetBallGrabbed(true); }
    public void OnRelease() { BowlingStateController.Instance?.SetBallReleased(true); }

    public void RollBall()
    {
        BowlingStateController.Instance?.SetBallRolled(true);
        // BUG-001: NRE — no AudioSource on ball GameObject.
        GetComponent<AudioSource>().Play();
    }

    /// <summary>Mark frame as scored — bug increments score BEFORE checking lane.PinsKnocked.</summary>
    public void RegisterFrameResult()
    {
        // BUG-009: side effect (frame scored + score added) BEFORE validating pins.
        FrameScoreboard.Instance?.AddFrameScore(10);
        if (BowlingStateController.Instance != null) BowlingStateController.Instance.CurrentFrame++;
        if (lane == null || lane.PinsKnockedThisFrame == 0)
        {
            BowlingOracleRegistry.Trigger("BUG-009",
                "Frame scored before validating pin count");
            return;
        }
    }
}

/// <summary>Single pin. Hosts BUG-002 (counted without contact) and BUG-005 (wrong tilt axis).</summary>
public class BowlingPin : MonoBehaviour
{
    public bool HasFallen { get; private set; }
    public LaneController lane;

    /// <summary>Called by collision OR external Trigger. wasRealCollision should gate the count.</summary>
    public void OnFall(bool wasRealCollision)
    {
        // BUG-002: skips wasRealCollision check — pin counts as fallen on any call.
        if (HasFallen) return;
        HasFallen = true;
        BowlingOracleRegistry.Check("BUG-002",
            !wasRealCollision,
            "Pin counted as fallen with no real collision");
        if (lane != null) lane.RegisterPinFall(this);
        BowlingStateController.Instance?.RegisterPinKnocked();

        // BUG-005: tilts in -X (which buries pin into ground in this scene) instead of +X.
        // CORRECT: transform.Rotate(90, 0, 0);
        transform.Rotate(-90, 0, 0);
        BowlingOracleRegistry.Check("BUG-005", true, "Pin tilted in -X axis (buries into ground)");
    }

    public void ForceFallWithoutContact() => OnFall(false);
    public void Reset() { HasFallen = false; transform.localRotation = Quaternion.identity; }
}

/// <summary>Lane state + reset cycle. Hosts BUG-003 (Reset doesn't clear Active) and BUG-004 (timer not reset).</summary>
public class LaneController : MonoBehaviour
{
    public List<BowlingPin> pins = new();
    public bool IsActive { get; private set; }
    public int  PinsKnockedThisFrame { get; private set; }
    public float resetDuration = 1.5f;
    public bool IsResetting { get; private set; }
    private float _resetTimer = 0f;

    public void StartFrame()
    {
        IsActive = true;
        PinsKnockedThisFrame = 0;
    }

    public void EndFrame()
    {
        // BUG-003: only zeros pin count, IsActive stays true.
        PinsKnockedThisFrame = 0;
        BowlingOracleRegistry.Check("BUG-003",
            IsActive == true,
            "LaneController.EndFrame() left IsActive=true");
    }

    public void RegisterPinFall(BowlingPin pin) { PinsKnockedThisFrame++; }

    public void StartReset()
    {
        // BUG-004: _resetTimer not reset to 0 on retry.
        IsResetting = true;
        BowlingOracleRegistry.Check("BUG-004",
            _resetTimer > 0.01f,
            $"Reset timer carried over: {_resetTimer:F2}s");
    }

    public void CancelReset() { IsResetting = false; }

    private void Update()
    {
        if (!IsResetting) return;
        _resetTimer += Time.deltaTime;
        if (_resetTimer >= resetDuration)
        {
            IsResetting = false;
            foreach (var p in pins) if (p != null) p.Reset();
            BowlingStateController.Instance?.LaneReset.Equals(true);
        }
    }
}

/// <summary>Score panel. Hosts BUG-007 (wrong precondition).</summary>
public class FrameScoreboard : MonoBehaviour
{
    public static FrameScoreboard Instance;
    public int TotalScore { get; private set; }
    public int CurrentFrameScore { get; private set; }

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void AddFrameScore(int v)
    {
        // BUG-007: should require BowlingStateController.BallReleased; checks BallGrabbed.
        var ctrl = BowlingStateController.Instance;
        if (ctrl == null) return;
        BowlingOracleRegistry.Check("BUG-007",
            ctrl.BallGrabbed && !ctrl.BallReleased,
            "Score added with wrong precondition (BallGrabbed vs BallReleased)");
        CurrentFrameScore = v;
        TotalScore += v;
    }

    public void ResetState() { TotalScore = 0; CurrentFrameScore = 0; }
}

/// <summary>Pin reset light — visual indicator. Hosts BUG-008 (light stuck on).</summary>
public class PinResetLight : MonoBehaviour
{
    public GameObject lightBulb;
    public float duration = 0.5f;

    private float _timer = 0f;
    private bool _on = false;

    public void Flash()
    {
        if (lightBulb != null) lightBulb.SetActive(true);
        _on = true;
        _timer = 0f;
    }

    private void Update()
    {
        if (!_on) return;
        _timer += Time.deltaTime;
        if (_timer >= duration)
        {
            // BUG-008: missing SetActive(false).
            _on = false;
            BowlingOracleRegistry.Check("BUG-008",
                lightBulb != null && lightBulb.activeSelf,
                "PinResetLight bulb stuck on");
        }
    }
}
