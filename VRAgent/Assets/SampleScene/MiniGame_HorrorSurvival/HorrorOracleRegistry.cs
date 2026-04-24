using System.Collections.Generic;
using UnityEngine;

public static class HorrorOracleRegistry
{
    public struct BugInfo { public string id, category, severity, title, script, method; }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new() { id="BUG-001", category="crash",      severity="high",   title="NRE in FlashlightController.ToggleLight (no AudioSource)",       script="HorrorControllers.cs", method="ToggleLight" },
        ["BUG-002"] = new() { id="BUG-002", category="functional", severity="medium", title="Battery applied to flashlight without being grabbed",            script="HorrorControllers.cs", method="ApplyToFlashlight" },
        ["BUG-003"] = new() { id="BUG-003", category="state",      severity="medium", title="DoorLockController.ToggleLockOff doesn't reset IsLocked",        script="HorrorControllers.cs", method="ToggleLockOff" },
        ["BUG-004"] = new() { id="BUG-004", category="functional", severity="medium", title="EnemyAI chase timer not reset on retry",                         script="HorrorControllers.cs", method="StartChase" },
        ["BUG-005"] = new() { id="BUG-005", category="functional", severity="low",    title="Battery slot orientation upside-down (-90 vs +90)",              script="HorrorControllers.cs", method="ApplyToFlashlight" },
        ["BUG-006"] = new() { id="BUG-006", category="functional", severity="high",   title="TryEscape skips required-keys check",                            script="HorrorControllers.cs", method="TryEscape" },
        ["BUG-007"] = new() { id="BUG-007", category="state",      severity="medium", title="DoorLockController.TryUnlock checks KeyFound instead of count",  script="HorrorControllers.cs", method="TryUnlock" },
        ["BUG-008"] = new() { id="BUG-008", category="visual",     severity="low",    title="HP red bar overlay stuck active after Heal",                     script="HorrorControllers.cs", method="Heal" },
        ["BUG-009"] = new() { id="BUG-009", category="functional", severity="medium", title="Flashlight toggled before validating battery",                   script="HorrorControllers.cs", method="ToggleLight" },
        ["BUG-010"] = new() { id="BUG-010", category="state",      severity="medium", title="ResetAllState doesn't cascade to EnemyAI/Health/HUD",            script="HorrorControllers.cs", method="ResetAllState" }
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
