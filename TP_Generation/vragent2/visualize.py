"""
VRAgent 2.0 — Result Visualization Module.

Generates a self-contained HTML dashboard from pipeline / replay results.

Usage (CLI):
    python -m vragent2 --scene_name X ... --visualize
    python -m vragent2 --visualize Results_VRAgent2.0/Kitchen_TestRoom

Programmatic:
    from vragent2.visualize import generate_report
    generate_report("Results_VRAgent2.0/Kitchen_TestRoom")
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── helpers ──────────────────────────────────────────────────────────

def _load_json(path: str) -> Optional[Any]:
    """Load JSON with graceful fallback."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _latest_replay(output_dir: str) -> Optional[str]:
    """Return path to the most recent replay file, or None."""
    replay_dir = os.path.join(output_dir, "replay")
    if not os.path.isdir(replay_dir):
        return None
    replays = sorted(
        [f for f in os.listdir(replay_dir) if f.startswith("replay_") and f.endswith(".json")],
        reverse=True,
    )
    return os.path.join(replay_dir, replays[0]) if replays else None


def _escape(text: str) -> str:
    """HTML-escape a string."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ── data extraction ─────────────────────────────────────────────────

def _extract_summary(output_dir: str) -> Dict[str, Any]:
    data = _load_json(os.path.join(output_dir, "summary.json"))
    if data:
        return data
    # Fallback: build from available files
    return {}


def _extract_iteration_logs(output_dir: str) -> List[Dict[str, Any]]:
    data = _load_json(os.path.join(output_dir, "iteration_logs.json"))
    return data if isinstance(data, list) else []


def _extract_gate_graph(output_dir: str) -> Dict[str, Any]:
    data = _load_json(os.path.join(output_dir, "gate_graph.json"))
    return data if isinstance(data, dict) else {}


def _extract_session(output_dir: str) -> Dict[str, Any]:
    data = _load_json(os.path.join(output_dir, "session_state.json"))
    return data if isinstance(data, dict) else {}


def _extract_replay(output_dir: str, replay_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    path = replay_path or _latest_replay(output_dir)
    if not path:
        return None
    return _load_json(path)


# ── analysis helpers ─────────────────────────────────────────────────

def _classify_bugs(bugs: List[str]) -> Dict[str, List[str]]:
    """Categorize bug strings into exception / warning / other."""
    cats: Dict[str, List[str]] = {"exception": [], "warning": [], "other": []}
    for b in bugs:
        lower = b.lower()
        if "[exception]" in lower or "exception" in lower[:30]:
            cats["exception"].append(b)
        elif "[console_warn]" in lower or "warning" in lower[:30]:
            cats["warning"].append(b)
        else:
            cats["other"].append(b)
    return cats


def _action_type_stats(traces: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Per-action-type success/fail counts from replay traces."""
    stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0, "total": 0})
    for t in traces:
        action_str = t.get("action", "")
        atype = action_str.split(":")[0] if ":" in action_str else action_str
        stats[atype]["total"] += 1
        if t.get("success"):
            stats[atype]["ok"] += 1
        else:
            stats[atype]["fail"] += 1
    return dict(stats)


def _state_diffs(traces: List[Dict]) -> List[Dict[str, Any]]:
    """Extract meaningful state changes from traces."""
    diffs = []
    for t in traces:
        before = t.get("state_before", {})
        after = t.get("state_after", {})
        if not before or not after:
            continue
        changes = {}
        # position
        pb, pa = before.get("position", {}), after.get("position", {})
        if pb and pa:
            dist = sum((pa.get(k, 0) - pb.get(k, 0)) ** 2 for k in ("x", "y", "z")) ** 0.5
            if dist > 0.001:
                changes["position"] = f"moved {dist:.3f}u"
        # components
        cb = set(before.get("components", []))
        ca = set(after.get("components", []))
        added = ca - cb
        removed = cb - ca
        if added:
            changes["components_added"] = list(added)
        if removed:
            changes["components_removed"] = list(removed)
        # active
        if before.get("active") != after.get("active"):
            changes["active"] = f"{before.get('active')} → {after.get('active')}"
        if changes:
            diffs.append({"action": t.get("action", "?"), "changes": changes})
    return diffs


def _unique_objects(traces: List[Dict]) -> List[str]:
    """Unique object names touched in traces."""
    names = []
    seen = set()
    for t in traces:
        action = t.get("action", "")
        name = action.split(":", 1)[1] if ":" in action else action
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _gate_edge_summary(gate_graph: Dict) -> Tuple[int, int, int, List[str]]:
    """Return (total, success, fail, unique_actions) from gate graph edges."""
    edges = gate_graph.get("edges", [])
    total = len(edges)
    ok = sum(1 for e in edges if e.get("success"))
    fail = total - ok
    unique = list({e.get("action", "") for e in edges})
    return total, ok, fail, unique


