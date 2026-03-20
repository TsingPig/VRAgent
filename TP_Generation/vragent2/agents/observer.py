"""
Observer / Oracle Agent — Three-capability architecture:

O1. State Delta Interpreter  — what changed, was it expected?
O2. Failure Hypothesis Builder — why did it fail, what's needed?
O3. Strategy Recommender     — what to do next, writes back to blackboard.

Unlike a traditional test oracle that uses hard assertions, this agent
performs "弱 oracle" observation and produces structured recommendations
that directly influence the Scheduler, Planner, and world state.

Output: coverage delta, bug signals, gate_hints, failure_summary,
        state_delta (O1), failure_hypotheses (O2), strategy (O3).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_agent import BaseAgent
from ..contracts import (
    ObserverOutput,
    ExplorationMode,
    CoverageDelta,
    TraceEntry,
    StateDelta,
    FailureHypothesis,
    StrategyRecommendation,
)
from ..retrieval.condition_inference import infer_conditions

if TYPE_CHECKING:
    from ..utils.llm_client import LLMClient
    from ..utils.config_loader import AgentLLMConfig


# -- LLM system prompt for the strategy recommender (O3) ---------------

_OBSERVER_STRATEGY_SYSTEM = """\
You are the Observer agent in a multi-agent VR test system. You have just \
received the execution trace and your job is to produce a structured analysis.

You must output a JSON object with these fields:
{
  "state_delta": {
    "changed_objects": ["<object names whose state changed>"],
    "expected_changes": ["<changes that match the plan intent>"],
    "unexpected_changes": ["<changes that were not intended>"],
    "gates_opened": ["<gate conditions that are now satisfied>"],
    "gates_still_blocked": ["<gate conditions still unsolved>"],
    "semantic_failures": ["<action succeeded technically but had no meaningful effect>"]
  },
  "failure_hypotheses": [
    {
      "hypothesis": "<what went wrong>",
      "evidence": ["<supporting observations>"],
      "confidence": 0.0,
      "blocked_object": "<object that couldn't be interacted with>",
      "needed_condition": "<what needs to happen first>"
    }
  ],
  "strategy": {
    "new_facts": ["<inferred truths about the scene>"],
    "gates_inferred": [{"blocked_object": "<obj>", "needed_condition": "<cond>"}],
    "planner_instruction": "<specific directive for the next planning round>",
    "scheduler_bias": ["<objects to prioritize next>"],
    "oracle_updates": ["<new observable rules learned>"]
  }
}

