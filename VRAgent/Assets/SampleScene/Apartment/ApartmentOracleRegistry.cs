using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Central oracle registry for Apartment benchmark bugs.
/// Tracks injected bugs and emits structured [ORACLE] markers to Unity console
/// so the VRAgent 2.0 pipeline can measure oracle coverage.
///
/// Log format: [ORACLE:BUG-XXX:TRIGGERED] description
/// Log format: [ORACLE:STATE:label] field=value
/// </summary>
public static class ApartmentOracleRegistry
{
    // ── Bug metadata ─────────────────────────────────────────────────
    public struct BugInfo
    {
        public string id;
        public string category;   // crash | functional | state | visual
        public string severity;   // high | medium | low
        public string title;
        public string script;
        public string method;
        public bool triggered;
    }

    private static readonly Dictionary<string, BugInfo> _bugs = new()
    {
        ["BUG-001"] = new BugInfo
        {
            id = "BUG-001", category = "crash", severity = "high",
            title = "NullReferenceException in CoffeeMachineController.FinishBrew",
            script = "CoffeeMachineController.cs", method = "FinishBrew"
        },
        ["BUG-002"] = new BugInfo
        {
            id = "BUG-002", category = "functional", severity = "medium",
            title = "Coffee machine brews without cup in socket",
            script = "CoffeeMachineController.cs", method = "TryStartBrew"
        },
        ["BUG-003"] = new BugInfo
        {
            id = "BUG-003", category = "state", severity = "medium",
            title = "Circuit breaker OFF does not reset PowerOn state",
            script = "CircuitBreakerController.cs", method = "Toggle"
        },
        ["BUG-004"] = new BugInfo
        {
            id = "BUG-004", category = "functional", severity = "medium",
            title = "Toaster timer not reset on bread re-insert",
            script = "ToasterController.cs", method = "OnBreadInserted"
        },
        ["BUG-005"] = new BugInfo
        {
            id = "BUG-005", category = "functional", severity = "low",
            title = "Window blind opens downward instead of upward (sign error)",
            script = "WindowBlindController.cs", method = "Start"
        },
        ["BUG-006"] = new BugInfo
        {
            id = "BUG-006", category = "functional", severity = "high",
            title = "Faucet washes dishes without power — skips hot-water gate",
            script = "FaucetController.cs", method = "TryWashDishes"
        },
        ["BUG-007"] = new BugInfo
        {
            id = "BUG-007", category = "state", severity = "medium",
            title = "Power enables with key pickup only — skips mailbox unlock step",
            script = "ApartmentStateController.cs", method = "SetPowerOn"
        },
        ["BUG-008"] = new BugInfo
        {
            id = "BUG-008", category = "visual", severity = "low",
            title = "Fridge alarm indicator stays on after door closed",
            script = "FridgeDoorController.cs", method = "Toggle"
        },
        ["BUG-009"] = new BugInfo
        {
            id = "BUG-009", category = "functional", severity = "medium",
            title = "TV CycleChannel calls SetTvNewsWatched before power check",
            script = "TVController.cs", method = "CycleChannel"
        },
        ["BUG-010"] = new BugInfo
        {
            id = "BUG-010", category = "state", severity = "medium",
            title = "ResetAllState does not reset downstream controller flags",
            script = "ApartmentStateController.cs", method = "ResetAllState"
        }
    };

    private static readonly HashSet<string> _triggered = new();

    /// <summary>Number of defined oracles.</summary>
    public static int TotalBugs => _bugs.Count;

    /// <summary>Number of triggered oracles this session.</summary>
    public static int TriggeredCount => _triggered.Count;

    // ── Trigger ──────────────────────────────────────────────────────

    /// <summary>
    /// Report that a bug oracle has been triggered.
    /// Emits a structured log line that the Python pipeline can grep.
    /// </summary>
    public static void Trigger(string bugId, string detail = "")
    {
        if (!_bugs.ContainsKey(bugId)) return;
        if (_triggered.Contains(bugId)) return; // report only once per session

        _triggered.Add(bugId);
        var info = _bugs[bugId];
        string msg = $"[ORACLE:{bugId}:TRIGGERED] [{info.category}/{info.severity}] {info.title}";
        if (!string.IsNullOrEmpty(detail))
            msg += $" | {detail}";

        Debug.LogWarning(msg);
    }

    /// <summary>
    /// Conditional trigger: only fires if condition is true.
    /// </summary>
    public static void Check(string bugId, bool condition, string detail = "")
    {
        if (condition) Trigger(bugId, detail);
    }

    // ── State oracle ─────────────────────────────────────────────────

    /// <summary>
    /// Emit a state oracle snapshot line.
    /// Format: [ORACLE:STATE:label] field1=v1 | field2=v2 ...
    /// </summary>
    public static void StateAssert(string label, string stateDescription)
    {
        Debug.Log($"[ORACLE:STATE:{label}] {stateDescription}");
    }

    // ── Query ────────────────────────────────────────────────────────

    public static bool IsTriggered(string bugId) => _triggered.Contains(bugId);

    public static IReadOnlyDictionary<string, BugInfo> AllBugs => _bugs;

    /// <summary>Print summary of oracle coverage to console.</summary>
    public static void PrintSummary()
    {
        Debug.Log($"[ORACLE:SUMMARY] {_triggered.Count}/{_bugs.Count} bugs triggered");
        foreach (var kvp in _bugs)
        {
            string status = _triggered.Contains(kvp.Key) ? "TRIGGERED" : "NOT_HIT";
            Debug.Log($"[ORACLE:SUMMARY] {kvp.Key} [{status}] {kvp.Value.title}");
        }
    }

    /// <summary>Reset for new test session.</summary>
    public static void Reset()
    {
        _triggered.Clear();
    }
}