# ── HTML generation ──────────────────────────────────────────────────

_CSS = """\
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0f1117;color:#e0e0e0;padding:24px}
h1{font-size:1.8rem;margin-bottom:4px;color:#fff}
h2{font-size:1.15rem;margin:28px 0 12px;color:#a0cfff;border-bottom:1px solid #2a2e3a;padding-bottom:6px}
h3{font-size:0.95rem;margin:12px 0 6px;color:#ccc}
.subtitle{color:#888;font-size:.85rem;margin-bottom:20px}
.grid{display:grid;gap:16px;margin-bottom:12px}
.grid-4{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}
.grid-3{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.grid-2{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card{background:#1a1d27;border-radius:10px;padding:18px;border:1px solid #2a2e3a}
.card-metric{text-align:center}
.card-metric .val{font-size:2rem;font-weight:700;line-height:1.2}
.card-metric .label{font-size:.75rem;color:#888;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
.green{color:#4ade80}.red{color:#f87171}.yellow{color:#fbbf24}.blue{color:#60a5fa}.purple{color:#c084fc}.cyan{color:#22d3ee}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600;margin:2px}
.badge-ok{background:#166534;color:#4ade80}.badge-fail{background:#7f1d1d;color:#fca5a5}
.badge-warn{background:#78350f;color:#fde68a}.badge-info{background:#1e3a5f;color:#93c5fd}
table{width:100%;border-collapse:collapse;font-size:.82rem;margin:8px 0}
th{background:#1e2130;text-align:left;padding:8px 10px;color:#94a3b8;font-weight:600;position:sticky;top:0}
td{padding:7px 10px;border-bottom:1px solid #1e2130}
tr:hover td{background:#1e2130}
.bar-wrap{background:#1e2130;border-radius:4px;height:18px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:4px;transition:width .5s}
.bar-text{position:absolute;right:6px;top:0;line-height:18px;font-size:.7rem;color:#fff}
.timeline{position:relative;padding-left:28px}
.timeline::before{content:'';position:absolute;left:12px;top:0;bottom:0;width:2px;background:#2a2e3a}
.tl-item{position:relative;margin-bottom:10px}
.tl-dot{position:absolute;left:-22px;top:4px;width:10px;height:10px;border-radius:50%;border:2px solid #2a2e3a}
.tl-dot.ok{background:#4ade80;border-color:#166534}.tl-dot.fail{background:#f87171;border-color:#7f1d1d}
.tl-action{font-weight:600;font-size:.85rem}.tl-detail{font-size:.75rem;color:#888;margin-top:2px}
.events-list{font-size:.75rem;color:#94a3b8;margin-top:3px}
.toggle-btn{cursor:pointer;background:#1e2130;border:1px solid #2a2e3a;color:#a0cfff;padding:4px 12px;border-radius:5px;font-size:.78rem;margin:4px 0}
.toggle-btn:hover{background:#2a2e3a}
details summary{cursor:pointer;color:#a0cfff;font-size:.82rem;margin:6px 0}
details summary:hover{color:#fff}
.log-box{max-height:260px;overflow-y:auto;background:#12141c;border:1px solid #2a2e3a;border-radius:6px;padding:10px;font-family:'Cascadia Code','Fira Code',monospace;font-size:.72rem;line-height:1.6;white-space:pre-wrap;word-break:break-all}
.log-warn{color:#fbbf24}.log-err{color:#f87171}.log-info{color:#94a3b8}
.node-graph{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.node-box{background:#1e2130;border:1px solid #2a2e3a;border-radius:8px;padding:10px 14px;min-width:110px;text-align:center}
.node-box .nn{font-weight:700;font-size:.88rem}.node-box .ns{font-size:.7rem;color:#888;margin-top:2px}
.edge-ok{border-color:#166534}.edge-fail{border-color:#7f1d1d}
.heatmap{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:6px}
.hm-cell{border-radius:6px;padding:8px 6px;text-align:center;font-size:.72rem;font-weight:600}
.search-box{width:100%;padding:8px 12px;background:#12141c;border:1px solid #2a2e3a;border-radius:6px;color:#e0e0e0;font-size:.82rem;margin-bottom:10px}
.search-box:focus{outline:none;border-color:#60a5fa}
.flex-row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
"""

_JS = """\
function filterTable(inputId,tableId){
  var f=document.getElementById(inputId).value.toLowerCase();
  var rows=document.getElementById(tableId).getElementsByTagName('tr');
  for(var i=1;i<rows.length;i++){rows[i].style.display=rows[i].textContent.toLowerCase().includes(f)?'':'none';}
}
function toggleSection(id){
  var el=document.getElementById(id);
  el.style.display=el.style.display==='none'?'block':'none';
}
"""