Rules:
- Be specific and actionable, not vague.
- "planner_instruction" must be a single clear sentence.
- "scheduler_bias" must contain real object names from the scene.
- "new_facts" should only contain things you are confident about.
- Return ONLY valid JSON.
"""


class ObserverAgent(BaseAgent):
    """Agent 4 — Judges execution results and recommends next moves.

    When an ``LLMClient`` is provided, the observer augments its rule-based
    analysis with an LLM call for deeper failure reasoning and richer
    next-step suggestions.
    """

    name = "ObserverAgent"

    def __init__(
        self,
        *,
        novelty_threshold_k: int = 5,
        retrieval=None,
        llm: Optional["LLMClient"] = None,
        llm_config: Optional["AgentLLMConfig"] = None,
        default_model: str = "gpt-4o",
    ):
        self.novelty_threshold_k = novelty_threshold_k
        self._consecutive_zero_novelty: int = 0
        self._total_coverage = CoverageDelta()
        self.retrieval = retrieval  # RetrievalLayer (optional, for observer context)
        self.llm = llm
        self.llm_config = llm_config
        self._default_model = default_model

    # ------------------------------------------------------------------
    # Contract entry point
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        input_data : dict
            Required keys:
                executor_output – dict from ExecutorAgent.run()
            Optional keys:
                previous_coverage – CoverageDelta dict
                console_logs      – list of Unity console log strings
                goal              – current ExplorationGoal description
                actions           – the actions that were executed
                world_state       – SharedWorldState prompt summary

        Returns
        -------
        dict with keys: coverage_delta, bug_signals, next_exploration_suggestion,
        recommended_mode, gate_hints, failure_summary,
        state_delta (O1), failure_hypotheses (O2), strategy (O3), llm_analysis.
        """
        exec_out = input_data.get("executor_output", {})
        console_logs: List[str] = input_data.get("console_logs", [])
        goal: str = input_data.get("goal", "")
        actions: List[Dict] = input_data.get("actions", [])
        world_summary: str = input_data.get("world_state", "")

        trace = exec_out.get("trace", [])
        coverage = exec_out.get("coverage_delta", {})
        exceptions = exec_out.get("exceptions", [])

        # ① Detect bug signals (rule-based)
        bug_signals = self._detect_bugs(exceptions, console_logs, trace)

        # ② Compute novelty / coverage gain
        delta = self._evaluate_coverage(coverage)

        # ③ Run failure-to-condition inference (rule-based)
        conditions = infer_conditions(
            actions=actions,
            executor_output=exec_out,
            console_logs=console_logs,
        )
        gate_hints = [c.to_dict() for c in conditions]

        # ④ Build failure summary
        failure_summary = self._build_failure_summary(conditions, bug_signals)

        # ⑤ Rule-based exploration suggestion (baseline)
        suggestion, mode = self._suggest_next(delta, bug_signals, trace, goal, conditions)

        # ⑥ O1 State Delta Interpreter (rule-based baseline)
        state_delta = self._interpret_state_delta(trace, actions)

        # ⑦ O2 Failure Hypothesis Builder (rule-based baseline)
        failure_hypotheses = self._build_failure_hypotheses(
            trace, bug_signals, conditions, actions,
        )

        # ⑧ O3 Strategy Recommender — LLM-enhanced (combines O1/O2/O3)
        strategy = StrategyRecommendation()
        llm_analysis = ""
        if self.llm and self.llm_config and self.llm_config.enabled:
            llm_result = self._llm_strategy_analysis(
                actions=actions,
                trace=trace,
                bug_signals=bug_signals,
                failure_summary=failure_summary,
                state_delta=state_delta,
                failure_hypotheses=failure_hypotheses,
                delta=delta,
                goal=goal,
                world_summary=world_summary,
            )
            if llm_result:
                # LLM can override/enrich all three sub-outputs
                if "state_delta" in llm_result:
                    sd = llm_result["state_delta"]
                    state_delta = StateDelta(
                        changed_objects=sd.get("changed_objects", state_delta.changed_objects),
                        expected_changes=sd.get("expected_changes", state_delta.expected_changes),
                        unexpected_changes=sd.get("unexpected_changes", state_delta.unexpected_changes),
                        gates_opened=sd.get("gates_opened", state_delta.gates_opened),
                        gates_still_blocked=sd.get("gates_still_blocked", state_delta.gates_still_blocked),
                        semantic_failures=sd.get("semantic_failures", state_delta.semantic_failures),
                    )
                if "failure_hypotheses" in llm_result:
                    for fh in llm_result["failure_hypotheses"]:
                        failure_hypotheses.append(FailureHypothesis(
                            hypothesis=fh.get("hypothesis", ""),
                            evidence=fh.get("evidence", []),
                            confidence=float(fh.get("confidence", 0.5)),
                            blocked_object=fh.get("blocked_object", ""),
                            needed_condition=fh.get("needed_condition", ""),
                        ))
                if "strategy" in llm_result:
                    s = llm_result["strategy"]
                    strategy = StrategyRecommendation(
                        new_facts=s.get("new_facts", []),
                        gates_inferred=s.get("gates_inferred", []),
                        planner_instruction=s.get("planner_instruction", ""),
                        scheduler_bias=s.get("scheduler_bias", []),
                        oracle_updates=s.get("oracle_updates", []),
                    )
                    # Override mode if strategy has a strong planner instruction
                    if strategy.scheduler_bias:
                        mode = ExplorationMode.EXPLOIT
                    if strategy.planner_instruction:
                        suggestion = strategy.planner_instruction

                llm_analysis = json.dumps(llm_result, ensure_ascii=False)

        output = {
            "coverage_delta": delta,
            "bug_signals": bug_signals,
            "next_exploration_suggestion": suggestion,
            "recommended_mode": mode.value,
            "gate_hints": gate_hints,
            "failure_summary": failure_summary,
            # O1/O2/O3 structured outputs
            "state_delta": state_delta.to_dict(),
            "failure_hypotheses": [h.to_dict() for h in failure_hypotheses],
            "strategy": strategy.to_dict(),
            "llm_analysis": llm_analysis,
        }
        return output

    # ------------------------------------------------------------------
    # Bug detection (weak oracle)
    # ------------------------------------------------------------------

    def _detect_bugs(
        self,
        exceptions: List[str],
        console_logs: List[str],
        trace: List[Dict],
    ) -> List[str]:
        signals: List[str] = []

        # Runtime exceptions from executor
        for exc in exceptions:
            signals.append(f"[EXCEPTION] {exc}")

        # Console log analysis
        error_pattern = re.compile(
            r"(NullReferenceException|IndexOutOfRange|MissingComponent"
            r"|ArgumentException|InvalidOperation|KeyNotFoundException"
            r"|StackOverflow|OutOfMemory|AssertionFailed)",
            re.IGNORECASE,
        )
        warning_pattern = re.compile(
            r"(warning|deprecated|obsolete)", re.IGNORECASE
        )

        for log in console_logs:
            if error_pattern.search(log):
                signals.append(f"[CONSOLE_ERROR] {log[:200]}")
            elif warning_pattern.search(log):
                signals.append(f"[CONSOLE_WARN] {log[:200]}")

        # Trace anomaly: action dispatched but no state change
        for entry in trace:
            if isinstance(entry, dict):
                before = entry.get("state_before", {})
                after = entry.get("state_after", {})
                if before and after and before == after:
                    signals.append(
                        f"[NO_STATE_CHANGE] Action '{entry.get('action', '')}' had no effect"
                    )

        return signals

    # ------------------------------------------------------------------
    # Coverage evaluation
    # ------------------------------------------------------------------

    def _evaluate_coverage(self, coverage_dict: Dict[str, float]) -> float:
        """Compute an aggregate coverage delta."""
        lc = coverage_dict.get("LC", 0.0)
        mc = coverage_dict.get("MC", 0.0)
        coigo = coverage_dict.get("CoIGO", 0.0)

        # Weighted aggregate
        delta = 0.4 * lc + 0.3 * mc + 0.3 * coigo

        # Track novelty streak
        if delta <= 0.001:
            self._consecutive_zero_novelty += 1
        else:
            self._consecutive_zero_novelty = 0

        return round(delta, 4)

    # ------------------------------------------------------------------
    # Failure summary builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_failure_summary(conditions, bug_signals: List[str]) -> str:
        """Build a human-readable failure summary for logging / downstream agents."""
        parts: List[str] = []
        if conditions:
            parts.append("Inferred conditions:")
            for c in conditions:
                parts.append(
                    f"  - [{c.failure_type}] {c.missing_condition} "
                    f"(confidence={c.confidence:.2f})"
                )
        if bug_signals:
            parts.append(f"Bug signals ({len(bug_signals)}):")
            for sig in bug_signals[:5]:
                parts.append(f"  - {sig[:150]}")
        return "\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # Exploration suggestion (now condition-aware)
    # ------------------------------------------------------------------

    def _suggest_next(
        self,
        delta: float,
        bug_signals: List[str],
        trace: List[Dict],
        goal: str,
        conditions=None,
    ) -> tuple[str, ExplorationMode]:
        """Recommend next exploration mode + specific action hint."""

        # Recover mode: no progress
        if self._consecutive_zero_novelty >= self.novelty_threshold_k:
            self._consecutive_zero_novelty = 0  # reset after triggering
            return (
                f"No coverage gain for {self.novelty_threshold_k} consecutive steps. "
                "Recommend backtracking and re-indexing alternative interaction paths.",
                ExplorationMode.RECOVER,
            )

        # Exploit mode: structural condition detected
        if conditions:
            actionable = [c for c in conditions if c.failure_type != "unknown" and c.confidence >= 0.5]
            if actionable:
                top = actionable[0]
                return (
                    f"Condition inferred: [{top.failure_type}] {top.missing_condition} "
                    f"(confidence={top.confidence:.2f}). Resolve this condition first.",
                    ExplorationMode.EXPLOIT,
                )

        # Exploit mode: gate / lock detected from bug signals
        gate_keywords = re.compile(
            r"(locked|need_item|need_key|need_state|ui_hidden|cannot open|not interactable)",
            re.IGNORECASE,
        )
        for signal in bug_signals:
            if gate_keywords.search(signal):
                return (
                    f"Gate detected: {signal}. "
                    "Focus on resolving the gating condition before continuing.",
                    ExplorationMode.EXPLOIT,
                )

        # Expand mode: progress being made
        if delta > 0:
            return (
                f"Coverage increased by {delta:.4f}. "
                "Continue exploring new rooms / UI branches.",
                ExplorationMode.EXPAND,
            )

        return (
            "Minor progress. Consider trying untested interaction patterns.",
            ExplorationMode.EXPAND,
        )

    # ------------------------------------------------------------------
    # LLM-enhanced observation (O1+O2+O3 combined)
    # ------------------------------------------------------------------

    def _llm_strategy_analysis(
        self,
        actions: List[Dict],
        trace: List[Dict],
        bug_signals: List[str],
        failure_summary: str,
        state_delta: StateDelta,
        failure_hypotheses: List[FailureHypothesis],
        delta: float,
        goal: str,
        world_summary: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Call LLM to produce structured O1/O2/O3 analysis."""
        model = self.llm_config.effective_model(self._default_model)
        temp = self.llm_config.temperature

        trace_sample = trace[:10]
        trace_block = json.dumps(trace_sample, indent=2, ensure_ascii=False)
        bug_block = json.dumps(bug_signals[:10], indent=2, ensure_ascii=False)
        delta_block = json.dumps(state_delta.to_dict(), indent=2, ensure_ascii=False)

        # Compact action summary (names only)
        action_summary = [
            f"{a.get('type','?')}: {a.get('source_object_name','?')} → {a.get('target_object_name', a.get('condition', '?'))}"
            for a in actions[:15]
        ]

        parts = [
            f"Goal: {goal}\n" if goal else "",
            f"Coverage Delta: {delta:.4f}\n",
            f"Actions Executed ({len(actions)}):\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(action_summary)) + "\n",
            f"Bug Signals:\n```json\n{bug_block}\n```\n",
            f"Execution Trace (first {len(trace_sample)}):\n```json\n{trace_block}\n```\n",
            f"Rule-based State Delta:\n```json\n{delta_block}\n```\n",
        ]

        if failure_summary:
            parts.append(f"Failure Summary:\n{failure_summary}\n")
        if world_summary:
            parts.append(f"World State:\n{world_summary}\n")

        # Existing failure hypotheses from rules
        if failure_hypotheses:
            hyp_block = json.dumps([h.to_dict() for h in failure_hypotheses], indent=2, ensure_ascii=False)
            parts.append(f"Rule-based Hypotheses:\n```json\n{hyp_block}\n```\n")

        prompt = "\n".join(p for p in parts if p)

        try:
            raw = self.llm.chat(
                [
                    {"role": "system", "content": _OBSERVER_STRATEGY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temp,
            )
            if raw:
                return self.llm.extract_json(raw)
        except Exception as exc:
            print(f"[OBSERVER] LLM strategy analysis failed: {exc}")
        return None

    # ------------------------------------------------------------------
    # O1: State Delta Interpreter (rule-based baseline)
    # ------------------------------------------------------------------

    def _interpret_state_delta(
        self, trace: List[Dict], actions: List[Dict],
    ) -> StateDelta:
        """Analyse trace entries to identify what state changed."""
        changed = []
        expected = []
        unexpected = []
        semantic_failures = []

        for entry in trace:
            if not isinstance(entry, dict):
                continue
            action_name = entry.get("action", "")
            before = entry.get("state_before", {})
            after = entry.get("state_after", {})
            events = entry.get("events", [])

            if before and after and before != after:
                changed.append(action_name)
                expected.append(f"{action_name} caused state change")
            elif before and after and before == after:
                if events:
                    semantic_failures.append(
                        f"{action_name}: events fired but no state change"
                    )
                else:
                    semantic_failures.append(
                        f"{action_name}: no effect at all"
                    )

        return StateDelta(
            changed_objects=changed,
            expected_changes=expected,
            unexpected_changes=unexpected,
            semantic_failures=semantic_failures,
        )

    # ------------------------------------------------------------------
    # O2: Failure Hypothesis Builder (rule-based baseline)
    # ------------------------------------------------------------------

    def _build_failure_hypotheses(
        self,
        trace: List[Dict],
        bug_signals: List[str],
        conditions,
        actions: List[Dict],
    ) -> List[FailureHypothesis]:
        """Build structured failure hypotheses from rule-based analysis."""
        hypotheses: List[FailureHypothesis] = []

        # From condition inference
        for c in (conditions or []):
            hypotheses.append(FailureHypothesis(
                hypothesis=f"[{c.failure_type}] {c.missing_condition}",
                evidence=[c.evidence] if hasattr(c, "evidence") and c.evidence else [],
                confidence=c.confidence if hasattr(c, "confidence") else 0.5,
                blocked_object=c.blocked_object if hasattr(c, "blocked_object") else "",
                needed_condition=c.missing_condition if hasattr(c, "missing_condition") else "",
            ))

        # From no-state-change patterns
        no_effect_count = 0
        for entry in trace:
            if isinstance(entry, dict):
                before = entry.get("state_before", {})
                after = entry.get("state_after", {})
                if before and after and before == after:
                    no_effect_count += 1

        if no_effect_count > 0 and no_effect_count == len(trace) and len(trace) > 1:
            hypotheses.append(FailureHypothesis(
                hypothesis="All actions had no state effect — likely missing a precondition or targeting wrong objects",
                evidence=[f"{no_effect_count}/{len(trace)} actions had zero state change"],
                confidence=0.7,
            ))

        return hypotheses

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def novelty_streak(self) -> int:
        return self._consecutive_zero_novelty

    def reset(self) -> None:
        self._consecutive_zero_novelty = 0
