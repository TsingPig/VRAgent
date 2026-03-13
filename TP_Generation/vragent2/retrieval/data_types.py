"""
Retrieval data structures — unified query/result types for agent-specific retrieval.

Defines:
    - RetrievalQuery  : typed query request
    - RetrievalHit    : a single retrieval result
    - ContextPack     : agent-ready context package (token-controlled)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    """Origin type of a retrieval hit."""
    SCENE_META = "scene_meta"
    SCRIPT = "script"
    HIERARCHY = "hierarchy"
    RUNTIME_LOG = "runtime_log"
    TRACE = "trace"
    GATE_GRAPH = "gate_graph"
    SPECIAL_LOGIC = "special_logic"


class TargetAgent(str, Enum):
    """Which agent the context is built for."""
    PLANNER = "planner"
    VERIFIER = "verifier"
    OBSERVER = "observer"


class QueryType(str, Enum):
    """What kind of retrieval is being requested."""
    OBJECT_LOOKUP = "object_lookup"
    COMPONENT_CHECK = "component_check"
    SCRIPT_SEARCH = "script_search"
    HIERARCHY_WALK = "hierarchy_walk"
    KEYWORD_SEARCH = "keyword_search"
    FAILURE_ANALYSIS = "failure_analysis"
    CONTEXT_BUILD = "context_build"


@dataclass
class RetrievalQuery:
    """A typed retrieval request."""
    query_type: QueryType = QueryType.CONTEXT_BUILD
    target_agent: TargetAgent = TargetAgent.PLANNER
    object_ids: List[str] = field(default_factory=list)
    file_ids: List[str] = field(default_factory=list)
    script_names: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    top_k: int = 10
    max_tokens: int = 4000


@dataclass
class RetrievalHit:
    """A single retrieval result."""
    source_type: str = ""           # SourceType.value
    source_id: str = ""             # fileID, script name, node id, etc.
    content: str = ""               # the actual snippet / metadata
    score: float = 0.0              # relevance score (0..1)
    evidence: str = ""              # explanation of why this hit is relevant
    token_estimate: int = 0         # approximate token count

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPack:
    """Agent-ready context package — everything an agent needs in one struct."""
    target_agent: str = ""          # TargetAgent.value
    hits: List[RetrievalHit] = field(default_factory=list)
    total_tokens: int = 0

    # High-level sections (structured, ready for prompt insertion)
    object_summary: str = ""
    nearby_interactables: str = ""
    relevant_scripts: str = ""
    special_logic: str = ""
    gate_hints: str = ""
    recent_failures: str = ""
    scene_meta: str = ""

    # For Verifier: structured object/component lookup results
    object_existence: Dict[str, bool] = field(default_factory=dict)
    component_info: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    method_index: Dict[str, List[str]] = field(default_factory=dict)

    # For Observer: failure analysis
    failure_conditions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["hits"] = [h.to_dict() if hasattr(h, "to_dict") else h for h in self.hits]
        return d

    def to_prompt_text(self, max_tokens: int = 6000) -> str:
        """Convert the ContextPack into a prompt-friendly text block."""
        sections: List[str] = []
        budget = max_tokens

        def _add(header: str, content: str) -> None:
            nonlocal budget
            if not content or not content.strip():
                return
            est = len(content) // 3  # rough char→token
            if est > budget:
                content = content[: budget * 3]
            sections.append(f"### {header}\n{content}")
            budget -= est

        _add("Object Summary", self.object_summary)
        _add("Nearby Interactables", self.nearby_interactables)
        _add("Relevant Scripts", self.relevant_scripts)
        _add("Special Logic", self.special_logic)
        _add("Scene Meta", self.scene_meta)
        _add("Gate Hints (from previous failures)", self.gate_hints)
        _add("Recent Failures", self.recent_failures)

        return "\n\n".join(sections) if sections else "(no context available)"