def _bar(pct: float, color: str = "#4ade80", width: int = 100) -> str:
    """Render an inline progress bar."""
    p = max(0.0, min(100.0, pct))
    return (
        f'<div class="bar-wrap" style="width:{width}px">'
        f'<div class="bar-fill" style="width:{p:.1f}%;background:{color}"></div>'
        f'<div class="bar-text">{p:.1f}%</div>'
        f'</div>'
    )


def _metric_card(value: Any, label: str, css_class: str = "") -> str:
    return (
        f'<div class="card card-metric">'
        f'<div class="val {css_class}">{_escape(str(value))}</div>'
        f'<div class="label">{_escape(label)}</div>'
        f'</div>'
    )


def _excepted_action_names(exceptions: List[str]) -> set:
    """Extract action names from the top-level exceptions list.

    Exception format: ``"ActionType:SourceName → message"``
    """
    names: set = set()
    for exc_str in exceptions:
        if " \u2192 " in exc_str:
            names.add(exc_str.split(" \u2192 ")[0].strip())
    return names


def _reconcile_replay(replay: Dict) -> Dict:
    """Return a *shallow copy* of *replay* with corrected success fields.

    Fixes stale data in old replay files (generated before exception-
    injection was added) by cross-referencing the top-level ``exceptions``
    list with per-trace events.  Reconciles:

    * ``traces[i]["success"]`` — override to False when the action had an
      exception (either already in events or only in top-level list).
    * ``successes`` / ``failures`` — recomputed from corrected traces.
    * ``gates_solved`` / ``gates_failed`` — recomputed consistently.
    """
    replay = dict(replay)                         # shallow copy
    exceptions = replay.get("exceptions", [])
    excepted = _excepted_action_names(exceptions)

    error_keywords = ("error:", "exception:", "bridge_error:", "import_error:")

    new_traces: List[Dict] = []
    for t in replay.get("traces", []):
        t = dict(t)                               # shallow copy
        action_name = t.get("action", "")
        events = t.get("events", [])
        joined = " ".join(events)

        # Override success → False if events contain errors, or if the
        # action appears in the top-level exceptions list.
        if any(kw in joined for kw in error_keywords):
            t["success"] = False
        elif action_name in excepted:
            t["success"] = False
        new_traces.append(t)

    replay["traces"] = new_traces

    # Recompute aggregates
    ok = sum(1 for t in new_traces if t.get("success"))
    replay["successes"] = ok
    replay["failures"] = len(new_traces) - ok

    # Recompute gate lists (unique action names, solved vs failed)
    solved: List[str] = []
    failed: List[str] = []
    seen: set = set()
    for t in new_traces:
        name = t.get("action", "")
        if name in seen:
            continue
        seen.add(name)
        if t.get("success"):
            solved.append(name)
        else:
            failed.append(name)
    replay["gates_solved"] = solved
    replay["gates_failed"] = failed

    return replay


def _section_summary(summary: Dict, replay: Optional[Dict] = None) -> str:
    """Dashboard summary cards.

    When a replay is available, gate stats are recomputed from traces
    (summary.json may be stale if generated before bug-fixes).
    """
    exp = summary.get("explorer", {})
    total_actions = summary.get("total_actions", summary.get("total_traces", 0))
    iters = summary.get("iterations", 0)
    nodes = summary.get("gate_graph_nodes", 0)
    edges = summary.get("gate_graph_edges", 0)
    coverage = exp.get("total_coverage", 0.0) * 100
    mode = exp.get("mode", "N/A")
    budget = exp.get("budget_remaining", "N/A")

    # Compute gate stats — prefer replay-derived data over stale summary.json
    if replay:
        gates_solved_list = replay.get("gates_solved", [])
        gates_failed_list = replay.get("gates_failed", [])
        gates_solved = len(gates_solved_list)
        gates_total = len(gates_solved_list) + len(gates_failed_list)
    else:
        gates_solved = exp.get("gates_solved", 0)
        gates_total = exp.get("gates_frontier", 0)

    cov_color = "green" if coverage > 50 else ("yellow" if coverage > 10 else "red")

    html = '<h2>Session Dashboard</h2><div class="grid grid-4">'
    html += _metric_card(total_actions, "Total Actions", "blue")
    html += _metric_card(iters, "Iterations", "purple")
    html += _metric_card(f"{coverage:.1f}%", "Coverage", cov_color)
    html += _metric_card(f"{gates_solved}/{gates_total}", "Gates Solved", "green" if gates_solved > 0 else "red")
    html += _metric_card(nodes, "State Nodes", "cyan")
    html += _metric_card(edges, "Gate Edges", "cyan")
    html += _metric_card(mode, "Explorer Mode", "yellow")
    html += _metric_card(budget, "Budget Left", "blue")
    html += '</div>'
    return html


