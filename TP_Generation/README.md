# TP_Generation - Python Scripts Documentation

This project contains a collection of Python scripts for analyzing Unity projects and generating test plans. The scripts work together to extract scene dependencies, analyze code structure, and generate comprehensive test plans for Unity GameObjects.

## Project Overview

The project is designed to:
1. Extract and analyze Unity scene dependencies
2. Parse C# scripts and their relationships
3. Generate test plans for GameObjects with MonoBehavior components
4. Create hierarchical representations of scene objects
5. Use LLM (Large Language Model) APIs to generate intelligent test plans

## Python Scripts and Their Functions

### 1. `ExtractSceneDependency.py` - Main Scene Analysis Script
**Purpose**: This is the primary script that orchestrates the entire analysis process.

**Main Functions**:
- Analyzes Unity project settings and scene files
- Extracts GameObject hierarchies and component relationships
- Processes C# scripts and their metadata
- Creates scene databases with NetworkX graphs
- Generates relationship mappings between GameObjects

**Key Features**:
- Uses UnityDataAnalyzer.exe to parse Unity assets
- Uses CSharpAnalyzer.exe to analyze C# scripts
- Uses CodeStructureAnalyzer.exe to analyze code structure
- Creates GML (Graph Modeling Language) files for scene representation
- Handles Prefab instances and their relationships
- Extracts tag information and logic relationships

**Execution**: Run this script first to set up the analysis infrastructure.

### 2. `TraverseSceneHierarchy.py` - Scene Hierarchy Traversal
**Purpose**: Traverses the scene hierarchy and generates test plans for GameObjects.

**Main Functions**:
- Loads GML files created by ExtractSceneDependency.py
- Traverses GameObject hierarchies in a structured manner
- Identifies GameObjects with MonoBehavior components
- Generates hierarchical test plans
- Creates gobj_hierarchy.json with structured GameObject information

**Key Features**:
- Recursive traversal of GameObject hierarchies
- Identification of testable objects (those with MonoBehavior components)
- Generation of structured test plans
- Support for Prefab instances and their modifications
- Tag logic relationship processing

**Execution**: Run after ExtractSceneDependency.py to generate the hierarchy structure.

### 3. `TagLogicPreprocessor.py` - Tag Logic Preprocessing
**Purpose**: Preprocesses tag logic information and generates sorted target logic info.

**Main Functions**:
- Processes tag_logic_info from GameObject hierarchies
- Uses LLM API to filter and sort tag-related GameObjects
- Generates sorted_target_logic_info for efficient test plan generation
- Updates gobj_hierarchy.json with processed tag information

**Key Features**:
- LLM-based filtering of relevant GameObjects
- Tag relationship analysis
- Preprocessing for efficient test plan generation
- Integration with OpenAI API for intelligent filtering

**Execution**: Run after TraverseSceneHierarchy.py to preprocess tag logic.

### 4. `GenerateTestPlan.py` - Test Plan Generation (Original)
**Purpose**: Generates comprehensive test plans using LLM APIs.

**Main Functions**:
- Creates test plan conversations with LLM
- Handles multi-turn dialogues for complex test scenarios
- Processes tag logic information dynamically
- Generates structured test plans in JSON format

**Key Features**:
- Multi-turn conversation handling
- Dynamic tag logic processing
- Comprehensive test plan generation
- Support for complex GameObject relationships

**Execution**: Run after TagLogicPreprocessor.py for original test plan generation.

### 5. `GenerateTestPlanModified.py` - Test Plan Generation (Modified)
**Purpose**: Modified version that uses preprocessed tag logic information.

**Main Functions**:
- Uses sorted_target_logic_info from preprocessing
- Generates test plans with pre-filtered tag information
- More efficient than the original version
- Simplified tag logic handling

**Key Features**:
- Uses preprocessed tag information
- More efficient test plan generation
- Simplified conversation flow
- Better performance for large scenes

**Execution**: Run after TagLogicPreprocessor.py for optimized test plan generation.


### 6. `config.py` - Configuration File
**Purpose**: Contains all configuration settings and prompt templates.

**Main Functions**:
- Defines file paths for analyzers
- Contains prompt templates for LLM interactions
- Sets up API configurations
- Defines test plan formats

**Key Features**:
- Centralized configuration management
- Prompt template definitions
- API key and endpoint configurations
- Test plan format specifications

**Execution**: Imported by other scripts, not run directly.

## Execution Order

