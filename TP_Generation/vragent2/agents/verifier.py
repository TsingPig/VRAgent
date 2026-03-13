"""
Verifier Agent — Correctness / Consistency / Duplication checking.

Refactored from validateTestPlan.py + GenerateTestPlanModified validation helpers.
Provides:
    - JSON Schema validation (structural correctness)
    - FileID existence checking (scene graph lookup)
    - Component requirements (Rigidbody for Grab, Collider checks)
    - Duplicate action detection
    - Method/parameter validation
    - Repeated-invalid-target detection
    - Structured error output with fix suggestions + evidence

Now consumes ``RetrievalLayer.build_verifier_context()`` for hard structural checks.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent
from ..contracts import VerifierOutput, VerifierError, VerifierErrorType
from ..retrieval.retrieval_layer import RetrievalLayer
from ..retrieval.hierarchy_builder import FORBIDDEN_NAMES


# ---------------------------------------------------------------------------
# JSON Schema (abridged — matches VRAgent's test-plan format)
# ---------------------------------------------------------------------------
TEST_PLAN_SCHEMA = {
    "type": "object",
    "required": ["taskUnits"],
    "properties": {
        "taskUnits": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["actionUnits"],
            },
        }
    },
}


class VerifierAgent(BaseAgent):
    """Agent 2 — Validates candidate actions before execution."""

    name = "VerifierAgent"

    def __init__(self, retrieval: RetrievalLayer):
        self.retrieval = retrieval

    # ------------------------------------------------------------------
    # Contract entry point
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        input_data : dict
            Required keys:
                actions – list of action-unit dicts from Planner

        Returns
        -------
        dict matching VerifierOutput schema + ``evidence`` list.
        """
        actions: List[Dict] = input_data.get("actions", [])
        errors: List[VerifierError] = []
        patched: List[Dict] = []
        evidence: List[Dict[str, Any]] = []

        # ── Build structured verifier context from RetrievalLayer ────
        ctx = self.retrieval.build_verifier_context(actions)

        for idx, au in enumerate(actions):
            au_errors = self.validate_action_unit(au, index=idx, ctx=ctx)
            if au_errors:
                errors.extend(au_errors)
            else:
                patched.append(au)

        # Deduplication
        patched, dup_errors = self._deduplicate(patched)
        errors.extend(dup_errors)

        # Repeated-invalid-target detection
        repeat_errors = self._detect_repeated_invalid_targets(actions, ctx)
        errors.extend(repeat_errors)

        total = len(actions)
        valid = len(patched)
        score = valid / total if total > 0 else 0.0
        passed = len(errors) == 0

        # Collect evidence from ctx
        for fid, exists in ctx.object_existence.items():
            evidence.append({"fileID": fid, "exists": exists})
        for fid, comps in ctx.component_info.items():
            evidence.append({"fileID": fid, "components": comps})

        output = VerifierOutput(
            executable_score=round(score, 3),
            errors=errors,
            passed=passed,
            patched_actions=patched,
        )
        result = output.to_dict()
        result["evidence"] = evidence
        return result

    # ------------------------------------------------------------------
    # Per-action validation
    # ------------------------------------------------------------------

    def validate_action_unit(
        self,
        au: Dict[str, Any],
        *,
        index: int = 0,
        ctx=None,
    ) -> List[VerifierError]:
        """Run all checks on a single action unit."""
        errors: List[VerifierError] = []
        location = f"actionUnits[{index}]"
        action_type = au.get("type", "")

        # ① Forbidden object names
        for key in ("source_object_name", "target_object_name"):
            name = au.get(key, "")
            for forbidden in FORBIDDEN_NAMES:
                if forbidden in name:
                    errors.append(VerifierError(
                        type=VerifierErrorType.MISSING_OBJECT.value,
                        location=f"{location}.{key}",
                        fix_suggestion=f"Do not directly interact with '{forbidden}'. Use a different target.",
                    ))

        # ② FileID validity
        for key, value in au.items():
            if "fileid" in key.lower():
                if not self._is_valid_fileid(value):
                    errors.append(VerifierError(
                        type=VerifierErrorType.INVALID_PARAMETER.value,
                        location=f"{location}.{key}",
                        fix_suggestion=f"Value '{value}' is not a valid integer fileID.",
                    ))
                elif value == 0:
                    errors.append(VerifierError(
                        type=VerifierErrorType.INVALID_PARAMETER.value,
                        location=f"{location}.{key}",
                        fix_suggestion="fileID must not be 0.",
                    ))

        # ③ FileID existence — use ctx cache when available, else scene graph
        for key in ("source_object_fileID", "target_object_fileID"):
            fid = au.get(key)
            if fid and self._is_valid_fileid(fid):
                fid_str = str(fid)
                exists = (ctx.object_existence.get(fid_str)
                          if ctx else self.retrieval.object_exists(fid_str))
                if not exists:
                    errors.append(VerifierError(
                        type=VerifierErrorType.MISSING_OBJECT.value,
                        location=f"{location}.{key}",
                        fix_suggestion=f"fileID {fid} does not exist in the scene graph.",
                    ))

        # ④ Component requirements (Grab needs Rigidbody/Collider)
        if action_type == "Grab" and ctx:
            sfid = str(au.get("source_object_fileID", ""))
            comps = ctx.component_info.get(sfid, {})
            if comps and not comps.get("Has_Rigidbody", False):
                errors.append(VerifierError(
                    type=VerifierErrorType.MISSING_COMPONENT.value,
                    location=f"{location}.source_object_fileID",
                    fix_suggestion=(
                        f"Source object {sfid} has no Rigidbody. "
                        "Grab actions typically require a Rigidbody on the source object."
                    ),
                ))
            if comps and not comps.get("Has_Collider", False):
                errors.append(VerifierError(
                    type=VerifierErrorType.MISSING_COMPONENT.value,
                    location=f"{location}.source_object_fileID",
                    fix_suggestion=(
                        f"Source object {sfid} has no Collider. "
                        "Grab actions typically require a Collider for interaction."
                    ),
                ))

        # ⑤ Method existence check (Trigger / methodCallUnits)
        if ctx:
            for event_key in ("triggerring_events", "triggerred_events"):
                for ei, event in enumerate(au.get(event_key, [])):
                    for mi, mc in enumerate(event.get("methodCallUnits", [])):
                        sfid = str(mc.get("script_fileID", ""))
                        method = mc.get("method_name", "")
                        known_methods = ctx.method_index.get(sfid, [])
                        if known_methods and method and method not in known_methods:
                            errors.append(VerifierError(
                                type=VerifierErrorType.INVALID_METHOD.value,
                                location=f"{location}.{event_key}[{ei}].methodCallUnits[{mi}].method_name",
                                fix_suggestion=(
                                    f"Method '{method}' not found on script {sfid}. "
                                    f"Available: {', '.join(known_methods[:10])}"
                                ),
                            ))

        # ⑥ Type-specific structural checks
        if action_type == "Grab":
            errors.extend(self._check_grab(au, location))
        elif action_type == "Trigger":
            errors.extend(self._check_trigger(au, location, ctx=ctx))
        elif action_type == "Transform":
            errors.extend(self._check_transform(au, location))
        elif action_type:
            errors.append(VerifierError(
                type=VerifierErrorType.SCHEMA_ERROR.value,
                location=f"{location}.type",
                fix_suggestion=f"Unknown action type '{action_type}'. Must be Grab/Trigger/Transform.",
            ))

        return errors

    # ------------------------------------------------------------------
    # Type-specific checks
    # ------------------------------------------------------------------

    def _check_grab(self, au: Dict, loc: str) -> List[VerifierError]:
        errors: List[VerifierError] = []
        has_target_obj = au.get("target_object_fileID") is not None
        has_target_pos = au.get("target_position") is not None

        if not has_target_obj and not has_target_pos:
            errors.append(VerifierError(
                type=VerifierErrorType.SCHEMA_ERROR.value,
                location=loc,
                fix_suggestion="Grab requires either target_object_fileID or target_position.",
            ))
        return errors

    def _check_trigger(self, au: Dict, loc: str, *, ctx=None) -> List[VerifierError]:
        errors: List[VerifierError] = []
        # Trigger must have condition
        if not au.get("condition"):
            errors.append(VerifierError(
                type=VerifierErrorType.SCHEMA_ERROR.value,
                location=f"{loc}.condition",
                fix_suggestion="Trigger action must specify a condition description.",
            ))

        # Trigger should contain at least one method call unit.
        event_count = 0
        for event_key in ("triggerring_events", "triggerred_events"):
            for event in au.get(event_key, []):
                event_count += len(event.get("methodCallUnits", []))
        if event_count == 0:
            errors.append(VerifierError(
                type=VerifierErrorType.SCHEMA_ERROR.value,
                location=f"{loc}.triggerring_events",
                fix_suggestion="Trigger action must include at least one methodCallUnit.",
            ))

        # Validate method calls in events (script_fileID existence)
        for event_key in ("triggerring_events", "triggerred_events"):
            for ei, event in enumerate(au.get(event_key, [])):
                for mi, mc in enumerate(event.get("methodCallUnits", [])):
                    script_fid = mc.get("script_fileID")
                    if script_fid and self._is_valid_fileid(script_fid):
                        fid_str = str(script_fid)
                        exists = (ctx.object_existence.get(fid_str)
                                  if ctx else self.retrieval.object_exists(fid_str))
                        if not exists:
                            errors.append(VerifierError(
                                type=VerifierErrorType.INVALID_METHOD.value,
                                location=f"{loc}.{event_key}[{ei}].methodCallUnits[{mi}].script_fileID",
                                fix_suggestion=f"script_fileID {script_fid} not found in scene.",
                            ))
        return errors

    def _check_transform(self, au: Dict, loc: str) -> List[VerifierError]:
        errors: List[VerifierError] = []
        for vec_key in ("delta_position", "delta_rotation", "delta_scale"):
            vec = au.get(vec_key)
            if vec is None:
                errors.append(VerifierError(
                    type=VerifierErrorType.SCHEMA_ERROR.value,
                    location=f"{loc}.{vec_key}",
                    fix_suggestion=f"Transform action must include {vec_key} with x/y/z.",
                ))
            elif not all(k in vec for k in ("x", "y", "z")):
                errors.append(VerifierError(
                    type=VerifierErrorType.SCHEMA_ERROR.value,
                    location=f"{loc}.{vec_key}",
                    fix_suggestion=f"{vec_key} must contain x, y, z numeric fields.",
                ))
        return errors

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(self, actions: List[Dict]) -> tuple[List[Dict], List[VerifierError]]:
        """Remove exact-duplicate actions."""
        seen: List[str] = []
        unique: List[Dict] = []
        errors: List[VerifierError] = []

        for idx, au in enumerate(actions):
            key = json.dumps(
                {k: v for k, v in au.items() if k != "_round_index"},
                sort_keys=True,
            )
            if key in seen:
                errors.append(VerifierError(
                    type=VerifierErrorType.DUPLICATE_ACTION.value,
                    location=f"actionUnits[{idx}]",
                    fix_suggestion="This action is a duplicate and was removed.",
                ))
            else:
                seen.append(key)
                unique.append(au)
        return unique, errors

    # ------------------------------------------------------------------
    # Repeated-invalid-target detection
    # ------------------------------------------------------------------

    def _detect_repeated_invalid_targets(
        self, actions: List[Dict], ctx
    ) -> List[VerifierError]:
        """Flag sequences that repeatedly target the same non-existent object."""
        errors: List[VerifierError] = []
        target_counts: Dict[str, int] = {}

        for au in actions:
            for key in ("source_object_fileID", "target_object_fileID"):
                fid = au.get(key)
                if not fid:
                    continue
                fid_str = str(fid)
                exists = (ctx.object_existence.get(fid_str, True) if ctx else True)
                if not exists:
                    target_counts[fid_str] = target_counts.get(fid_str, 0) + 1

        for fid_str, count in target_counts.items():
            if count >= 3:
                errors.append(VerifierError(
                    type=VerifierErrorType.RUNTIME_REF_INVALID.value,
                    location=f"fileID={fid_str}",
                    fix_suggestion=(
                        f"fileID {fid_str} is referenced {count} times but does not exist. "
                        "Remove all actions targeting this invalid object."
                    ),
                ))

        return errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_fileid(value: Any) -> bool:
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        return False