def _section_replay(replay: Dict) -> str:
    """Replay overview section."""
    ts = replay.get("timestamp", "N/A")
    total = replay.get("total_actions", 0)
    executed = replay.get("executed", 0)
    successes = replay.get("successes", 0)
    failures = replay.get("failures", 0)
    exceptions = replay.get("exceptions", [])
    gates_solved = replay.get("gates_solved", [])
    gates_failed = replay.get("gates_failed", [])

    succ_pct = (successes / executed * 100) if executed > 0 else 0

    html = '<h2>Replay Results</h2>'
    html += f'<div class="subtitle">Timestamp: {_escape(ts)}</div>'
    html += '<div class="grid grid-4">'
    html += _metric_card(total, "Total Actions", "blue")
    html += _metric_card(executed, "Executed", "blue")
    html += _metric_card(successes, "Successes", "green")
    html += _metric_card(failures, "Failures", "red" if failures > 0 else "green")
    html += '</div>'

    # Gates solved/failed (from new replay output)
    if gates_solved or gates_failed:
        total_gates = len(gates_solved) + len(gates_failed)
        gate_pct = (len(gates_solved) / total_gates * 100) if total_gates > 0 else 0
        html += '<div class="grid grid-3" style="margin-top:10px">'
        html += _metric_card(f"{len(gates_solved)}/{total_gates}", "Gates Solved (Technical)", "green" if gate_pct > 50 else "red")
        html += _metric_card(len(gates_solved), "Unique Actions OK", "green")
        html += _metric_card(len(gates_failed), "Unique Actions Failed", "red" if gates_failed else "green")
        html += '</div>'

    # Success rate bar
    html += '<div style="margin:12px 0">'
    html += f'<h3>Execution Success Rate</h3>'
    html += f'<div class="bar-wrap" style="width:100%;height:24px">'
    color = "#4ade80" if succ_pct > 80 else ("#fbbf24" if succ_pct > 50 else "#f87171")
    html += f'<div class="bar-fill" style="width:{succ_pct:.1f}%;background:{color}"></div>'
    html += f'<div class="bar-text" style="font-size:.82rem">{successes}/{executed} ({succ_pct:.1f}%)</div>'
    html += '</div></div>'

    # Exceptions
    if exceptions:
        html += '<h3>Exceptions</h3>'
        html += '<div class="log-box">'
        for e in exceptions:
            html += f'<span class="log-err">{_escape(e)}</span>\n'
        html += '</div>'

    return html


def _section_action_timeline(traces: List[Dict], max_display: int = 200) -> str:
    """Interactive action timeline with state changes."""
    if not traces:
        return ""

    html = '<h2>Action Timeline</h2>'
    html += f'<input class="search-box" id="tl-search" placeholder="Filter actions..." oninput="filterTimeline()">'

    html += '<div class="timeline" id="tl-container">'
    for i, t in enumerate(traces[:max_display]):
        action = t.get("action", "?")
        success = t.get("success", False)
        duration = t.get("duration_ms", 0)
        events = t.get("events", [])
        dot_class = "ok" if success else "fail"
        badge = '<span class="badge badge-ok">OK</span>' if success else '<span class="badge badge-fail">FAIL</span>'

        html += f'<div class="tl-item" data-action="{_escape(action.lower())}">'
        html += f'<div class="tl-dot {dot_class}"></div>'
        html += f'<div class="tl-action">#{i+1} {_escape(action)} {badge}'
        if duration:
            html += f' <span style="color:#888;font-size:.72rem">{duration:.0f}ms</span>'
        html += '</div>'

        # State changes
        before = t.get("state_before", {})
        after = t.get("state_after", {})
        detail_parts = []
        if before and after:
            # Position diff
            pb, pa = before.get("position", {}), after.get("position", {})
            if pb and pa:
                dist = sum((pa.get(k, 0) - pb.get(k, 0)) ** 2 for k in ("x", "y", "z")) ** 0.5
                if dist > 0.001:
                    detail_parts.append(f"moved {dist:.3f}u")
            # Component diff
            cb = set(before.get("components", []))
            ca = set(after.get("components", []))
            added = ca - cb
            if added:
                detail_parts.append(f"+{', '.join(sorted(added))}")
            removed = cb - ca
            if removed:
                detail_parts.append(f"-{', '.join(sorted(removed))}")
            # Active change
            if before.get("active") != after.get("active"):
                detail_parts.append(f"active: {before.get('active')} → {after.get('active')}")

        if detail_parts:
            html += f'<div class="tl-detail">{_escape(" | ".join(detail_parts))}</div>'

        if events:
            html += '<details><summary>Events ({0})</summary>'.format(len(events))
            html += '<div class="events-list">' + '<br>'.join(_escape(e) for e in events) + '</div>'
            html += '</details>'

        html += '</div>'

    if len(traces) > max_display:
        html += f'<div style="color:#888;font-size:.8rem;margin-top:8px">... and {len(traces) - max_display} more actions</div>'

    html += '</div>'

    # Timeline filter JS
    html += """<script>
function filterTimeline(){
  var f=document.getElementById('tl-search').value.toLowerCase();
  var items=document.querySelectorAll('#tl-container .tl-item');
  items.forEach(function(el){el.style.display=el.getAttribute('data-action').includes(f)?'':'none';});
}
</script>"""
    return html


