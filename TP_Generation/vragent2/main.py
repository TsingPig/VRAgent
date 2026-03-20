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
    p.add_argument("--model", default="gpt-4o",
                   help="LLM model identifier")
    p.add_argument("--api_key", default=None,
                   help="OpenAI API key (or set OPENAI_API_KEY env var)")
    p.add_argument("--api_base", default=None,
                   help="OpenAI API base URL override")
    p.add_argument("--scripts_dir", default=None,
                   help="Path to C# scripts directory (for ScriptIndexer)")
    p.add_argument("--limit", type=int, default=0,
                   help="Limit number of objects to process (0 = all)")

    # Unity Bridge (online mode)
    p.add_argument("--unity", action="store_true", default=False,
                   help="Connect to Unity via TCP for real-time execution")
    p.add_argument("--unity_host", default="127.0.0.1",
                   help="Unity AgentBridge host (default: 127.0.0.1)")
    p.add_argument("--unity_port", type=int, default=6400,
                   help="Unity AgentBridge port (default: 6400)")

    # Session resume
    p.add_argument("--resume", action="store_true", default=False,
                   help="Resume from last session state (skip processed objects, reuse LLM cache)")

    # Replay mode — execute existing test_plan.json in Unity without LLM
    p.add_argument("--replay", default=None, metavar="TEST_PLAN_JSON",
                   help="Replay an existing test_plan.json in Unity (no LLM needed). "
                        "Requires --unity. Pass path to test_plan.json or 'auto' to use "
                        "<output>/test_plan.json.")

    # Clean previous results
    p.add_argument("--clean", choices=["llm", "analysis", "all"], default=None,
                   help="Clean previous results before running. "
                        "'llm' = LLM pipeline output only (test_plan, traces, etc.); "
                        "'analysis' = upstream analysis results only (GML, hierarchy, scripts); "
                        "'all' = both. Cannot be combined with --resume or --replay.")

    # Unity project integration
    p.add_argument("--unity_project", default=None,
                   help="Unity project Assets path. Results auto-copy to scene folder. "
                        "E.g. d:/MyProject/Assets")

    # --- Scene understanding ---
    p.add_argument("--scene_doc", default=None,
                   help="Path to scene .md ground-truth doc (file or directory)")

    # --- Per-agent LLM overrides ---
    p.add_argument("--planner_model", default=None)
    p.add_argument("--planner_temp", type=float, default=None)
    p.add_argument("--verifier_model", default=None)
    p.add_argument("--verifier_temp", type=float, default=None)
    p.add_argument("--observer_model", default=None)
    p.add_argument("--observer_temp", type=float, default=None)
    p.add_argument("--scene_model", default=None,
                   help="Model for SceneUnderstandingAgent")
    p.add_argument("--scene_temp", type=float, default=None)

    # --- Enable/disable LLM per agent ---
    p.add_argument("--verifier_llm", action="store_true", default=True,
                   help="Enable LLM for Verifier (default: on)")
    p.add_argument("--no_verifier_llm", dest="verifier_llm", action="store_false")
    p.add_argument("--observer_llm", action="store_true", default=True,
                   help="Enable LLM for Observer (default: on)")
    p.add_argument("--no_observer_llm", dest="observer_llm", action="store_false")

    # --- Info-sharing toggles ---
    p.add_argument("--no_info_sharing", action="store_true", default=False,
                   help="Disable all inter-agent info sharing")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Imports (deferred to keep --help fast) ────────────────────────
    from .utils.llm_client import LLMClient
    from .utils.config_loader import load_config
    from .utils.file_utils import load_json, ensure_dir
    from .retrieval.retrieval_layer import RetrievalLayer
    from .controller import VRAgentController
    from .bridge.unity_bridge import UnityBridge

    # ── Config ────────────────────────────────────────────────────────
    config = load_config()

    # Apply CLI overrides to per-agent LLM configs
    from .utils.config_loader import AgentLLMConfig, InfoSharingConfig

    if args.scene_doc:
        config.scene_doc_path = args.scene_doc

    # Per-agent model/temperature overrides
    if args.planner_model:
        config.planner_llm.model = args.planner_model
    if args.planner_temp is not None:
        config.planner_llm.temperature = args.planner_temp

    config.verifier_llm.enabled = args.verifier_llm
    if args.verifier_model:
        config.verifier_llm.model = args.verifier_model
    if args.verifier_temp is not None:
        config.verifier_llm.temperature = args.verifier_temp

    config.observer_llm.enabled = args.observer_llm
    if args.observer_model:
        config.observer_llm.model = args.observer_model
    if args.observer_temp is not None:
        config.observer_llm.temperature = args.observer_temp

    if args.scene_model:
        config.scene_understanding_llm.model = args.scene_model
    if args.scene_temp is not None:
        config.scene_understanding_llm.temperature = args.scene_temp

    # Disable info sharing if requested
    if args.no_info_sharing:
        config.info_sharing = InfoSharingConfig(
            planner_summary_to_verifier=False,
            planner_summary_to_observer=False,
            verifier_evidence_to_planner=False,
            verifier_evidence_to_observer=False,
            observer_gate_hints_to_planner=False,
            observer_gate_hints_to_verifier=False,
            observer_failure_summary_to_planner=False,
            observer_failure_summary_to_verifier=False,
            scene_summary_to_planner=False,
            scene_summary_to_verifier=False,
            scene_summary_to_observer=False,
        )

    # ── LLM Client ────────────────────────────────────────────────────
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    api_base = args.api_base or os.environ.get("OPENAI_API_BASE", "")
    if not api_key:
        # Attempt to load from legacy config
        try:
            import importlib
            legacy = importlib.import_module("config")
            api_key = getattr(legacy, "OPENAI_API_KEY", "") or getattr(legacy, "API_KEY", "")
            api_base = api_base or getattr(legacy, "basicUrl_gpt35", "") or getattr(legacy, "BASE_URL", "")
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

    # Derive results_dir from hierarchy_json path
    results_dir = str(Path(args.hierarchy_json).parent)
    retrieval = RetrievalLayer(
        results_dir=results_dir,
        scene_name=args.scene_name,
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

    # Filter out infra/system objects that are not meaningful interaction targets
    default_skip_tokens = (
        "vragent",
        "fileidmanager",
        "agentbridge",
        "eventsystem",
        "xr interaction manager",
        "xr origin",
        "main camera",
    )
    filtered_list = []
    for obj in gobj_list:
        obj_name = str(obj.get("gameobject_name", "")).strip()
        low = obj_name.lower()
        if any(token in low for token in default_skip_tokens):
            continue
        filtered_list.append(obj)
    if filtered_list:
        gobj_list = filtered_list

    if args.limit > 0:
        gobj_list = gobj_list[:args.limit]

    print(f"[MAIN] Scene: {args.scene_name}")
    print(f"[MAIN] Objects: {len(gobj_list)}")
    print(f"[MAIN] Budget: {args.budget}")
    print(f"[MAIN] Model: {args.model}")
    print(f"[MAIN] Output: {args.output}")
    print(f"[MAIN] Unity Bridge: {'ON' if args.unity else 'OFF (dry-run)'}")

    # ── Unity Bridge (optional) ───────────────────────────────────────
    unity_bridge = None
    if args.unity:
        unity_bridge = UnityBridge(host=args.unity_host, port=args.unity_port)
        try:
            unity_bridge.connect()
            if unity_bridge.ping():
                print(f"[MAIN] Unity connected at {args.unity_host}:{args.unity_port}")
                try:
                    reset_resp = unity_bridge.reset()
                    if reset_resp.get("success", False):
                        print("[MAIN] Unity runtime reset completed")
                except Exception as reset_exc:
                    print(f"[MAIN] WARNING: Unity reset failed: {reset_exc}")
            else:
                print("[MAIN] ERROR: Unity connected but ping failed")
                sys.exit(1)
        except Exception as exc:
            print(f"[MAIN] ERROR: Cannot connect to Unity — {exc}")
            print("[MAIN] Hint: ensure Unity is in Play mode and AgentBridge port matches --unity_port")
            sys.exit(1)

    # ── Clean previous results ────────────────────────────────────────
    if args.clean:
        if args.resume:
            print("[ERROR] --clean and --resume cannot be used together.")
            sys.exit(1)
        if args.replay:
            print("[ERROR] --clean and --replay cannot be used together (would delete the plan to replay).")
            sys.exit(1)
        analysis_dir = str(Path(args.hierarchy_json).parent)
        if args.clean in ("llm", "all"):
            _clean_output(args.output)
        if args.clean in ("analysis", "all"):
            _clean_analysis_output(analysis_dir)
        print("[CLEAN] Done. Exiting.")
        return

    # ── Replay mode — skip LLM, just execute existing test_plan ────────
    if args.replay:
        if unity_bridge is None or not unity_bridge.connected:
            print("[ERROR] --replay requires --unity (must connect to Unity).")
            sys.exit(1)

        replay_path = args.replay
        if replay_path.lower() == "auto":
            replay_path = str(Path(args.output) / "test_plan.json")

        results = _replay_test_plan(replay_path, unity_bridge, args.output)

        if unity_bridge is not None:
            try:
                unity_bridge.close()
                print("[MAIN] Unity Bridge disconnected")
            except Exception:
                pass
        return

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
        unity_bridge=unity_bridge,
    )

    # Resume from previous session if requested
    if args.resume:
        controller.load_session()

    results = controller.run(gobj_list)

    # ── Copy results to Unity scene folder ────────────────────────
    unity_assets = args.unity_project
    if not unity_assets:
        # Auto-detect from workspace structure
        candidate = Path(args.hierarchy_json).parent.parent.parent / "VRAgent" / "Assets"
        if candidate.is_dir():
            unity_assets = str(candidate)
    if unity_assets:
        _copy_results_to_unity(args.output, unity_assets, args.scene_name)

    # ── Cleanup bridge ────────────────────────────────────────────────
    if unity_bridge is not None:
        try:
            unity_bridge.close()
            print("[MAIN] Unity Bridge disconnected")
        except Exception:
            pass

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


