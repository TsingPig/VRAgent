"""
Executor Agent — Deterministic execution + trace recording.

This agent does NOT participate in generation — it only executes a verified
action sequence and records the resulting trace.

In the full VRAgent 2.0 pipeline this will interface with the Unity C# side
(AAU Manager + EAT actions) via a bridge (e.g. WebSocket, named pipe, or
file-based protocol).  For now we provide the Python-side contract + a
file-based stub that writes commands for Unity to consume.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent
from ..contracts import ExecutorOutput, TraceEntry, CoverageDelta
from ..utils.file_utils import save_json, load_json


class ExecutorAgent(BaseAgent):
    """Agent 3 — Executes verified actions and records traces."""

    name = "ExecutorAgent"

    def __init__(self, output_dir: str = ""):
        self.output_dir = output_dir
        self._trace: List[TraceEntry] = []
        self._exceptions: List[str] = []

    # ------------------------------------------------------------------
    # Contract entry point
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        input_data : dict
            Required keys:
                actions – list of verified action-unit dicts

        Returns
        -------
        dict matching ExecutorOutput schema.
        """
        actions: List[Dict] = input_data.get("actions", [])
        self._trace.clear()
        self._exceptions.clear()

        for action in actions:
            entry = self._execute_single(action)
            self._trace.append(entry)

        output = ExecutorOutput(
            trace=self._trace,
            coverage_delta=self._compute_coverage(),
            exceptions=self._exceptions,
        )

        # Persist trace to disk
        if self.output_dir:
            self._save_trace()

        return output.to_dict()

    # ------------------------------------------------------------------
    # Execution (stub — will be replaced by Unity bridge)
    # ------------------------------------------------------------------

    def _execute_single(self, action: Dict[str, Any]) -> TraceEntry:
        """Execute one action unit.

        Currently writes the action to a command file for the Unity side
        to pick up.  In the future this will use a real-time bridge.
        """
        action_type = action.get("type", "Unknown")
        source_name = action.get("source_object_name", "")
        entry = TraceEntry(
            action=f"{action_type}:{source_name}",
            state_before={},
            state_after={},
            events=[],
        )

        try:
            # Write command for Unity bridge
            if self.output_dir:
                cmd_path = os.path.join(self.output_dir, "pending_command.json")
                save_json(cmd_path, action)

                # In production: wait for Unity to execute and return state
                # For now, log the action
                print(f"[EXECUTOR] Dispatched: {action_type} on {source_name}")
                entry.events.append(f"dispatched:{action_type}")

                # Check if Unity has left a result file
                result_path = os.path.join(self.output_dir, "command_result.json")
                if os.path.exists(result_path):
                    result = load_json(result_path)
                    entry.state_after = result.get("state_after", {})
                    entry.events.extend(result.get("events", []))
                    os.remove(result_path)
            else:
                print(f"[EXECUTOR] (dry-run) {action_type} on {source_name}")

        except Exception as exc:
            self._exceptions.append(f"{action_type}:{source_name} → {exc}")
            print(f"[EXECUTOR] Exception: {exc}")

        return entry

    # ------------------------------------------------------------------
    # Coverage computation (stub — will use Unity Code Coverage API)
    # ------------------------------------------------------------------

    def _compute_coverage(self) -> CoverageDelta:
        """Compute coverage delta after execution.

        In production this will read from Unity's Code Coverage package
        output.  For now returns zeroes.
        """
        return CoverageDelta(LC=0.0, MC=0.0, CoIGO=0.0)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_trace(self) -> None:
        path = os.path.join(self.output_dir, f"trace_{datetime.now():%Y%m%d_%H%M%S}.json")
        from dataclasses import asdict
        save_json(path, [asdict(t) for t in self._trace])
        print(f"[EXECUTOR] Trace saved: {path}")
