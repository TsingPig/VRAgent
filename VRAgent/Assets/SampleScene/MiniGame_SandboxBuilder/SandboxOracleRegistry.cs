using System.Collections.Generic;
using UnityEngine;

public static class SandboxOracleRegistry
{
    public struct BugInfo { public string id, category, severity, title, script, method; }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new() { id="BUG-001", category="crash",      severity="high",   title="NRE in BlockPlacer.PlaceBlock (no AudioSource)",                  script="SandboxControllers.cs", method="PlaceBlock" },
        ["BUG-002"] = new() { id="BUG-002", category="functional", severity="medium", title="BuildingBlock stacked with no support below",                     script="SandboxControllers.cs", method="StackOn" },
        ["BUG-003"] = new() { id="BUG-003", category="state",      severity="medium", title="ToolboxController.DeselectTool leaves IsToolActive=true",         script="SandboxControllers.cs", method="DeselectTool" },
        ["BUG-004"] = new() { id="BUG-004", category="functional", severity="medium", title="Toolbox cooldown timer not reset on retry",                       script="SandboxControllers.cs", method="TriggerCooldown" },
        ["BUG-005"] = new() { id="BUG-005", category="functional", severity="low",    title="Block rotated around X axis (lays sideways)",                    script="SandboxControllers.cs", method="Rotate90" },
        ["BUG-006"] = new() { id="BUG-006", category="functional", severity="high",   title="TryPublish skips MinBlocksToPublish check",                       script="SandboxControllers.cs", method="TryPublish" },
        ["BUG-007"] = new() { id="BUG-007", category="state",      severity="medium", title="SaveLevel accepts empty level name",                              script="SandboxControllers.cs", method="SaveLevel" },
        ["BUG-008"] = new() { id="BUG-008", category="visual",     severity="low",    title="HighlightOutline mesh stuck visible after window",                script="SandboxControllers.cs", method="Update" },
        ["BUG-009"] = new() { id="BUG-009", category="functional", severity="medium", title="Block placed before grid alignment validated",                   script="SandboxControllers.cs", method="PlaceBlock" },
        ["BUG-010"] = new() { id="BUG-010", category="state",      severity="medium", title="ResetAllState doesn't clear SaveLoad data / placed blocks",      script="SandboxControllers.cs", method="ResetAllState" }
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