def _section_object_heatmap(traces: List[Dict]) -> str:
    """Object interaction heatmap."""
    if not traces:
        return ""
    counts: Counter = Counter()
    successes: Counter = Counter()
    for t in traces:
        action = t.get("action", "")
        name = action.split(":", 1)[1] if ":" in action else action
        counts[name] += 1
        if t.get("success"):
            successes[name] += 1

    max_count = max(counts.values()) if counts else 1

    html = '<h2>Object Interaction Heatmap</h2>'
    html += '<div class="heatmap">'
    for obj, count in counts.most_common():
        ok = successes.get(obj, 0)
        fail = count - ok
        intensity = count / max_count
        # Color: green if mostly success, red if mostly fail, blend otherwise
        ok_ratio = ok / count if count > 0 else 0
        r = int(30 + (1 - ok_ratio) * intensity * 180)
        g = int(30 + ok_ratio * intensity * 180)
        b = 30
        a = 0.4 + intensity * 0.6
        html += (
            f'<div class="hm-cell" style="background:rgba({r},{g},{b},{a:.2f})">'
            f'<div>{_escape(obj)}</div>'
            f'<div style="font-size:.65rem;margin-top:2px">{ok}✓ {fail}✗ ({count})</div>'
            f'</div>'
        )
    html += '</div>'
    return html


def _section_gate_graph(gate_data: Dict) -> str:
    """Gate graph visualization."""
    nodes = gate_data.get("nodes", {})
    edges = gate_data.get("edges", [])
    if not nodes and not edges:
        return ""

    html = '<h2>Gate Graph (State Space)</h2>'

    # Nodes
    html += '<h3>State Nodes</h3><div class="node-graph">'
    for nid, ninfo in nodes.items():
        label = ninfo.get("label", nid)
        room = ninfo.get("room", "")
        html += (
            f'<div class="node-box">'
            f'<div class="nn">{_escape(label)}</div>'
            f'<div class="ns">{_escape(room)}</div>'
            f'</div>'
        )
    html += '</div>'

    # Edge stats
    total, ok, fail, unique_actions = _gate_edge_summary(gate_data)
    html += '<div class="grid grid-3" style="margin:10px 0">'
    html += _metric_card(total, "Total Edges", "blue")
    html += _metric_card(ok, "Successful", "green")
    html += _metric_card(fail, "Blocked", "red")
    html += '</div>'

    # Edge table
    html += '<h3>Edge Details</h3>'
    html += '<input class="search-box" id="edge-search" placeholder="Filter edges..." oninput="filterTable(\'edge-search\',\'edge-table\')">'
    html += '<div style="max-height:300px;overflow-y:auto">'
    html += '<table id="edge-table"><tr><th>From</th><th>Action</th><th>To</th><th>Status</th><th>Evidence</th></tr>'
    for e in edges:
        from_s = e.get("from_state", "")
        to_s = e.get("to_state", "")
        action = e.get("action", "")
        success = e.get("success", False)
        evidence = e.get("evidence", "")
        ft = e.get("failure_type", "")
        badge = '<span class="badge badge-ok">OK</span>' if success else '<span class="badge badge-fail">BLOCKED</span>'
        if ft:
            badge += f' <span class="badge badge-warn">{_escape(ft)}</span>'
        short_evidence = (evidence[:80] + "...") if len(evidence) > 80 else evidence
        html += (
            f'<tr><td>{_escape(from_s)}</td><td>{_escape(action)}</td>'
            f'<td>{_escape(to_s)}</td><td>{badge}</td>'
            f'<td style="color:#888;font-size:.72rem" title="{_escape(evidence)}">{_escape(short_evidence)}</td></tr>'
        )
    html += '</table></div>'
    return html


