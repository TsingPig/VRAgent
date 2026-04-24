using UnityEngine;

// =============================================================================
// MiniGame_RhythmBeat — All gameplay controllers in one file (10 injected bugs)
// =============================================================================

/// <summary>Central state machine: 7-step flow (PowerOn → SongLoaded → DifficultySelected →
/// SaberHeld → SongPlaying → AllBlocksHit → ScoreSubmitted).</summary>
public class RhythmBeatStateController : MonoBehaviour
{
    public static RhythmBeatStateController Instance;

    public bool PowerOn, SongLoaded, DifficultySelected, SaberHeld, SongPlaying, ScoreSubmitted, GameComplete;
    public int  BlocksHit;
    public int  BlocksRequired = 8;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)              { PowerOn = v;            RhythmBeatOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetSongLoaded(bool v)           { SongLoaded = v; }
    public void SetDifficultySelected(bool v)   { DifficultySelected = v; }
    public void SetSaberHeld(bool v)            { SaberHeld = v; }
    public void SetSongPlaying(bool v)          { SongPlaying = v; }
    public void RegisterBlockHit()              { BlocksHit++; RhythmBeatOracleRegistry.StateAssert("Hit", $"BlocksHit={BlocksHit}/{BlocksRequired}"); }
    public void SetScoreSubmitted(bool v)       { ScoreSubmitted = v; }

    /// <summary>Mark complete — REQUIRES all blocks hit.</summary>
    public void TryFinishSong()
    {
        // BUG-006: skips BlocksHit >= BlocksRequired check.
        RhythmBeatOracleRegistry.Check("BUG-006",
            BlocksHit < BlocksRequired,
            $"Song complete with only {BlocksHit}/{BlocksRequired} blocks");
        GameComplete = true;
    }

    /// <summary>Reset everything — should cascade to combo / song / difficulty UI.</summary>
    public void ResetAllState()
    {
        PowerOn = SongLoaded = DifficultySelected = SaberHeld = SongPlaying = ScoreSubmitted = GameComplete = false;
        BlocksHit = 0;
        // BUG-010: forgets to cascade reset to ComboCounter / SongController / DifficultySelector.
        RhythmBeatOracleRegistry.Check("BUG-010",
            ComboCounter.Instance != null && ComboCounter.Instance.CurrentCombo > 0,
            "ResetAllState left combo counter non-zero");
    }
}

/// <summary>Light saber — Grab-able weapon. Hosts BUG-001 (NRE) and BUG-009 (combo before validation).</summary>
public class BeatSaberWeapon : MonoBehaviour
{
    public string saberColor = "blue"; // "blue" or "red"

    public void OnGrab()
    {
        RhythmBeatStateController.Instance?.SetSaberHeld(true);
    }
    public void OnRelease()
    {
        RhythmBeatStateController.Instance?.SetSaberHeld(false);
    }

    /// <summary>Player slashes the saber — direction in {"up","down","left","right"}.</summary>
    public void Slash(string direction)
    {
        // BUG-001: NRE — no AudioSource on this GameObject.
        // CORRECT: var s = GetComponent<AudioSource>(); if (s != null) s.Play();
        GetComponent<AudioSource>().Play();
    }

    /// <summary>Register a swing: increments combo BEFORE validating direction (bug).</summary>
    public void RegisterSwing(string direction, BeatBlock block)
    {
        // BUG-009: side-effect (combo increment) BEFORE validating direction.
        // CORRECT: validate direction first, then increment.
        ComboCounter.Instance?.IncrementCombo();
        if (block == null || block.requiredDirection != direction)
        {
            RhythmBeatOracleRegistry.Trigger("BUG-009",
                $"Combo incremented before direction validation (block dir={block?.requiredDirection}, swing={direction})");
            return;
        }
        block.OnSlash(direction, true);
    }
}

/// <summary>Cube block flying toward player. Hosts BUG-002 (no direction match) and BUG-005 (wrong axis).</summary>
public class BeatBlock : MonoBehaviour
{
    public string requiredDirection = "down";
    public float  speed = 4f;

    public bool IsHit { get; private set; }

    private void Update()
    {
        // BUG-005: moves +Z (away from player) instead of -Z (toward player).
        // CORRECT: transform.position += Vector3.back * speed * Time.deltaTime;
        transform.position += Vector3.forward * speed * Time.deltaTime;
        RhythmBeatOracleRegistry.Check("BUG-005",
            speed > 0 && transform.position.z > 0.5f,
            $"Block moving in +Z direction (wrong way) at z={transform.position.z:F2}");
    }

