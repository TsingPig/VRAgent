"""
Contract-based Interaction Protocol — Agent I/O Schema Definitions

Every agent's output MUST conform to these schemas so multi-agent
collaboration becomes a testable pipeline rather than free-form chat.

v2.1: SharedWorldState blackboard — agents read/write a shared state object
instead of piping dicts through a sequential chain.
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
            "passed": self.passed,
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
# Scene Understanding output
# ---------------------------------------------------------------------------

@dataclass
class InteractionDependency:
    """A single dependency in the interaction chain."""
    source: str = ""        # e.g. "Key" or "PowerSwitch"
    target: str = ""        # e.g. "LockedCabinet"
    relation: str = ""      # e.g. "unlocks", "enables", "requires"


@dataclass
class SceneUnderstandingOutput:
    """Structured summary produced by SceneUnderstandingAgent."""
    scene_overview: str = ""
    key_objects: List[str] = field(default_factory=list)
    interaction_dependencies: List[InteractionDependency] = field(default_factory=list)
    gate_chains: List[str] = field(default_factory=list)        # ordered gate descriptions
    main_path: List[str] = field(default_factory=list)          # correct walkthrough steps
    failure_paths: List[str] = field(default_factory=list)      # common failure patterns
    object_priority_ranking: List[str] = field(default_factory=list)  # object names ranked by importance
    # v2.1 additions
    object_roles: Dict[str, str] = field(default_factory=dict)  # e.g. {"Key": "unlocker", "Door": "gated_target"}
    oracle_hints: List[str] = field(default_factory=list)       # e.g. ["door open state should change"]
    completion_criteria: List[str] = field(default_factory=list) # what counts as "done"
    forbidden_test_objects: List[str] = field(default_factory=list)  # objects to never test

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_overview": self.scene_overview,
            "key_objects": self.key_objects,
            "interaction_dependencies": [asdict(d) for d in self.interaction_dependencies],
            "gate_chains": self.gate_chains,
            "main_path": self.main_path,
            "failure_paths": self.failure_paths,
            "object_priority_ranking": self.object_priority_ranking,
            "object_roles": self.object_roles,
            "oracle_hints": self.oracle_hints,
            "completion_criteria": self.completion_criteria,
            "forbidden_test_objects": self.forbidden_test_objects,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SceneUnderstandingOutput":
        deps = [InteractionDependency(**dep) for dep in d.get("interaction_dependencies", [])]
        return SceneUnderstandingOutput(
            scene_overview=d.get("scene_overview", ""),
            key_objects=d.get("key_objects", []),
            interaction_dependencies=deps,
            gate_chains=d.get("gate_chains", []),
            main_path=d.get("main_path", []),
            failure_paths=d.get("failure_paths", []),
            object_priority_ranking=d.get("object_priority_ranking", []),
            object_roles=d.get("object_roles", {}),
            oracle_hints=d.get("oracle_hints", []),
            completion_criteria=d.get("completion_criteria", []),
            forbidden_test_objects=d.get("forbidden_test_objects", []),
        )

    def to_prompt_text(self) -> str:
        """Format as text block for LLM prompts."""
        parts = [f"## Scene Understanding\n{self.scene_overview}"]
        if self.key_objects:
            parts.append(f"**Key Objects**: {', '.join(self.key_objects)}")
        if self.interaction_dependencies:
            dep_lines = [f"  - {d.source} --[{d.relation}]--> {d.target}"
                         for d in self.interaction_dependencies]
            parts.append("**Interaction Dependencies**:\n" + "\n".join(dep_lines))
        if self.gate_chains:
            parts.append("**Gate Chains**:\n" + "\n".join(f"  {i+1}. {g}" for i, g in enumerate(self.gate_chains)))
        if self.main_path:
            parts.append("**Main Path**:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.main_path)))
        if self.failure_paths:
            parts.append("**Common Failures**:\n" + "\n".join(f"  - {f}" for f in self.failure_paths))
        if self.object_roles:
            role_lines = [f"  - {obj}: {role}" for obj, role in self.object_roles.items()]
            parts.append("**Object Roles**:\n" + "\n".join(role_lines))
        if self.oracle_hints:
            parts.append("**Oracle Hints**:\n" + "\n".join(f"  - {h}" for h in self.oracle_hints))
        if self.completion_criteria:
            parts.append("**Completion Criteria**:\n" + "\n".join(f"  - {c}" for c in self.completion_criteria))
        if self.forbidden_test_objects:
            parts.append(f"**Do NOT test**: {', '.join(self.forbidden_test_objects)}")
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Scheduler output
# ---------------------------------------------------------------------------

@dataclass
class SchedulerDecision:
    """Output of the dynamic ObjectScheduler — which object to process next."""
    object_name: str = ""
    object_info: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    priority_score: float = 0.0
    skip_list: List[str] = field(default_factory=list)  # objects explicitly skipped


# ---------------------------------------------------------------------------
# Semantic Verifier output (V2 — LLM critic)
# ---------------------------------------------------------------------------

@dataclass
class SemanticVerifierOutput:
    """Output of the LLM-based Semantic Verifier (V2).

    Unlike the rule-based StaticVerifier which checks structural validity,
    the SemanticVerifier evaluates whether a plan *makes sense* w.r.t. the
    scene ground truth, gate chains, and prior failures.
    """
    semantic_risk_score: float = 0.0
    missing_preconditions: List[str] = field(default_factory=list)
    suspicious_steps: List[str] = field(default_factory=list)
    counter_plan: List[str] = field(default_factory=list)   # alternative actions
    verdict: str = "accept"  # accept | reject | revise

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SemanticVerifierOutput":
        return SemanticVerifierOutput(**{
            k: d[k] for k in (
                "semantic_risk_score", "missing_preconditions",
                "suspicious_steps", "counter_plan", "verdict",
            ) if k in d
        })


# ---------------------------------------------------------------------------
# Observer structured sub-outputs (O1/O2/O3)
# ---------------------------------------------------------------------------

@dataclass
class StateDelta:
    """O1 — State Delta Interpreter output."""
    changed_objects: List[str] = field(default_factory=list)
    expected_changes: List[str] = field(default_factory=list)
    unexpected_changes: List[str] = field(default_factory=list)
    gates_opened: List[str] = field(default_factory=list)
    gates_still_blocked: List[str] = field(default_factory=list)
    semantic_failures: List[str] = field(default_factory=list)  # "action ok but semantically wrong"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailureHypothesis:
    """O2 — Failure Hypothesis Builder output."""
    hypothesis: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    blocked_object: str = ""
    needed_condition: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyRecommendation:
    """O3 — Strategy Recommender structured output."""
    new_facts: List[str] = field(default_factory=list)
    gates_inferred: List[Dict[str, str]] = field(default_factory=list)
    planner_instruction: str = ""
    scheduler_bias: List[str] = field(default_factory=list)   # object names to prioritize
    oracle_updates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# SharedWorldState — Blackboard
# ---------------------------------------------------------------------------

@dataclass
class SharedWorldState:
    """Global blackboard that all agents read from and write to.

    The Controller does NOT pass dicts between agents; instead, every agent
    reads the fields it needs and writes back its conclusions.  This makes
    inter-agent coupling explicit and testable.
    """
    # ── Scene ground truth (written by SceneUnderstandingAgent) ────────
    scene_understanding: Optional[SceneUnderstandingOutput] = None

    # ── Accumulated world knowledge ───────────────────────────────────
    facts: List[str] = field(default_factory=list)              # inferred truths
    open_gates: List[str] = field(default_factory=list)
    blocked_gates: List[str] = field(default_factory=list)

    # ── Object tracking ──────────────────────────────────────────────
    tested_objects: List[str] = field(default_factory=list)
    object_risk_scores: Dict[str, float] = field(default_factory=dict)
    object_failure_counts: Dict[str, int] = field(default_factory=dict)

    # ── Recent context ───────────────────────────────────────────────
    recent_failures: List[str] = field(default_factory=list)
    recent_traces: List[Dict[str, Any]] = field(default_factory=list)

    # ── Oracle rules (from Observer / DELIVERY_NOTES) ─────────────────
    oracle_rules: List[str] = field(default_factory=list)

    # ── Plan negotiation ─────────────────────────────────────────────
    candidate_plan: Optional[Dict[str, Any]] = None       # PlannerOutput dict
    semantic_critique: Optional[SemanticVerifierOutput] = None
    accepted_plan: Optional[Dict[str, Any]] = None

    # ── Observer analysis ────────────────────────────────────────────
    state_delta: Optional[StateDelta] = None
    failure_hypotheses: List[FailureHypothesis] = field(default_factory=list)
    strategy: Optional[StrategyRecommendation] = None

    # ── Coverage ─────────────────────────────────────────────────────
    total_coverage: float = 0.0
    coverage_history: List[float] = field(default_factory=list)

    # ── Scheduler bias (written by Observer O3) ──────────────────────
    scheduler_bias: List[str] = field(default_factory=list)

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        d["facts"] = self.facts
        d["open_gates"] = self.open_gates
        d["blocked_gates"] = self.blocked_gates
        d["tested_objects"] = self.tested_objects
        d["object_risk_scores"] = self.object_risk_scores
        d["object_failure_counts"] = self.object_failure_counts
        d["recent_failures"] = self.recent_failures
        d["oracle_rules"] = self.oracle_rules
        d["total_coverage"] = self.total_coverage
        d["coverage_history"] = self.coverage_history
        d["scheduler_bias"] = self.scheduler_bias
        if self.scene_understanding:
            d["scene_understanding"] = self.scene_understanding.to_dict()
        if self.state_delta:
            d["state_delta"] = self.state_delta.to_dict()
        if self.failure_hypotheses:
            d["failure_hypotheses"] = [h.to_dict() for h in self.failure_hypotheses]
        if self.strategy:
            d["strategy"] = self.strategy.to_dict()
        if self.semantic_critique:
            d["semantic_critique"] = self.semantic_critique.to_dict()
        return d

    def add_fact(self, fact: str) -> None:
        if fact not in self.facts:
            self.facts.append(fact)

    def record_failure(self, object_name: str, summary: str) -> None:
        self.object_failure_counts[object_name] = (
            self.object_failure_counts.get(object_name, 0) + 1
        )
        self.recent_failures.append(f"{object_name}: {summary}")
        self.recent_failures = self.recent_failures[-30:]  # bounded

    def mark_tested(self, object_name: str) -> None:
        if object_name not in self.tested_objects:
            self.tested_objects.append(object_name)

    def to_prompt_summary(self) -> str:
        """Compact text block for injecting into LLM prompts."""
        parts: List[str] = []
        if self.scene_understanding:
            parts.append(self.scene_understanding.to_prompt_text())
        if self.facts:
            parts.append("**Known Facts**:\n" + "\n".join(f"  - {f}" for f in self.facts[-15:]))
        if self.open_gates:
            parts.append(f"**Open Gates**: {', '.join(self.open_gates)}")
        if self.blocked_gates:
            parts.append(f"**Blocked Gates**: {', '.join(self.blocked_gates)}")
        if self.failure_hypotheses:
            hyps = [f"  - [{h.confidence:.1f}] {h.hypothesis}" for h in self.failure_hypotheses[-5:]]
            parts.append("**Failure Hypotheses**:\n" + "\n".join(hyps))
        if self.strategy and self.strategy.planner_instruction:
            parts.append(f"**Observer Instruction**: {self.strategy.planner_instruction}")
        if self.oracle_rules:
            parts.append("**Oracle Rules**:\n" + "\n".join(f"  - {r}" for r in self.oracle_rules[-10:]))
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def serialize(obj) -> str:
    """Serialize a dataclass to JSON string."""
    if hasattr(obj, "to_dict"):
        return json.dumps(obj.to_dict(), indent=2, ensure_ascii=False)
    return json.dumps(asdict(obj), indent=2, ensure_ascii=False)
