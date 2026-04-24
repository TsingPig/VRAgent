using System.Collections.Generic;
using UnityEngine;

public static class RhythmBeatOracleRegistry
{
    public struct BugInfo { public string id, category, severity, title, script, method; }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new() { id="BUG-001", category="crash",      severity="high",   title="NRE in BeatSaberWeapon.Slash (no AudioSource)",                       script="RhythmBeatControllers.cs", method="Slash" },
        ["BUG-002"] = new() { id="BUG-002", category="functional", severity="medium", title="Block scores on wrong slash direction",                                script="RhythmBeatControllers.cs", method="OnSlash" },
        ["BUG-003"] = new() { id="BUG-003", category="state",      severity="medium", title="SongController.Stop does not reset IsPlaying",                         script="RhythmBeatControllers.cs", method="Stop" },
        ["BUG-004"] = new() { id="BUG-004", category="functional", severity="medium", title="ComboCounter combo timer not reset on retry",                          script="RhythmBeatControllers.cs", method="IncrementCombo" },
        ["BUG-005"] = new() { id="BUG-005", category="functional", severity="low",    title="BeatBlock moves in +Z (away from player)",                             script="RhythmBeatControllers.cs", method="Update" },
        ["BUG-006"] = new() { id="BUG-006", category="functional", severity="high",   title="TryFinishSong skips required-blocks check",                            script="RhythmBeatControllers.cs", method="TryFinishSong" },
        ["BUG-007"] = new() { id="BUG-007", category="state",      severity="medium", title="Song.Play uses wrong precondition (SongLoaded vs DifficultySelected)", script="RhythmBeatControllers.cs", method="Play" },
        ["BUG-008"] = new() { id="BUG-008", category="visual",     severity="low",    title="Difficulty selected indicator stuck active after Clear()",             script="RhythmBeatControllers.cs", method="Clear" },
        ["BUG-009"] = new() { id="BUG-009", category="functional", severity="medium", title="RegisterSwing increments combo before direction validation",          script="RhythmBeatControllers.cs", method="RegisterSwing" },
        ["BUG-010"] = new() { id="BUG-010", category="state",      severity="medium", title="ResetAllState does not cascade to combo/song/difficulty",              script="RhythmBeatControllers.cs", method="ResetAllState" }
    };

    private static readonly HashSet<string> _triggered = new();
    public static int TotalBugs => _bugs.Count;
    public static int TriggeredCount => _triggered.Count;

    public static void Trigger(string bugId, string detail = "")
    {
        if (!_bugs.ContainsKey(bugId) || _triggered.Contains(bugId)) return;
        _triggered.Add(bugId);
        var info = _bugs[bugId];
        var msg = $"[ORACLE:{bugId}:TRIGGERED] [{info.category}/{info.severity}] {info.title}";
        if (!string.IsNullOrEmpty(detail)) msg += $" | {detail}";
        Debug.LogWarning(msg);
    }

    public static void Check(string bugId, bool condition, string detail = "") { if (condition) Trigger(bugId, detail); }
    public static void StateAssert(string label, string desc) { Debug.Log($"[ORACLE:STATE:{label}] {desc}"); }
    public static bool IsTriggered(string bugId) => _triggered.Contains(bugId);

    public static void PrintSummary()
    {
        Debug.Log($"[ORACLE:SUMMARY] {_triggered.Count}/{_bugs.Count} bugs triggered");
        foreach (var kvp in _bugs)
            Debug.Log($"[ORACLE:SUMMARY] {kvp.Key} [{(_triggered.Contains(kvp.Key)?"TRIGGERED":"NOT_HIT")}] {kvp.Value.title}");
    }
    public static void Reset() => _triggered.Clear();
}