    /// <summary>Called when slashed. validDirection should be checked but bug skips it.</summary>
    public void OnSlash(string slashDir, bool _ignored)
    {
        // BUG-002: scores even when slash direction != requiredDirection.
        // CORRECT: if (slashDir != requiredDirection) return;
        IsHit = true;
        RhythmBeatOracleRegistry.Check("BUG-002",
            slashDir != requiredDirection,
            $"Block scored on wrong direction: required={requiredDirection} got={slashDir}");
        ScoreBoard.Instance?.AddScore(100);
        RhythmBeatStateController.Instance?.RegisterBlockHit();
    }

    /// <summary>VRAgent helper: trigger an obviously-wrong slash to expose BUG-002.</summary>
    public void ForceSlashWrongDirection() => OnSlash("up", true);
}

/// <summary>Combo timer/counter. Hosts BUG-004 (combo timer not reset on retry).</summary>
public class ComboCounter : MonoBehaviour
{
    public static ComboCounter Instance;
    public float comboWindow = 1.0f;
    public int   CurrentCombo { get; private set; }
    private float _comboTimer = 0f;
    private bool  _comboActive = false;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void IncrementCombo()
    {
        // BUG-004: when starting a new combo after a miss/break, _comboTimer is NOT reset.
        // Stale timer from previous combo persists → next IncrementCombo can immediately
        // exceed comboWindow and the combo "instantly times out".
        // CORRECT: if (!_comboActive) _comboTimer = 0f;
        CurrentCombo++;
        _comboActive = true;
        RhythmBeatOracleRegistry.Check("BUG-004",
            _comboTimer > comboWindow * 0.5f && CurrentCombo == 1,
            $"Combo timer carried over: {_comboTimer:F2}s of {comboWindow:F2}s");
    }

    public void BreakCombo()
    {
        CurrentCombo = 0;
        _comboActive = false;
    }

    private void Update()
    {
        if (!_comboActive) return;
        _comboTimer += Time.deltaTime;
        if (_comboTimer >= comboWindow)
        {
            _comboActive = false;
            CurrentCombo = 0;
        }
    }

    public void ResetState() { CurrentCombo = 0; _comboActive = false; _comboTimer = 0f; }
}

/// <summary>Song playback. Hosts BUG-003 (Stop doesn't reset Playing) and BUG-007 (wrong precondition).</summary>
public class SongController : MonoBehaviour
{
    public static SongController Instance;
    public bool IsPlaying { get; private set; }
    public bool SongLoaded { get; private set; }

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void LoadSong(string name) { SongLoaded = true; RhythmBeatStateController.Instance?.SetSongLoaded(true); }

    public void Play()
    {
        // BUG-007: should require DifficultySelected, not just SongLoaded.
        // CORRECT: if (!RhythmBeatStateController.Instance.DifficultySelected) return;
        var ctrl = RhythmBeatStateController.Instance;
        if (ctrl == null || !ctrl.SongLoaded) return;
        RhythmBeatOracleRegistry.Check("BUG-007",
            !ctrl.DifficultySelected,
            "Song.Play used wrong precondition (SongLoaded vs DifficultySelected)");
        IsPlaying = true;
        ctrl.SetSongPlaying(true);
    }

    public void Stop()
    {
        // BUG-003: only zeros local timing but IsPlaying remains true.
        // CORRECT: IsPlaying = false; ctrl.SetSongPlaying(false);
        RhythmBeatOracleRegistry.Check("BUG-003",
            IsPlaying == true,
            "SongController.Stop() left IsPlaying=true");
    }

    public void ForceStop() { IsPlaying = false; RhythmBeatStateController.Instance?.SetSongPlaying(false); }
}

/// <summary>Difficulty UI selector. Hosts BUG-008 (visual indicator stuck).</summary>
public class DifficultySelector : MonoBehaviour
{
    public GameObject selectedIndicator; // visual badge
    public string Selected { get; private set; } = "";

    public void Select(string difficulty)
    {
        Selected = difficulty;
        if (selectedIndicator != null) selectedIndicator.SetActive(true);
        RhythmBeatStateController.Instance?.SetDifficultySelected(true);
    }

    public void Clear()
    {
        Selected = "";
        // BUG-008: indicator NOT deactivated — UI shows stale "selected" highlight.
        // CORRECT: if (selectedIndicator != null) selectedIndicator.SetActive(false);
        RhythmBeatStateController.Instance?.SetDifficultySelected(false);
        RhythmBeatOracleRegistry.Check("BUG-008",
            selectedIndicator != null && selectedIndicator.activeSelf,
            "Difficulty indicator stuck active after Clear()");
    }
}

/// <summary>Score tracker.</summary>
public class ScoreBoard : MonoBehaviour
{
    public static ScoreBoard Instance;
    public int Score { get; private set; }

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void AddScore(int v) { Score += v; }
    public void SubmitScore() { RhythmBeatStateController.Instance?.SetScoreSubmitted(true); }
    public void ResetState() { Score = 0; }
}