def _section_iteration_logs(logs: List[Dict]) -> str:
    """Per-iteration analysis."""
    if not logs:
        return ""

    html = '<h2>Iteration Logs</h2>'
    for it in logs:
        idx = it.get("iteration", "?")
        obj = it.get("object", "?")
        mode = it.get("mode", "?")
        planned = it.get("planned_actions", 0)
        verified = it.get("verified_actions", 0)
        vs = it.get("verifier_score", 0)
        bugs = it.get("bugs", [])
        cd = it.get("coverage_delta", 0)
        ts = it.get("timestamp", "")

        mode_color = {"Expand": "blue", "Exploit": "yellow", "Recover": "red"}.get(mode, "cyan")

        html += f'<details><summary>Iteration {idx}: <b>{_escape(obj)}</b> '
        html += f'<span class="badge badge-info">{_escape(mode)}</span> '
        html += f'— {planned} actions, verifier={vs:.2f}, bugs={len(bugs)}</summary>'
        html += '<div class="card" style="margin:6px 0 12px">'

        # Metrics row
        html += '<div class="grid grid-4" style="margin-bottom:10px">'
        html += _metric_card(planned, "Planned", "blue")
        html += _metric_card(verified, "Verified", "green" if vs >= 0.8 else "yellow")
        html += _metric_card(f"{vs:.2f}", "Verifier Score", "green" if vs >= 0.8 else "red")
        html += _metric_card(f"{cd:.4f}", "Coverage Δ", "green" if cd > 0 else "red")
        html += '</div>'

        # Bugs
        if bugs:
            html += '<h3>Bug Signals</h3><div class="log-box" style="max-height:160px">'
            for b in bugs:
                cls = "log-err" if "[exception]" in b.lower() else ("log-warn" if "[console_warn]" in b.lower() else "log-info")
                html += f'<span class="{cls}">{_escape(b)}</span>\n'
            html += '</div>'

        # Gate hints
        gate_hints = it.get("gate_hints", [])
        if gate_hints:
            html += '<h3>Gate Hints</h3><table><tr><th>Type</th><th>Missing</th><th>Confidence</th><th>Evidence</th></tr>'
            for gh in gate_hints:
                ft = gh.get("failure_type", "")
                mc = gh.get("missing_condition", "")
                conf = gh.get("confidence", 0)
                ev = gh.get("evidence", "")
                short_ev = (ev[:80] + "...") if len(ev) > 80 else ev
                html += (
                    f'<tr><td><span class="badge badge-warn">{_escape(ft)}</span></td>'
                    f'<td>{_escape(mc)}</td><td>{conf:.2f}</td>'
                    f'<td style="color:#888;font-size:.72rem">{_escape(short_ev)}</td></tr>'
                )
            html += '</table>'

        # State delta
        sd = it.get("state_delta", {})
        if sd:
            html += '<h3>State Delta</h3>'
            for key in ("expected_changes", "unexpected_changes", "semantic_failures", "gates_still_blocked"):
                items = sd.get(key, [])
                if items:
                    label_map = {
                        "expected_changes": ("Expected", "badge-info"),
                        "unexpected_changes": ("Unexpected", "badge-warn"),
                        "semantic_failures": ("Semantic Fail", "badge-fail"),
                        "gates_still_blocked": ("Still Blocked", "badge-fail"),
                    }
                    label, badge_cls = label_map.get(key, (key, "badge-info"))
                    html += f'<div style="margin:4px 0"><span class="badge {badge_cls}">{label}</span></div>'
                    html += '<ul style="margin:0 0 8px 20px;font-size:.78rem;color:#aaa">'
                    for item in items:
                        html += f'<li>{_escape(item)}</li>'
                    html += '</ul>'

        # Observer suggestion
        obs = it.get("observer_suggestion", "")
        if obs:
            html += f'<h3>Observer Suggestion</h3><div style="font-size:.8rem;color:#a0cfff;padding:6px;background:#12141c;border-radius:4px">{_escape(obs)}</div>'

        html += '</div></details>'

    return html


def _section_console_logs(replay: Dict) -> str:
    """Console log viewer from replay."""
    logs = replay.get("console_logs", [])
    if not logs:
        return ""

    html = '<h2>Console Logs</h2>'
    html += f'<div class="subtitle">{len(logs)} entries</div>'

    # Stats
    warn_count = sum(1 for l in logs if "[warning]" in l.lower() or "warn" in l.lower()[:10])
    err_count = sum(1 for l in logs if "[error]" in l.lower() or "exception" in l.lower())
    info_count = len(logs) - warn_count - err_count

    html += '<div class="grid grid-3" style="margin-bottom:8px">'
    html += _metric_card(info_count, "Info", "blue")
    html += _metric_card(warn_count, "Warnings", "yellow")
    html += _metric_card(err_count, "Errors", "red")
    html += '</div>'

    html += '<input class="search-box" id="log-search" placeholder="Filter logs..." oninput="filterLogs()">'
    html += '<div class="log-box" id="log-container" style="max-height:400px">'
    for log in logs:
        lower = log.lower()
        if "[error]" in lower or "exception" in lower:
            cls = "log-err"
        elif "[warning]" in lower or "warn" in lower[:10]:
            cls = "log-warn"
        else:
            cls = "log-info"
        html += f'<div class="log-line {cls}">{_escape(log)}</div>'
    html += '</div>'

    html += """<script>
function filterLogs(){
  var f=document.getElementById('log-search').value.toLowerCase();
  var lines=document.querySelectorAll('#log-container .log-line');
  lines.forEach(function(el){el.style.display=el.textContent.toLowerCase().includes(f)?'':'none';});
}
</script>"""
    return html


