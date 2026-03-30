"""
Benchmark — Aggregated run statistics across scenes and models.

Stores a running log at ``<output_base>/benchmark.json`` so all experiment
runs can be compared in one place. Each entry captures:

- Scene, model, timestamps
- Token usage (input / output / total / per-agent)
- Coverage (Line / Method) from Unity CodeCoverage XML
- Pipeline stats (actions, iterations, gates, etc.)
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_utils import load_json, save_json


# ---------------------------------------------------------------------------
# Coverage XML parser
# ---------------------------------------------------------------------------

def parse_coverage_summary(coverage_report_dir: str) -> Optional[Dict[str, Any]]:
    """Parse Unity CodeCoverage ``Summary.xml`` and return key metrics.

    Args:
        coverage_report_dir: Path to ``<Project>/CodeCoverage/Report/``.

    Returns:
        Dict with line_coverage, method_coverage, covered_lines, etc.
        ``None`` if the file is not found.
    """
    summary_xml = os.path.join(coverage_report_dir, "Summary.xml")
    if not os.path.isfile(summary_xml):
        return None

    try:
        tree = ET.parse(summary_xml)
        root = tree.getroot()
        s = root.find("Summary")
        if s is None:
            return None

        def _txt(tag: str, default: str = "0") -> str:
            el = s.find(tag)
            return el.text if el is not None and el.text else default

        return {
            "generated_on": _txt("Generatedon", ""),
            "line_coverage": float(_txt("Linecoverage")),
            "method_coverage": float(_txt("Methodcoverage")),
            "covered_lines": int(_txt("Coveredlines")),
            "coverable_lines": int(_txt("Coverablelines")),
            "total_lines": int(_txt("Totallines")),
            "covered_methods": int(_txt("Coveredmethods")),
            "total_methods": int(_txt("Totalmethods")),
            "classes": int(_txt("Classes")),
        }
    except Exception as exc:
        print(f"[BENCHMARK] Failed to parse {summary_xml}: {exc}")
        return None


def parse_coverage_per_class(coverage_report_dir: str) -> List[Dict[str, Any]]:
    """Parse per-class coverage from Summary.xml."""
    summary_xml = os.path.join(coverage_report_dir, "Summary.xml")
    if not os.path.isfile(summary_xml):
        return []

    try:
        tree = ET.parse(summary_xml)
        root = tree.getroot()
        classes = []
        for asm in root.iter("Assembly"):
            for cls in asm.iter("Class"):
                classes.append({
                    "name": cls.get("name", ""),
                    "line_coverage": float(cls.get("coverage", "0")),
                    "covered_lines": int(cls.get("coveredlines", "0")),
                    "coverable_lines": int(cls.get("coverablelines", "0")),
                    "method_coverage": float(cls.get("methodcoverage", "0")),
                    "covered_methods": int(cls.get("coveredmethods", "0")),
                    "total_methods": int(cls.get("totalmethods", "0")),
                })
        return classes
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Benchmark entry builder
# ---------------------------------------------------------------------------

def build_benchmark_entry(
    scene_name: str,
    model: str,
    summary: Dict[str, Any],
    iteration_logs: List[Dict],
    *,
    cost: Optional[float] = None,
    coverage_report_dir: Optional[str] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Build a single benchmark entry from pipeline outputs.

    Args:
        scene_name: Scene name (e.g. "Kitchen_TestRoom").
        model: Model name (e.g. "gpt-5.4").
        summary: The summary dict from ``_finalize()``.
        iteration_logs: List of iteration log dicts.
        cost: Optional API cost in USD.
        coverage_report_dir: Optional path to CodeCoverage/Report/ to parse.
        notes: Free-form notes.
    """
    # Timestamps from iteration logs
    timestamps = [log.get("timestamp", "") for log in iteration_logs if log.get("timestamp")]
    first_ts = min(timestamps) if timestamps else ""
    last_ts = max(timestamps) if timestamps else ""

    # Token usage
    token_usage = summary.get("token_usage", {})
    total_tokens = token_usage.get("_total", {})

    # Explorer stats
    exp = summary.get("explorer", {})

    entry: Dict[str, Any] = {
        "scene": scene_name,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "run_start": first_ts,
        "run_end": last_ts,
        "total_actions": summary.get("total_actions", 0),
        "iterations": summary.get("iterations", 0),
        "gates_solved": exp.get("gates_solved", 0),
        "gates_frontier": exp.get("gates_frontier", 0),
        "budget_remaining": exp.get("budget_remaining", 0),
        "token_usage": {
            "prompt_tokens": total_tokens.get("prompt_tokens", 0),
            "completion_tokens": total_tokens.get("completion_tokens", 0),
            "total_tokens": total_tokens.get("total_tokens", 0),
            "calls": total_tokens.get("calls", 0),
            "per_agent": {
                k: v for k, v in token_usage.items() if k != "_total"
            },
        },
    }

    if cost is not None:
        entry["cost_usd"] = cost

    # Coverage from Unity
    if coverage_report_dir:
        cov = parse_coverage_summary(coverage_report_dir)
        if cov:
            entry["coverage"] = cov
            entry["coverage"]["per_class"] = parse_coverage_per_class(coverage_report_dir)

    if notes:
        entry["notes"] = notes

    return entry


# ---------------------------------------------------------------------------
# Benchmark file I/O
# ---------------------------------------------------------------------------

def _benchmark_path(output_base: str) -> str:
    """Return the canonical benchmark.json path."""
    return os.path.join(output_base, "benchmark.json")


def load_benchmark(output_base: str) -> List[Dict[str, Any]]:
    """Load existing benchmark entries, or return empty list."""
    path = _benchmark_path(output_base)
    if os.path.isfile(path):
        try:
            data = load_json(path)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def append_benchmark(output_base: str, entry: Dict[str, Any]) -> str:
    """Append *entry* to the benchmark file and return its path."""
    entries = load_benchmark(output_base)
    entries.append(entry)
    path = _benchmark_path(output_base)
    save_json(path, entries)
    print(f"[BENCHMARK] Entry appended → {path} (total: {len(entries)} entries)")
    return path