def _clean_output(output_dir: str) -> None:
    """Remove all previous pipeline results from the output directory."""
    import shutil

    if not os.path.isdir(output_dir):
        print(f"[CLEAN] Output directory does not exist yet: {output_dir}")
        return

    removed = 0
    # Remove known result files
    for fname in ("all_actions.json", "iteration_logs.json", "summary.json",
                  "gate_graph.json", "test_plan.json", "session_state.json",
                  "scene_understanding.json", "pending_command.json"):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
            removed += 1

    # Remove execution/ and replay/ subdirectories
    for subdir in ("execution", "replay"):
        dirpath = os.path.join(output_dir, subdir)
        if os.path.isdir(dirpath):
            count = len(os.listdir(dirpath))
            shutil.rmtree(dirpath)
            removed += count

    print(f"[CLEAN] Removed {removed} files/entries from {output_dir}")


def _clean_analysis_output(analysis_dir: str) -> None:
    """Remove upstream analysis results (GML, hierarchy, script_info, etc.)."""
    import shutil

    if not os.path.isdir(analysis_dir):
        print(f"[CLEAN-ANALYSIS] Analysis directory does not exist: {analysis_dir}")
        return

    removed = 0
    # Remove known subdirectories
    for subdir in ("scene_detailed_info", "script_detailed_info",
                   "BuildAsset_info", "TagManager_info"):
        dirpath = os.path.join(analysis_dir, subdir)
        if os.path.isdir(dirpath):
            count = len(os.listdir(dirpath))
            shutil.rmtree(dirpath)
            removed += count

    # Remove generated files (JSON, CSV, etc.) but keep the directory itself
    for fname in os.listdir(analysis_dir):
        fpath = os.path.join(analysis_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
            removed += 1

    print(f"[CLEAN-ANALYSIS] Removed {removed} files/entries from {analysis_dir}")
    print(f"[CLEAN-ANALYSIS] You need to re-run Stage 1 & 2 (ExtractSceneDependency + TraverseSceneHierarchy) to regenerate.")


def _replay_test_plan(test_plan_path: str, bridge, output_dir: str) -> Dict[str, Any]:
    """Replay an existing test_plan.json via Unity Bridge — zero LLM calls."""
    from .utils.file_utils import load_json, save_json, ensure_dir
    from typing import Dict, Any, List

    print(f"[REPLAY] Loading test plan from: {test_plan_path}")
    plan = load_json(test_plan_path)
    if not plan or "taskUnits" not in plan:
        print(f"[ERROR] Invalid or missing test plan at {test_plan_path}")
        sys.exit(1)

    # Flatten all action units
    all_actions: List[Dict[str, Any]] = []
    for task in plan["taskUnits"]:
        all_actions.extend(task.get("actionUnits", []))

    print(f"[REPLAY] {len(all_actions)} actions to execute")

    # Import objects (pre-resolve FileIDs)
    print("[REPLAY] Importing objects into Unity...")
    import_result = bridge.import_objects(plan, use_file_id=True)
    print(f"[REPLAY] Import result: {import_result}")

    # Execute each action and record traces
    ensure_dir(os.path.join(output_dir, "replay"))
    traces: List[Dict[str, Any]] = []
    exceptions: List[str] = []

    for i, action in enumerate(all_actions):
        action_type = action.get("type", "Unknown")
        source_name = action.get("source_object_name", "")
        print(f"[REPLAY] [{i+1}/{len(all_actions)}] {action_type} on {source_name}")

        try:
            result = bridge.execute(action)
            success = result.get("success", False)
            duration = result.get("duration_ms", 0)
            status = "OK" if success else "FAIL"
            print(f"[REPLAY]   {status} ({duration:.0f}ms)")

            trace_entry = {
                "action": f"{action_type}:{source_name}",
                "state_before": result.get("state_before", {}),
                "state_after": result.get("state_after", {}),
                "events": result.get("events", []),
                "success": success,
                "duration_ms": duration,
            }
            traces.append(trace_entry)

            for exc in result.get("exceptions", []):
                exceptions.append(f"{action_type}:{source_name} → {exc}")
                print(f"[REPLAY]   Exception: {exc}")

        except Exception as exc:
            exceptions.append(f"{action_type}:{source_name} → {exc}")
            traces.append({
                "action": f"{action_type}:{source_name}",
                "state_before": {},
                "state_after": {},
                "events": [f"bridge_error:{exc}"],
                "success": False,
            })
            print(f"[REPLAY]   Bridge error: {exc}")

    # Collect console logs
    logs: List[str] = []
    try:
        log_result = bridge.query_logs(since_index=0)
        logs = [f"[{l.get('level','Log')}] {l.get('message','')}" for l in log_result.get("logs", [])]
    except Exception:
        pass

    # Save replay results
    from datetime import datetime
    replay_result = {
        "timestamp": datetime.now().isoformat(),
        "test_plan_path": test_plan_path,
        "total_actions": len(all_actions),
        "executed": len(traces),
        "successes": sum(1 for t in traces if t.get("success")),
        "failures": sum(1 for t in traces if not t.get("success")),
        "exceptions": exceptions,
        "traces": traces,
        "console_logs": logs,
    }

    replay_file = os.path.join(output_dir, "replay",
                               f"replay_{datetime.now():%Y%m%d_%H%M%S}.json")
    save_json(replay_file, replay_result)

    print(f"\n{'='*60}")
    print(f"[REPLAY] Complete")
    print(f"  Actions   : {len(all_actions)}")
    print(f"  Successes : {replay_result['successes']}")
    print(f"  Failures  : {replay_result['failures']}")
    print(f"  Exceptions: {len(exceptions)}")
    print(f"  Trace     : {replay_file}")
    print(f"{'='*60}")

    return replay_result


def _copy_results_to_unity(output_dir: str, unity_assets: str, scene_name: str) -> None:
    """Copy pipeline results to the Unity scene folder for easy inspector access."""
    import shutil
    dest = Path(unity_assets) / "SampleScene" / scene_name / "VRAgent2_Results"
    dest.mkdir(parents=True, exist_ok=True)

    for fname in ("all_actions.json", "iteration_logs.json", "summary.json",
                  "gate_graph.json", "test_plan.json", "session_state.json"):
        src = Path(output_dir) / fname
        if src.exists():
            shutil.copy2(str(src), str(dest / fname))

    # Copy execution traces
    exec_src = Path(output_dir) / "execution"
    if exec_src.is_dir():
        exec_dest = dest / "execution"
        exec_dest.mkdir(exist_ok=True)
        for trace_file in exec_src.glob("trace_*.json"):
            shutil.copy2(str(trace_file), str(exec_dest / trace_file.name))

    print(f"[MAIN] Results copied to Unity: {dest}")

if __name__ == "__main__":
    main()
