"""
Condition Inference — Minimal failure-to-condition reasoning for Observer.

Given executor output + console logs + optional object metadata,
infer **why** an action failed and output a structured condition.

Output types:
    locked | need_item | need_state | ui_hidden | reference_invalid | unknown

This is the minimal "§B3.2 Failure-to-Condition" implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class InferredCondition:
    """Structured failure-to-condition output."""
    failure_type: str = "unknown"
    missing_condition: str = ""
    candidate_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Keyword pattern → failure type mapping
# ---------------------------------------------------------------------------

_PATTERNS: List[tuple] = [
    # (regex_pattern, failure_type, confidence_base)
    (re.compile(r"(locked|lock[_ ]|cannot open|拒绝|denied)", re.I),
     "locked", 0.75),

    (re.compile(r"(key|钥匙|item|物品|inventory|背包|pickup|collect)", re.I),
     "need_item", 0.70),

    (re.compile(r"(switch|flag|lever|开关|quest|mission|task|complete|finish)", re.I),
     "need_state", 0.60),

    (re.compile(r"(disabled|inactive|SetActive\(false\)|not active|隐藏|invisible|hidden|canvas|panel)", re.I),
     "ui_hidden", 0.65),

    (re.compile(r"(null|NullReference|MissingReference|destroyed|not found|missing|引用失效)", re.I),
     "reference_invalid", 0.80),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer_conditions(
    actions: List[Dict[str, Any]],
    executor_output: Dict[str, Any],
    console_logs: List[str],
    *,
    object_metadata: Optional[Dict[str, Any]] = None,
) -> List[InferredCondition]:
    """Analyse execution results and infer structured failure conditions.

    Parameters
    ----------
    actions : list of action-unit dicts
        The actions that were attempted.
    executor_output : dict
        Executor trace + exceptions.
    console_logs : list of str
        Unity console log lines.
    object_metadata : dict or None
        Optional component / scene-graph info about involved objects.

    Returns
    -------
    list of InferredCondition
    """
    conditions: List[InferredCondition] = []
    seen_types: set = set()

    trace = executor_output.get("trace", [])
    exceptions = executor_output.get("exceptions", [])

    # ① Check trace entries for failed / no-effect actions
    for entry in trace:
        if isinstance(entry, dict):
            events = entry.get("events", [])
            action_name = entry.get("action", "")
            evidence_text = " ".join(str(e) for e in events)

            # No state change = suspicious
            before = entry.get("state_before", {})
            after = entry.get("state_after", {})
            if before and after and before == after:
                evidence_text += " NO_STATE_CHANGE"

            cond = _match_patterns(evidence_text, action_name)
            if cond and cond.failure_type not in seen_types:
                conditions.append(cond)
                seen_types.add(cond.failure_type)

    # ② Check exceptions
    for exc in exceptions:
        cond = _match_patterns(str(exc), "exception")
        if cond and cond.failure_type not in seen_types:
            conditions.append(cond)
            seen_types.add(cond.failure_type)

    # ③ Check console logs
    combined_log = " ".join(console_logs)
    if combined_log:
        cond = _match_patterns(combined_log, "console_log")
        if cond and cond.failure_type not in seen_types:
            conditions.append(cond)
            seen_types.add(cond.failure_type)

    # ④ Check object metadata for inactive / missing components
    if object_metadata:
        for obj_id, info in object_metadata.items():
            if isinstance(info, dict):
                if info.get("active") is False or info.get("activeSelf") is False:
                    if "ui_hidden" not in seen_types:
                        conditions.append(InferredCondition(
                            failure_type="ui_hidden",
                            missing_condition=f"Object {obj_id} is inactive",
                            candidate_sources=[obj_id],
                            confidence=0.85,
                            evidence=f"activeSelf=false for {obj_id}",
                        ))
                        seen_types.add("ui_hidden")

    # ⑤ If nothing matched but we have failures, emit unknown
    if not conditions and (exceptions or _has_failures(trace)):
        all_evidence = " | ".join(exceptions[:3])
        conditions.append(InferredCondition(
            failure_type="unknown",
            missing_condition="",
            candidate_sources=[],
            confidence=0.2,
            evidence=all_evidence[:300] or "Undiagnosed failure",
        ))

    return conditions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_patterns(text: str, action_name: str) -> Optional[InferredCondition]:
    """Try to match *text* against known failure patterns."""
    for pattern, ftype, conf_base in _PATTERNS:
        m = pattern.search(text)
        if m:
            matched_span = m.group(0)
            # Try to extract a noun after the keyword (simple heuristic)
            noun = _extract_noun_after(text, m.end())
            return InferredCondition(
                failure_type=ftype,
                missing_condition=noun or matched_span,
                candidate_sources=[],
                confidence=conf_base,
                evidence=f"Pattern '{matched_span}' in {action_name}: {text[:200]}",
            )
    return None


def _extract_noun_after(text: str, start: int) -> str:
    """Grab the next word-like token after *start*."""
    rest = text[start:start + 100].strip()
    m = re.match(r"[:\s=]*['\"]?(\w+)", rest)
    return m.group(1) if m else ""


def _has_failures(trace: List[Dict]) -> bool:
    for entry in trace:
        if isinstance(entry, dict):
            events = entry.get("events", [])
            for ev in events:
                if "error" in str(ev).lower() or "fail" in str(ev).lower():
                    return True
    return False
