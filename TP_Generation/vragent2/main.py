"""
VRAgent 2.0 — CLI entry point.

Replaces GenerateTestPlanModified.py's ``if __name__ == "__main__"`` block
with a cleaner interface that drives the four-agent pipeline.

Usage::

    python -m vragent2.main \\
        --scene_name MyScene \\
        --hierarchy_json gobj_hierarchy.json \\
        --scene_gml scene_dependency_graph.gml \\
        --output Results_VRAgent2.0

Or from the TP_Generation directory::

    python -m vragent2 --help
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="vragent2",
        description="VRAgent 2.0 — Multi-Agent Closed-Loop VR Test Generation",
    )
    p.add_argument("--scene_name", required=True, help="Unity scene name")
    p.add_argument("--hierarchy_json", required=True,
                   help="Path to gobj_hierarchy.json (from TraverseSceneHierarchy)")
    p.add_argument("--scene_gml", required=True,
                   help="Path to scene dependency graph .gml (from ExtractSceneDependency)")
    p.add_argument("--output", default="Results_VRAgent2.0",
                   help="Output directory (default: Results_VRAgent2.0)")
    p.add_argument("--app_name", default="UnityApp",
                   help="Application display name")
    p.add_argument("--budget", type=int, default=100,
                   help="Total exploration budget (iterations)")
    p.add_argument("--max_repair", type=int, default=2,
                   help="Max Verifier→Planner repair rounds per iteration")
    p.add_argument("--model", default="gpt-5",
                   help="LLM model identifier")
    p.add_argument("--api_key", default=None,
                   help="OpenAI API key (or set OPENAI_API_KEY env var)")
    p.add_argument("--api_base", default=None,
                   help="OpenAI API base URL override")
    p.add_argument("--scripts_dir", default=None,
                   help="Path to C# scripts directory (for ScriptIndexer)")
    p.add_argument("--limit", type=int, default=0,
                   help="Limit number of objects to process (0 = all)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Imports (deferred to keep --help fast) ────────────────────────
    from .utils.llm_client import LLMClient
    from .utils.config_loader import load_config
    from .utils.file_utils import load_json, ensure_dir
    from .retrieval.retrieval_layer import RetrievalLayer
    from .controller import VRAgentController

    # ── Config ────────────────────────────────────────────────────────
    config = load_config()

    # ── LLM Client ────────────────────────────────────────────────────
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    api_base = args.api_base or os.environ.get("OPENAI_API_BASE", "")
    if not api_key:
        # Attempt to load from legacy config
        try:
            import importlib
            legacy = importlib.import_module("config")
            api_key = getattr(legacy, "API_KEY", "")
            api_base = getattr(legacy, "BASE_URL", api_base)
        except ImportError:
            pass

    if not api_key:
        print("[ERROR] No API key. Set --api_key or OPENAI_API_KEY env var.")
        sys.exit(1)

    llm = LLMClient(api_key=api_key, base_url=api_base or None)

    # ── Retrieval Layer ───────────────────────────────────────────────
    hierarchy_data = load_json(args.hierarchy_json)
    if not hierarchy_data:
        print(f"[ERROR] Cannot load hierarchy from {args.hierarchy_json}")
        sys.exit(1)

    retrieval = RetrievalLayer(
        gml_path=args.scene_gml,
        hierarchy_data=hierarchy_data,
        scripts_dir=args.scripts_dir or "",
    )

    # ── Build object list ─────────────────────────────────────────────
    gobj_list: list = []
    if isinstance(hierarchy_data, list):
        gobj_list = hierarchy_data
    elif isinstance(hierarchy_data, dict):
        # Could be {id: info, ...} or {gobj_list: [...]}
        if "gobj_list" in hierarchy_data:
            gobj_list = hierarchy_data["gobj_list"]
        else:
            gobj_list = list(hierarchy_data.values())

    if args.limit > 0:
        gobj_list = gobj_list[:args.limit]

    print(f"[MAIN] Scene: {args.scene_name}")
    print(f"[MAIN] Objects: {len(gobj_list)}")
    print(f"[MAIN] Budget: {args.budget}")
    print(f"[MAIN] Model: {args.model}")
    print(f"[MAIN] Output: {args.output}")

    # ── Run Controller ────────────────────────────────────────────────
    controller = VRAgentController(
        config=config,
        llm=llm,
        retrieval=retrieval,
        output_dir=args.output,
        app_name=args.app_name,
        scene_name=args.scene_name,
        total_budget=args.budget,
        max_repair_rounds=args.max_repair,
        llm_model=args.model,
    )

    results = controller.run(gobj_list)

    # ── Print summary ─────────────────────────────────────────────────
    summary = results.get("summary", {})
    print(f"\n{'='*60}")
    print(f"VRAgent 2.0 Complete")
    print(f"  Total actions : {summary.get('total_actions', 0)}")
    print(f"  Iterations    : {summary.get('iterations', 0)}")
    print(f"  Gate nodes    : {summary.get('gate_graph_nodes', 0)}")
    print(f"  Gate edges    : {summary.get('gate_graph_edges', 0)}")
    exp = summary.get("explorer", {})
    print(f"  Coverage      : {exp.get('total_coverage', 0):.4f}")
    print(f"  Gates solved  : {exp.get('gates_solved', 0)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
