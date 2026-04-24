using System.Collections.Generic;
using UnityEngine;

public static class EscapeRoomOracleRegistry
{
    public struct BugInfo { public string id, category, severity, title, script, method; }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new() { id="BUG-001", category="crash",      severity="high",   title="NRE in KeySafeController.TryUnlock (no AudioSource)",            script="EscapeRoomControllers.cs", method="TryUnlock" },
        ["BUG-002"] = new() { id="BUG-002", category="functional", severity="medium", title="Puzzle accepts wrong answer (no comparison)",                    script="EscapeRoomControllers.cs", method="SubmitAnswer" },
        ["BUG-003"] = new() { id="BUG-003", category="state",      severity="medium", title="DoorController.CloseDoor does not reset IsOpen",                  script="EscapeRoomControllers.cs", method="CloseDoor" },
        ["BUG-004"] = new() { id="BUG-004", category="functional", severity="medium", title="KeyController insert timer not reset on retry",                   script="EscapeRoomControllers.cs", method="OnInsert" },
        ["BUG-005"] = new() { id="BUG-005", category="functional", severity="low",    title="CombinationLock dial rotates in wrong direction (sign error)",    script="EscapeRoomControllers.cs", method="RotateDial" },
        ["BUG-006"] = new() { id="BUG-006", category="functional", severity="high",   title="TryEscape skips puzzle-count check",                              script="EscapeRoomControllers.cs", method="TryEscape" },
        ["BUG-007"] = new() { id="BUG-007", category="state",      severity="medium", title="DoorController uses wrong precondition (SafeUnlocked vs KeyInserted)", script="EscapeRoomControllers.cs", method="OpenDoor" },
        ["BUG-008"] = new() { id="BUG-008", category="visual",     severity="low",    title="HintLight stays on after puzzle solved",                          script="EscapeRoomControllers.cs", method="OnSolved" },
        ["BUG-009"] = new() { id="BUG-009", category="functional", severity="medium", title="KeySafe opens before validating combination",                     script="EscapeRoomControllers.cs", method="TryUnlock" },
        ["BUG-010"] = new() { id="BUG-010", category="state",      severity="medium", title="ResetAllState does not cascade to HintLight/Door",                script="EscapeRoomControllers.cs", method="ResetAllState" }
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