The scripts should be executed in the following order for a complete analysis:

### Phase 1: Data Extraction and Analysis
1. **`ExtractSceneDependency.py`**
   ```bash
   python ExtractSceneDependency.py -p <unity_project_path> -r <results_directory>
   ```
   - Analyzes Unity project
   - Extracts scene dependencies
   - Creates initial data structures

### Phase 2: Hierarchy Processing
2. **`TraverseSceneHierarchy.py`**
   ```bash
   python TraverseSceneHierarchy.py -r <results_directory>
   ```
   - Traverses scene hierarchies
   - Generates gobj_hierarchy.json
   - Identifies testable objects

### Phase 3: Tag Logic Preprocessing (Optional but Recommended)
3. **`TagLogicPreprocessor.py`**
   ```bash
   python TagLogicPreprocessor.py -r <results_directory> -s <scene_name> -a <app_name>
   ```
   - Preprocesses tag logic information
   - Updates gobj_hierarchy.json with sorted_target_logic_info

### Phase 4: Test Plan Generation
4. **`GenerateTestPlanModified.py`** (Recommended)
   ```bash
   python GenerateTestPlanModified.py -r <results_directory> -s <scene_name> -a <app_name>
   ```
   - Generates test plans using preprocessed information
   - More efficient and reliable

   OR

   **`GenerateTestPlan.py`** (Original)
   ```bash
   python GenerateTestPlan.py -r <results_directory> -s <scene_name> -a <app_name>
   ```
   - Generates test plans with dynamic tag processing
   - More complex but comprehensive

## Dependencies

### External Tools
- **UnityDataAnalyzer.exe**: Analyzes Unity project files
- **CSharpAnalyzer.exe**: Analyzes C# scripts
- **CodeStructureAnalyzer.exe**: Analyzes code structure

### Python Libraries
- `networkx`: Graph manipulation and analysis
- `json`: JSON data handling
- `os`: File system operations
- `argparse`: Command-line argument parsing
- `openai`: LLM API integration
- `requests`: HTTP requests for API calls
- `matplotlib`: Graph visualization (optional)

## Output Files

The scripts generate several output files:

1. **`gobj_hierarchy.json`**: Structured GameObject hierarchy information
2. **`gobj_tag.json`**: GameObject tag mappings
3. **`*.gml`**: Graph files representing scene structures
4. **`test_plan_conversations_*.json`**: Generated test plans
5. **`llm_responses/`**: Directory containing LLM interaction logs

## Configuration

Before running the scripts, ensure:

1. **API Configuration**: Update `config.py` with your OpenAI API key
2. **Tool Paths**: Verify paths to UnityDataAnalyzer.exe, CSharpAnalyzer.exe, and CodeStructureAnalyzer.exe
3. **Project Path**: Have the Unity project path ready
4. **Results Directory**: Create or specify a results directory

## Usage Examples

### Complete Analysis Workflow
```bash
# Step 1: Extract scene dependencies
python ExtractSceneDependency.py -p "C:/UnityProjects/MyGame" -r "Results_MyGame"

# Step 2: Traverse hierarchy
python TraverseSceneHierarchy.py -r "Results_MyGame"

# Step 3: Preprocess tag logic
python TagLogicPreprocessor.py -r "Results_MyGame" -s "MainScene" -a "MyGame"

# Step 4: Generate test plans
python GenerateTestPlanModified.py -r "Results_MyGame" -s "MainScene" -a "MyGame"
```

### Testing with Simulated LLM (No API calls)
```bash
python GenerateTestPlanModified.py -r "Results_MyGame" -s "MainScene" -a "MyGame" --disable-llm
```

## Notes

- The scripts are designed to work with Unity projects containing C# scripts
- LLM API calls require internet connectivity and valid API keys
- Large projects may take significant time to process
- The modified version (GenerateTestPlanModified.py) is recommended for better performance
- All scripts include comprehensive error handling and logging

## Troubleshooting

1. **File Not Found Errors**: Ensure all analyzer executables are in the correct paths
2. **API Errors**: Check API key configuration and internet connectivity
3. **Memory Issues**: For large projects, consider processing scenes individually
4. **Permission Errors**: Ensure write permissions for the results directory

This documentation provides a comprehensive overview of the Python scripts in the Unity Dependency Extract project. Each script serves a specific purpose in the analysis pipeline, and they work together to provide a complete solution for Unity project analysis and test plan generation.
