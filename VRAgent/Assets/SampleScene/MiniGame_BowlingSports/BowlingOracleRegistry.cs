using System.Collections.Generic;
using UnityEngine;

public static class BowlingOracleRegistry
{
    public struct BugInfo { public string id, category, severity, title, script, method; }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new() { id="BUG-001", category="crash",      severity="high",   title="NRE in BowlingBall.RollBall (no AudioSource)",                  script="BowlingControllers.cs", method="RollBall" },
        ["BUG-002"] = new() { id="BUG-002", category="functional", severity="medium", title="Pin counts as fallen without real collision",                   script="BowlingControllers.cs", method="OnFall" },
        ["BUG-003"] = new() { id="BUG-003", category="state",      severity="medium", title="LaneController.EndFrame leaves IsActive=true",                  script="BowlingControllers.cs", method="EndFrame" },
        ["BUG-004"] = new() { id="BUG-004", category="functional", severity="medium", title="Lane reset timer not reset on retry",                           script="BowlingControllers.cs", method="StartReset" },
        ["BUG-005"] = new() { id="BUG-005", category="functional", severity="low",    title="Pin tilts in -X (buries into ground)",                          script="BowlingControllers.cs", method="OnFall" },
        ["BUG-006"] = new() { id="BUG-006", category="functional", severity="high",   title="TryFinishGame skips required frames check",                     script="BowlingControllers.cs", method="TryFinishGame" },
        ["BUG-007"] = new() { id="BUG-007", category="state",      severity="medium", title="AddFrameScore wrong precondition (BallGrabbed vs BallReleased)", script="BowlingControllers.cs", method="AddFrameScore" },
        ["BUG-008"] = new() { id="BUG-008", category="visual",     severity="low",    title="PinResetLight bulb stuck active after window",                  script="BowlingControllers.cs", method="Update" },
        ["BUG-009"] = new() { id="BUG-009", category="functional", severity="medium", title="RegisterFrameResult scores before pin validation",              script="BowlingControllers.cs", method="RegisterFrameResult" },
        ["BUG-010"] = new() { id="BUG-010", category="state",      severity="medium", title="ResetAllState doesn't cascade to Scoreboard/Lane/Pins",         script="BowlingControllers.cs", method="ResetAllState" }
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
        foreach (var kvp in _bugs) Debug.Log($"[ORACLE:SUMMARY] {kvp.Key} [{(_triggered.Contains(kvp.Key)?"TRIGGERED":"NOT_HIT")}] {kvp.Value.title}");
    }
    public static void Reset() => _triggered.Clear();
}
