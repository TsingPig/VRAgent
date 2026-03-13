"""
Keyword Retriever — Lightweight keyword / heuristic search over scripts and scene data.

Capabilities:
    - Multi-field scoring: object name > script name > source code > comments
    - Top-K retrieval with configurable weights
    - Designed as drop-in for future BM25 / embedding upgrade (路线 B)

Interface contract:
    search(query_terms, top_k) -> List[RetrievalHit]
"""

from __future__ import annotations

import math
import os
import re
from typing import Any, Dict, List, Optional

from .data_types import RetrievalHit, SourceType
from .scene_analyzer import SceneAnalyzer
from .hierarchy_builder import HierarchyBuilder
from ..utils.file_utils import load_text


# Field weights for heuristic scoring
_FIELD_WEIGHTS = {
    "object_name": 3.0,
    "script_name": 2.5,
    "method_name": 2.0,
    "comment":     1.0,
    "source_body": 0.8,
}


class KeywordRetriever:
    """Heuristic keyword search across scene metadata + script source code.

    This is a lightweight implementation suitable for small-to-medium projects.
    The ``search()`` interface is designed so that it can later be swapped for
    BM25 (e.g. ``rank_bm25``) or embedding-based retrieval without changing
    call sites.
    """

    def __init__(
        self,
        scene: SceneAnalyzer,
        hierarchy: HierarchyBuilder,
        script_data_dir: str = "",
    ):
        self.scene = scene
        self.hierarchy = hierarchy
        self.script_data_dir = script_data_dir

        # Lazy-built corpus: list of (doc_id, field_name, text)
        self._corpus: Optional[List[_CorpusEntry]] = None

    # ------------------------------------------------------------------
    # Public API (designed for future backend swap)
    # ------------------------------------------------------------------

    def search(
        self,
        query_terms: List[str],
        *,
        top_k: int = 10,
        source_filter: Optional[str] = None,
    ) -> List[RetrievalHit]:
        """Search for *query_terms* and return top-K hits.

        Parameters
        ----------
        query_terms : list of str
            Terms to search for (case-insensitive).
        top_k : int
            Maximum results to return.
        source_filter : str or None
            If set, only search documents of this SourceType value.
        """
        corpus = self._get_corpus()
        if not corpus:
            return []

        # Score each document
        scored: Dict[str, float] = {}
        evidence_map: Dict[str, str] = {}
        source_map: Dict[str, str] = {}
        content_map: Dict[str, str] = {}

        for entry in corpus:
            if source_filter and entry.source_type != source_filter:
                continue

            doc_score = self._score_entry(entry, query_terms)
            if doc_score <= 0:
                continue

            key = entry.doc_id
            if key not in scored or doc_score > scored[key]:
                scored[key] = doc_score
                evidence_map[key] = f"matched in {entry.field_name}"
                source_map[key] = entry.source_type
                content_map[key] = entry.text[:500]

        # Sort by score descending, take top_k
        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:top_k]

        hits: List[RetrievalHit] = []
        for doc_id, score in ranked:
            hits.append(RetrievalHit(
                source_type=source_map.get(doc_id, SourceType.SCRIPT.value),
                source_id=doc_id,
                content=content_map.get(doc_id, ""),
                score=round(score, 4),
                evidence=evidence_map.get(doc_id, ""),
                token_estimate=len(content_map.get(doc_id, "")) // 3,
            ))
        return hits

    # ------------------------------------------------------------------
    # Corpus building (lazy, one-time)
    # ------------------------------------------------------------------

    def _get_corpus(self) -> List[_CorpusEntry]:
        if self._corpus is None:
            self._corpus = self._build_corpus()
        return self._corpus

    def _build_corpus(self) -> List[_CorpusEntry]:
        entries: List[_CorpusEntry] = []

        # ① Objects from hierarchy
        for gobj in self.hierarchy.all_gameobjects:
            gid = gobj.get("gameobject_id", "")
            gname = gobj.get("gameobject_name", "")
            if gname:
                entries.append(_CorpusEntry(
                    doc_id=gid,
                    field_name="object_name",
                    text=gname,
                    source_type=SourceType.HIERARCHY.value,
                ))

            # Children
            for child in gobj.get("child_mono_comp_info", []):
                cid = child.get("child_id", "")
                cname = child.get("child_name", "")
                if cname:
                    entries.append(_CorpusEntry(
                        doc_id=cid,
                        field_name="object_name",
                        text=cname,
                        source_type=SourceType.HIERARCHY.value,
                    ))

        # ② Script files from disk
        if self.script_data_dir and os.path.isdir(self.script_data_dir):
            for fname in os.listdir(self.script_data_dir):
                if not fname.endswith(".cs"):
                    continue
                fpath = os.path.join(self.script_data_dir, fname)
                content = load_text(fpath)
                if not content:
                    continue

                entries.append(_CorpusEntry(
                    doc_id=fname,
                    field_name="script_name",
                    text=fname,
                    source_type=SourceType.SCRIPT.value,
                ))
                entries.append(_CorpusEntry(
                    doc_id=fname,
                    field_name="source_body",
                    text=content,
                    source_type=SourceType.SCRIPT.value,
                ))

                # Extract method names
                methods = re.findall(
                    r"(?:public|protected|private|internal)\s+\w+\s+(\w+)\s*\(",
                    content,
                )
                if methods:
                    entries.append(_CorpusEntry(
                        doc_id=fname,
                        field_name="method_name",
                        text=" ".join(methods),
                        source_type=SourceType.SCRIPT.value,
                    ))

        # ③ Scene graph node labels
        g = self.scene.graph
        if g is not None:
            for node_id in g.nodes:
                nd = g.nodes[node_id]
                label = nd.get("label", nd.get("type", ""))
                if label:
                    entries.append(_CorpusEntry(
                        doc_id=str(node_id),
                        field_name="object_name",
                        text=label,
                        source_type=SourceType.SCENE_META.value,
                    ))

        return entries

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score_entry(entry: _CorpusEntry, query_terms: List[str]) -> float:
        """Heuristic multi-field scoring for one entry."""
        text_lower = entry.text.lower()
        weight = _FIELD_WEIGHTS.get(entry.field_name, 1.0)
        total = 0.0

        for term in query_terms:
            term_lower = term.lower()
            if not term_lower:
                continue
            # Exact substring match
            count = text_lower.count(term_lower)
            if count > 0:
                # Saturating tf: log(1 + count)
                tf = math.log1p(count)
                total += tf * weight

        return total


# ------------------------------------------------------------------
# Internal corpus entry (not exported)
# ------------------------------------------------------------------

class _CorpusEntry:
    """One indexed fragment in the keyword corpus."""
    __slots__ = ("doc_id", "field_name", "text", "source_type")

    def __init__(self, doc_id: str, field_name: str, text: str, source_type: str):
        self.doc_id = doc_id
        self.field_name = field_name
        self.text = text
        self.source_type = source_type
