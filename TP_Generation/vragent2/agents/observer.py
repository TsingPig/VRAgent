"""
Observer / Oracle Agent — Weak oracle judgement + exploration strategy.

Unlike a traditional test oracle that uses hard assertions, this agent
performs "弱 oracle" observation:
    - Unity Console log anomalies
    - Exception/error detection
    - Key event trigger verification
    - Object state achievement checking
    - Coverage delta evaluation

Output: coverage delta, bug signals, and next-exploration suggestions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent
from ..contracts import (
    ObserverOutput,
    ExplorationMode,
    CoverageDelta,
    TraceEntry,
)


class ObserverAgent(BaseAgent):
    """Agent 4 — Judges execution results and recommends next moves."""

    name = "ObserverAgent"

    def __init__(self, *, novelty_threshold_k: int = 5):
        self.novelty_threshold_k = novelty_threshold_k
        self._consecutive_zero_novelty: int = 0
        self._total_coverage = CoverageDelta()

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

        Returns
        -------
        dict matching ObserverOutput schema.
        """
        exec_out = input_data.get("executor_output", {})
        console_logs: List[str] = input_data.get("console_logs", [])
        goal: str = input_data.get("goal", "")

        trace = exec_out.get("trace", [])
        coverage = exec_out.get("coverage_delta", {})
        exceptions = exec_out.get("exceptions", [])

        # ① Detect bug signals
        bug_signals = self._detect_bugs(exceptions, console_logs, trace)

        # ② Compute novelty / coverage gain
        delta = self._evaluate_coverage(coverage)

        # ③ Suggest next exploration action
        suggestion, mode = self._suggest_next(delta, bug_signals, trace, goal)

        output = ObserverOutput(
            coverage_delta=delta,
            bug_signals=bug_signals,
            next_exploration_suggestion=suggestion,
            recommended_mode=mode,
        )
        return output.to_dict()

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
    # Exploration suggestion
    # ------------------------------------------------------------------

    def _suggest_next(
        self,
        delta: float,
        bug_signals: List[str],
        trace: List[Dict],
        goal: str,
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

        # Exploit mode: gate / lock detected
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
    # State accessors
    # ------------------------------------------------------------------

    @property
    def novelty_streak(self) -> int:
        return self._consecutive_zero_novelty

    def reset(self) -> None:
        self._consecutive_zero_novelty = 0
