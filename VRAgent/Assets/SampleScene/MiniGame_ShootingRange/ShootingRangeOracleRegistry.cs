using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Oracle registry for the MiniGame_ShootingRange benchmark.
/// Mirrors the Kitchen_TestRoom OracleRegistry contract.
/// </summary>
public static class ShootingRangeOracleRegistry
{
    public struct BugInfo
    {
        public string id, category, severity, title, script, method;
    }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new BugInfo { id="BUG-001", category="crash",      severity="high",   title="NullReferenceException in WeaponController.Fire (no AudioSource)",    script="WeaponController.cs",         method="Fire" },
        ["BUG-002"] = new BugInfo { id="BUG-002", category="functional", severity="medium", title="Target awards score without bullet collision",                          script="TargetController.cs",         method="OnHit" },
        ["BUG-003"] = new BugInfo { id="BUG-003", category="state",      severity="medium", title="WaveSpawner.StopWave does not reset IsActive flag",                     script="WaveSpawner.cs",              method="StopWave" },
        ["BUG-004"] = new BugInfo { id="BUG-004", category="functional", severity="medium", title="AmmoMagazine reload timer not reset on retry — instant reload",         script="AmmoMagazine.cs",             method="OnInsert" },
        ["BUG-005"] = new BugInfo { id="BUG-005", category="functional", severity="low",    title="Target rotates with negated angle (away from player)",                  script="TargetController.cs",         method="Activate" },
        ["BUG-006"] = new BugInfo { id="BUG-006", category="functional", severity="high",   title="Game completes without checking required hit count",                    script="ShootingRangeStateController.cs", method="TryFinishGame" },
        ["BUG-007"] = new BugInfo { id="BUG-007", category="state",      severity="medium", title="ScoreManager.AwardPoints uses wrong precondition (IsActive vs IsHit)",  script="ScoreManager.cs",             method="AwardPoints" },
        ["BUG-008"] = new BugInfo { id="BUG-008", category="visual",     severity="low",    title="Muzzle flash quad stays active after visibility window",                script="MuzzleFlashController.cs",    method="Update" },
        ["BUG-009"] = new BugInfo { id="BUG-009", category="functional", severity="medium", title="Reload increments chamber before validating magazine",                  script="WeaponController.cs",         method="Reload" },
        ["BUG-010"] = new BugInfo { id="BUG-010", category="state",      severity="medium", title="ResetAllState does not cascade reset combo / wave / muzzle",            script="ShootingRangeStateController.cs", method="ResetAllState" }
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

    public static void Check(string bugId, bool condition, string detail = "")
    {
        if (condition) Trigger(bugId, detail);
    }

    public static void StateAssert(string label, string desc)
    {
        Debug.Log($"[ORACLE:STATE:{label}] {desc}");
    }

    public static bool IsTriggered(string bugId) => _triggered.Contains(bugId);

    public static void PrintSummary()
    {
        Debug.Log($"[ORACLE:SUMMARY] {_triggered.Count}/{_bugs.Count} bugs triggered");
        foreach (var kvp in _bugs)
        {
            var status = _triggered.Contains(kvp.Key) ? "TRIGGERED" : "NOT_HIT";
            Debug.Log($"[ORACLE:SUMMARY] {kvp.Key} [{status}] {kvp.Value.title}");
        }
    }

    public static void Reset() => _triggered.Clear();
}
