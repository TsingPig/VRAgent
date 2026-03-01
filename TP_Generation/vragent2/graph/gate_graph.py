"""
Gate Graph — Online-updated graph for non-linear exploration (§B3).

Nodes = state signatures (room / UI panel / game state)
Edges = actions (interaction / movement / UI operation)
Edge annotations = success/failure + failure type + evidence

Supports Failure-to-Condition reverse reasoning (§B3.2):
    When blocked, query the retrieval layer for scripts/UI that
    explain the gating condition and produce structured unlock hints.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..contracts import GateEdge, GateCondition, GateFailureType


# ---------------------------------------------------------------------------
# State signature
# ---------------------------------------------------------------------------

@dataclass
class StateNode:
    """A snapshot of the world state at one exploration step."""
    node_id: str
    label: str = ""
    room: str = ""
    active_ui: str = ""
    flags: Dict[str, Any] = field(default_factory=dict)

    @property
    def signature(self) -> str:
        """Deterministic hash-like key for dedup."""
        parts = [self.room, self.active_ui]
        parts.extend(f"{k}={v}" for k, v in sorted(self.flags.items()))
        return "|".join(parts)


# ---------------------------------------------------------------------------
# Gate Graph
# ---------------------------------------------------------------------------

class GateGraph:
    """
    Maintain an online-updated directed graph of explored states.

    Usage::

        gg = GateGraph()
        s0 = gg.add_state(StateNode("s0", room="Room1"))
        s1 = gg.add_state(StateNode("s1", room="Room2"))
        gg.add_edge(s0, s1, action="MoveToRoom2", success=True)
        gg.add_edge(s0, "locked_door", action="OpenDoor",
                    success=False, failure_type=GateFailureType.LOCKED,
                    evidence="Door requires BlueKey")
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, StateNode] = {}
        self.edges: List[GateEdge] = []
        self._sig_to_id: Dict[str, str] = {}  # signature → node_id

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_state(self, node: StateNode) -> str:
        """Add a state node (dedup by signature). Return node_id."""
        sig = node.signature
        if sig in self._sig_to_id:
            return self._sig_to_id[sig]
        self.nodes[node.node_id] = node
        self._sig_to_id[sig] = node.node_id
        return node.node_id

    def get_state(self, node_id: str) -> Optional[StateNode]:
        return self.nodes.get(node_id)

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        *,
        action: str,
        success: bool = True,
        failure_type: Optional[GateFailureType] = None,
        evidence: str = "",
    ) -> GateEdge:
        edge = GateEdge(
            from_state=from_id,
            to_state=to_id,
            action=action,
            success=success,
            failure_type=failure_type.value if failure_type else "",
            evidence=evidence,
        )
        self.edges.append(edge)
        return edge

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_failed_edges(self) -> List[GateEdge]:
        return [e for e in self.edges if not e.success]

    def get_unreached_from(self, node_id: str) -> List[GateEdge]:
        """Get edges from *node_id* that failed, i.e. gated transitions."""
        return [e for e in self.edges if e.from_state == node_id and not e.success]

    def get_reachable(self, start_id: str) -> Set[str]:
        """BFS reachable set from *start_id* using success-edges only."""
        visited: Set[str] = set()
        queue = [start_id]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            for edge in self.edges:
                if edge.from_state == curr and edge.success and edge.to_state not in visited:
                    queue.append(edge.to_state)
        return visited

    def get_frontier(self) -> List[GateEdge]:
        """Failed edges whose from-states ARE reachable from any root node.

        These are the "gates" worth solving next.
        """
        # Find roots (nodes with no incoming success edge)
        has_incoming = {e.to_state for e in self.edges if e.success}
        roots = [nid for nid in self.nodes if nid not in has_incoming]
        if not roots:
            roots = list(self.nodes.keys())[:1]

        reachable: Set[str] = set()
        for r in roots:
            reachable |= self.get_reachable(r)

        return [e for e in self.edges if not e.success and e.from_state in reachable]

    # ------------------------------------------------------------------
    # Failure-to-Condition reverse reasoning (§B3.2)
    # ------------------------------------------------------------------

    def reason_gate_condition(
        self, edge: GateEdge, retrieval: Any
    ) -> Optional[GateCondition]:
        """Ask the retrieval layer to explain *why* the gate failed.

        Steps:
            1. Parse evidence for keywords (key, switch, flag, item)
            2. Search scripts & UI bindings for condition logic
            3. Return structured condition + candidate obtain-path

        Parameters
        ----------
        edge : GateEdge
        retrieval : RetrievalLayer

        Returns
        -------
        GateCondition or None if no hypothesis can be formed.
        """
        evidence = edge.evidence.lower()
        condition_type = ""
        condition_value = ""

        # Heuristic keyword extraction
        if any(kw in evidence for kw in ("key", "钥匙", "item", "物品")):
            condition_type = "need_item"
            condition_value = self._extract_item_name(edge.evidence)
        elif any(kw in evidence for kw in ("switch", "开关", "flag", "lever")):
            condition_type = "need_flag"
            condition_value = self._extract_flag_name(edge.evidence)
        elif any(kw in evidence for kw in ("hidden", "invisible", "不可见", "disabled")):
            condition_type = "ui_hidden"
            condition_value = edge.action
        elif any(kw in evidence for kw in ("locked", "锁")):
            condition_type = "locked"
            condition_value = edge.action
        else:
            condition_type = "unknown"
            condition_value = edge.evidence[:80]

        # Try to find obtain-path via retrieval
        obtain_hints: List[str] = []
        if hasattr(retrieval, "scene") and retrieval.scene:
            # Search for scripts mentioning the condition
            search_terms = [condition_value] if condition_value else []
            for term in search_terms:
                results = retrieval.scene.search_scripts(term) if hasattr(retrieval.scene, "search_scripts") else []
                for r in results:
                    obtain_hints.append(f"Script mentions '{term}': {r}")

        return GateCondition(
            gate_edge_action=edge.action,
            condition_type=condition_type,
            condition_value=condition_value,
            obtain_path_hints=obtain_hints,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: asdict(n) for nid, n in self.nodes.items()},
            "edges": [asdict(e) for e in self.edges],
        }

    def save(self, path: str) -> None:
        from ..utils.file_utils import save_json
        save_json(path, self.to_dict())

    @classmethod
    def load(cls, path: str) -> GateGraph:
        from ..utils.file_utils import load_json
        data = load_json(path)
        gg = cls()
        for nid, nd in data.get("nodes", {}).items():
            gg.nodes[nid] = StateNode(**nd)
            gg._sig_to_id[gg.nodes[nid].signature] = nid
        for ed in data.get("edges", []):
            gg.edges.append(GateEdge(**ed))
        return gg

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_item_name(evidence: str) -> str:
        """Simple regex extraction — "requires BlueKey" → "BlueKey"."""
        import re
        m = re.search(r"(?:requires?|need[s]?|缺少)\s+['\"]?(\w+)['\"]?", evidence, re.IGNORECASE)
        return m.group(1) if m else ""

    @staticmethod
    def _extract_flag_name(evidence: str) -> str:
        import re
        m = re.search(r"(?:switch|flag|lever|开关)\s*[=: ]*['\"]?(\w+)['\"]?", evidence, re.IGNORECASE)
        return m.group(1) if m else ""
