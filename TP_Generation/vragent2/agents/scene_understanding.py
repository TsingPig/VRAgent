"""
Scene Understanding Agent — Reads scene ground-truth docs and produces a
structured ``SceneUnderstandingOutput`` via LLM.

This agent is the first to run in a VRAgent 2.0 session.  It ingests
Bezi-generated (or manually authored) ``.md`` documentation that describes
a VR scene's objects, interactions, and dependencies, then produces a
compact summary consumed by the Planner, Verifier, Observer, and
ObjectScheduler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_agent import BaseAgent
from ..contracts import SceneUnderstandingOutput, InteractionDependency

if TYPE_CHECKING:
    from ..utils.llm_client import LLMClient
    from ..utils.config_loader import AgentLLMConfig


_SYSTEM_PROMPT = """\
You are an expert VR scene analyst. Given documentation about a Unity VR scene,
extract structured knowledge that will guide automated VR testing.

Return a JSON object with the following fields:
{
  "scene_overview": "<1-3 sentence overview of what the scene is about>",
  "key_objects": ["<objectName>", ...],
  "interaction_dependencies": [
    {"source": "<obj>", "target": "<obj>", "relation": "<unlocks|enables|requires|triggers>"},
    ...
  ],
  "gate_chains": [
    "<Step N: description of gating requirement>",
    ...
  ],
  "main_path": [
    "<Step 1: first thing to do>",
    ...
  ],
  "failure_paths": [
    "<Common failure pattern description>",
    ...
  ],
  "object_priority_ranking": ["<mostImportantObj>", "<nextObj>", ...]
}

Rules:
- "key_objects" should list all interactable GameObjects mentioned in the docs.
- "interaction_dependencies" captures causal relationships (A unlocks B, etc.).
- "gate_chains" describes locked/gated sequences the player must solve in order.
- "main_path" is the intended walkthrough sequence.
- "failure_paths" lists things that commonly go wrong.
- "object_priority_ranking" orders objects by testing importance (gates first, then critical interactions, then optional).
- Be concise. Do NOT invent objects/interactions not mentioned in the docs.
- Return ONLY valid JSON, no extra text.
"""


class SceneUnderstandingAgent(BaseAgent):
    """Agent 0 — Produces structured scene knowledge from documentation."""

    name = "SceneUnderstandingAgent"

    def __init__(
        self,
        *,
        llm: "LLMClient",
        llm_config: Optional["AgentLLMConfig"] = None,
        default_model: str = "gpt-4o",
    ):
        self.llm = llm
        self.llm_config = llm_config
        self._default_model = default_model

    # ------------------------------------------------------------------
    # Contract entry
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        input_data : dict
            Required keys:
                scene_doc_path : str  — path to the ``.md`` scene documentation
            Optional keys:
                extra_context  : str  — additional context to include in the prompt

        Returns
        -------
        dict  — serialised ``SceneUnderstandingOutput``
        """
        doc_path = input_data.get("scene_doc_path", "")
        extra_ctx = input_data.get("extra_context", "")

        # Load document(s)
        doc_text = self._load_docs(doc_path)
        if not doc_text:
            print(f"[SCENE_UNDERSTANDING] No docs found at: {doc_path}")
            return SceneUnderstandingOutput().to_dict()

        # Build prompt
        user_prompt = f"## Scene Documentation\n\n{doc_text}"
        if extra_ctx:
            user_prompt += f"\n\n## Additional Context\n\n{extra_ctx}"

        # Call LLM
        model = (
            self.llm_config.effective_model(self._default_model)
            if self.llm_config
            else self._default_model
        )
        temp = self.llm_config.temperature if self.llm_config else 0.2

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        raw = self.llm.chat(messages, model=model, temperature=temp)

        if not raw:
            print("[SCENE_UNDERSTANDING] LLM returned empty response")
            return SceneUnderstandingOutput().to_dict()

        # Parse
        parsed = self.llm.extract_json(raw)
        if parsed is None:
            print("[SCENE_UNDERSTANDING] Failed to parse LLM JSON")
            return SceneUnderstandingOutput(scene_overview=raw[:500]).to_dict()

        output = SceneUnderstandingOutput.from_dict(parsed)
        return output.to_dict()

    # ------------------------------------------------------------------
    # Document loader
    # ------------------------------------------------------------------

    @staticmethod
    def _load_docs(path_str: str) -> str:
        """Load ``.md`` files from a file or directory path."""
        if not path_str:
            return ""

        p = Path(path_str)
        parts: List[str] = []

        if p.is_file() and p.suffix.lower() == ".md":
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
        elif p.is_dir():
            for md in sorted(p.glob("*.md")):
                parts.append(f"# {md.name}\n\n{md.read_text(encoding='utf-8', errors='replace')}")
        else:
            print(f"[SCENE_UNDERSTANDING] Invalid path: {p}")

        return "\n\n---\n\n".join(parts)
