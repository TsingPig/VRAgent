"""
Executor Agent — Deterministic execution + trace recording.

This agent does NOT participate in generation — it only executes a verified
action sequence and records the resulting trace.

Supports two modes:
    1. **Online** (UnityBridge connected) — sends actions via TCP to Unity,
       receives real state_before/state_after/events/exceptions.
    2. **Offline / dry-run** — logs actions to disk for manual import.
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

    def __init__(self, output_dir: str = "", unity_bridge=None):
        """
        Parameters
        ----------
        output_dir : str
            Directory for trace persistence.
        unity_bridge : UnityBridge or None
            If provided, actions are executed in Unity via TCP.
            If None, falls back to dry-run / file-based mode.
        """
        self.output_dir = output_dir
        self.bridge = unity_bridge  # vragent2.bridge.UnityBridge
        self._trace: List[TraceEntry] = []
        self._exceptions: List[str] = []
        self._log_cursor: int = 0  # for incremental log queries

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
    # Execution — routes to online (TCP) or offline (file) mode
    # ------------------------------------------------------------------

    def _execute_single(self, action: Dict[str, Any]) -> TraceEntry:
        """Execute one action unit."""
        action_type = action.get("type", "Unknown")
        source_name = action.get("source_object_name", "")

        # ── Online mode: real Unity execution ────────────────────────
        if self.bridge is not None and self.bridge.connected:
            return self._execute_via_bridge(action, action_type, source_name)

        # ── Offline / dry-run mode ───────────────────────────────────
        return self._execute_offline(action, action_type, source_name)

    def _execute_via_bridge(self, action: Dict, action_type: str, source_name: str) -> TraceEntry:
        """Send action to Unity via TCP and parse the response."""
        entry = TraceEntry(
            action=f"{action_type}:{source_name}",
            state_before={},
            state_after={},
            events=[],
        )
        try:
            prewarm_plan = {
                "taskUnits": [
                    {
                        "actionUnits": [action]
                    }
                ]
            }
            import_result = self.bridge.import_objects(prewarm_plan, use_file_id=True)
            if not import_result.get("success", False):
                error_msg = import_result.get("error_message", "ImportObjects failed")
                self._exceptions.append(f"{action_type}:{source_name} → import_failed:{error_msg}")
                entry.events.append(f"import_error:{error_msg}")
                print(f"[EXECUTOR] IMPORT FAILED: {action_type} on {source_name} — {error_msg}")
                return entry

            result = self.bridge.execute(action)

            if result.get("success", False):
                entry.state_before = result.get("state_before", {}) or {}
                entry.state_after = result.get("state_after", {}) or {}
                entry.events = result.get("events", [])
                duration = result.get("duration_ms", 0)
                print(f"[EXECUTOR] {action_type} on {source_name} — {duration:.0f}ms")
            else:
                error_msg = result.get("error_message", "Unknown error")
                self._exceptions.append(f"{action_type}:{source_name} → {error_msg}")
                entry.events.append(f"error:{error_msg}")
                print(f"[EXECUTOR] FAILED: {action_type} on {source_name} — {error_msg}")

            # Collect any exceptions reported by Unity
            for exc in result.get("exceptions", []):
                self._exceptions.append(f"{action_type}:{source_name} → {exc}")
                entry.events.append(f"exception:{exc}")

        except Exception as exc:
            self._exceptions.append(f"{action_type}:{source_name} → {exc}")
            entry.events.append(f"bridge_error:{exc}")
            print(f"[EXECUTOR] Bridge exception: {exc}")

        return entry

    def _execute_offline(self, action: Dict, action_type: str, source_name: str) -> TraceEntry:
        """Dry-run / file-based fallback."""
        entry = TraceEntry(
            action=f"{action_type}:{source_name}",
            state_before={},
            state_after={},
            events=[],
        )
        try:
            if self.output_dir:
                cmd_path = os.path.join(self.output_dir, "pending_command.json")
                save_json(cmd_path, action)
                print(f"[EXECUTOR] Dispatched: {action_type} on {source_name}")
                entry.events.append(f"dispatched:{action_type}")

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
    # Unity Console Logs (online only)
    # ------------------------------------------------------------------

    def get_console_logs(self) -> List[str]:
        """Fetch new console logs from Unity since last call."""
        if self.bridge is None or not self.bridge.connected:
            return []
        try:
            result = self.bridge.query_logs(since_index=self._log_cursor)
            self._log_cursor = result.get("next_index", self._log_cursor)
            return [
                f"[{log.get('level', 'Log')}] {log.get('message', '')}"
                for log in result.get("logs", [])
            ]
        except Exception as exc:
            print(f"[EXECUTOR] Failed to query logs: {exc}")
            return []

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