def _section_action_type_chart(traces: List[Dict]) -> str:
    """SVG horizontal bar chart of action types."""
    stats = _action_type_stats(traces)
    if not stats:
        return ""

    html = '<h2>Action Type Breakdown</h2>'
    html += '<div class="grid grid-2">'

    # Table
    html += '<div><table><tr><th>Type</th><th>Total</th><th>OK</th><th>Fail</th><th>Rate</th></tr>'
    for atype, s in sorted(stats.items(), key=lambda x: -x[1]["total"]):
        rate = (s["ok"] / s["total"] * 100) if s["total"] > 0 else 0
        html += (
            f'<tr><td><b>{_escape(atype)}</b></td><td>{s["total"]}</td>'
            f'<td class="green">{s["ok"]}</td><td class="red">{s["fail"]}</td>'
            f'<td>{_bar(rate, "#4ade80" if rate > 80 else "#fbbf24", 80)}</td></tr>'
        )
    html += '</table></div>'

    # Visual bars
    max_total = max(s["total"] for s in stats.values()) if stats else 1
    html += '<div>'
    for atype, s in sorted(stats.items(), key=lambda x: -x[1]["total"]):
        w_ok = s["ok"] / max_total * 100
        w_fail = s["fail"] / max_total * 100
        html += f'<div style="margin:6px 0"><span style="font-size:.82rem;font-weight:600">{_escape(atype)}</span>'
        html += f'<div class="bar-wrap" style="width:100%;margin-top:3px">'
        html += f'<div class="bar-fill" style="width:{w_ok:.1f}%;background:#4ade80;display:inline-block;float:left"></div>'
        html += f'<div class="bar-fill" style="width:{w_fail:.1f}%;background:#f87171;display:inline-block;float:left;border-radius:0 4px 4px 0"></div>'
        html += f'<div class="bar-text">{s["ok"]}✓ {s["fail"]}✗</div>'
        html += '</div></div>'
    html += '</div></div>'
    return html


def _section_session(session: Dict) -> str:
    """Session state overview."""
    processed = session.get("processed_objects", [])
    all_actions = session.get("all_actions", [])
    if not processed and not all_actions:
        return ""

    html = '<h2>Session State</h2>'
    html += '<div class="grid grid-2">'
    html += _metric_card(len(processed), "Processed Objects", "blue")
    html += _metric_card(len(all_actions), "Planned Actions", "purple")
    html += '</div>'

    if processed:
        html += '<h3>Processed Objects</h3><div style="margin:6px 0">'
        for p in processed:
            html += f'<span class="badge badge-info">{_escape(p)}</span> '
        html += '</div>'

    # Action type distribution from session
    if all_actions:
        type_counts = Counter(a.get("type", "?") for a in all_actions)
        html += '<h3>Action Distribution</h3><div style="margin:6px 0">'
        for t, c in type_counts.most_common():
            html += f'<span class="badge badge-info">{_escape(t)}: {c}</span> '
        html += '</div>'

    return html


def _section_all_replays(output_dir: str) -> str:
    """List all replay files with key stats."""
    replay_dir = os.path.join(output_dir, "replay")
    if not os.path.isdir(replay_dir):
        return ""
    replays = sorted(
        [f for f in os.listdir(replay_dir) if f.startswith("replay_") and f.endswith(".json")],
        reverse=True,
    )
    if not replays:
        return ""

    html = '<h2>Replay History</h2>'
    html += '<table><tr><th>File</th><th>Timestamp</th><th>Actions</th><th>Successes</th><th>Failures</th><th>Exceptions</th></tr>'
    for fname in replays:
        data = _load_json(os.path.join(replay_dir, fname))
        if not data:
            continue
        data = _reconcile_replay(data)
        ts = data.get("timestamp", "?")
        total = data.get("total_actions", 0)
        succ = data.get("successes", 0)
        fail = data.get("failures", 0)
        exc = len(data.get("exceptions", []))
        html += (
            f'<tr><td>{_escape(fname)}</td><td>{_escape(ts)}</td>'
            f'<td>{total}</td><td class="green">{succ}</td>'
            f'<td class="{"red" if fail > 0 else "green"}">{fail}</td>'
            f'<td class="{"red" if exc > 0 else "green"}">{exc}</td></tr>'
        )
    html += '</table>'
    return html


