"""
Retrieval Layer — Unified facade over SceneAnalyzer, HierarchyBuilder and ScriptIndexer.

This is the **Project Retrieval Layer** described in §B2.1 of the roadmap.
All agents query project knowledge through this single entry point so we can
enforce token-budget control in one place.

路线 A: Hybrid Static Retrieval (symbolic + keyword + condition inference)
路线 B: Embedding Retrieval 预留 — ``search()`` 接口 accepts an optional
        ``backend`` parameter; default = keyword heuristic.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import networkx as nx

from .data_types import ContextPack, RetrievalHit, SourceType, TargetAgent
from .scene_analyzer import SceneAnalyzer
from .hierarchy_builder import HierarchyBuilder
from .script_indexer import ScriptIndexer
from .symbolic_retriever import SymbolicRetriever
from .keyword_retriever import KeywordRetriever
from .condition_inference import infer_conditions, InferredCondition
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

        # ④ Symbolic retriever (structural / graph queries)
        self.symbolic = SymbolicRetriever(self.scene, self.hierarchy)

        # ⑤ Keyword retriever (heuristic text search — 路线 B: swap for embedding)
        self.keyword = KeywordRetriever(
            self.scene, self.hierarchy,
            script_data_dir=os.path.join(results_dir, "script_detailed_info"),
        )

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

    # ==================================================================
    # Agent-specific context builders (ContextPack)
    # ==================================================================

    def build_planner_context(
        self,
        goal: str,
        gobj_info: Dict[str, Any],
        *,
        recent_trace: Optional[List[Dict]] = None,
        gate_hints: Optional[List[Dict]] = None,
        max_tokens: int = 6000,
    ) -> ContextPack:
        """Build a token-controlled context package for the Planner agent.

        Sections populated:
            object_summary, nearby_interactables, relevant_scripts,
            special_logic, gate_hints, recent_failures, scene_meta
        """
        gobj_id = gobj_info.get("gameobject_id", "")
        gobj_name = gobj_info.get("gameobject_name", "Unknown")
        scripts = gobj_info.get("mono_comp_relations", [])

        pack = ContextPack(target_agent=TargetAgent.PLANNER.value)
        budget = max_tokens

        # --- object summary ---
        comps = self.symbolic.get_components(gobj_id)
        children = gobj_info.get("child_relations", [])
        summary_parts = [
            f"Object: {gobj_name} ({gobj_id})",
            f"  Rigidbody: {comps.get('Has_Rigidbody', False)}",
            f"  Collider: {comps.get('Has_Collider', False)}",
            f"  EventTrigger: {comps.get('Has_Event_Trigger', False)}",
            f"  MonoComps: {len(comps.get('mono_comps', []))}",
            f"  Children: {len(children)}",
        ]
        tag = self.scene.get_tag_for_node(gobj_id)
        layer = self.scene.get_layer_for_node(gobj_id)
        if tag:
            summary_parts.append(f"  Tag: {tag}")
        if layer:
            summary_parts.append(f"  Layer: {layer}")
        pack.object_summary = "\n".join(summary_parts)
        budget -= len(pack.object_summary) // 3

        # --- scene meta ---
        meta = self.scene.extract_scene_meta(gobj_id, scripts)
        if meta and budget > 0:
            pack.scene_meta = meta[:budget * 3]
            budget -= len(pack.scene_meta) // 3

        # --- relevant scripts ---
        if budget > 0:
            src = self.scripts.build_combined_source(scripts)
            if src and src != "// No script source code found":
                pack.relevant_scripts = src[:budget * 3]
                budget -= len(pack.relevant_scripts) // 3

        # --- nearby interactables ---
        if budget > 200:
            nearby_hits = self.symbolic.find_nearby_interactables(gobj_id, max_results=8)
            if nearby_hits:
                lines = [f"- {h.source_id}: {h.content}" for h in nearby_hits]
                pack.nearby_interactables = "\n".join(lines)
                budget -= len(pack.nearby_interactables) // 3

        # --- special logic ---
        special_parts: List[str] = []
        for field_name in ("sorted_target_logic_info", "sorted_layer_logic_info",
                           "gameobject_find_info", "gameobject_instantiate_info"):
            val = gobj_info.get(field_name)
            if val:
                special_parts.append(f"[{field_name}]: {json.dumps(val, ensure_ascii=False)[:600]}")
        if special_parts and budget > 0:
            pack.special_logic = "\n".join(special_parts)[:budget * 3]
            budget -= len(pack.special_logic) // 3

        # --- gate hints (from previous Observer) ---
        if gate_hints and budget > 0:
            gate_text = json.dumps(gate_hints, indent=2, ensure_ascii=False)[:budget * 3]
            pack.gate_hints = gate_text
            budget -= len(pack.gate_hints) // 3

        # --- recent failures ---
        if recent_trace and budget > 0:
            fail_lines: List[str] = []
            for t in recent_trace[-5:]:
                events = t.get("events", [])
                action = t.get("action", "")
                for ev in events:
                    if "error" in str(ev).lower() or "fail" in str(ev).lower():
                        fail_lines.append(f"- {action}: {ev}")
            if fail_lines:
                pack.recent_failures = "\n".join(fail_lines)[:budget * 3]

        pack.total_tokens = max_tokens - budget
        return pack

    def build_verifier_context(
        self,
        actions: List[Dict[str, Any]],
        gobj_info: Optional[Dict[str, Any]] = None,
    ) -> ContextPack:
        """Build a context package for the Verifier agent.

        Populates ``object_existence``, ``component_info``, ``method_index``
        so the Verifier can do hard structural checks.
        """
        pack = ContextPack(target_agent=TargetAgent.VERIFIER.value)

        # Collect all fileIDs referenced in actions
        file_ids: set = set()
        script_ids: set = set()
        for au in actions:
            for key, val in au.items():
                if "fileid" in key.lower() and val:
                    file_ids.add(str(val))
            # Also collect script_fileIDs from method call units
            for event_key in ("triggerring_events", "triggerred_events"):
                for event in au.get(event_key, []):
                    for mc in event.get("methodCallUnits", []):
                        sfid = mc.get("script_fileID")
                        if sfid:
                            script_ids.add(str(sfid))
                            file_ids.add(str(sfid))

        # Check existence
        for fid in file_ids:
            pack.object_existence[fid] = self.symbolic.object_exists(fid)

        # Component info for source objects
        source_ids = set()
        for au in actions:
            sfid = au.get("source_object_fileID")
            if sfid:
                source_ids.add(str(sfid))
            tfid = au.get("target_object_fileID")
            if tfid:
                source_ids.add(str(tfid))

        for sid in source_ids:
            comps = self.symbolic.get_components(sid)
            pack.component_info[sid] = comps

        # Method index for script nodes
        for sid in script_ids:
            methods = self.symbolic.get_methods_for_script(sid)
            if methods:
                pack.method_index[sid] = methods

        return pack

    def build_observer_context(
        self,
        executor_output: Dict[str, Any],
        console_logs: List[str],
        *,
        actions: Optional[List[Dict]] = None,
        recent_trace: Optional[List[Dict]] = None,
    ) -> ContextPack:
        """Build a context package for the Observer agent.

        Runs condition inference and populates ``failure_conditions``.
        """
        pack = ContextPack(target_agent=TargetAgent.OBSERVER.value)

        conditions = infer_conditions(
            actions=actions or [],
            executor_output=executor_output,
            console_logs=console_logs,
        )

        pack.failure_conditions = [c.to_dict() for c in conditions]

        # Build failure summary for downstream consumption
        if conditions:
            lines = []
            for c in conditions:
                lines.append(
                    f"- [{c.failure_type}] {c.missing_condition} "
                    f"(confidence={c.confidence:.2f})"
                )
            pack.recent_failures = "\n".join(lines)

        pack.total_tokens = len(pack.recent_failures) // 3
        return pack

    # ==================================================================
    # Route-B extension point: unified search()
    # ==================================================================

    def search(
        self,
        query_terms: List[str],
        *,
        top_k: int = 10,
        source_filter: Optional[str] = None,
        backend: str = "keyword",
    ) -> List[RetrievalHit]:
        """Unified search interface — routes to keyword backend by default.

        路线 B: pass ``backend="embedding"`` to use an embedding retriever
        once implemented. Falls back to keyword if backend is unavailable.
        """
        if backend == "embedding":
            # Future: self.embedding_retriever.search(...)
            pass  # fallback to keyword
        return self.keyword.search(query_terms, top_k=top_k, source_filter=source_filter)

    # ==================================================================
    # Legacy context builders (kept for backward compatibility)
    # ==================================================================

    def build_context_for_gameobject(self, gobj_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build a full context package for one top-level GameObject.

        **Legacy interface** — kept for backward compatibility with existing
        Planner template flow. New code should use ``build_planner_context()``.

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
        return self.symbolic.object_exists(file_id)

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
