"""
Hierarchy Builder — Traverse scene TODG and build a queryable object index.

Refactored from TraverseSceneHierarchy.py + parts of GenerateTestPlanModified.
Provides:
    - Loading ``gobj_hierarchy.json``
    - Filtering testable GameObjects (those with MonoBehaviour components)
    - Priority sorting (special-logic children first)
    - Querying hierarchy by object ID
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from ..utils.file_utils import load_json, save_json

# Objects that should never be directly tested
FORBIDDEN_NAMES = [
    "XR Origin", "Player", "Camera", "TMP",
    "XR Interaction Manager", "EventSystem",
]


class HierarchyBuilder:
    """In-memory index over ``gobj_hierarchy.json``."""

    def __init__(self, results_dir: str, scene_name: str):
        self.results_dir = results_dir
        self.scene_name = scene_name
        self._hierarchy_path = os.path.join(results_dir, f"{scene_name}_gobj_hierarchy.json")
        self._data: List[Dict[str, Any]] = []
        self._index_by_id: Dict[str, Dict[str, Any]] = {}
        self._processed_ids: Set[str] = set()

        self._load()

    # ------------------------------------------------------------------
    # Loading & indexing
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._hierarchy_path):
            print(f"[HIERARCHY] File not found: {self._hierarchy_path}")
            return
        self._data = load_json(self._hierarchy_path)
        self._build_index()
        print(f"[HIERARCHY] Loaded {len(self._data)} top-level GameObjects")

    def _build_index(self) -> None:
        """Build a flat ID → info lookup for fast queries."""
        self._index_by_id.clear()
        for gobj in self._data:
            gid = gobj.get("gameobject_id")
            if gid:
                self._index_by_id[gid] = gobj
            for child in gobj.get("child_mono_comp_info", []):
                cid = child.get("child_id")
                if cid:
                    self._index_by_id[cid] = child

    def save(self) -> None:
        save_json(self._hierarchy_path, self._data)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def all_gameobjects(self) -> List[Dict[str, Any]]:
        return self._data

    def get_by_id(self, object_id: str) -> Optional[Dict[str, Any]]:
        return self._index_by_id.get(object_id)

    def get_children(self, gobj: Dict[str, Any], *, sorted: bool = True) -> List[Dict[str, Any]]:
        """Return the child_mono_comp_info list, optionally sorted by priority."""
        children = gobj.get("child_mono_comp_info", [])
        if sorted:
            children = self.sort_by_priority(children)
        return children

    # ------------------------------------------------------------------
    # Priority sorting
    # ------------------------------------------------------------------

    @staticmethod
    def has_special_logic(info: Dict[str, Any]) -> bool:
        """Check whether a child node has special logic fields."""
        for key in (
            "sorted_target_logic_info",
            "sorted_layer_logic_info",
            "tag_logic_info",
            "layer_logic_info",
            "gameobject_find_info",
            "gameobject_instantiate_info",
        ):
            val = info.get(key)
            if val and len(val) > 0:
                return True
        return False

    @classmethod
    def sort_by_priority(cls, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort children so those with special logic come first."""
        with_logic = [c for c in children if cls.has_special_logic(c)]
        without_logic = [c for c in children if not cls.has_special_logic(c)]
        return with_logic + without_logic

    # ------------------------------------------------------------------
    # Special logic lookups
    # ------------------------------------------------------------------

    def find_sorted_target_logic(self, object_id: str) -> Optional[List[Dict]]:
        return self._find_field(object_id, "sorted_target_logic_info")

    def find_sorted_layer_logic(self, object_id: str) -> Optional[List[Dict]]:
        return self._find_field(object_id, "sorted_layer_logic_info")

    def find_gameobject_find_info(self, object_id: str) -> Optional[List[Dict]]:
        return self._find_field(object_id, "gameobject_find_info")

    def find_gameobject_instantiate_info(self, object_id: str) -> Optional[List[Dict]]:
        return self._find_field(object_id, "gameobject_instantiate_info")

    def _find_field(self, object_id: str, field_name: str) -> Optional[List[Dict]]:
        for gobj in self._data:
            if gobj.get("gameobject_id") == object_id:
                val = gobj.get(field_name)
                if val:
                    return val
            for child in gobj.get("child_mono_comp_info", []):
                if child.get("child_id") == object_id:
                    val = child.get(field_name)
                    if val:
                        return val
        return None

    # ------------------------------------------------------------------
    # Processed tracking (used by Planner / Controller)
    # ------------------------------------------------------------------

    def mark_processed(self, object_id: str) -> None:
        self._processed_ids.add(object_id)

    def mark_processed_batch(self, ids) -> None:
        self._processed_ids.update(ids)

    def is_processed(self, object_id: str) -> bool:
        return object_id in self._processed_ids

    @property
    def processed_ids(self) -> Set[str]:
        return set(self._processed_ids)

    def reset_processed(self) -> None:
        self._processed_ids.clear()
