"""
Retrieval Layer — Unified facade over SceneAnalyzer, HierarchyBuilder and ScriptIndexer.

This is the **Project Retrieval Layer** described in §B2.1 of the roadmap.
All agents query project knowledge through this single entry point so we can
enforce token-budget control in one place.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import networkx as nx

from .scene_analyzer import SceneAnalyzer
from .hierarchy_builder import HierarchyBuilder
from .script_indexer import ScriptIndexer
from ..utils.file_utils import find_files


class RetrievalLayer:
    """Project-wide retrieval facade.

    Provides "局部子图 / 局部上下文包" for Planner, Verifier and Observer,
    with strict token control (only feed what is relevant to the current goal).
    """

    def __init__(self, results_dir: str, scene_name: str):
        self.results_dir = results_dir
        self.scene_name = scene_name

        # ① Scene analyzer (GML graph, tag/layer data)
        self.scene = SceneAnalyzer(results_dir, scene_name)

        # ② Hierarchy builder (gobj_hierarchy.json index)
        self.hierarchy = HierarchyBuilder(results_dir, scene_name)

        # ③ Script indexer (C# source code retrieval)
        #    needs all scene graphs so it can resolve Source_Code_File edges
        self._scene_graphs = self._load_all_scene_graphs()
        self.scripts = ScriptIndexer(results_dir, self._scene_graphs)

    # ------------------------------------------------------------------
    # Graph management
    # ------------------------------------------------------------------

    def _load_all_scene_graphs(self) -> Dict[str, nx.Graph]:
        meta_dir = os.path.join(self.results_dir, "scene_detailed_info", "mainResults")
        graphs: Dict[str, nx.Graph] = {}
        for path in find_files(meta_dir, ".gml"):
            fname = os.path.basename(path)
            name = fname.replace(".gml", "")
            try:
                graphs[name] = nx.read_gml(path)
            except Exception as exc:
                print(f"[RETRIEVAL] Skipping {fname}: {exc}")
        return graphs

    # ------------------------------------------------------------------
    # High-level context builders (token-controlled)
    # ------------------------------------------------------------------

    def build_context_for_gameobject(self, gobj_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build a full context package for one top-level GameObject.

        Returns a dict with keys:
            scene_meta:   stringified scene metadata
            script_source: combined script source code
            children:      list of child dicts with script + meta
            special_logic: any special logic fields present
        """
        gobj_id = gobj_info.get("gameobject_id", "")
        scripts = gobj_info.get("mono_comp_relations", [])

        result = {
            "scene_meta": self.scene.extract_scene_meta(gobj_id, scripts),
            "script_source": self.scripts.build_combined_source(scripts),
            "children": [],
            "special_logic": {},
        }

        # Collect special logic
        for field_name in ("sorted_target_logic_info", "sorted_layer_logic_info",
                           "gameobject_find_info", "gameobject_instantiate_info"):
            val = gobj_info.get(field_name)
            if val:
                result["special_logic"][field_name] = val

        # Build child summaries
        for child in self.hierarchy.get_children(gobj_info):
            child_id = child.get("child_id", "")
            mono_targets = child.get("mono_comp_targets", [])
            child_ctx = {
                "child_id": child_id,
                "child_name": child.get("child_name", "Unknown"),
                "script_source": self.scripts.build_combined_source(mono_targets),
                "scene_meta": self.scene.extract_scene_meta(child_id, mono_targets),
            }
            # Special logic on child
            for field_name in ("sorted_target_logic_info", "sorted_layer_logic_info",
                               "gameobject_find_info", "gameobject_instantiate_info"):
                val = child.get(field_name)
                if val:
                    child_ctx[field_name] = val
            result["children"].append(child_ctx)

        return result

    def build_context_for_special_logic(
        self, items: List[Dict[str, Any]]
    ) -> str:
        """Format script sources and scene meta for a special-logic item list."""
        return self.scripts.format_scripts_and_meta(items, self.scene_name, self.scene)

    # ------------------------------------------------------------------
    # Quick lookups
    # ------------------------------------------------------------------

    def object_exists(self, file_id: str) -> bool:
        """Check if a fileID maps to a known node in the scene graph."""
        if self.scene is None:
            return False
        g = self.scene.graph
        return g is not None and file_id in g.nodes

    def get_object_name(self, file_id: str) -> Optional[str]:
        if self.scene is None:
            return None
        g = self.scene.graph
        if g is None or file_id not in g.nodes:
            return None
        props = g.nodes[file_id]
        return props.get("properties", {}).get("m_Name") or props.get("label")

    def has_component(self, gobj_id: str, component_type: str) -> bool:
        """Check whether a GameObject has a specific component type."""
        data = self.scene.find_gameobject(gobj_id)
        if data is None:
            return False
        if component_type == "Rigidbody":
            return data.get("Has_Rigidbody", False)
        if component_type == "Collider":
            return data.get("Has_Collider", False)
        return component_type in data
