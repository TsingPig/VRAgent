"""
Observer / Oracle Agent — Weak oracle judgement + exploration strategy.

Unlike a traditional test oracle that uses hard assertions, this agent
performs "弱 oracle" observation:
    - Unity Console log anomalies
    - Exception/error detection
    - Key event trigger verification
    - Object state achievement checking
    - Coverage delta evaluation
    - **Failure-to-condition inference → gate_hints** (§B3.2)

Output: coverage delta, bug signals, next-exploration suggestions,
        gate_hints (structured, consumable by Planner), failure_summary.
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
)
from ..retrieval.condition_inference import infer_conditions

if TYPE_CHECKING:
    from ..utils.llm_client import LLMClient
    from ..utils.config_loader import AgentLLMConfig


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

        Returns
        -------
        dict with keys: coverage_delta, bug_signals, next_exploration_suggestion,
        recommended_mode, gate_hints, failure_summary.
        """
        exec_out = input_data.get("executor_output", {})
        console_logs: List[str] = input_data.get("console_logs", [])
        goal: str = input_data.get("goal", "")
        actions: List[Dict] = input_data.get("actions", [])

        trace = exec_out.get("trace", [])
        coverage = exec_out.get("coverage_delta", {})
        exceptions = exec_out.get("exceptions", [])

        # ① Detect bug signals
        bug_signals = self._detect_bugs(exceptions, console_logs, trace)

        # ② Compute novelty / coverage gain
        delta = self._evaluate_coverage(coverage)

        # ③ Run failure-to-condition inference
        conditions = infer_conditions(
            actions=actions,
            executor_output=exec_out,
            console_logs=console_logs,
        )
        gate_hints = [c.to_dict() for c in conditions]

        # ④ Build failure summary
        failure_summary = self._build_failure_summary(conditions, bug_signals)

        # ⑤ Suggest next exploration action (informed by conditions)
        suggestion, mode = self._suggest_next(delta, bug_signals, trace, goal, conditions)

        # ⑥ LLM-enhanced analysis (optional)
        llm_analysis = ""
        if self.llm and self.llm_config and self.llm_config.enabled:
            llm_analysis = self._llm_enhanced_analysis(
                actions=actions,
                trace=trace,
                bug_signals=bug_signals,
                failure_summary=failure_summary,
                delta=delta,
                goal=goal,
                shared_context=input_data.get("shared_context", {}),
            )

        # Build output (extended beyond base ObserverOutput)
        output = {
            "coverage_delta": delta,
            "bug_signals": bug_signals,
            "next_exploration_suggestion": suggestion,
            "recommended_mode": mode.value,
            "gate_hints": gate_hints,
            "failure_summary": failure_summary,
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
    # LLM-enhanced observation
    # ------------------------------------------------------------------

    def _llm_enhanced_analysis(
        self,
        actions: List[Dict],
        trace: List[Dict],
        bug_signals: List[str],
        failure_summary: str,
        delta: float,
        goal: str,
        shared_context: Optional[Dict] = None,
    ) -> str:
        """Call LLM to provide deeper analysis on execution results."""
        model = self.llm_config.effective_model(self._default_model)
        temp = self.llm_config.temperature

        trace_sample = trace[:10]
        trace_block = json.dumps(trace_sample, indent=2, ensure_ascii=False)
        bug_block = json.dumps(bug_signals[:10], indent=2, ensure_ascii=False)

        prompt_parts = [
            "You are a VR test observer. Analyze the execution results of a "
            "Unity VR test session and provide insights.\n",
            f"Goal: {goal}\n" if goal else "",
            f"Coverage Delta: {delta:.4f}\n",
            f"Bug Signals:\n```json\n{bug_block}\n```\n",
            f"Execution Trace (first {len(trace_sample)} entries):\n"
            f"```json\n{trace_block}\n```\n",
        ]

        if failure_summary:
            prompt_parts.append(f"Failure Summary:\n{failure_summary}\n")

        if shared_context:
            scene_sum = shared_context.get("scene_understanding_summary", "")
            if scene_sum:
                prompt_parts.append(f"Scene Ground Truth:\n{scene_sum}\n")
            verifier_sum = shared_context.get("verifier_summary", "")
            if verifier_sum:
                prompt_parts.append(f"Verifier Notes:\n{verifier_sum}\n")

        prompt_parts.append(
            "Provide a concise analysis covering:\n"
            "1. Root cause of any failures or anomalies.\n"
            "2. Whether the coverage gain is meaningful or superficial.\n"
            "3. One specific, actionable recommendation for the next step.\n"
            "Keep the response under 200 words."
        )
        prompt = "\n".join(p for p in prompt_parts if p)

        try:
            result = self.llm.ask(prompt, model=model, temperature=temp)
            return result or ""
        except Exception as exc:
            print(f"[OBSERVER] LLM analysis failed: {exc}")
            return ""

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def novelty_streak(self) -> int:
        return self._consecutive_zero_novelty

    def reset(self) -> None:
        self._consecutive_zero_novelty = 0
