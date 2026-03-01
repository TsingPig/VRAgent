"""
Scene Analyzer — Extract scene structure, metadata, and GML graph data.

Refactored from ExtractSceneDependency.py.
Provides:
    - Unity scene analysis via UnityDataAnalyzer.exe
    - Scene settings extraction (GameObjects, MonoBehaviours, PrefabInstances)
    - GML graph loading & querying
    - Tag / Layer data loading
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from ..utils.file_utils import load_json, find_files


class SceneAnalyzer:
    """Loads and queries one Unity scene's graph data."""

    def __init__(self, results_dir: str, scene_name: str):
        self.results_dir = results_dir
        self.scene_name = scene_name
        self.scene_meta_dir = os.path.join(results_dir, "scene_detailed_info", "mainResults")
        self.script_data_dir = os.path.join(results_dir, "script_detailed_info")

        # Lazy-loaded caches
        self._graph: Optional[nx.Graph] = None
        self._tag_data: Optional[Dict] = None
        self._layer_data: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Graph loading
    # ------------------------------------------------------------------

    @property
    def graph(self) -> Optional[nx.Graph]:
        if self._graph is None:
            self._graph = self._load_graph()
        return self._graph

    def _load_graph(self) -> Optional[nx.Graph]:
        """Load the GML graph for this scene."""
        if not os.path.isdir(self.scene_meta_dir):
            return None
        for fname in os.listdir(self.scene_meta_dir):
            if fname.endswith(".gml") and self.scene_name in fname:
                try:
                    g = nx.read_gml(os.path.join(self.scene_meta_dir, fname))
                    print(f"[SCENE] Loaded graph: {fname}  ({g.number_of_nodes()} nodes, {g.number_of_edges()} edges)")
                    return g
                except Exception as exc:
                    print(f"[SCENE] Failed to load {fname}: {exc}")
        return None

    # ------------------------------------------------------------------
    # Tag / Layer data
    # ------------------------------------------------------------------

    @property
    def tag_data(self) -> Dict:
        if self._tag_data is None:
            path = os.path.join(self.results_dir, f"{self.scene_name}_gobj_tag.json")
            self._tag_data = load_json(path) if os.path.exists(path) else {}
        return self._tag_data

    @property
    def layer_data(self) -> Dict:
        if self._layer_data is None:
            path = os.path.join(self.results_dir, f"{self.scene_name}_gobj_layer.json")
            self._layer_data = load_json(path) if os.path.exists(path) else {}
        return self._layer_data

    def get_tag_for_node(self, node_id: str) -> Optional[str]:
        """Return the tag name for *node_id*, or ``None``."""
        for tag_name, ids in self.tag_data.items():
            if isinstance(ids, list) and node_id in ids:
                return tag_name
        return None

    def get_layer_for_node(self, node_id: str) -> Optional[str]:
        for layer_name, ids in self.layer_data.items():
            if isinstance(ids, list) and node_id in ids:
                return layer_name
        return None

    # ------------------------------------------------------------------
    # GameObject queries on the graph
    # ------------------------------------------------------------------

    def find_gameobject(self, gobj_id: str) -> Optional[Dict[str, Any]]:
        """Find a GameObject node and collect its related components."""
        g = self.graph
        if g is None:
            return None

        result: Dict[str, Any] = {"Has_Rigidbody": False}
        found = False

        for node in g.nodes:
            node_data = g.nodes[node]
            if str(node).split("stripped")[0] == str(gobj_id).split("stripped")[0]:
                result[node_data.get("type", "Unknown")] = node_data
                found = True

                # PrefabInstance component checks
                if node_data.get("type") == "PrefabInstance":
                    for s, t, e in g.edges(data=True):
                        if e.get("type") == "PrefabInstance_INFO" and str(t) == str(gobj_id):
                            for s2, t2, e2 in g.edges(data=True):
                                if str(s2) == str(s):
                                    etype = e2.get("type")
                                    if etype == "Has_Rigidbody":
                                        result["Has_Rigidbody"] = True
                                    elif etype == "Has_Collider":
                                        result["Has_Collider"] = True
                                    elif etype == "Has_Event_Trigger":
                                        result["Has_Event_Trigger"] = True
                                    elif etype == "Has_Other_Comp":
                                        result["Transform"] = g.nodes[t2]

                # Direct component edges
                for s, t, e in g.edges(data=True):
                    etype = e.get("type")
                    if str(s) == str(gobj_id):
                        if etype == "Has_Other_Comp":
                            result["Transform"] = g.nodes[t]
                        elif etype == "PrefabInstance_INFO":
                            result["Source Prefab GameObject"] = g.nodes[t]
                        elif etype == "Has_Collider":
                            result[g.nodes[t].get("type", "Unknown")] = g.nodes[t]
                        elif etype == "Has_Rigidbody":
                            result["Has_Rigidbody"] = True
                        elif etype == "Has_Event_Trigger":
                            result["Has_Event_Trigger"] = True
                            result["Event_Trigger"] = g.nodes[t]

        return result if found else None

    def get_mono_comp_edges(self, gobj_id: str) -> List[Tuple[str, str, Dict]]:
        """Return all ``Has_Mono_Comp`` edges originating from *gobj_id*."""
        g = self.graph
        if g is None:
            return []
        return [
            (s, t, e)
            for s, t, e in g.edges(data=True)
            if e.get("type") == "Has_Mono_Comp" and s == gobj_id
        ]

    def get_source_code_edges(self, mono_comp_id: str) -> List[Tuple[str, str, Dict]]:
        """Return all ``Source_Code_File`` edges from a mono-component node."""
        g = self.graph
        if g is None:
            return []
        return [
            (s, t, e)
            for s, t, e in g.edges(data=True)
            if e.get("type") == "Source_Code_File" and s == mono_comp_id
        ]

    def extract_scene_meta(
        self, gobj_id: str, gobj_script_list: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """Return stringified scene metadata for *gobj_id*."""
        gobj_data = self.find_gameobject(gobj_id)
        if gobj_data is None:
            return None

        g = self.graph
        mono_list: List[Dict] = []
        if gobj_script_list:
            for i, script_info in enumerate(gobj_script_list):
                mono_list.append({f"MonoBehaviour_{i}": script_info.get("mono_property", {})})
        else:
            for j, (_, t, _) in enumerate(self.get_mono_comp_edges(gobj_id)):
                props = g.nodes[t].get("properties", {}) if g and t in g.nodes else {}
                mono_list.append({f"MonoBehaviour_{j}": props})

        if mono_list:
            gobj_data["MonoBehaviour"] = mono_list
        return str(gobj_data)


# ---------------------------------------------------------------------------
# Static analysis runners (thin wrappers around external .exe tools)
# ---------------------------------------------------------------------------

def run_unity_analyzer(analyzer_exe: str, asset_path: str, output_dir: str) -> None:
    """Invoke ``UnityDataAnalyzer.exe`` on a single asset."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = f'"{analyzer_exe}" -a "{asset_path}" -r "{output_dir}"'
    print(f"[ANALYZER] {cmd}")
    subprocess.run(cmd, check=True, shell=True, capture_output=True)


def run_csharp_analyzer(analyzer_exe: str, project_path: str, output_dir: str) -> None:
    """Invoke ``CSharpAnalyzer.exe``."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = f'"{analyzer_exe}" -p "{project_path}" -r "{output_dir}"'
    print(f"[ANALYZER] {cmd}")
    subprocess.run(cmd, check=True, shell=True, capture_output=True)
