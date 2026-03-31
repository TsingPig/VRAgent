"""
Oracle evaluation — detects injected bug triggers from Unity console logs.

Loads oracle definitions from ``oracle_bugs.json`` and evaluates replay
console logs to determine which bugs were triggered.

Log pattern conventions (emitted by C# OracleRegistry):
    [ORACLE:BUG-XXX:TRIGGERED] ...       — explicit oracle marker
    NullReferenceException ... Script     — exception-based detection
    [ORACLE:STATE:label] field=value      — state oracle assertion
    [ORACLE:SUMMARY] ...                  — end-of-session summary
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from .file_utils import load_json, save_json


# ---------------------------------------------------------------------------
# Oracle definition loader
# ---------------------------------------------------------------------------

def load_oracle_bugs(oracle_path: str) -> Optional[Dict[str, Any]]:
    """Load oracle_bugs.json and return the full definition dict."""
    if not os.path.isfile(oracle_path):
        return None
    data = load_json(oracle_path)
    if isinstance(data, dict) and "oracles" in data:
        return data
    return None


def find_oracle_file(output_dir: str, scene_doc: str = "") -> Optional[str]:
    """Try to locate oracle_bugs.json from various hints.

    Search order:
        1. <output_dir>/oracle_bugs.json (copied during pipeline run)
        2. Same directory as scene_doc (if provided)
        3. Walk up from output_dir looking for the file
    """
    # 1. In output directory
    candidate = os.path.join(output_dir, "oracle_bugs.json")
    if os.path.isfile(candidate):
        return candidate

    # 2. Next to scene_doc
    if scene_doc:
        doc_dir = os.path.dirname(scene_doc) if os.path.isfile(scene_doc) else scene_doc
        candidate = os.path.join(doc_dir, "oracle_bugs.json")
        if os.path.isfile(candidate):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Oracle evaluation
# ---------------------------------------------------------------------------

def evaluate_oracle_coverage(
    console_logs: List[str],
    oracle_def: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate which oracle bugs were triggered from Unity console logs.

    Args:
        console_logs: List of console log strings from replay.
        oracle_def: Loaded oracle_bugs.json dict.

    Returns:
        Dict with per-bug results and aggregate coverage metrics.
    """
    oracles = oracle_def.get("oracles", [])
    state_oracles = oracle_def.get("state_oracles", [])
    total = len(oracles)

    # Join all logs for efficient pattern matching
    all_logs = "\n".join(console_logs)

    # Evaluate each bug oracle
    results: List[Dict[str, Any]] = []
    triggered_count = 0
    severity_weights = {"high": 3, "medium": 2, "low": 1}
    weighted_total = 0
    weighted_triggered = 0

    for bug in oracles:
        bug_id = bug["id"]
        detection = bug.get("detection", {})
        det_type = detection.get("type", "")
        pattern = detection.get("pattern", "")

        triggered = False

        if det_type == "oracle_marker":
            # Look for [ORACLE:BUG-XXX:TRIGGERED]
            triggered = f"[ORACLE:{bug_id}:TRIGGERED]" in all_logs
        elif det_type == "exception":
            # Regex match on exception pattern
            if pattern:
                triggered = bool(re.search(pattern, all_logs, re.IGNORECASE))
        else:
            # Fallback: check for the bug ID marker
            triggered = f"[ORACLE:{bug_id}:TRIGGERED]" in all_logs

        if triggered:
            triggered_count += 1

        weight = severity_weights.get(bug.get("severity", "low"), 1)
        weighted_total += weight
        if triggered:
            weighted_triggered += weight

        results.append({
            "id": bug_id,
            "title": bug.get("title", ""),
            "category": bug.get("category", ""),
            "severity": bug.get("severity", ""),
            "script": bug.get("script", ""),
            "triggered": triggered,
        })

    # State oracle evaluation
    state_results: List[Dict[str, Any]] = []
    for so in state_oracles:
        so_id = so["id"]
        label = so.get("label", "")
        # Check if state oracle was logged
        marker = f"[ORACLE:STATE:{label}]"
        found = marker in all_logs
        state_results.append({
            "id": so_id,
            "label": label,
            "description": so.get("description", ""),
            "observed": found,
        })

    # Category breakdown
    category_stats: Dict[str, Dict[str, int]] = {}
    for r in results:
        cat = r["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "triggered": 0}
        category_stats[cat]["total"] += 1
        if r["triggered"]:
            category_stats[cat]["triggered"] += 1

    # Severity breakdown
    severity_stats: Dict[str, Dict[str, int]] = {}
    for r in results:
        sev = r["severity"]
        if sev not in severity_stats:
            severity_stats[sev] = {"total": 0, "triggered": 0}
        severity_stats[sev]["total"] += 1
        if r["triggered"]:
            severity_stats[sev]["triggered"] += 1

    coverage_pct = (triggered_count / total * 100) if total > 0 else 0.0
    weighted_pct = (weighted_triggered / weighted_total * 100) if weighted_total > 0 else 0.0

    return {
        "total_bugs": total,
        "triggered_bugs": triggered_count,
        "coverage_pct": coverage_pct,
        "weighted_coverage_pct": weighted_pct,
        "results": results,
        "category_stats": category_stats,
        "severity_stats": severity_stats,
        "state_oracles": state_results,
    }


# ---------------------------------------------------------------------------
# Copy oracle definition to output directory (for pipeline runs)
# ---------------------------------------------------------------------------

def copy_oracle_to_output(scene_doc: str, output_dir: str) -> Optional[str]:
    """Copy oracle_bugs.json from scene directory to output directory.

    Called during pipeline run so that visualization can find it later.
    """
    if not scene_doc:
        return None
    doc_dir = os.path.dirname(scene_doc) if os.path.isfile(scene_doc) else scene_doc
    src = os.path.join(doc_dir, "oracle_bugs.json")
    if not os.path.isfile(src):
        return None
    dst = os.path.join(output_dir, "oracle_bugs.json")
    import shutil
    shutil.copy2(src, dst)
    return dst
