"""
Symbolic Retriever — Rule-based / structural queries over scene graph + hierarchy.

Capabilities:
    - Lookup object by fileID / gameobject_id
    - Query components for an object (Rigidbody, Collider, EventTrigger, etc.)
    - Find related scripts for a component
    - Walk parent/child relationships
    - Find objects in the same subtree or room
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import networkx as nx

from .data_types import RetrievalHit, SourceType
from .scene_analyzer import SceneAnalyzer
from .hierarchy_builder import HierarchyBuilder


class SymbolicRetriever:
    """Static / symbolic retriever over scene graph + hierarchy index."""

    def __init__(self, scene: SceneAnalyzer, hierarchy: HierarchyBuilder):
        self.scene = scene
        self.hierarchy = hierarchy

    # ------------------------------------------------------------------
    # Object lookup
    # ------------------------------------------------------------------

    def object_exists(self, file_id: str) -> bool:
        """Check whether *file_id* is a known node in the scene graph."""
        g = self.scene.graph
        if g is None:
            return False
        return file_id in g.nodes

    def lookup_object(self, file_id: str) -> Optional[RetrievalHit]:
        """Return a hit with the object's metadata from the graph."""
        g = self.scene.graph
        if g is None or file_id not in g.nodes:
            return None
        node_data = dict(g.nodes[file_id])
        return RetrievalHit(
            source_type=SourceType.SCENE_META.value,
            source_id=file_id,
            content=str(node_data),
            score=1.0,
            evidence="direct node lookup",
            token_estimate=len(str(node_data)) // 3,
        )

    # ------------------------------------------------------------------
    # Component queries
    # ------------------------------------------------------------------

    def get_components(self, gobj_id: str) -> Dict[str, Any]:
        """Return a dict describing which components an object has.

        Keys include ``Has_Rigidbody``, ``Has_Collider``, ``Has_Event_Trigger``,
        ``Has_Mono_Comp``, ``Transform``, etc.
        """
        result: Dict[str, Any] = {
            "Has_Rigidbody": False,
            "Has_Collider": False,
            "Has_Event_Trigger": False,
            "mono_comps": [],
        }
        g = self.scene.graph
        if g is None:
            return result

        for s, t, e in g.edges(data=True):
            if s != gobj_id:
                continue
            etype = e.get("type", "")
            if etype == "Has_Rigidbody":
                result["Has_Rigidbody"] = True
            elif etype == "Has_Collider":
                result["Has_Collider"] = True
            elif etype == "Has_Event_Trigger":
                result["Has_Event_Trigger"] = True
            elif etype == "Has_Mono_Comp":
                result["mono_comps"].append(t)
            elif etype == "Has_Other_Comp":
                result["Transform"] = dict(g.nodes[t]) if t in g.nodes else {}

        # Also check PrefabInstance edges
        for s, t, e in g.edges(data=True):
            if e.get("type") == "PrefabInstance_INFO" and str(t) == str(gobj_id):
                for s2, t2, e2 in g.edges(data=True):
                    if str(s2) == str(s):
                        etype2 = e2.get("type")
                        if etype2 == "Has_Rigidbody":
                            result["Has_Rigidbody"] = True
                        elif etype2 == "Has_Collider":
                            result["Has_Collider"] = True
                        elif etype2 == "Has_Event_Trigger":
                            result["Has_Event_Trigger"] = True

        return result

    def has_rigidbody(self, gobj_id: str) -> bool:
        return self.get_components(gobj_id).get("Has_Rigidbody", False)

    def has_collider(self, gobj_id: str) -> bool:
        return self.get_components(gobj_id).get("Has_Collider", False)

    # ------------------------------------------------------------------
    # Script lookup for a component
    # ------------------------------------------------------------------

    def get_scripts_for_object(self, gobj_id: str) -> List[str]:
        """Return mono-component node IDs attached to *gobj_id*."""
        return self.get_components(gobj_id).get("mono_comps", [])

    def get_methods_for_script(self, script_node_id: str) -> List[str]:
        """Extract method names from the script source-code node properties.

        Note: This is a heuristic — we look for 'public.*void|bool|int …MethodName'
        patterns in the script source if available.
        """
        import re
        g = self.scene.graph
        if g is None:
            return []

        for s, t, e in g.edges(data=True):
            if s == script_node_id and e.get("type") == "Source_Code_File":
                node_data = g.nodes.get(t, {})
                props = node_data.get("properties", {})
                fp = props.get("file_path", "") if isinstance(props, dict) else ""
                if fp:
                    from ..utils.file_utils import load_text
                    src = load_text(fp.replace(".meta", "") if fp.endswith(".meta") else fp)
                    if src:
                        return re.findall(
                            r"(?:public|protected|private|internal)\s+\w+\s+(\w+)\s*\(",
                            src,
                        )
        return []

    # ------------------------------------------------------------------
    # Hierarchy / relationship queries
    # ------------------------------------------------------------------

    def get_parent(self, child_id: str) -> Optional[Dict[str, Any]]:
        """Find the parent gobj_info for a child_id."""
        for gobj in self.hierarchy.all_gameobjects:
            for child in gobj.get("child_mono_comp_info", []):
                if child.get("child_id") == child_id:
                    return gobj
        return None

    def get_siblings(self, child_id: str) -> List[Dict[str, Any]]:
        """Return other children of the same parent."""
        parent = self.get_parent(child_id)
        if parent is None:
            return []
        return [
            c for c in parent.get("child_mono_comp_info", [])
            if c.get("child_id") != child_id
        ]

    def get_subtree_objects(self, gobj_id: str, max_depth: int = 3) -> List[str]:
        """Return all object IDs in the subtree rooted at *gobj_id*."""
        info = self.hierarchy.get_by_id(gobj_id)
        if info is None:
            return [gobj_id]

        result: List[str] = [gobj_id]
        for child in info.get("child_mono_comp_info", []):
            cid = child.get("child_id")
            if cid:
                result.append(cid)
        return result

    def find_nearby_interactables(
        self, gobj_id: str, *, max_results: int = 10
    ) -> List[RetrievalHit]:
        """Find interactable objects near *gobj_id* in the hierarchy.

        "Near" = siblings + objects under the same parent.
        """
        hits: List[RetrievalHit] = []
        siblings = self.get_siblings(gobj_id)
        for sib in siblings[:max_results]:
            cid = sib.get("child_id", "")
            cname = sib.get("child_name", "")
            has_logic = self.hierarchy.has_special_logic(sib)
            score = 0.7 if has_logic else 0.4
            hits.append(RetrievalHit(
                source_type=SourceType.HIERARCHY.value,
                source_id=cid,
                content=f"{cname} (special_logic={has_logic})",
                score=score,
                evidence="sibling in hierarchy",
                token_estimate=20,
            ))
        return hits
