"""
Script Indexer — Extract and index C# script source code.

Refactored from GenerateTestPlanModified._extract_script_source_code()
and SpecialLogicPreprocessor script-loading logic.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import networkx as nx

from ..utils.file_utils import load_text


class ScriptIndexer:
    """Provides script source code retrieval for MonoBehaviour components."""

    def __init__(self, results_dir: str, scene_graphs: Dict[str, nx.Graph]):
        self.script_data_dir = os.path.join(results_dir, "script_detailed_info")
        self.scene_graphs = scene_graphs  # scene_name → nx.Graph

    # ------------------------------------------------------------------
    # Core: get source code for a Mono-component node
    # ------------------------------------------------------------------

    def get_source_code(self, mono_comp_id: str) -> Optional[str]:
        """Return the C# source code associated with *mono_comp_id*."""
        for _scene_name, g in self.scene_graphs.items():
            for s, t, e in g.edges(data=True):
                if s != mono_comp_id or e.get("type") != "Source_Code_File":
                    continue
                if t not in g.nodes:
                    continue

                target_node = g.nodes[t]
                props = target_node.get("properties", {})

                # Check for inheritance relation
                inheritance_content = self._get_inheritance_content(g, t)

                file_path = self._extract_file_path(props)
                if file_path is None:
                    continue

                # Skip PackageCache files unless they are XR Interaction related
                if "PackageCache" in file_path and "Interaction" not in file_path:
                    continue

                # XR Interaction Toolkit shortcut
                if "Library" in file_path and "Interaction" in file_path:
                    return (
                        f"// This script {os.path.basename(file_path)} is from XR Interaction Toolkit. "
                        "Only trigger the Interactable Events (m_Calls) in scene meta if they exist."
                    )

                content = self._load_script(file_path)
                if content is not None:
                    if inheritance_content:
                        inh_name = g.nodes.get(self._find_inheritance_target(g, t), {}).get(
                            "properties", {}
                        )
                        inh_name = inh_name.get("name", "Base") if isinstance(inh_name, dict) else "Base"
                        content = content + "\n// " + inh_name + ".cs\n" + inheritance_content
                    return content
        return None

    # ------------------------------------------------------------------
    # Build combined source for a list of mono-component edges
    # ------------------------------------------------------------------

    def build_combined_source(self, script_list: List[Dict[str, Any]]) -> str:
        """Return concatenated source code for a list of script edges."""
        if not script_list:
            return "// No script source code found"

        parts: List[str] = []
        for i, info in enumerate(script_list):
            target_id = info.get("target", "")
            src = self.get_source_code(target_id)
            parts.append(src or f"// Script source code not found for {target_id}")
            if i < len(script_list) - 1:
                parts.append(f"\n'''\n[Source code of {i + 1}th script files attached]\n'''\n")
        return "".join(parts)

    # ------------------------------------------------------------------
    # Format script + meta for a list of GameObjects (used by special logic)
    # ------------------------------------------------------------------

    def format_scripts_and_meta(
        self,
        items: List[Dict[str, Any]],
        scene_name: str,
        scene_analyzer,  # avoid circular import — pass instance at call site
    ) -> str:
        """Produce a formatted block of script source + scene meta for each item."""
        parts: List[str] = []
        for i, item in enumerate(items):
            gobj_id = item.get("id")
            gobj_id_replace = item.get("id_replace", gobj_id)
            gobj_name = item.get("gameobject_name", item.get("target_gameobject_name", "Unknown"))
            tag_name = item.get("tag_name", "")

            if not gobj_id:
                continue
            if i > 0:
                parts.append("\n")

            header = f'GameObject ID: "{gobj_id_replace}" GameObject Name: "{gobj_name}"'
            if tag_name:
                header += f' Tag: "{tag_name}"'
            parts.append(header + ":\n")

            # Script source
            script_source = self._collect_source_for_gobj(gobj_id, scene_name)
            if script_source:
                parts.append("[Source code of script files attached]\n'''\n")
                parts.append(script_source)
                parts.append("\n'''\n")

            # Scene meta
            meta = scene_analyzer.extract_scene_meta(gobj_id)
            if meta:
                parts.append("[Source code of scene meta file]\n'''\n")
                parts.append(meta)
                parts.append("\n'''\n")
            parts.append("\n")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_source_for_gobj(self, gobj_id: str, scene_name: str) -> str:
        """Collect all script sources for a GameObject via its mono-comp edges."""
        g = self.scene_graphs.get(scene_name)
        if g is None:
            # Try all graphs
            for name, graph in self.scene_graphs.items():
                g = graph
                break
        if g is None:
            return ""

        parts: List[str] = []
        for s, t, e in g.edges(data=True):
            if e.get("type") == "Has_Mono_Comp" and s == gobj_id:
                src = self.get_source_code(t)
                if src:
                    parts.append(src)
        return "\n".join(parts)

    def _load_script(self, file_path: str) -> Optional[str]:
        """Try to load a script file from disk."""
        # Direct path
        clean_path = file_path[:-5] if file_path.endswith(".meta") else file_path
        content = load_text(clean_path)
        if content:
            return content

        # Search by filename in script directory
        basename = os.path.basename(clean_path)
        if os.path.isdir(self.script_data_dir):
            for fname in os.listdir(self.script_data_dir):
                if fname == basename:
                    return load_text(os.path.join(self.script_data_dir, fname))
        return None

    @staticmethod
    def _extract_file_path(props) -> Optional[str]:
        """Extract ``file_path`` from node properties (may be dict or list)."""
        if isinstance(props, dict):
            fp = props.get("file_path")
            if fp:
                return fp[:-5] if fp.endswith(".meta") else fp
        elif isinstance(props, list):
            for p in props:
                if isinstance(p, dict) and "file_path" in p:
                    fp = p["file_path"]
                    return fp[:-5] if fp.endswith(".meta") else fp
        return None

    def _get_inheritance_content(self, g: nx.Graph, script_node: str) -> Optional[str]:
        target = self._find_inheritance_target(g, script_node)
        if target is None:
            return None
        props = g.nodes[target].get("properties", {})
        fp = self._extract_file_path(props)
        if fp:
            return self._load_script(fp)
        return None

    @staticmethod
    def _find_inheritance_target(g: nx.Graph, script_node: str) -> Optional[str]:
        for s, t, e in g.edges(data=True):
            if s == script_node and e.get("type") == "Inheritance_Relation":
                return t
        return None
