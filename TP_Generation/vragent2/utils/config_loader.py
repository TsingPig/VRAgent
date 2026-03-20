"""
Configuration loader — wraps the legacy ``config.py`` module and provides
typed access to all templates & settings needed by VRAgent 2.0.

Usage::

    from vragent2.utils.config_loader import load_config
    cfg = load_config("config")          # module name or path
    print(cfg.OPENAI_API_KEY)
    print(cfg.get_template("TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE"))
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Per-Agent LLM configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentLLMConfig:
    """LLM configuration for a single agent."""
    model: str = ""          # empty → use default_model from VRAgentConfig
    temperature: float = 0.0
    enabled: bool = True     # set False to keep agent rule-based only

    def effective_model(self, fallback: str) -> str:
        return self.model or fallback


# ---------------------------------------------------------------------------
# Inter-Agent information sharing configuration
# ---------------------------------------------------------------------------

@dataclass
class InfoSharingConfig:
    """Controls what information each agent shares with others.

    Each flag means: "<source_agent>'s <field> is forwarded to <target_agents>".
    """
    # Planner → others
    planner_summary_to_verifier: bool = True
    planner_summary_to_observer: bool = False

    # Verifier → others
    verifier_evidence_to_planner: bool = True   # already used in repair()
    verifier_evidence_to_observer: bool = True

    # Observer → others
    observer_gate_hints_to_planner: bool = True  # already used via controller
    observer_gate_hints_to_verifier: bool = False
    observer_failure_summary_to_planner: bool = True
    observer_failure_summary_to_verifier: bool = False

    # Scene understanding summary (high-priority ground truth)
    scene_summary_to_planner: bool = True
    scene_summary_to_verifier: bool = True
    scene_summary_to_observer: bool = True


# ---------------------------------------------------------------------------
# Main project config
# ---------------------------------------------------------------------------

@dataclass
class VRAgentConfig:
    """Typed holder for all configuration values."""

    # --- API ---
    OPENAI_API_KEY: str = ""
    OPENAI_API_KEY_1: str = ""
    base_url: str = ""
    default_model: str = "gpt-4o"

    # --- Paths to external analyzers ---
    unity_analyzer_path: str = ""
    csharp_analyzer_path: str = ""
    structure_analyzer_path: str = ""

    # --- Application defaults ---
    DEFAULT_APP_NAME: str = "UnityApp"

    # --- Prompt templates (stored as raw strings) ---
    _templates: Dict[str, str] = field(default_factory=dict, repr=False)

    # --- Exploration budget ---
    max_steps: int = 200
    novelty_threshold_k: int = 5  # consecutive 0-novelty steps → Recover mode

    # --- Per-agent LLM configs ---
    planner_llm: AgentLLMConfig = field(default_factory=lambda: AgentLLMConfig(enabled=True))
    verifier_llm: AgentLLMConfig = field(default_factory=lambda: AgentLLMConfig(enabled=False))
    observer_llm: AgentLLMConfig = field(default_factory=lambda: AgentLLMConfig(enabled=False))
    scene_understanding_llm: AgentLLMConfig = field(default_factory=lambda: AgentLLMConfig(enabled=True))

    # --- Info sharing ---
    info_sharing: InfoSharingConfig = field(default_factory=InfoSharingConfig)

    # --- Scene ground-truth document path ---
    scene_doc_path: str = ""

    # ------------------------------------------------------------------
    # Template access
    # ------------------------------------------------------------------

    def get_template(self, name: str) -> Optional[str]:
        return self._templates.get(name)

    def set_template(self, name: str, value: str) -> None:
        self._templates[name] = value

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def from_module(module) -> "VRAgentConfig":
        """Build a ``VRAgentConfig`` from an already-imported Python module."""
        cfg = VRAgentConfig()

        # Scalar attributes
        for attr in (
            "OPENAI_API_KEY", "OPENAI_API_KEY_1",
            "basicUrl_gpt35",
            "unity_analyzer_path", "csharp_analyzer_path", "structure_analyzer_path",
            "DEFAULT_APP_NAME",
        ):
            val = getattr(module, attr, None)
            if val is not None:
                if attr == "basicUrl_gpt35":
                    cfg.base_url = val
                else:
                    setattr(cfg, attr, val)

        # Collect all *_TEMPLATE* attributes as prompt templates
        for name in dir(module):
            if "TEMPLATE" in name:
                value = getattr(module, name, None)
                if isinstance(value, str):
                    cfg._templates[name] = value

        return cfg


def load_config(module_name: str = "config") -> VRAgentConfig:
    """Import *module_name* and return a typed ``VRAgentConfig``."""
    try:
        mod = importlib.import_module(module_name)
        print(f"[CONFIG] Loaded configuration module: {module_name}")
        return VRAgentConfig.from_module(mod)
    except ImportError as exc:
        print(f"[CONFIG] Failed to import '{module_name}': {exc}")
        raise
