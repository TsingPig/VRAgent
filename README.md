# LLM-based Automated Testing with Dependency Analysis for VR Apps

This repository couples a Python pipeline for automated Unity scene analysis and test-plan generation (**TP_Generation**) with a Unity runtime agent that imports and executes those plans in VR (**VRAgent**). Use it to turn Unity scenes into structured, reproducible interaction tests.

## Repository Layout
- [TP_Generation/README.md](TP_Generation/README.md) — Python scripts for extracting scene data, preprocessing logic, and producing test plans.
- [VRAgent/README.md](VRAgent/README.md) — Unity-side package for importing, validating, and running test plans in VRExplorer.
- [VRAgent/Documentation.md](VRAgent/Documentation.md) — Detailed Unity setup, usage, and test-plan schema.
- Analyzer configs and results: `TP_Generation/CodeStructureAnalyzer/`, `TP_Generation/CSharpScriptAnalyzer/`, `TP_Generation/Results*/`, `TP_Generation/UnityDataAnalyzer/`.

## Prerequisites
- Python 3.10+ on Windows (for TP_Generation scripts).
- Unity 2021.3.45f1c2 (recommended) with XR setup.
- Unity packages installed via Git URL in Package Manager:
  - VRExplorer: `https://github.com/TsingPig/VRExplorer_Release.git`
  - VRAgent: `https://github.com/TsingPig/VRAgent_Release.git`
- OpenAI API key if using LLM-based plan generation.

## End-to-End Workflow
1. **Analyze the Unity project** with TP_Generation to extract scenes, hierarchies, and C# relationships.
2. **Generate a test plan** (LLM-assisted or manual) in the expected JSON format.
3. **Import and validate** the plan in Unity via VRAgent/VRExplorer (FileIdManager, NavMesh, bindings).
4. **Run and iterate** tests in-editor or at runtime; optionally record coverage.

## TP_Generation (Python)
Purpose: Build structured, LLM-ready context from Unity scenes and emit executable test plans.
- Key scripts: `ExtractSceneDependency.py` → `TraverseSceneHierarchy.py` → `TagLogicPreprocessor.py` → `GenerateTestPlanModified.py` (or original `GenerateTestPlan.py`).
- External analyzers: `UnityDataAnalyzer.exe`, `CSharpAnalyzer.exe`, `CodeStructureAnalyzer.exe` (paths configured in `config.py`).
- Typical run:
  ```bash
  python ExtractSceneDependency.py -p <unity_project_path> -r <results_dir>
  python TraverseSceneHierarchy.py -r <results_dir>
  python TagLogicPreprocessor.py -r <results_dir> -s <scene_name> -a <app_name>
  python GenerateTestPlanModified.py -r <results_dir> -s <scene_name> -a <app_name>
  ```
- Outputs: GML graphs, `gobj_hierarchy.json`, tag metadata, and `test_plan_conversations_*.json` under `Results*` directories.

## VRAgent (Unity)
Purpose: Execute generated plans inside Unity/VRExplorer with automated bindings and runtime control.
- Setup highlights (see [VRAgent/Documentation.md](VRAgent/Documentation.md)):
  - Add VRAgent prefab to the target scene.
  - Bake NavMesh for static geometry (Window → AI → Navigation).
  - Ensure FileIdManager is generated and fileID mappings are valid.
- Usage:
  - Import plan: Tools → VRExplorer → Import Test Plan.
  - Validate bindings and optional code-coverage package setup.
- Test plan schema and action types (Grab, Trigger, etc.) are fully documented in [VRAgent/Documentation.md](VRAgent/Documentation.md).

## Quick Start Checklist
- Install Python deps (`networkx`, `requests`, `openai`, etc.) for TP_Generation.
- Configure `config.py` with analyzer paths and API keys.
- Run the TP_Generation pipeline against your Unity project; review experiment results under `Results*/`.
- Open the Unity project, install VRExplorer + VRAgent packages, add the prefab, bake NavMesh.
- Import the generated plan and execute;/'