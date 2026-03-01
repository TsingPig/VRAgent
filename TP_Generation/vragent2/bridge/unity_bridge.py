"""
Unity Bridge — Python TCP client that talks to Unity's AgentBridge server.

Wire format: [4-byte LE length prefix][UTF-8 JSON body]

This module replaces the file-based stub in executor.py with a real-time
TCP connection to the Unity runtime.

Usage::

    bridge = UnityBridge("127.0.0.1", 6400)
    bridge.connect()

    # Pre-resolve FileIDs
    import_result = bridge.import_objects(task_list_dict)

    # Execute a single action
    result = bridge.execute(action_unit_dict)
    print(result["state_after"])

    # Query live state
    states = bridge.query_state(["12345", "67890"])

    # Get console logs
    logs = bridge.query_logs(since_index=0)

    bridge.close()
"""

from __future__ import annotations

import json
import socket
import struct
import uuid
from typing import Any, Dict, List, Optional


class UnityBridge:
    """TCP client for VRAgent 2.0 ↔ Unity communication."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6400, timeout: float = 60.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to Unity's AgentBridge TCP server."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.connect((self.host, self.port))
        print(f"[UnityBridge] Connected to {self.host}:{self.port}")

    def close(self) -> None:
        """Gracefully disconnect."""
        if self._sock:
            try:
                self._send_command({"type": "Shutdown", "request_id": self._rid()})
                # Read the Pong response
                self._recv_response()
            except Exception:
                pass
            finally:
                self._sock.close()
                self._sock = None
        print("[UnityBridge] Disconnected")

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Check if Unity is responsive."""
        resp = self._request({"type": "Ping"})
        return resp.get("success", False)

    def import_objects(self, task_list: Dict[str, Any], use_file_id: bool = True) -> Dict[str, Any]:
        """Pre-resolve FileIDs in Unity — equivalent to VRAgent.ImportTestPlan().

        Parameters
        ----------
        task_list : dict
            A test plan dict with "taskUnits" key.
        use_file_id : bool
            Whether to use FileID (True) or GUID (False) for resolution.

        Returns
        -------
        dict with keys: objects_found, objects_total, components_found, components_total
        """
        return self._request({
            "type": "ImportObjects",
            "task_list": task_list,
            "use_file_id": use_file_id,
        })

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single ActionUnit in Unity.

        Parameters
        ----------
        action : dict
            An action unit dict, e.g. {"type": "Grab", "source_object_fileID": "123", ...}

        Returns
        -------
        dict with keys: action_type, source_object, state_before, state_after,
                        events, exceptions, duration_ms
        """
        return self._request({
            "type": "Execute",
            "action": action,
        })

    def execute_batch(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute multiple ActionUnits sequentially.

        Returns
        -------
        dict with keys: results (list of execution results), total_duration_ms
        """
        return self._request({
            "type": "ExecuteBatch",
            "actions": actions,
        })

    def query_state(self, file_ids: List[str]) -> Dict[str, Any]:
        """Query current state of objects by FileID.

        Returns
        -------
        dict with key "states" → {fileId: {name, active, position, rotation, ...}}
        """
        return self._request({
            "type": "QueryState",
            "object_fileids": file_ids,
        })

    def query_logs(self, since_index: int = 0) -> Dict[str, Any]:
        """Get Unity Console logs since the given index.

        Returns
        -------
        dict with keys: logs (list of {index, level, message, timestamp}), next_index
        """
        return self._request({
            "type": "QueryLogs",
            "since_index": since_index,
        })

    def reset(self) -> Dict[str, Any]:
        """Reset Unity scene state (clear FileIDs, temp objects, logs)."""
        return self._request({"type": "Reset"})

    # ------------------------------------------------------------------
    # Low-level protocol
    # ------------------------------------------------------------------

    def _request(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command and wait for the response."""
        if not command.get("request_id"):
            command["request_id"] = self._rid()

        self._send_command(command)
        return self._recv_response()

    def _send_command(self, command: Dict[str, Any]) -> None:
        """Send a length-prefixed JSON message."""
        if self._sock is None:
            raise ConnectionError("Not connected to Unity. Call connect() first.")

        body = json.dumps(command, ensure_ascii=False).encode("utf-8")
        header = struct.pack("<I", len(body))  # 4 bytes little-endian
        self._sock.sendall(header + body)

    def _recv_response(self) -> Dict[str, Any]:
        """Receive a length-prefixed JSON response."""
        # Read 4-byte header
        header = self._recv_exact(4)
        length = struct.unpack("<I", header)[0]

        if length <= 0 or length > 10 * 1024 * 1024:
            raise ValueError(f"Invalid response length: {length}")

        body = self._recv_exact(length)
        return json.loads(body.decode("utf-8"))

    def _recv_exact(self, n: int) -> bytes:
        """Read exactly n bytes from the socket."""
        data = bytearray()
        while len(data) < n:
            chunk = self._sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Unity connection closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    @staticmethod
    def _rid() -> str:
        """Generate a short unique request ID."""
        return uuid.uuid4().hex[:8]
