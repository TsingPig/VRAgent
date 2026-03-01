"""
Exploration Controller — Three-mode PFSM variant (§B4).

| Mode      | Goal                           | Trigger                       |
|-----------|--------------------------------|-------------------------------|
| Expand    | Discover new rooms/UI branches | Init or unlock → new area     |
| Exploit   | Resolve gate conditions        | lock/need_item detected       |
| Recover   | Backtrack & re-index           | K steps with 0 novelty        |

The controller selects the current mode and provides a goal to the Planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..contracts import ExplorationMode, ExplorationGoal
from ..graph.gate_graph import GateGraph, GateEdge, StateNode


@dataclass
class ExplorationState:
    """Mutable state maintained by the explorer across iterations."""
    mode: ExplorationMode = ExplorationMode.EXPAND
    current_node_id: str = ""
    step_count: int = 0
    zero_novelty_streak: int = 0
    total_coverage: float = 0.0
    budget_remaining: int = 100
    solved_gates: List[str] = field(default_factory=list)


class ExplorationController:
    """PFSM-style controller that decides *what to explore next*."""

    def __init__(
        self,
        gate_graph: GateGraph,
        *,
        novelty_k: int = 5,
        total_budget: int = 100,
    ):
        self.gate_graph = gate_graph
        self.novelty_k = novelty_k
        self.state = ExplorationState(budget_remaining=total_budget)

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def next_goal(self, observer_output: Dict[str, Any]) -> Optional[ExplorationGoal]:
        """Consume Observer output and produce the next exploration goal.

        Returns None when the budget is exhausted.
        """
        if self.state.budget_remaining <= 0:
            return None

        # Update internal state from observer
        delta = observer_output.get("coverage_delta", 0.0)
        bug_signals: List[str] = observer_output.get("bug_signals", [])
        mode = observer_output.get("recommended_mode", "")
        suggestion = observer_output.get("next_exploration_suggestion", "")

        self.state.step_count += 1
        self.state.budget_remaining -= 1
        self.state.total_coverage += delta

        # Update novelty streak
        if delta <= 0.001:
            self.state.zero_novelty_streak += 1
        else:
            self.state.zero_novelty_streak = 0

        # Determine mode
        new_mode = self._select_mode(delta, bug_signals, mode)
        self.state.mode = new_mode

        # Build goal
        goal = self._build_goal(new_mode, suggestion, bug_signals)
        return goal

    # ------------------------------------------------------------------
    # Mode selection
    # ------------------------------------------------------------------

    def _select_mode(
        self, delta: float, bugs: List[str], observer_mode: str
    ) -> ExplorationMode:
        # Recover: stuck
        if self.state.zero_novelty_streak >= self.novelty_k:
            self.state.zero_novelty_streak = 0
            return ExplorationMode.RECOVER

        # Exploit: gates found
        frontier = self.gate_graph.get_frontier()
        unsolved = [e for e in frontier if e.action not in self.state.solved_gates]
        if unsolved:
            # Check if any gate has a condition we might be able to solve
            return ExplorationMode.EXPLOIT

        # Observer recommendation
        if observer_mode:
            try:
                return ExplorationMode(observer_mode)
            except ValueError:
                pass

        # Default: expand
        return ExplorationMode.EXPAND

    # ------------------------------------------------------------------
    # Goal construction
    # ------------------------------------------------------------------

    def _build_goal(
        self,
        mode: ExplorationMode,
        observer_suggestion: str,
        bugs: List[str],
    ) -> ExplorationGoal:
        if mode == ExplorationMode.RECOVER:
            return ExplorationGoal(
                mode=mode,
                description=(
                    "Stuck — backtrack to last productive state and try "
                    "alternative interaction paths."
                ),
                target_objects=[],
                priority=0.9,
            )

        if mode == ExplorationMode.EXPLOIT:
            frontier = self.gate_graph.get_frontier()
            targets = [e.action for e in frontier[:3]]  # top 3 gates
            desc = "Resolve gate conditions: " + ", ".join(targets)
            return ExplorationGoal(
                mode=mode,
                description=desc,
                target_objects=targets,
                priority=0.8,
            )

        # Expand
        return ExplorationGoal(
            mode=mode,
            description=observer_suggestion or "Explore new interaction targets.",
            target_objects=[],
            priority=0.5,
        )

    # ------------------------------------------------------------------
    # Gate resolution bookkeeping
    # ------------------------------------------------------------------

    def mark_gate_solved(self, action: str) -> None:
        if action not in self.state.solved_gates:
            self.state.solved_gates.append(action)

    @property
    def is_exhausted(self) -> bool:
        return self.state.budget_remaining <= 0

    def summary(self) -> Dict[str, Any]:
        return {
            "mode": self.state.mode.value,
            "step": self.state.step_count,
            "budget_remaining": self.state.budget_remaining,
            "total_coverage": round(self.state.total_coverage, 4),
            "gates_frontier": len(self.gate_graph.get_frontier()),
            "gates_solved": len(self.state.solved_gates),
        }
