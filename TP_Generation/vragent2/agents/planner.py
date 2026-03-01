"""
Planner Agent — Generate candidate action units (HAU / AAU) for a given goal.

Refactored from GenerateTestPlanModified:
    - Prompt construction (first_request, child_request, special-logic variants)
    - Multi-turn conversation management
    - Response parsing
    - Structured-repair on Verifier feedback

The Planner does NOT validate or execute — it only proposes.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import BaseAgent
from ..contracts import PlannerOutput
from ..retrieval.retrieval_layer import RetrievalLayer
from ..utils.llm_client import LLMClient
from ..utils.config_loader import VRAgentConfig


class PlannerAgent(BaseAgent):
    """Agent 1 — Generates candidate test-plan actions."""

    name = "PlannerAgent"

    def __init__(
        self,
        llm: LLMClient,
        retrieval: RetrievalLayer,
        config: VRAgentConfig,
        *,
        app_name: str = "UnityApp",
        max_multi_turns: int = 3,
        max_child_runs: int = 4,
        llm_model: str = "gpt-5",
    ):
        self.llm = llm
        self.retrieval = retrieval
        self.config = config
        self.app_name = app_name
        self.max_multi_turns = max_multi_turns
        self.max_child_runs = max_child_runs
        self.llm_model = llm_model

    # ------------------------------------------------------------------
    # Contract entry point
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        input_data : dict
            Required keys:
                gobj_info   – dict from gobj_hierarchy.json
                scene_name  – str

        Returns
        -------
        dict matching PlannerOutput schema.
        """
        gobj_info = input_data["gobj_info"]
        scene_name = input_data["scene_name"]
        goal = input_data.get("goal", "")

        conversation, actions = self.generate_test_plan(gobj_info, scene_name)

        return PlannerOutput(
            actions=actions,
            intent=f"Test plan for {gobj_info.get('gameobject_name', 'Unknown')} — {goal}",
            expected_reward=0.0,
        ).to_dict()

    # ------------------------------------------------------------------
    # Full conversation flow
    # ------------------------------------------------------------------

    def generate_test_plan(
        self, gobj_info: Dict[str, Any], scene_name: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """Generate a full test plan conversation for one top-level GameObject.

        Returns (conversation_history, merged_action_units).
        """
        conversation: List[Dict] = []
        llm_ctx: List[Dict[str, str]] = []
        turn_count = 0

        # ── Step 1: First request (main object) ─────────────────────
        first_req = self._build_first_request(gobj_info, scene_name)
        self._record(conversation, "user", first_req, request_type="first_request")

        first_resp = self.llm.ask_with_context(first_req, llm_ctx, model=self.llm_model)
        parsed = self._parse_and_record(first_resp, conversation, llm_ctx, first_req)
        turn_count += 1

        if not first_resp:
            return conversation, []

        # ── Step 2: Main-object special logic ────────────────────────
        gobj_id = gobj_info.get("gameobject_id", "")
        for logic_type in ("sorted_target_logic_info", "sorted_layer_logic_info",
                           "gameobject_find_info", "gameobject_instantiate_info"):
            logic_data = self.retrieval.hierarchy.find_sorted_target_logic(gobj_id) \
                if logic_type == "sorted_target_logic_info" \
                else self.retrieval.hierarchy.find_sorted_layer_logic(gobj_id) \
                if logic_type == "sorted_layer_logic_info" \
                else self.retrieval.hierarchy.find_gameobject_find_info(gobj_id) \
                if logic_type == "gameobject_find_info" \
                else self.retrieval.hierarchy.find_gameobject_instantiate_info(gobj_id)

            if logic_data:
                tc = self._handle_special_logic(
                    gobj_info, scene_name, logic_type, logic_data,
                    conversation, llm_ctx, is_main=True,
                )
                turn_count += tc

        # ── Step 3: Children ─────────────────────────────────────────
        children = self.retrieval.hierarchy.get_children(gobj_info, sorted=True)
        for i, child in enumerate(children, 1):
            child_id = child.get("child_id", "")
            if self.retrieval.hierarchy.is_processed(child_id):
                continue

            if turn_count >= self.max_child_runs:
                llm_ctx = self._rebuild_context(conversation, gobj_info)
                turn_count = 0

            tc = self._handle_child(child, i, scene_name, conversation, llm_ctx)
            turn_count += tc

        # ── Merge actions from conversation ──────────────────────────
        actions = self._merge_actions(conversation)
        return conversation, actions

    # ------------------------------------------------------------------
    # Structured repair (Verifier feedback → patched actions)
    # ------------------------------------------------------------------

    def repair(
        self,
        original_actions: List[Dict],
        errors: List[Dict],
        context: List[Dict[str, str]],
    ) -> List[Dict]:
        """Given Verifier errors, ask the LLM to produce a targeted fix.

        This implements "结构化修复 instead of 重写整计划".
        """
        error_block = json.dumps(errors, indent=2, ensure_ascii=False)
        action_block = json.dumps(original_actions, indent=2, ensure_ascii=False)
        prompt = (
            "The Verifier found the following errors in the proposed actions:\n"
            f"```json\n{error_block}\n```\n\n"
            "Original actions:\n"
            f"```json\n{action_block}\n```\n\n"
            "Please fix ONLY the flagged actions.  Return the complete corrected "
            "action list as a JSON array.  Do NOT rewrite actions that are already valid."
        )
        resp = self.llm.ask_with_context(prompt, context, model=self.llm_model)
        if resp:
            parsed = LLMClient.extract_json(resp)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "taskUnits" in parsed:
                actions = []
                for tu in parsed["taskUnits"]:
                    actions.extend(tu.get("actionUnits", []))
                return actions
        return original_actions  # fallback: return originals unchanged

    # ==================================================================
    # Prompt builders
    # ==================================================================

    def _build_first_request(self, gobj_info: Dict[str, Any], scene_name: str) -> str:
        """Build the initial prompt for a top-level GameObject."""
        gobj_name = gobj_info.get("gameobject_name", "")
        gobj_id_r = gobj_info.get("gameobject_id_replace", "")
        gobj_id = gobj_info.get("gameobject_id", "")
        scripts = gobj_info.get("mono_comp_relations", [])
        children = gobj_info.get("child_relations", [])

        scene_meta = self.retrieval.scene.extract_scene_meta(gobj_id, scripts)
        script_src = self.retrieval.scripts.build_combined_source(scripts)
        has_children = len(children) > 0
        has_scripts = len(scripts) > 0

        # Pick the right template
        if has_scripts and has_children:
            tpl_name = "TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE"
        elif has_scripts and not has_children:
            tpl_name = "TEST_PLAN_FIRST_REQUEST_NO_CHILD_SCRIPT_TEMPLATE"
        elif not has_scripts and has_children:
            tpl_name = "TEST_PLAN_FIRST_REQUEST_TEMPLATE"
        else:
            tpl_name = "TEST_PLAN_FIRST_REQUEST_NO_CHILD_TEMPLATE"

        tpl = self.config.get_template(tpl_name)
        if tpl is None:
            return f"[ERROR] Template {tpl_name} not found in config"

        kwargs = dict(
            app_name=self.app_name,
            scene_name=scene_name,
            gobj_name=gobj_name,
            gobj_id=gobj_id_r,
            scene_meta=scene_meta or "// Scene meta data not found",
        )
        if has_scripts:
            kwargs["script_source"] = script_src
        if has_children:
            kwargs["children_ids"] = [c.get("target") for c in children]

        return tpl.format(**kwargs)

    def _build_child_request(
        self, child: Dict[str, Any], index: int, scene_name: str
    ) -> str:
        """Build a normal (non-special-logic) child request."""
        tpl = self.config.get_template("TEST_PLAN_CHILD_REQUEST_TEMPLATE")
        if tpl is None:
            return "[ERROR] TEST_PLAN_CHILD_REQUEST_TEMPLATE not found"

        child_id = child.get("child_id", "")
        mono_targets = child.get("mono_comp_targets", [])
        script_src = self.retrieval.scripts.build_combined_source(mono_targets)

        child_meta_obj = self.retrieval.scene.find_gameobject(child_id)
        if child_meta_obj:
            mono_list = []
            for j, mc in enumerate(mono_targets):
                mono_list.append({f"MonoBehaviour_{j}": mc.get("mono_property", {})})
            if mono_list:
                child_meta_obj["MonoBehaviour"] = mono_list

        return tpl.format(
            child_index=index,
            parent_name=child.get("parent_info", {}).get("parent_name", ""),
            child_name=child.get("child_name", ""),
            child_id=child.get("child_id_replace", ""),
            script_source=script_src,
            child_scene_meta=str(child_meta_obj) if child_meta_obj else "// Not found",
        )

    # ------------------------------------------------------------------
    # Special-logic handling
    # ------------------------------------------------------------------

    def _handle_special_logic(
        self,
        info: Dict[str, Any],
        scene_name: str,
        logic_type: str,
        logic_data: List[Dict],
        conversation: List[Dict],
        llm_ctx: List[Dict[str, str]],
        *,
        is_main: bool = False,
    ) -> int:
        """Handle one type of special logic; return turn count."""
        template_map = {
            "sorted_target_logic_info": (
                "TAG_LOGIC_MAIN_REQUEST_TEMPLATE" if is_main else "TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW"
            ),
            "sorted_layer_logic_info": (
                "LAYER_LOGIC_MAIN_REQUEST_TEMPLATE" if is_main else "LAYER_LOGIC_CHILD_REQUEST_TEMPLATE"
            ),
            "gameobject_find_info": (
                "GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE" if is_main
                else "GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE"
            ),
            "gameobject_instantiate_info": (
                "GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE" if is_main
                else "GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE"
            ),
        }

        tpl_name = template_map.get(logic_type, "")
        tpl = self.config.get_template(tpl_name)
        if tpl is None:
            print(f"[PLANNER] Missing template: {tpl_name}")
            return 0

        # Mark processed
        ids = [item.get("id") or item.get("target") for item in logic_data if item.get("id") or item.get("target")]
        self.retrieval.hierarchy.mark_processed_batch(ids)

        context_str = self.retrieval.build_context_for_special_logic(logic_data)

        # Build needed IDs
        needed_ids = ids
        gobj_name = info.get("gameobject_name", info.get("child_name", ""))
        gobj_id_r = info.get("gameobject_id_replace", info.get("child_id_replace", ""))

        # Build the prompt with available template variables
        try:
            if is_main:
                request = tpl.format(
                    gobj_name=gobj_name,
                    gobj_id=gobj_id_r,
                    needed_gameobject_ids=needed_ids,
                    script_sources_and_meta=context_str,
                )
            else:
                mono_targets = info.get("mono_comp_targets", [])
                request = tpl.format(
                    child_name=info.get("child_name", ""),
                    child_id=info.get("child_id_replace", ""),
                    parent_name=info.get("parent_info", {}).get("parent_name", ""),
                    combined_script_source=self.retrieval.scripts.build_combined_source(mono_targets),
                    child_scene_meta=self.retrieval.scene.extract_scene_meta(
                        info.get("child_id", ""), mono_targets
                    ) or "// Not found",
                    needed_gameobject_ids=needed_ids,
                    script_sources_and_meta=context_str,
                )
        except KeyError as exc:
            print(f"[PLANNER] Template key error: {exc}")
            return 0

        self._record(conversation, "user", request, request_type=f"{logic_type}_request")
        resp = self.llm.ask_with_context(request, llm_ctx, model=self.llm_model)
        self._parse_and_record(resp, conversation, llm_ctx, request)
        return 1

    # ------------------------------------------------------------------
    # Child handling
    # ------------------------------------------------------------------

    def _handle_child(
        self,
        child: Dict[str, Any],
        index: int,
        scene_name: str,
        conversation: List[Dict],
        llm_ctx: List[Dict[str, str]],
    ) -> int:
        child_id = child.get("child_id", "")

        # Check special logic types first
        for logic_type in ("sorted_target_logic_info", "sorted_layer_logic_info",
                           "gameobject_find_info", "gameobject_instantiate_info"):
            finder = {
                "sorted_target_logic_info": self.retrieval.hierarchy.find_sorted_target_logic,
                "sorted_layer_logic_info": self.retrieval.hierarchy.find_sorted_layer_logic,
                "gameobject_find_info": self.retrieval.hierarchy.find_gameobject_find_info,
                "gameobject_instantiate_info": self.retrieval.hierarchy.find_gameobject_instantiate_info,
            }[logic_type]

            data = finder(child_id)
            if data:
                self.retrieval.hierarchy.mark_processed(child_id)
                return self._handle_special_logic(
                    child, scene_name, logic_type, data,
                    conversation, llm_ctx, is_main=False,
                )

        # Normal child
        request = self._build_child_request(child, index, scene_name)
        self._record(conversation, "user", request, request_type="child_request")
        resp = self.llm.ask_with_context(request, llm_ctx, model=self.llm_model)
        self._parse_and_record(resp, conversation, llm_ctx, request)
        return 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_and_record(
        self,
        response: Optional[str],
        conversation: List[Dict],
        llm_ctx: List[Dict[str, str]],
        request: str,
    ) -> Optional[Dict]:
        if not response:
            self._record(conversation, "assistant", "[ERROR] No LLM response",
                         response_type="error")
            return None

        plan = LLMClient.extract_test_plan(response)
        self._record(
            conversation, "assistant", response,
            response_type="test_plan_response",
            test_plan=plan,
        )
        return plan

    @staticmethod
    def _record(history: List[Dict], role: str, content: str, **meta) -> None:
        msg = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        msg.update(meta)
        history.append(msg)

    def _rebuild_context(
        self, conversation: List[Dict], gobj_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Rebuild a trimmed LLM context to stay within token budget."""
        ctx: List[Dict[str, str]] = []
        # Keep the first request + response
        for msg in conversation:
            if msg.get("request_type") == "first_request":
                ctx.append({"role": "user", "content": msg["content"]})
            elif msg.get("response_type") == "test_plan_response" and not ctx:
                continue
            elif ctx and msg["role"] == "assistant":
                ctx.append({"role": "assistant", "content": msg["content"]})
                break
        # Keep the most recent test plan response
        for msg in reversed(conversation):
            if msg.get("role") == "assistant" and msg.get("test_plan"):
                if len(ctx) < 3:
                    ctx.append({"role": "assistant", "content": msg["content"]})
                break
        return ctx

    # ------------------------------------------------------------------
    # Action merging & validation
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_actions(conversation: List[Dict]) -> List[Dict]:
        """Merge all test_plan actions from conversation into a deduplicated list."""
        seen_keys: List[str] = []
        merged: List[Dict] = []

        for msg in conversation:
            if msg.get("role") != "assistant" or not msg.get("test_plan"):
                continue
            plan = msg["test_plan"]
            if isinstance(plan, str):
                try:
                    plan = json.loads(plan)
                except json.JSONDecodeError:
                    continue
            if not isinstance(plan, dict):
                continue

            for tu in plan.get("taskUnits", []):
                for au in tu.get("actionUnits", []):
                    key = json.dumps(au, sort_keys=True)
                    if key not in seen_keys:
                        seen_keys.append(key)
                        merged.append(au)

        return merged
