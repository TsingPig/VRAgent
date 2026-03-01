#!/usr/bin/env python3
"""
Phase 0: Extract Home_TwoRooms scene data using UnityDataAnalyzer.

This script directly analyzes the Home_TwoRooms.unity scene file and generates
the scene dependency graph (GML), then runs TraverseSceneHierarchy to produce
gobj_hierarchy.json.
"""

import subprocess
import os
import sys

# Add parent dir to path for config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PROJECT_PATH = r"d:\--UnityProject\HenryLabXR\VRAgent\VRAgent"
SCENE_FILE = os.path.join(PROJECT_PATH, "Assets", "SampleScene", "Home_TwoRooms", "Home_TwoRooms.unity")
RESULTS_DIR = os.path.join("Results", "Results_Home_TwoRooms")

def run_cmd(cmd, description):
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"  CMD: {cmd}\n")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[STDERR] {result.stderr}")
    if result.returncode != 0:
        print(f"[WARN] Command exited with code {result.returncode}")
    return result.returncode == 0


def main():
    print("=" * 60)
    print("Phase 0: Home_TwoRooms Scene Data Extraction")
    print("=" * 60)
    
    # Verify scene file exists
    if not os.path.exists(SCENE_FILE):
        print(f"[ERROR] Scene file not found: {SCENE_FILE}")
        sys.exit(1)
    print(f"[OK] Scene file found: {SCENE_FILE}")
    
    # Verify analyzers exist
    for tool_name, tool_path in [
        ("UnityDataAnalyzer", config.unity_analyzer_path),
        ("CSharpAnalyzer", config.csharp_analyzer_path),
        ("CodeStructureAnalyzer", config.structure_analyzer_path),
    ]:
        if os.path.exists(tool_path):
            print(f"[OK] {tool_name}: {tool_path}")
        else:
            print(f"[WARN] {tool_name} not found: {tool_path}")
    
    # Create output directories
    scene_info_dir = os.path.join(RESULTS_DIR, "scene_detailed_info")
    script_info_dir = os.path.join(RESULTS_DIR, "script_detailed_info")
    os.makedirs(scene_info_dir, exist_ok=True)
    os.makedirs(script_info_dir, exist_ok=True)
    
    # ── Step 1: Analyze scene file ────────────────────────────
    run_cmd(
        f'"{config.unity_analyzer_path}" -a "{SCENE_FILE}" -r "{scene_info_dir}"',
        "Step 1: Analyze Home_TwoRooms.unity scene file"
    )
    
    # ── Step 2: Analyze TagManager ────────────────────────────
    tag_manager_path = os.path.join(PROJECT_PATH, "ProjectSettings", "TagManager.asset")
    tag_info_dir = os.path.join(RESULTS_DIR, "TagManager_info")
    os.makedirs(tag_info_dir, exist_ok=True)
    run_cmd(
        f'"{config.unity_analyzer_path}" -a "{tag_manager_path}" -r "{tag_info_dir}"',
        "Step 2: Analyze TagManager"
    )
    
    # ── Step 3: Analyze EditorBuildSettings ────────────────────
    build_settings_path = os.path.join(PROJECT_PATH, "ProjectSettings", "EditorBuildSettings.asset")
    build_info_dir = os.path.join(RESULTS_DIR, "BuildAsset_info")
    os.makedirs(build_info_dir, exist_ok=True)
    run_cmd(
        f'"{config.unity_analyzer_path}" -a "{build_settings_path}" -r "{build_info_dir}"',
        "Step 3: Analyze EditorBuildSettings"
    )
    
    # ── Step 4: Analyze C# scripts ────────────────────────────
    assets_path = os.path.join(PROJECT_PATH, "Assets")
    script_main_dir = os.path.join(script_info_dir, "mainResults")
    os.makedirs(script_main_dir, exist_ok=True)
    
    run_cmd(
        f'"{config.csharp_analyzer_path}" -p "{assets_path}" -r "{script_main_dir}"',
        "Step 4: Analyze C# scripts"
    )
    
    # ── Step 5: Analyze code structure ────────────────────────
    code_analysis_json = os.path.join(script_main_dir, "CodeAnalysis.json")
    if os.path.exists(code_analysis_json):
        run_cmd(
            f'"{config.structure_analyzer_path}" -d "{code_analysis_json}" -r "{script_main_dir}"',
            "Step 5: Analyze code structure"
        )
    else:
        print(f"[WARN] CodeAnalysis.json not found, skipping structure analysis")
    
    # ── Step 6: Create scene database (GML) ───────────────────
    # Use ExtractSceneDependency functions properly to build graph with Source_Code_File edges
    print(f"\n{'='*60}")
    print(f"  Step 6: Create scene dependency graph (GML)")
    print(f"{'='*60}")
    
    scene_main_dir = os.path.join(scene_info_dir, "mainResults")
    if os.path.exists(scene_main_dir):
        scene_json_files = [f for f in os.listdir(scene_main_dir) if f.endswith('.unity.json')]
        if scene_json_files:
            print(f"  Found scene JSON files: {scene_json_files}")
            
            from ExtractSceneDependency import create_scene_database, analyze_csharp_meta
            import json
            
            # Get layer list from TagManager (same logic as analyze_tagManager)
            layer_lis = []
            tag_main_dir = os.path.join(tag_info_dir, "mainResults")
            tag_json = os.path.join(tag_main_dir, "TagManager.asset.json")
            if os.path.exists(tag_json):
                with open(tag_json, 'r') as f:
                    data = json.load(f)
                    tag_manager_data = data.get("COMPONENTS", [])[0].get("TagManager", [])
                    for item in tag_manager_data:
                        if 'layers' in item:
                            scene_layers = item['layers']
                            for layer in scene_layers:
                                layer_name = list(layer.values())[0].split('-')[1].strip()
                                if layer_name != '':
                                    layer_lis.append(layer_name)
                print(f"  Layers: {layer_lis}")
            
            # Get script_lis as list of dicts with GUID info 
            # (same as analyze_csharp_meta returns)
            # Read from the existing .meta.json files in metaResults
            script_lis = []
            meta_dir = os.path.join(script_info_dir, "metaResults")
            if os.path.exists(meta_dir):
                for fname in os.listdir(meta_dir):
                    if fname.endswith('.meta.json'):
                        if "TextMesh" in fname:
                            continue
                        fpath = os.path.join(meta_dir, fname)
                        with open(fpath, 'r', encoding='utf-8') as f:
                            script_dic = json.load(f)
                            script_lis.append(script_dic)
            print(f"  Scripts (with GUIDs): {len(script_lis)} files")
            if script_lis:
                print(f"  Sample GUID: {script_lis[0].get('guid', '?')} => {script_lis[0].get('name', '?')}")
            
            create_scene_database(scene_json_files, PROJECT_PATH, RESULTS_DIR, script_lis, layer_lis)
        else:
            print(f"  [WARN] No .unity.json files found in {scene_main_dir}")
            print(f"  Files present: {os.listdir(scene_main_dir) if os.path.exists(scene_main_dir) else 'dir not found'}")
    else:
        print(f"  [WARN] scene_detailed_info/mainResults not found")
    
    # ── Step 7: Run TraverseSceneHierarchy ────────────────────
    print(f"\n{'='*60}")
    print(f"  Step 7: Generate gobj_hierarchy.json")
    print(f"{'='*60}")
    
    run_cmd(
        f'python TraverseSceneHierarchy.py -r "{RESULTS_DIR}"',
        "Running TraverseSceneHierarchy"
    )
    
    # ── Verify outputs ────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Verification: Checking generated files")
    print(f"{'='*60}")
    
    expected_files = [
        ("gobj_hierarchy.json", RESULTS_DIR),
        ("scene_detailed_info/mainResults", RESULTS_DIR),
        ("script_detailed_info/mainResults", RESULTS_DIR),
    ]
    
    all_ok = True
    for fname, basedir in expected_files:
        fpath = os.path.join(basedir, fname)
        exists = os.path.exists(fpath)
        status = "OK" if exists else "MISSING"
        print(f"  [{status}] {fpath}")
        if not exists:
            all_ok = False
    
    # Check for GML files
    gml_dir = os.path.join(RESULTS_DIR, "scene_detailed_info", "mainResults")
    if os.path.exists(gml_dir):
        gml_files = [f for f in os.listdir(gml_dir) if f.endswith('.gml')]
        print(f"  [INFO] GML files: {gml_files}")
    
    # Check for hierarchy json
    for f in os.listdir(RESULTS_DIR):
        if f.endswith('_gobj_hierarchy.json') or f == 'gobj_hierarchy.json':
            print(f"  [INFO] Hierarchy: {f}")
    
    print(f"\n{'='*60}")
    if all_ok:
        print("Phase 0 Status: PASS - All data generated")
    else:
        print("Phase 0 Status: PARTIAL - Some files missing (check above)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
