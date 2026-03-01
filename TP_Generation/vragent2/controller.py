"""
Controller — Top-level orchestrator for the VRAgent 2.0 pipeline (§B2.3).

Loop: Planner → Verifier → [repair] → Executor → Observer → ExplorationController
Repeats until budget exhausted or coverage target reached.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agents.planner import PlannerAgent
from .agents.verifier import VerifierAgent
from .agents.executor import ExecutorAgent
from .agents.observer import ObserverAgent
from .contracts import ExplorationGoal, ExplorationMode
from .exploration.explorer import ExplorationController
from .graph.gate_graph import GateGraph, StateNode
from .retrieval.retrieval_layer import RetrievalLayer
from .utils.llm_client import LLMClient
from .utils.config_loader import VRAgentConfig, load_config
from .utils.file_utils import save_json, load_json, ensure_dir


class VRAgentController:
    """Main orchestrator — drives the four-agent closed-loop pipeline."""

    def __init__(
        self,
        config: VRAgentConfig,
        llm: LLMClient,
        retrieval: RetrievalLayer,
        *,
        output_dir: str = "Results_VRAgent2.0",
        app_name: str = "UnityApp",
        scene_name: str = "",
        total_budget: int = 100,
        max_repair_rounds: int = 2,
        llm_model: str = "gpt-4o",
        unity_bridge=None,
    ):
        self.config = config
        self.output_dir = output_dir
        self.scene_name = scene_name
        self.max_repair_rounds = max_repair_rounds
        self.unity_bridge = unity_bridge

        # Build sub-components
        self.gate_graph = GateGraph()
        self.planner = PlannerAgent(
            llm, retrieval, config,
            app_name=app_name, llm_model=llm_model,
        )
        self.verifier = VerifierAgent(retrieval)
        self.executor = ExecutorAgent(
            output_dir=os.path.join(output_dir, "execution"),
            unity_bridge=unity_bridge,
        )
        self.observer = ObserverAgent()
        self.explorer = ExplorationController(
            self.gate_graph,
            total_budget=total_budget,
        )
        self.retrieval = retrieval
        self.llm = llm

        # Accumulated results
        self._all_actions: List[Dict] = []
        self._all_traces: List[Dict] = []
        self._iteration_logs: List[Dict] = []
        self._processed_objects: set = set()  # Object names already processed (for resume)

    # ------------------------------------------------------------------
    # Session persistence (resume support)
    # ------------------------------------------------------------------

    def save_session(self) -> None:
        """Persist current session state so it can be resumed later."""
        session = {
            "processed_objects": list(self._processed_objects),
            "all_actions": self._all_actions,
            "all_traces": self._all_traces,
            "iteration_logs": self._iteration_logs,
            "explorer_state": {
                "mode": self.explorer.state.mode.value,
                "step_count": self.explorer.state.step_count,
                "budget_remaining": self.explorer.state.budget_remaining,
                "total_coverage": self.explorer.state.total_coverage,
                "zero_novelty_streak": self.explorer.state.zero_novelty_streak,
                "solved_gates": self.explorer.state.solved_gates,
            },
            "gate_graph": self.gate_graph.to_dict(),
        }
        path = os.path.join(self.output_dir, "session_state.json")
        ensure_dir(self.output_dir)
        save_json(path, session)
        print(f"[CONTROLLER] Session saved ({len(self._processed_objects)} objects processed)")

    def load_session(self) -> bool:
        """Load previous session state if available. Returns True if loaded."""
        path = os.path.join(self.output_dir, "session_state.json")
        if not os.path.exists(path):
            print("[CONTROLLER] No previous session found — starting fresh")
            return False

        from .graph.gate_graph import GateGraph
        from .contracts import ExplorationMode

        data = load_json(path)
        if not data:
            return False

        self._processed_objects = set(data.get("processed_objects", []))
        self._all_actions = data.get("all_actions", [])
        self._all_traces = data.get("all_traces", [])
        self._iteration_logs = data.get("iteration_logs", [])

        # Restore explorer state
        es = data.get("explorer_state", {})
        if es:
            self.explorer.state.step_count = es.get("step_count", 0)
            self.explorer.state.budget_remaining = es.get("budget_remaining",
                                                          self.explorer.state.budget_remaining)
            self.explorer.state.total_coverage = es.get("total_coverage", 0.0)
            self.explorer.state.zero_novelty_streak = es.get("zero_novelty_streak", 0)
            self.explorer.state.solved_gates = es.get("solved_gates", [])
            try:
                self.explorer.state.mode = ExplorationMode(es.get("mode", "expand"))
            except ValueError:
                pass

        # Restore gate graph
        gg_data = data.get("gate_graph", {})
        if gg_data:
            self.gate_graph = GateGraph.load_from_dict(gg_data)
            self.explorer.gate_graph = self.gate_graph

        print(f"[CONTROLLER] Session resumed — {len(self._processed_objects)} objects already processed, "
              f"{len(self._all_actions)} actions cached, "
              f"budget remaining: {self.explorer.state.budget_remaining}")
        return True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, gobj_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run the complete pipeline over a list of top-level GameObjects.

        Parameters
        ----------
        gobj_list : list of dicts
            Each dict is a gobj_info from gobj_hierarchy.json.

        Returns
        -------
        dict with keys: actions, traces, iterations, gate_graph, summary.
        """
        ensure_dir(self.output_dir)
        ensure_dir(os.path.join(self.output_dir, "execution"))
        print(f"[CONTROLLER] Starting VRAgent 2.0 — {len(gobj_list)} objects, scene={self.scene_name}")

        # Initial goal: Expand (explore everything)
        observer_output: Dict[str, Any] = {
            "coverage_delta": 0.0,
            "bug_signals": [],
            "next_exploration_suggestion": "Initial exploration of all interactable objects.",
            "recommended_mode": ExplorationMode.EXPAND.value,
        }

        iteration = 0
        for gobj_info in gobj_list:
            gobj_name = gobj_info.get("gameobject_name", "?")

            # Skip objects already processed in a previous session
            if gobj_name in self._processed_objects:
                print(f"[CONTROLLER] Skipping {gobj_name} (already processed in previous session)")
                continue

            goal = self.explorer.next_goal(observer_output)
            if goal is None:
                print("[CONTROLLER] Budget exhausted.")
                break

            print(f"\n{'='*60}")
            print(f"[CONTROLLER] Iteration {iteration} | Mode: {goal.mode.value} | Object: {gobj_name}")
            print(f"[CONTROLLER] Goal: {goal.description}")
            print(f"{'='*60}")

            result = self._run_single_object(gobj_info, goal, iteration)
            observer_output = result.get("observer_output", observer_output)

            # Mark object as processed and save session incrementally
            self._processed_objects.add(gobj_name)
            self.save_session()

            iteration += 1

        # Save final results
        return self._finalize()

    # ------------------------------------------------------------------
    # Single-object pipeline
    # ------------------------------------------------------------------

    def _run_single_object(
        self, gobj_info: Dict, goal: ExplorationGoal, iteration: int
    ) -> Dict[str, Any]:
        log_entry: Dict[str, Any] = {
            "iteration": iteration,
            "object": gobj_info.get("gameobject_name", ""),
            "goal": goal.description,
            "mode": goal.mode.value,
            "timestamp": datetime.now().isoformat(),
        }

        # ── 1. Plan ──────────────────────────────────────────────────
        print("[CONTROLLER] → Planner")
        planner_output = self.planner.run({
            "gobj_info": gobj_info,
            "scene_name": self.scene_name,
            "goal": goal.description,
        })
        actions = planner_output.get("actions", [])
        log_entry["planned_actions"] = len(actions)
        print(f"[CONTROLLER]   Planner proposed {len(actions)} actions")

        # ── 2. Verify (+ repair loop) ────────────────────────────────
        print("[CONTROLLER] → Verifier")
        llm_ctx: List[Dict[str, str]] = []
        for repair_round in range(self.max_repair_rounds + 1):
            verifier_output = self.verifier.run({"actions": actions})
            errors = verifier_output.get("errors", [])
            passed = verifier_output.get("passed", verifier_output.get("pass", False))
            score = verifier_output.get("executable_score", 0.0)
            print(f"[CONTROLLER]   Verifier score={score:.2f}, errors={len(errors)}, pass={passed}")

            if passed or repair_round >= self.max_repair_rounds:
                actions = verifier_output.get("patched_actions", actions)
                break

            # Structured repair
            print(f"[CONTROLLER]   Repair round {repair_round + 1}")
            actions = self.planner.repair(actions, errors, llm_ctx)

        log_entry["verified_actions"] = len(actions)
        log_entry["verifier_score"] = score
        log_entry["verifier_errors"] = len(errors)

        # ── 3. Execute ───────────────────────────────────────────────
        print("[CONTROLLER] → Executor")
        executor_output = self.executor.run({"actions": actions})
        trace = executor_output.get("trace", [])
        exceptions = executor_output.get("exceptions", [])
        print(f"[CONTROLLER]   Executed {len(trace)} actions, {len(exceptions)} exceptions")

        self._all_actions.extend(actions)
        self._all_traces.extend(trace)

        # ── 4. Observe ───────────────────────────────────────────────
        print("[CONTROLLER] → Observer")
        console_logs = self.executor.get_console_logs()
        observer_output = self.observer.run({
            "executor_output": executor_output,
            "console_logs": console_logs,
            "goal": goal.description,
        })
        delta = observer_output.get("coverage_delta", 0.0)
        bugs = observer_output.get("bug_signals", [])
        print(f"[CONTROLLER]   Coverage delta={delta:.4f}, bugs={len(bugs)}")

        # ── 5. Update Gate Graph ─────────────────────────────────────
        self._update_gate_graph(gobj_info, actions, executor_output, observer_output)

        log_entry["coverage_delta"] = delta
        log_entry["bugs"] = bugs
        log_entry["observer_suggestion"] = observer_output.get("next_exploration_suggestion", "")
        self._iteration_logs.append(log_entry)

        return {"observer_output": observer_output, "log": log_entry}

    # ------------------------------------------------------------------
    # Gate Graph updates
    # ------------------------------------------------------------------

    def _update_gate_graph(
        self,
        gobj_info: Dict,
        actions: List[Dict],
        executor_output: Dict,
        observer_output: Dict,
    ) -> None:
        gobj_name = gobj_info.get("gameobject_name", "unknown")
        node = StateNode(
            node_id=f"state_{self.explorer.state.step_count}",
            label=gobj_name,
            room=gobj_name,
        )
        self.gate_graph.add_state(node)

        # Record success/failure edges based on trace
        for trace_entry in executor_output.get("trace", []):
            events = trace_entry.get("events", [])
            action_name = trace_entry.get("action", "")
            success = "dispatched" in " ".join(events) if events else True
            if success:
                self.gate_graph.add_edge(
                    node.node_id, node.node_id,
                    action=action_name, success=True,
                )
            else:
                evidence = "; ".join(events)
                self.gate_graph.add_edge(
                    node.node_id, f"blocked_{action_name}",
                    action=action_name, success=False,
                    evidence=evidence,
                )

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def _finalize(self) -> Dict[str, Any]:
        summary = {
            "total_actions": len(self._all_actions),
            "total_traces": len(self._all_traces),
            "iterations": len(self._iteration_logs),
            "explorer": self.explorer.summary(),
            "gate_graph_nodes": len(self.gate_graph.nodes),
            "gate_graph_edges": len(self.gate_graph.edges),
        }
        print(f"\n[CONTROLLER] === DONE ===")
        print(f"[CONTROLLER] {json.dumps(summary, indent=2)}")

        # Save outputs
        save_json(os.path.join(self.output_dir, "all_actions.json"), self._all_actions)
        save_json(os.path.join(self.output_dir, "iteration_logs.json"), self._iteration_logs)
        save_json(os.path.join(self.output_dir, "summary.json"), summary)
        self.gate_graph.save(os.path.join(self.output_dir, "gate_graph.json"))

        # Save test plan in VRAgent-compatible format
        test_plan = self._build_test_plan()
        save_json(os.path.join(self.output_dir, "test_plan.json"), test_plan)

        return {
            "actions": self._all_actions,
            "traces": self._all_traces,
            "iterations": self._iteration_logs,
            "gate_graph": self.gate_graph.to_dict(),
            "test_plan": test_plan,
            "summary": summary,
        }

    def _build_test_plan(self) -> Dict[str, Any]:
        """Convert accumulated actions into VRAgent 1.0–compatible test plan format."""
        task_units = []
        current_task: Dict[str, Any] = {"actionUnits": []}

        for action in self._all_actions:
            current_task["actionUnits"].append(action)
            # Group by source object (one taskUnit per object)
            if len(current_task["actionUnits"]) >= 10:
                task_units.append(current_task)
                current_task = {"actionUnits": []}

        if current_task["actionUnits"]:
            task_units.append(current_task)

        return {"taskUnits": task_units}
