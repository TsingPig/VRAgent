"""
Contract-based Interaction Protocol — Agent I/O Schema Definitions

Every agent's output MUST conform to these schemas so multi-agent
collaboration becomes a testable pipeline rather than free-form chat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    GRAB = "Grab"
    TRIGGER = "Trigger"
    TRANSFORM = "Transform"


class VerifierErrorType(str, Enum):
    """Verifier error categories (maps to VRAgent 1.0 error taxonomy)."""
    MISSING_OBJECT = "MissingObject"           # Object not found in scene
    MISSING_COMPONENT = "MissingComponent"     # Required component absent (e.g. Rigidbody)
    INVALID_METHOD = "InvalidMethodSignature"  # Method does not exist or signature mismatch
    INVALID_PARAMETER = "InvalidParameter"     # Parameter fileID / type mismatch
    UI_STATE_MISMATCH = "UIStateMismatch"      # UI element hidden / disabled
    DUPLICATE_ACTION = "DuplicateAction"       # Redundant action unit
    RUNTIME_REF_INVALID = "RuntimeRefInvalid"  # Dynamic object reference stale
    SCHEMA_ERROR = "SchemaError"               # JSON schema violation


class ExplorationMode(str, Enum):
    EXPAND = "Expand"
    EXPLOIT = "Exploit"
    RECOVER = "Recover"


class GateFailureType(str, Enum):
    LOCKED = "locked"
    NEED_ITEM = "need_item"
    NEED_STATE = "need_state"
    UI_HIDDEN = "ui_hidden"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------

@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class MethodCallUnit:
    script_fileID: int = 0
    method_name: str = ""
    parameter_fileID: List[Any] = field(default_factory=list)


@dataclass
class EventUnit:
    methodCallUnits: List[MethodCallUnit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Action Units (the atomic test step)
# ---------------------------------------------------------------------------

@dataclass
class GrabActionUnit:
    type: str = "Grab"
    source_object_name: str = ""
    source_object_fileID: int = 0
    # format 1: target object
    target_object_name: Optional[str] = None
    target_object_fileID: Optional[int] = None
    # format 2: target position
    target_position: Optional[Vec3] = None


@dataclass
class TriggerActionUnit:
    type: str = "Trigger"
    source_object_name: str = ""
    source_object_fileID: int = 0
    triggerring_time: float = 0.0
    condition: str = ""
    triggerring_events: List[EventUnit] = field(default_factory=list)
    triggerred_events: List[EventUnit] = field(default_factory=list)


@dataclass
class TransformActionUnit:
    type: str = "Transform"
    source_object_name: str = ""
    source_object_fileID: int = 0
    delta_position: Vec3 = field(default_factory=Vec3)
    delta_rotation: Vec3 = field(default_factory=Vec3)
    delta_scale: Vec3 = field(default_factory=Vec3)
    triggerring_events: List[EventUnit] = field(default_factory=list)
    triggerred_events: List[EventUnit] = field(default_factory=list)
    triggerring_time: float = 0.0


# Union type for convenience
ActionUnit = Union[GrabActionUnit, TriggerActionUnit, TransformActionUnit]


# ---------------------------------------------------------------------------
# Planner output
# ---------------------------------------------------------------------------

@dataclass
class PlannerOutput:
    """What the Planner Agent produces."""
    actions: List[Dict[str, Any]] = field(default_factory=list)   # raw AAU dicts
    intent: str = ""
    expected_reward: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"actions": self.actions, "intent": self.intent, "expected_reward": self.expected_reward}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PlannerOutput":
        return PlannerOutput(
            actions=d.get("actions", []),
            intent=d.get("intent", ""),
            expected_reward=d.get("expected_reward", 0.0),
        )


# ---------------------------------------------------------------------------
# Verifier output
# ---------------------------------------------------------------------------

@dataclass
class VerifierError:
    type: str = ""
    location: str = ""
    fix_suggestion: str = ""


@dataclass
class VerifierOutput:
    """What the Verifier Agent produces."""
    executable_score: float = 0.0
    errors: List[VerifierError] = field(default_factory=list)
    passed: bool = False
    patched_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executable_score": self.executable_score,
            "errors": [asdict(e) for e in self.errors],
            "pass": self.passed,
            "patched_actions": self.patched_actions,
        }


# ---------------------------------------------------------------------------
# Executor output
# ---------------------------------------------------------------------------

@dataclass
class TraceEntry:
    action: str = ""
    state_before: Dict[str, Any] = field(default_factory=dict)
    state_after: Dict[str, Any] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)


@dataclass
class CoverageDelta:
    LC: float = 0.0   # Line Coverage delta
    MC: float = 0.0   # Method Coverage delta
    CoIGO: float = 0.0  # Coverage of Interesting Game Objects delta


@dataclass
class ExecutorOutput:
    """What the Executor Agent produces."""
    trace: List[TraceEntry] = field(default_factory=list)
    coverage_delta: CoverageDelta = field(default_factory=CoverageDelta)
    exceptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace": [asdict(t) for t in self.trace],
            "coverage_delta": asdict(self.coverage_delta),
            "exceptions": self.exceptions,
        }


# ---------------------------------------------------------------------------
# Observer output
# ---------------------------------------------------------------------------

@dataclass
class ObserverOutput:
    """What the Observer / Oracle Agent produces."""
    coverage_delta: float = 0.0
    bug_signals: List[str] = field(default_factory=list)
    next_exploration_suggestion: str = ""
    recommended_mode: ExplorationMode = ExplorationMode.EXPAND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_delta": self.coverage_delta,
            "bug_signals": self.bug_signals,
            "next_exploration_suggestion": self.next_exploration_suggestion,
            "recommended_mode": self.recommended_mode.value,
        }


# ---------------------------------------------------------------------------
# Gate Graph structures
# ---------------------------------------------------------------------------

@dataclass
class GateEdge:
    """An edge in the Gate Graph."""
    from_state: str = ""
    to_state: str = ""
    action: str = ""
    success: bool = False
    failure_type: str = ""           # GateFailureType.value or empty
    evidence: str = ""


@dataclass
class GateCondition:
    """Structured conclusion from Failure-to-Condition reasoning."""
    gate_edge_action: str = ""      # which edge triggered this analysis
    condition_type: str = ""        # "need_item" | "need_flag" | "ui_hidden" | "locked"
    condition_value: str = ""       # e.g. "BlueKey", "SwitchA=true"
    obtain_path_hints: List[str] = field(default_factory=list)  # how to obtain


# ---------------------------------------------------------------------------
# Controller goal
# ---------------------------------------------------------------------------

@dataclass
class ExplorationGoal:
    """Current goal set by the Controller / ExplorationController."""
    mode: ExplorationMode = ExplorationMode.EXPAND
    description: str = ""
    target_objects: List[str] = field(default_factory=list)
    priority: float = 0.5           # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def serialize(obj) -> str:
    """Serialize a dataclass to JSON string."""
    if hasattr(obj, "to_dict"):
        return json.dumps(obj.to_dict(), indent=2, ensure_ascii=False)
    return json.dumps(asdict(obj), indent=2, ensure_ascii=False)
