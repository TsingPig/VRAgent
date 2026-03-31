using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Central oracle registry for Kitchen_TestRoom benchmark bugs.
/// Tracks injected bugs and emits structured [ORACLE] markers to Unity console
/// so the VRAgent 2.0 pipeline can measure oracle coverage.
///
/// Log format: [ORACLE:BUG-XXX:TRIGGERED] description
/// Log format: [ORACLE:STATE:label] field=value
/// </summary>
public static class OracleRegistry
{
    // ── Bug metadata ─────────────────────────────────────────────────
    public struct BugInfo
    {
        public string id;
        public string category;   // crash | functional | state | visual | performance
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
            title = "NullReferenceException in StoveController.FinishCooking",
            script = "StoveController.cs", method = "FinishCooking"
        },
        ["BUG-002"] = new BugInfo
        {
            id = "BUG-002", category = "functional", severity = "medium",
            title = "Stove starts cooking without bowl on hob",
            script = "StoveController.cs", method = "TryStartCooking"
        },
        ["BUG-003"] = new BugInfo
        {
            id = "BUG-003", category = "state", severity = "medium",
            title = "Power toggle-off does not reset RecipeController.PowerEnabled",
            script = "PowerSwitchController.cs", method = "Toggle"
        },
        ["BUG-004"] = new BugInfo
        {
            id = "BUG-004", category = "functional", severity = "medium",
            title = "Sink wash timer not reset — instant wash on retry",
            script = "SinkWashStation.cs", method = "OnIngredientPlaced"
        },
        ["BUG-005"] = new BugInfo
        {
            id = "BUG-005", category = "functional", severity = "low",
            title = "Cabinet slides in wrong direction (sign error)",
            script = "LockedCabinetController.cs", method = "Start"
        },
        ["BUG-006"] = new BugInfo
        {
            id = "BUG-006", category = "functional", severity = "high",
            title = "ServingPlateSocket accepts uncooked dish — skips cooking gate",
            script = "ServingPlateSocket.cs", method = "OnDishPlaced"
        },
        ["BUG-007"] = new BugInfo
        {
            id = "BUG-007", category = "state", severity = "medium",
            title = "RecipeController allows power without opening pantry (wrong precondition)",
            script = "RecipeController.cs", method = "SetPowerEnabled"
        },
        ["BUG-008"] = new BugInfo
        {
            id = "BUG-008", category = "visual", severity = "low",
            title = "Badge panel stays red after successful kitchen unlock",
            script = "KitchenBadgeUnlockReceiver.cs", method = "OnBadgeInserted"
        },
        ["BUG-009"] = new BugInfo
        {
            id = "BUG-009", category = "functional", severity = "medium",
            title = "CuttingBoard calls SetIngredientCut(false) before validation",
            script = "CuttingBoardController.cs", method = "TryCut"
        },
        ["BUG-010"] = new BugInfo
        {
            id = "BUG-010", category = "state", severity = "medium",
            title = "ResetAllState does not reset downstream controller flags",
            script = "RecipeController.cs", method = "ResetAllState"
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