# ── main entry ───────────────────────────────────────────────────────

def generate_report(
    output_dir: str,
    replay_path: Optional[str] = None,
    out_html: Optional[str] = None,
) -> str:
    """
    Generate a self-contained HTML report from VRAgent 2.0 results.

    Args:
        output_dir: Path to results directory (e.g., Results_VRAgent2.0/Kitchen_TestRoom).
        replay_path: Specific replay JSON to highlight (default: latest).
        out_html: Output HTML path (default: <output_dir>/report.html).

    Returns:
        Path to the generated HTML file.
    """
    output_dir = str(Path(output_dir).resolve())
    scene_name = Path(output_dir).name

    # Load all data (robust: each piece is optional)
    summary = _extract_summary(output_dir)
    iteration_logs = _extract_iteration_logs(output_dir)
    gate_graph = _extract_gate_graph(output_dir)
    session = _extract_session(output_dir)
    replay = _extract_replay(output_dir, replay_path)

    # Reconcile replay data once — fixes stale success fields in old replays
    if replay:
        replay = _reconcile_replay(replay)

    traces = replay.get("traces", []) if replay else []

    # Determine output path
    if not out_html:
        out_html = os.path.join(output_dir, "report.html")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build HTML
    parts: List[str] = []
    parts.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">')
    parts.append(f'<meta name="viewport" content="width=device-width,initial-scale=1.0">')
    parts.append(f'<title>VRAgent 2.0 — {_escape(scene_name)}</title>')
    parts.append(f'<style>{_CSS}</style>')
    parts.append(f'</head><body>')
    parts.append(f'<h1>VRAgent 2.0 Report — {_escape(scene_name)}</h1>')
    parts.append(f'<div class="subtitle">Generated: {now} | Dir: {_escape(output_dir)}</div>')

    # Sections — each is independently robust
    if summary:
        parts.append(_section_summary(summary, replay=replay))
    if replay:
        parts.append(_section_replay(replay))
    if traces:
        parts.append(_section_action_type_chart(traces))
        parts.append(_section_object_heatmap(traces))
        parts.append(_section_action_timeline(traces))
    if gate_graph:
        parts.append(_section_gate_graph(gate_graph))
    if iteration_logs:
        parts.append(_section_iteration_logs(iteration_logs))
    if session:
        parts.append(_section_session(session))
    parts.append(_section_all_replays(output_dir))
    if replay:
        parts.append(_section_console_logs(replay))

    # No data at all
    has_data = summary or replay or gate_graph or iteration_logs or session
    if not has_data:
        parts.append(
            '<div class="card" style="text-align:center;margin:40px 0;padding:40px">'
            '<div class="val red">No Data Found</div>'
            f'<div class="label" style="margin-top:8px">Searched: {_escape(output_dir)}</div>'
            '<div style="margin-top:12px;color:#888;font-size:.85rem">'
            'Expected files: summary.json, iteration_logs.json, gate_graph.json, session_state.json, replay/*.json'
            '</div></div>'
        )

    parts.append(f'<script>{_JS}</script>')
    parts.append('</body></html>')

    html_content = "\n".join(parts)

    # Write
    os.makedirs(os.path.dirname(out_html) or ".", exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    return out_html


def main_cli(output_dir: str, replay_path: Optional[str] = None) -> None:
    """CLI entry point for visualization."""
    print(f"[VISUALIZE] Scanning results in: {output_dir}")

    # List available data
    for fname in ("summary.json", "iteration_logs.json", "gate_graph.json",
                  "session_state.json", "test_plan.json"):
        fpath = os.path.join(output_dir, fname)
        status = "[OK]" if os.path.isfile(fpath) else "[--]"
        print(f"  {status} {fname}")

    replay_dir = os.path.join(output_dir, "replay")
    if os.path.isdir(replay_dir):
        replays = [f for f in os.listdir(replay_dir) if f.endswith(".json")]
        print(f"  {'[OK]' if replays else '[--]'} replay/ ({len(replays)} files)")
    else:
        print(f"  [--] replay/")

    out = generate_report(output_dir, replay_path=replay_path)
    print(f"\n[VISUALIZE] Report generated: {out}")
    print(f"[VISUALIZE] Open in browser to view the dashboard.")

    # Try to open in default browser
    try:
        import webbrowser
        webbrowser.open(f"file:///{out.replace(os.sep, '/')}")
        print("[VISUALIZE] Opened in browser.")
    except Exception:
        pass
