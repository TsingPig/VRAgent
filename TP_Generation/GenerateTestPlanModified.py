 #!/usr/bin/env python3
"""
Modified GenerateTestPlan.py - Uses sorted_target_logic_info field

This file is a modified version of GenerateTestPlan.py with the following main changes:
1. When calling generate_test_plan_conversation function, directly query the sorted_target_logic_info field
2. Use TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW template to provide tag-related prompt information to LLM
3. No longer need complex tag_logic_info processing logic, directly use preprocessed results
"""

import json
import os
import sys
import argparse
import importlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import networkx as nx
import openai
import time
import shutil
import re

forbid_lis = ["XR Origin", "Player", "Camera", "TMP", "XR Interaction Manager", "EventSystem"]



class GenerateTestPlanModified:
    """Modified test plan generator"""
    
    def __init__(self, results_dir: str, scene_name: str = None, app_name: str = None, enable_llm: bool = True, config_module = None):
        """
        Initialize test plan generator
        
        Args:
            results_dir: Results directory path
            scene_name: Scene name
            app_name: Application name
            enable_llm: Whether to enable LLM API calls (default True)
            config_module: Configuration module containing templates and settings
        """
        # Store config module
        if config_module is None:
            # Default to config module if not provided
            import config as config_module
        self.config = config_module
        
        # Load configuration values
        self.TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW = getattr(config_module, 'TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW', None)
        self.LAYER_LOGIC_CHILD_REQUEST_TEMPLATE = getattr(config_module, 'LAYER_LOGIC_CHILD_REQUEST_TEMPLATE', None)
        self.GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE = getattr(config_module, 'GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE', None)
        self.GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE = getattr(config_module, 'GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE', None)
        self.TAG_LOGIC_MAIN_REQUEST_TEMPLATE = getattr(config_module, 'TAG_LOGIC_MAIN_REQUEST_TEMPLATE', None)
        self.LAYER_LOGIC_MAIN_REQUEST_TEMPLATE = getattr(config_module, 'LAYER_LOGIC_MAIN_REQUEST_TEMPLATE', None)
        self.GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE = getattr(config_module, 'GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE', None)
        self.GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE = getattr(config_module, 'GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE', None)
        self.TEST_PLAN_FIRST_REQUEST_TEMPLATE = getattr(config_module, 'TEST_PLAN_FIRST_REQUEST_TEMPLATE', None)
        self.TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE = getattr(config_module, 'TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE', None)
        self.TEST_PLAN_FIRST_REQUEST_NO_CHILD_TEMPLATE = getattr(config_module, 'TEST_PLAN_FIRST_REQUEST_NO_CHILD_TEMPLATE', None)
        self.TEST_PLAN_FIRST_REQUEST_NO_CHILD_SCRIPT_TEMPLATE = getattr(config_module, 'TEST_PLAN_FIRST_REQUEST_NO_CHILD_SCRIPT_TEMPLATE', None)
        self.TEST_PLAN_CHILD_REQUEST_TEMPLATE = getattr(config_module, 'TEST_PLAN_CHILD_REQUEST_TEMPLATE', None)
        self.DEFAULT_APP_NAME = getattr(config_module, 'DEFAULT_APP_NAME', 'UnityApp')
        self.basicUrl_gpt35 = getattr(config_module, 'basicUrl_gpt35', None)
        self.OPENAI_API_KEY = getattr(config_module, 'OPENAI_API_KEY', None)
        
        self.results_dir = results_dir
        self.scene_name = scene_name  # Keep original value, don't set default
        self.app_name = app_name or self.DEFAULT_APP_NAME
        self.enable_llm = enable_llm
        self.gobj_hierarchy_path = os.path.join(results_dir, f"{scene_name}_gobj_hierarchy.json")
        self.scene_data_dir = os.path.join(results_dir, "scene_detailed_info")
        self.script_data_dir = os.path.join(results_dir, "script_detailed_info")
        self.scene_meta_dir = os.path.join(results_dir, 'scene_detailed_info', 'mainResults')
        
        # Setup OpenAI API (only when LLM is enabled)
        if self.enable_llm:
            self._setup_openai_api()
        else:
            print("[WARN]  LLM API calls disabled, will use simulation mode")
            
        # Load GML file data (used for both scene metadata and scene graphs)
        self.scene_graphs = self._load_gml_files()
        self.scene_meta_data = self._load_scene_meta_data()
        # Load gobj_hierarchy.json
        self.gobj_hierarchy = self._load_gobj_hierarchy()

        
        # Used to track object IDs that have been processed through sorted_target_logic_info
        self.processed_object_ids = set()
    
    def _load_gobj_hierarchy(self) -> List[Dict[str, Any]]:
        """Load gobj_hierarchy.json file"""
        try:
            with open(self.gobj_hierarchy_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load gobj_hierarchy.json: {e}")
            return []
    
    def _sort_children_by_special_logic(self, child_mono_comp_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort child_mono_comp_info, prioritizing child nodes with special logic
        
        Special logic includes:
        - sorted_target_logic_info (non-empty)
        - sorted_layer_logic_info (non-empty)
        - tag_logic_info (non-empty)
        - layer_logic_info (non-empty)
        - gameobject_find_info (non-empty)
        - gameobject_instantiate_info (non-empty)
        
        Args:
            child_mono_comp_info: Child node information list
        
        Returns:
            List[Dict[str, Any]]: Sorted child node information list
        """
        def has_special_logic(child_info: Dict[str, Any]) -> bool:
            """Check if child node contains special logic"""
            # Check sorted_target_logic_info
            if child_info.get('sorted_target_logic_info') and len(child_info.get('sorted_target_logic_info', [])) > 0:
                return True
            
            # Check sorted_layer_logic_info
            if child_info.get('sorted_layer_logic_info') and len(child_info.get('sorted_layer_logic_info', [])) > 0:
                return True
            
            # Check tag_logic_info
            if child_info.get('tag_logic_info') and len(child_info.get('tag_logic_info', [])) > 0:
                return True
            
            # Check layer_logic_info
            if child_info.get('layer_logic_info') and len(child_info.get('layer_logic_info', [])) > 0:
                return True
            
            # Check gameobject_find_info
            if child_info.get('gameobject_find_info') and len(child_info.get('gameobject_find_info', [])) > 0:
                return True
            
            # Check gameobject_instantiate_info
            if child_info.get('gameobject_instantiate_info') and len(child_info.get('gameobject_instantiate_info', [])) > 0:
                return True
            
            return False
        
        # Divide child nodes into two groups: those with special logic and those without
        children_with_special_logic = []
        children_without_special_logic = []
        
        for child_info in child_mono_comp_info:
            if has_special_logic(child_info):
                children_with_special_logic.append(child_info)
            else:
                children_without_special_logic.append(child_info)
        
        # Print sorting result statistics
        if children_with_special_logic:
            print(f"[SEARCH] Sorting child nodes: {len(children_with_special_logic)} with special logic, {len(children_without_special_logic)} without special logic")
            print(f"   Child nodes with special logic: {[child['child_name'] for child in children_with_special_logic]}")
        
        # Put child nodes with special logic first, those without special logic last
        return children_with_special_logic + children_without_special_logic
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Clean illegal characters in filename, replace them with underscores
        
        Windows illegal filename characters: < > : " / \\ | ? *
        
        Args:
            filename: Original filename
            
        Returns:
            str: Cleaned safe filename
        """
        illegal_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in illegal_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized
    
    def _setup_openai_api(self):
        """Setup OpenAI API configuration"""
        try:
            openai.base_url = self.basicUrl_gpt35
            openai.api_key = self.OPENAI_API_KEY
            print("[OK] OpenAI API configuration successful")
        except Exception as e:
            print(f"[ERROR] OpenAI API configuration failed: {e}")
            print("Please check API configuration in config module")
    
    def _load_gml_files(self) -> Dict[str, nx.Graph]:
        """Load all GML files, return scene graph data"""
        scene_graphs = {}
        
        if not os.path.exists(self.scene_meta_dir):
            print(f"Warning: Scene metadata directory does not exist: {self.scene_meta_dir}")
            return scene_graphs
        
        # Find and load all GML files
        for file in os.listdir(self.scene_meta_dir):
            if file.endswith('.gml'):
                gml_file_path = os.path.join(self.scene_meta_dir, file)
                try:
                    graph = nx.read_gml(gml_file_path)
                    # Use filename (without .gml suffix) as scene name
                    scene_name = file.replace('.gml', '')
                    scene_graphs[scene_name] = graph
                    print(f"Loaded scene graph: {scene_name}")
                except Exception as e:
                    print(f"Failed to load GML file {file}: {e}")
        
        return scene_graphs
    
    def _load_scene_meta_data(self) -> Dict[str, Any]:
        """Load scene metadata (from GML files)"""
        scene_meta_data = {}
        
        if not os.path.exists(self.scene_meta_dir):
            print(f"Warning: Scene metadata directory does not exist: {self.scene_meta_dir}")
            return scene_meta_data
        
        # Find GML files
        for file in os.listdir(self.scene_meta_dir):
            if file.endswith('.gml'):
                gml_file_path = os.path.join(self.scene_meta_dir, file)
                try:
                    # Load GML file
                    graph = nx.read_gml(gml_file_path)
                    scene_name = file.split(".unity")[0]
                    scene_meta_data[scene_name] = graph
                    print(f"Loaded scene GML file: {scene_name}")
                except Exception as e:
                    print(f"Failed to load GML file {file}: {e}")
        
        return scene_meta_data
    
    def _call_llm_api(self, prompt: str, context: List[Dict[str, str]] = None, max_retries: int = 5, llm_model: str = 'gpt-5') -> Optional[str]:
        """
        Call LLM API to get response, supports passing conversation history
        
        Args:
            prompt: Prompt to send to LLM
            context: Conversation history context, if None then use single-turn conversation
            max_retries: Maximum retry count
        
        Returns:
            str: LLM response content, returns None if failed
        """
        # If LLM API is disabled, use simulation mode
        if not self.enable_llm:
            return self._generate_simulated_response(prompt)
        
        # Build message list
        if context is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            # Copy context and add current prompt
            messages = context.copy()
            messages.append({"role": "user", "content": prompt})
        
        for attempt in range(max_retries):
            try:
                print(f"[PROCESS] Calling LLM API (attempt {attempt + 1}/{max_retries})...")
                if context:
                    print(f"   Conversation history length: {len(context)} messages")
                
                response = openai.chat.completions.create(
                    model=llm_model,
                    messages=messages,
                    temperature=0
                )
                
                # Extract response content
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    print("[OK] LLM API call successful")
                    return content
                else:
                    print("[ERROR] LLM response is empty")
                    return None
                    
            except Exception as e:
                print(f"[ERROR] LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("⏳ Waiting 30 seconds before retry...")
                    time.sleep(30)
                else:
                    print("[ERROR] All retries failed")
                    return None
        
        return None
    
    def _generate_simulated_response(self, prompt: str) -> str:
        """Generate simulated LLM response (for testing)"""
        print("[BOT] Generating simulated LLM response...")
        
        # Simplified simulated response template
        if "child_request" in prompt or "children" in prompt.lower():
            return '''{
  "taskUnit": [
    {
      "actionUnits": [
        {
          "type": "Grab",
          "source_object_name": "Player",
          "source_object_fileID": "12345",
          "target_object_name": "Interactive Object",
          "target_object_fileID": "67890"
        },
        {
          "type": "Trigger",
          "source_object_name": "Interactive Object",
          "method": "OnTriggerEnter",
          "condition": "Trigger once when player enters collision area"
        }
      ]
    }
  ],
  "Need_more_Info": false
}'''
        else:
            return '''{
  "taskUnit": [
    {
      "actionUnits": [
        {
          "type": "Trigger",
          "source_object_name": "Test Object",
          "method": "Basic test",
          "condition": "Single execution"
        }
      ]
    }
  ],
  "Need_more_Info": false
}'''
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response, determine if more information is needed"""
        try:
            THINK_RE = re.compile(r'<\s*think\s*>.*?<\s*/\s*think\s*>', re.IGNORECASE | re.DOTALL)
            response = THINK_RE.sub('', response)
            if '```json' in response:
                    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                    if json_match:
                        response = json_match.group(1).strip()
            if 'taskUnits' in response:
                # Try to parse JSON
                try:
                    parsed_response = json.loads(response)
                    return {'need_more_info': False, 'test_plan': parsed_response}
                except json.JSONDecodeError:
                    return {'need_more_info': False, 'test_plan': response}
            else:
                return {'need_more_info': True, 'test_plan': None}
        except Exception as e:
            print(f"[WARN]  Failed to parse LLM response: {e}")
            return {'need_more_info': True, 'test_plan': None}
    
    def _extract_scene_meta_info(self, gobj_id: str, scene_name: str, gobj_script_lis: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract information of specified GameObject from scene metadata
        
        Args:
            gobj_id: GameObject ID
            scene_name: Scene name
            gobj_script_lis: GameObject script list
        
        Returns:
            str: Scene metadata information, returns None if not found
        """
        if scene_name not in self.scene_meta_data:
            return None
        
        scene_graph = self.scene_meta_data[scene_name]
        
        # Find GameObject metadata
        MonoBehaviour_lis = []
        gobj_data = self._find_gameobject_in_scene_data(gobj_id, scene_graph)
        
        if gobj_data:
            if gobj_script_lis:
                for i, script_info in enumerate(gobj_script_lis):
                    mono_comp_info = {}
                    mono_comp_info[f"MonoBehaviour_{i}"] = script_info['mono_property']
                    MonoBehaviour_lis.append(mono_comp_info)
                if MonoBehaviour_lis:
                    gobj_data['MonoBehaviour'] = MonoBehaviour_lis
            else:
                # Use enumerate to get correct index
                mono_comp_edges = [(source, target, edge_data) for source, target, edge_data in scene_graph.edges(data=True) 
                                  if edge_data.get('type') == 'Has_Mono_Comp' and source == gobj_id]
                
                for j, (source, target, edge_data) in enumerate(mono_comp_edges):
                    mono_comp_id = target
                    mono_comp_info = {}
                    # Write index j correctly into field name
                    mono_comp_info[f"MonoBehaviour_{j}"] = scene_graph.nodes[mono_comp_id].get('properties', {})
                    MonoBehaviour_lis.append(mono_comp_info)
                
                if MonoBehaviour_lis:
                    gobj_data['MonoBehaviour'] = MonoBehaviour_lis

        return str(gobj_data)
    
    def _extract_script_source_code(self, mono_comp_id: str) -> Optional[str]:
        """
        Extract source code from script data
        
        Args:
            mono_comp_id: Mono component ID
        
        Returns:
            str: Source code, returns None if not found
        """
        # Search for Source_Code_File relationships in all scene graphs
        for scene_name, scene_graph in self.scene_graphs.items():
            # Find all Source_Code_File relationships with mono_comp_id as source
            for source, target, edge_data in scene_graph.edges(data=True):
                target_inheritance = None
                inheritance_script_content = None
                if (source == mono_comp_id and 
                    edge_data.get('type') == 'Source_Code_File'):
                    
                    # Get file_path from target node's properties
                    if target in scene_graph.nodes:
                        target_node = scene_graph.nodes[target]
                        for s, t, e in scene_graph.edges(data=True):
                            if s == target and e.get('type') == 'Inheritance_Relation':
                                target_inheritance = t
                                break

                        if 'properties' in target_node:
                            properties = target_node['properties']

                            if target_inheritance:
                                inheritance_file_path = scene_graph.nodes[target_inheritance].get('properties', {}).get('file_path', '')
                                inheritance_name = scene_graph.nodes[target_inheritance].get('properties', {}).get('name', '')
                                if inheritance_file_path.endswith('.meta'):
                                    inheritance_file_path = inheritance_file_path[:-5]  # Remove .meta suffix
                                inheritance_script_content = self._load_script_file(inheritance_file_path)
                            
                            # Check if properties is dict or list
                            if isinstance(properties, dict):
                                # properties is dict, directly find file_path
                                if 'file_path' in properties:
                                    file_path = properties['file_path']
                                    if "Library" and "Interaction" in file_path:
                                        script_content = "// This script" + os.path.basename(file_path) + " is the XR Interaction Toolkit. You only need to trigger the Interactable Events (m_Calls) in scene meta file if exist."
                                        return script_content

                                    # Process file_path field, strip '.meta', get the field from strip[0]
                                    if file_path.endswith('.meta'):
                                        file_path = file_path[:-5]  # Remove .meta suffix
                                    
                                    # Try to load script file
                                    script_content = self._load_script_file(file_path)
                                    if script_content:
                                        if inheritance_script_content:
                                            script_content = script_content + "\n" + "// " + inheritance_name + ".cs" + "\n" + inheritance_script_content
                                        script_content = script_content.replace("\ufeff", "")
                                        return script_content
                                        
                            elif isinstance(properties, list):
                                # properties is list, iterate to find file_path
                                for prop in properties:
                                    if isinstance(prop, dict) and 'file_path' in prop:
                                        file_path = prop['file_path']
                                        if "Library" and "Interaction" in file_path:
                                            script_content = "// This script" + os.path.basename(file_path) + " is the XR Interaction Toolkit. You only need to trigger the Interactable Events (m_Calls) in scene meta file if exist."
                                            return script_content
                                            
                                        # Process file_path field, strip '.meta', get the field from strip[0]
                                        if file_path.endswith('.meta'):
                                            file_path = file_path[:-5]  # Remove .meta suffix
                                        
                                        # Try to load script file
                                        script_content = self._load_script_file(file_path)
                                        if script_content:
                                            if inheritance_script_content:
                                                script_content = script_content + "\n" + "// " + inheritance_name + ".cs" + "\n" + inheritance_script_content
                                            script_content = script_content.replace("\ufeff", "")
                                            return script_content
        
        return None
    
    def _load_script_file(self, file_path: str) -> Optional[str]:
        """Load script file content"""
        try:
            # Try to load file directly
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Search for file with same name in script directory
            script_filename = os.path.basename(file_path)
            if os.path.exists(self.script_data_dir):
                for script_file in os.listdir(self.script_data_dir):
                    if script_file == script_filename:
                        script_file_path = os.path.join(self.script_data_dir, script_file)
                        with open(script_file_path, 'r', encoding='utf-8') as f:
                            return f.read()
            
            return None
        except Exception as e:
            print(f"Failed to load script file {file_path}: {e}")
            return None
    
    def _find_child_gameobject_info(self, child_id: str, scene_name: str, mono_comp_ids: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find child GameObject information
        
        Args:
            child_id: Child GameObject ID
            scene_name: Scene name
            mono_comp_ids: Mono component information list
        
        Returns:
            Dict: Child GameObject information, returns None if not found
        """
        if scene_name not in self.scene_meta_data:
            return None
        
        scene_graph = self.scene_meta_data[scene_name]
        
        # Find child GameObject metadata
        gobj_data = self._find_gameobject_in_scene_data(child_id, scene_graph)
        if gobj_data:
            MonoBehaviour_lis = []
            for i, mono_comp in enumerate(mono_comp_ids):
                mono_comp_info = {}
                mono_comp_info[f"MonoBehaviour_{i}"] = mono_comp['mono_property']
                MonoBehaviour_lis.append(mono_comp_info)
            if MonoBehaviour_lis:
                gobj_data['MonoBehaviour'] = MonoBehaviour_lis

            return {
                'id': child_id,
                'name': gobj_data.get('GameObject', {}).get('m_Name', 'Unknown'),
                'scene_meta': gobj_data
            }
        
        return None
    
    def _find_gameobject_in_scene_data(self, gobj_id: str, scene_graph: nx.Graph) -> Optional[Dict[str, Any]]:
        """Find GameObject with specified ID in scene data"""

        gobj_data = {}
        gobj_data["Has_Rigidbody"] = False
        found_node = None
        
        for node in scene_graph.nodes:
            node_data = scene_graph.nodes[node] 
            if str(node.split("stripped")[0]) == str(gobj_id.split("stripped")[0]):
                gobj_data[node_data.get('type', 'Unknown')] = node_data
                found_node = node

                if node_data.get('type', 'Unknown') == "PrefabInstance":
                    for source, target, edge_data in scene_graph.edges(data=True):
                        if (edge_data.get('type') == "PrefabInstance_INFO" and 
                        str(target) == str(gobj_id)):
                            for s, t, e in scene_graph.edges(data=True):
                                if e.get('type') == "Has_Rigidbody" and str(s) == str(source):
                                    gobj_data["Has_Rigidbody"] = True
                                if e.get('type') == "Has_Collider" and str(s) == str(source):
                                    gobj_data["Has_Collider"] = True
                                if e.get('type') == "Has_Event_Trigger" and str(s) == str(source):
                                    gobj_data["Has_Event_Trigger"] = True
                                if e.get('type') == "Has_Other_Comp" and str(s) == str(source):
                                    gobj_data["Transform"] = scene_graph.nodes[t]

                
                # Find related Transform components
                for source, target, edge_data in scene_graph.edges(data=True):
                    if (edge_data.get('type') == "Has_Other_Comp" and 
                        str(source) == str(gobj_id)):
                        target_node = scene_graph.nodes[target]
                        gobj_data["Transform"] = target_node

                    if (edge_data.get('type') == "PrefabInstance_INFO" and 
                        str(source) == str(gobj_id)):
                        target_node = scene_graph.nodes[target]
                        gobj_data["Source Prefab GameObject"] = target_node
                    
                    if (edge_data.get('type') == "Has_Collider" and 
                        str(source) == str(gobj_id)):
                        target_node = scene_graph.nodes[target]
                        gobj_data[target_node.get('type', 'Unknown')] = target_node
                    
                    if (edge_data.get('type') == "Has_Rigidbody" and 
                        str(source) == str(gobj_id)):
                        target_node = scene_graph.nodes[target]
                        gobj_data["Has_Rigidbody"] = True
                    
                    if (edge_data.get('type') == "Has_Event_Trigger" and 
                        str(source) == str(gobj_id)):
                        target_node = scene_graph.nodes[target]
                        gobj_data["Has_Event_Trigger"] = True
                        gobj_data['Event_Trigger'] = target_node
        
        
        if found_node:
            print(f"[OK] Successfully found GameObject, returning data structure:")
            for key, value in gobj_data.items():
                print(f"   {key}: {type(value)} - {len(str(value))} characters")
            return gobj_data
        else:
            print(f"[ERROR] GameObject ID not found: {gobj_id}")
            return None
            
    def _save_llm_responses(self, gobj_info: Dict[str, Any], conversation_history: List[Dict[str, Any]], scene_name: str, llm_responses_dir: str):
        """
        Save LLM responses to file
        
        Args:
            gobj_info: GameObject information
            conversation_history: Conversation history
            scene_name: Scene name
        """
        # Create response save directory (clean illegal characters in scene name)
        safe_gameobject_name = self._sanitize_filename(gobj_info['gameobject_name'])
        conversation_file = os.path.join(llm_responses_dir, f"{safe_gameobject_name}_{gobj_info['gameobject_id_replace']}_conversation.json")
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_history, f, indent=2, ensure_ascii=False)
        
        # Extract and merge test plans
        merged_test_plan = {
            "taskUnits": [
                {
                    "actionUnits": []
                }
            ]
        }
        
        # Used to store existing actionUnits, avoid duplicates
        existing_action_units = []
        total_processed_units = 0  # Total processed actionUnits count
        filtered_units = 0  # Filtered actionUnits count
        
        # Collect all assistant messages containing test_plan, process in chronological order
        all_test_plan_messages = []
        for msg in conversation_history:
            if msg.get('role') == 'assistant' and msg.get('test_plan'):
                # Check if actionUnits in this assistant message's test_plan are mentioned in current round's user message
                '''
                if self._validate_action_units_in_user_context(msg, conversation_history):
                
                    all_test_plan_messages.append(msg)
                else:
                    print(f"[WARN]  Skipping assistant message: source_object_fileID in actionUnits not mentioned in current round user message")
                '''
                all_test_plan_messages.append(msg)
        
        # Process all rounds of test plans
        if all_test_plan_messages:
            print(f"[INFO] Found {len(all_test_plan_messages)} assistant messages containing test_plan, starting merge...")
            
            for msg_index, msg in enumerate(all_test_plan_messages):
                test_plan = msg['test_plan']
                print(f"   Processing round {msg_index + 1} test plan...")
                if True:
                    # Check if test_plan is dict or string
                    if isinstance(test_plan, dict) and 'taskUnits' in test_plan:
                        # test_plan is dict, directly access
                        for task in test_plan['taskUnits']:
                            if 'actionUnits' in task:
                                total_processed_units += len(task['actionUnits'])
                                original_count = len(existing_action_units)
                                self._merge_action_units_with_priority(existing_action_units, task['actionUnits'], msg_index)
                                filtered_units += len(task['actionUnits']) - (len(existing_action_units) - original_count)
                    elif isinstance(test_plan, str) and 'taskUnits' in test_plan:
                        # test_plan is string, try to parse JSON
                        try:
                            parsed_plan = json.loads(test_plan)
                            if 'taskUnits' in parsed_plan:
                                for task in parsed_plan['taskUnits']:
                                    if 'actionUnits' in task:
                                        total_processed_units += len(task['actionUnits'])
                                        original_count = len(existing_action_units)
                                        self._merge_action_units_with_priority(existing_action_units, task['actionUnits'], msg_index)
                                        filtered_units += len(task['actionUnits']) - (len(existing_action_units) - original_count)
                        except json.JSONDecodeError:
                            print(f"[WARN]  Unable to parse test plan JSON: {test_plan[:100]}...")
        else:
            print("[WARN]  No assistant messages containing test_plan found")
        
        # Clean internal markers in actionUnits, prepare for final output
        cleaned_action_units = []
        for unit in existing_action_units:
            # Create copy and remove internal markers
            cleaned_unit = {k: v for k, v in unit.items() if k != '_round_index'}
            cleaned_action_units.append(cleaned_unit)
        
        # Add deduplicated actionUnits to merged_test_plan
        merged_test_plan['taskUnits'][0]['actionUnits'] = cleaned_action_units
        
        # Save merged test plan (clean illegal characters in filename)
        if merged_test_plan['taskUnits'][0]['actionUnits']:
            test_plan_file = os.path.join(llm_responses_dir, f"{safe_gameobject_name}_{gobj_info['gameobject_id_replace']}_test_plans.json")
            with open(test_plan_file, 'w', encoding='utf-8') as f:
                json.dump(merged_test_plan, f, indent=2, ensure_ascii=False)
            
            print(f"[SAVE] Merged test plan saved to: {test_plan_file}")
            print(f"   Contains {len(merged_test_plan['taskUnits'][0]['actionUnits'])} action units (deduplicated and validated)")
        
        # Display processing statistics
        print(f"[STATS] Processing statistics:")
        print(f"   - Total processed action units: {total_processed_units}")
        print(f"   - Filtered invalid action units: {filtered_units}")
        print(f"   - Final retained action units: {len(merged_test_plan['taskUnits'][0]['actionUnits'])}")
        
        print(f"[SAVE] Conversation history saved to: {conversation_file}")
    
    def _merge_action_units_with_priority(self, existing_units: List[Dict[str, Any]], new_units: List[Dict[str, Any]], round_index: int):
        """
        Merge actionUnits, supports deduplication strategy based on round priority
        
        Args:
            existing_units: Existing actionUnits list
            new_units: New actionUnits list
            round_index: Current round index (for priority judgment)
        """
        for new_unit in new_units:
            # First validate fileID field
            if not self._validate_action_unit_fileids(new_unit):
                # If fileID field is invalid, skip this actionUnit
                continue
            
            # Check if matching actionUnit already exists
            matched_index = self._find_matching_action_unit(existing_units, new_unit)
            
            if matched_index is not None:
                # Found match, compare priority (higher round number has priority)
                existing_unit = existing_units[matched_index]
                existing_round = existing_unit.get('_round_index', 0)
                
                if round_index > existing_round:
                    # Current round is larger, replace existing item
                    new_unit['_round_index'] = round_index
                    existing_units[matched_index] = new_unit
                    print(f"[PROCESS] Replacing actionUnit at index {matched_index} (round {existing_round} -> {round_index})")
                else:
                    # Existing round is larger or equal, keep existing item
                    print(f"[SKIP]  Keeping existing actionUnit (round {existing_round} >= {round_index})")
            else:
                # No match found, add new actionUnit
                new_unit['_round_index'] = round_index
                existing_units.append(new_unit)
                print(f"[ADD] Adding new actionUnit (round {round_index})")

    
    def _find_matching_action_unit(self, existing_units: List[Dict[str, Any]], new_unit: Dict[str, Any]) -> Optional[int]:
        """
        Find matching actionUnit, use different matching strategies based on type
        
        Args:
            existing_units: Existing actionUnits list
            new_unit: New actionUnit
        
        Returns:
            Optional[int]: Matching index, returns None if no match found
        """
        new_type = new_unit.get('type', '')
        
        for i, existing_unit in enumerate(existing_units):
            existing_type = existing_unit.get('type', '')
            
            # Types must be the same
            if new_type != existing_type:
                continue
            
            if new_type in ['Grab', 'Transform']:
                # Grab and Transform: all key values are the same
                if self._are_action_units_identical(existing_unit, new_unit):
                    return i
            elif new_type == 'Trigger':
                # Trigger: specific field matching
                if self._are_trigger_units_matching(existing_unit, new_unit):
                    return i
        
        return None
    
    def _are_trigger_units_matching(self, unit1: Dict[str, Any], unit2: Dict[str, Any]) -> bool:
        """
        Compare if two Trigger type actionUnits match (based on specific fields)
        
        Args:
            unit1: First Trigger actionUnit
            unit2: Second Trigger actionUnit
        
        Returns:
            bool: Returns True if matching, otherwise False
        """
        # Check key fields (including source_object_name, source_object_fileID, condition)
        key_fields = ['source_object_name', 'source_object_fileID', 'condition']
        # Check methodCallUnits in triggerring_events
        events1 = unit1.get('triggerring_events', [])
        events2 = unit2.get('triggerring_events', [])

        for field in key_fields:
            if unit1.get(field) != unit2.get(field):
                return False

        # Check triggerring_events
        if len(events1) != len(events2):
            return False
        
        for event1, event2 in zip(events1, events2):
            method_calls1 = event1.get('methodCallUnits', [])
            method_calls2 = event2.get('methodCallUnits', [])
            
            if len(method_calls1) != len(method_calls2):
                return False
            
            for call1, call2 in zip(method_calls1, method_calls2):
                if (call1.get('script_fileID') != call2.get('script_fileID') or 
                    call1.get('method_name') != call2.get('method_name')):
                    return False
        
        # Check triggerred_events
        triggered_events1 = unit1.get('triggerred_events', [])
        triggered_events2 = unit2.get('triggerred_events', [])
        
        if len(triggered_events1) != len(triggered_events2):
            return False
        
        for event1, event2 in zip(triggered_events1, triggered_events2):
            method_calls1 = event1.get('methodCallUnits', [])
            method_calls2 = event2.get('methodCallUnits', [])
            
            if len(method_calls1) != len(method_calls2):
                return False
            
            for call1, call2 in zip(method_calls1, method_calls2):
                if (call1.get('script_fileID') != call2.get('script_fileID') or 
                    call1.get('method_name') != call2.get('method_name')):
                    return False

        return True
    
    def _are_action_units_identical(self, unit1: Dict[str, Any], unit2: Dict[str, Any]) -> bool:
        """
        Compare if two actionUnits are identical (exact match)
        
        Args:
            unit1: First actionUnit
            unit2: Second actionUnit
        
        Returns:
            bool: Returns True if two actionUnits are the same, otherwise False
        """
        # Create copies and remove internal marker fields
        clean_unit1 = {k: v for k, v in unit1.items() if k != '_round_index'}
        clean_unit2 = {k: v for k, v in unit2.items() if k != '_round_index'}
        
        # Compare all key-value pairs
        if set(clean_unit1.keys()) != set(clean_unit2.keys()):
            return False
        
        for key in clean_unit1.keys():
            if clean_unit1[key] != clean_unit2[key]:
                return False
        
        return True
    
    def _is_valid_fileid_value(self, value: Any) -> bool:
        """
        Check if fileID field value is valid integer or long integer type
        
        Args:
            value: Value to check
        
        Returns:
            bool: Returns True if valid integer or long integer, otherwise False
        """
        if value is None:
            return False
        
        # Check if it's integer type
        if isinstance(value, int):
            return True
        
        # Check if it's integer in string form
        if isinstance(value, str):
            try:
                # Try to convert to integer
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        
        # Check if it's long integer (Python 2 compatibility, in Python 3 int is long integer)
        if hasattr(value, '__class__') and value.__class__.__name__ == 'long':
            return True
        
        return False
    
    def _validate_action_units_in_user_context(self, assistant_msg: Dict[str, Any], conversation_history: List[Dict[str, Any]]) -> bool:
        """
        Validate if actionUnits in assistant message's test_plan are mentioned in current round's user message
        
        Args:
            assistant_msg: assistant message
            conversation_history: Complete conversation history
        
        Returns:
            bool: Returns True if all actionUnits' source_object_fileID are mentioned in current round user message, otherwise False
        """
        # Find current assistant message's position in conversation history
        assistant_index = None
        for i, msg in enumerate(conversation_history):
            if msg is assistant_msg:
                assistant_index = i
                break
        
        if assistant_index is None:
            print("[WARN]  Unable to find assistant message position in conversation history")
            return False
        
        # Find current round's corresponding user message (last user message before assistant message)
        current_user_msg = None
        for i in range(assistant_index - 1, -1, -1):
            if conversation_history[i].get('role') == 'user':
                current_user_msg = conversation_history[i]
                break
        
        if current_user_msg is None:
            print("[WARN]  Current round's corresponding user message not found")
            return False
        
        user_content = current_user_msg.get('content', '')
        if not user_content:
            print("[WARN]  Current round user message content is empty")
            return False
        
        # Extract actionUnits from test_plan
        test_plan = assistant_msg.get('test_plan')
        if not test_plan:
            return True  # No test_plan, no need to validate
        
        # Process string format test_plan
        if isinstance(test_plan, str):
            try:
                test_plan = json.loads(test_plan)
            except json.JSONDecodeError:
                print("[WARN]  Unable to parse test_plan JSON")
                return False
        
        if not isinstance(test_plan, dict) or 'taskUnits' not in test_plan:
            return True  # Incorrect format, skip validation
        
        # Collect all source_object_fileID from actionUnits
        action_units_fileids = set()
        for task in test_plan.get('taskUnits', []):
            for action_unit in task.get('actionUnits', []):
                # Collect all field values containing fileID
                for key, value in action_unit.items():
                    if 'fileid' in key.lower() and value is not None:
                        action_units_fileids.add(str(value))
        
        if not action_units_fileids:
            return True  # No fileID fields, no need to validate
        
        # Check if these fileIDs are mentioned in user message content (supports multiple formats)
        for fileid in action_units_fileids:
            # Check multiple possible formats: direct number, quoted number, JSON format, etc.
            fileid_found = False
            if fileid in user_content:
                fileid_found = True
            elif f'"{fileid}"' in user_content:
                fileid_found = True
            elif f"'{fileid}'" in user_content:
                fileid_found = True
            elif f"fileID: {fileid}" in user_content:
                fileid_found = True
            elif f"'fileID': '{fileid}'" in user_content:
                fileid_found = True
            
            if not fileid_found:
                print(f"[WARN]  fileID {fileid} not mentioned in current round user message")
                return False
        
        print(f"[OK] All actionUnits' fileIDs are mentioned in current round user message")
        return True
    
    def _validate_action_unit_fileids(self, action_unit: Dict[str, Any]) -> bool:
        """
        Validate if all field values containing "fileID" in actionUnit are valid integer or long integer
        
        Args:
            action_unit: actionUnit to validate
        
        Returns:
            bool: Returns True if all fileID fields are valid, otherwise False
        """
        action_type = action_unit.get('type', '')
        
        # First validate fileID fields
        for key, value in action_unit.items():
            if "source_object_name" in key.lower():
                for forbid in forbid_lis:
                    if forbid in value:
                        return False
            if "fileid" in key.lower():  # Case-insensitive check
                if not self._is_valid_fileid_value(value) or value == 0:
                    print(f"[WARN]  Filtering out invalid test_plan: field '{key}' value '{value}' is not a valid integer type")
                    return False
        
        # Only validate triggering/triggerred events for 'Trigger' type actionUnits
        '''
        if action_type == 'Trigger':
            has_triggering = False
            has_triggerred = False
            triggering_valid = False
            triggerred_valid = False
            
            for key, value in action_unit.items():
                if "triggerring_events" in key.lower():
                    has_triggering = True
                    triggering_valid = len(value) > 0 and any(
                        'methodCallUnits' in event and len(event.get('methodCallUnits', [])) > 0 
                        for event in value
                    )
                    
                if "triggerred_events" in key.lower():
                    has_triggerred = True
                    triggerred_valid = len(value) > 0 and any(
                        'methodCallUnits' in event and len(event.get('methodCallUnits', [])) > 0 
                        for event in value
                    )
            
            # Simplified logic
            if has_triggering and has_triggerred:
                # Both exist: at least one valid is enough
                return triggering_valid or triggerred_valid
            elif has_triggering:
                # Only triggering exists: must be valid
                return triggering_valid
            elif has_triggerred:
                # Only triggerred exists: must be valid
                return triggerred_valid
            else:
                # Neither exists: invalid
                return False
        else:
            # For non-'Trigger' type actionUnits (e.g., 'Transform', 'Grab'), directly return True
            return True
        '''
        return True

    def _rebuild_llm_context(self, conversation_history: List[Dict[str, Any]], 
                           gobj_info: Dict[str, Any], remaining_children: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Rebuild LLM connection, context contains conversation information of main object and remaining child objects
        
        Args:
            conversation_history: Current conversation history
            gobj_info: Main GameObject information
            remaining_children: Remaining child object list
        
        Returns:
            List[Dict[str, str]]: Rebuilt LLM context
        """
        print(f"[PROCESS] Rebuilding LLM connection, including main object and {len(remaining_children)} remaining child objects information")
        
        # Create new LLM context
        new_context = []
        
        last_assistant_msg_with_test_plan = None
        for msg in reversed(conversation_history):
            if msg.get('role') == 'assistant' and msg.get('response_type') == 'test_plan_response':
                last_assistant_msg_with_test_plan = msg
                break
        
        # Add main object's conversation information (only includes main object's requests and responses)
        for msg in conversation_history:
            if msg.get('role') in ['user', 'assistant']:
                # Only include main object's conversation, exclude child objects' conversation
                request_type = msg.get('request_type', '')
                
                if request_type in ['first_request', ''] or request_type == 'first_response':
                    # Main object's request or response
                    new_context.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
                else:
                    break
        
        if last_assistant_msg_with_test_plan:
            new_context.append({
                'role': last_assistant_msg_with_test_plan['role'],
                'content': last_assistant_msg_with_test_plan['content']
            })
        
        print(f"[OK] LLM context rebuild complete, contains {len(new_context)} messages")
        return new_context
    
    def _build_script_content(self, script_list: List[Dict[str, Any]]) -> str:
        """
        Build script source code content
        
        Args:
            script_list: Script information list
        
        Returns:
            str: Formatted script source code content
        """
        if not script_list:
            return "// Script source code not found"
        
        script_content = ""
        for i, script_info in enumerate(script_list):
            target_script_id = script_info.get('target', '')
            script_source = self._extract_script_source_code(target_script_id)
            
            if i == len(script_list) - 1:
                script_content += script_source or f"// Script source code for {target_script_id}"
            else:
                script_content += script_source or f"// Script source code for {target_script_id}"
                script_content += "\n'''\n"
                script_content += f"[Source code of {i+1}th script files attached]\n'''\n"
        
        return script_content
    
    def _add_conversation_message(self, conversation_history: List[Dict[str, Any]], 
                                 role: str, content: str, llm_context: List[Dict[str, str]] = None, **kwargs) -> None:
        """
        Add conversation message to history
        
        Args:
            conversation_history: Conversation history
            role: Role ('user', 'assistant', 'system')
            content: Message content
            llm_context: LLM context (optional)
            **kwargs: Other message attributes
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        # If llm_context is provided, add it to message (truncate content to first 100 characters)
        if llm_context is not None:
            truncated_context = []
            for ctx_item in llm_context:
                if isinstance(ctx_item, dict) and 'content' in ctx_item:
                    truncated_item = ctx_item.copy()
                    # Truncate content to first 100 characters
                    if len(truncated_item['content']) > 100:
                        truncated_item['content'] = truncated_item['content'][:100] + "..."
                    truncated_context.append(truncated_item)
                else:
                    truncated_context.append(ctx_item)
            message['llm_context'] = truncated_context
        
        message.update(kwargs)
        conversation_history.append(message)
    
    def _handle_llm_response(self, response: str, conversation_history: List[Dict[str, Any]], 
                           llm_context: List[Dict[str, str]], request: str, 
                           response_type: str = 'test_plan_response', **kwargs) -> tuple[bool, int]:
        """
        General method to handle LLM response
        
        Args:
            response: LLM response content
            conversation_history: Conversation history
            llm_context: LLM context
            request: Original request
            response_type: Response type
            **kwargs: Other message attributes
        
        Returns:
            tuple: (whether more information is needed, actual conversation turn count)
        """
        if not response:
            self._add_conversation_message(
                conversation_history, 'assistant', 
                "Error: Failed to get LLM response", 
                llm_context=llm_context,
                response_type='error', need_more_info=True, **kwargs
            )
            return True, 0
        
        # Add response to LLM context
        llm_context.append({'role': 'user', 'content': request})
        llm_context.append({'role': 'assistant', 'content': response})
        
        # Parse LLM response
        parsed_response = self._parse_llm_response(response)
        
        # If more information is needed, enable multi-turn conversation
        if parsed_response['need_more_info']:
            print(f"[INFO] More information needed, enabling multi-turn conversation...")
            final_response, llm_context, multi_turn_count = self._handle_multi_turn_conversation(
                request, max_turns=3, llm_context=llm_context
            )
            
            self._add_conversation_message(
                conversation_history, 'assistant', final_response,
                llm_context=llm_context,
                response_type=response_type, need_more_info=False,
                test_plan=self._parse_llm_response(final_response)['test_plan'], **kwargs
            )
            print(f"[OK] Multi-turn conversation complete, conducted {multi_turn_count} turns")
            return False, multi_turn_count
        else:
            self._add_conversation_message(
                conversation_history, 'assistant', response,
                llm_context=llm_context,
                response_type=response_type, 
                need_more_info=parsed_response['need_more_info'],
                test_plan=parsed_response['test_plan'], **kwargs
            )
            print(f"[OK] Sufficient information obtained")
            return False, 1
    
    def _get_formatted_script_sources_and_meta(self, sorted_target_logic_info: List[Dict[str, Any]], scene_name: str) -> str:
        """
        Get script source code and scene metadata for specified GameObject, format output
        
        Args:
            sorted_target_logic_info: sorted_target_logic_info list, each element contains id, gameobject_name, tag_name and other fields
            scene_name: Scene name
        
        Returns:
            str: Formatted script source code and scene metadata
        """
        result = ""
        
        for i, item in enumerate(sorted_target_logic_info):
            gobj_id = item.get('id')
            gobj_id_replace = item.get('id_replace')
            gobj_name = item.get('gameobject_name', 'Unknown')
            tag_name = item.get('tag_name', 'Unknown')
            
            if not gobj_id:
                continue
            
            # Add separator and title for each GameObject
            if i > 0:
                result += "\n"
            
            result += f"""GameObject ID: "{gobj_id_replace}" GameObject Name: "{gobj_name}" Tag: "{tag_name}":\n"""
            
            # Get this GameObject's script source code
            # Need to find Has_Mono_Comp relationship in graph, use its target to call _extract_script_source_code
            script_source = ""
            found_mono_comp = False
            if scene_name in self.scene_meta_data:
                scene_graph = self.scene_meta_data[scene_name]   
                # Find Has_Mono_Comp relationships with gobj_id as source
                for source, target, edge_data in scene_graph.edges(data=True):
                    if (edge_data.get('type') == 'Has_Mono_Comp' and 
                        source == gobj_id):                        
                        # Found Has_Mono_Comp relationship, use target to call _extract_script_source_code
                        mono_comp_id = target
                        found_mono_comp = True
                        extracted_script = self._extract_script_source_code(mono_comp_id)
                        if extracted_script:
                            script_source += extracted_script
            
            if script_source:
                result += "[Source code of script files attached]\n"
                result += "'''\n"
                result += script_source
                result += "\n'''\n"
            else:
                if found_mono_comp:
                    result += "[Source code of script files attached]\n"
                    result += "// Script source code not found for this GameObject\n"
            
            result += "\n"
            
            # Get this GameObject's scene metadata
            # Use _extract_scene_meta_info method to get scene metadata
            scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, [])
            if scene_meta:
                result += "[Source code of scene meta file]\n"
                result += "'''\n"
                result += scene_meta
                result += "\n'''\n"
            else:
                result += "[Source code of scene meta file]\n"
                result += "// Scene meta data not found for this GameObject\n"
            
            result += "\n"
        
        return result
    
    def generate_first_request(self, gobj_info: Dict[str, Any], scene_name: str) -> str:
        """
        Generate first request (introduce GameObject and scene information)
        
        Args:
            gobj_info: GameObject information
            scene_name: Scene name
        
        Returns:
            str: Content of first request
        """
        gobj_name = gobj_info['gameobject_name']
        gobj_id = gobj_info['gameobject_id']
        gobj_replace_id = gobj_info['gameobject_id_replace']
        gobj_script_lis = gobj_info['mono_comp_relations']
        child_relations = gobj_info.get('child_relations', [])
        scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, gobj_script_lis)

        # Check if there are child object relationships
        has_children = len(child_relations) > 0

        if len(gobj_script_lis) > 0:
            # Case with scripts
            script_content = self._build_script_content(gobj_script_lis)
            
            if has_children:
                # Has child objects, use template that requires continuing to provide child object information
                request = self.TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE.format(
                    app_name=self.app_name,
                    scene_name=scene_name,
                    gobj_name=gobj_name,
                    gobj_id=gobj_replace_id,
                    scene_meta=scene_meta if scene_meta else "// Scene meta data not found",
                    script_source=script_content,
                    children_ids=[child.get('target') for child in child_relations]
                )
            else:
                # No child objects, use template that directly generates test plan
                request = self.TEST_PLAN_FIRST_REQUEST_NO_CHILD_SCRIPT_TEMPLATE.format(
                    app_name=self.app_name,
                    scene_name=scene_name,
                    gobj_name=gobj_name,
                    gobj_id=gobj_replace_id,
                    scene_meta=scene_meta if scene_meta else "// Scene meta data not found",
                    script_source=script_content                )
        else:
            # Case without scripts
            if has_children:
                # Has child objects, use template that requires continuing to provide child object information
                request = self.TEST_PLAN_FIRST_REQUEST_TEMPLATE.format(
                    app_name=self.app_name,
                    scene_name=scene_name,
                    gobj_name=gobj_name,
                    gobj_id=gobj_replace_id,
                    scene_meta=scene_meta if scene_meta else "// Scene meta data not found",
                    children_ids=[child.get('target') for child in child_relations]
                )
            else:
                # No child objects, use template that directly generates test plan
                request = self.TEST_PLAN_FIRST_REQUEST_NO_CHILD_TEMPLATE.format(
                    app_name=self.app_name,
                    scene_name=scene_name,
                    gobj_name=gobj_name,
                    gobj_id=gobj_replace_id,
                    scene_meta=scene_meta if scene_meta else "// Scene meta data not found"
                )
        
        return request
    
    def generate_child_request(self, child_info: Dict[str, Any], child_index: int, scene_name: str, conversation_history: List[Dict[str, Any]] = None, llm_context: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate child object request and handle sorted_target_logic_info and gameobject_find_info logic (supports multi-turn conversation)
        
        Args:
            child_info: Child object information
            child_index: Child object index
            scene_name: Scene name
            conversation_history: Conversation history (for handling sorted_target_logic_info and gameobject_find_info)
            llm_context: LLM conversation context
        
        Returns:
            Dict: Dictionary containing request content and processing results
        """
        parent_name = child_info['parent_info']['parent_name']
        child_name = child_info['child_name']
        child_id = child_info['child_id']
        child_id_replace = child_info['child_id_replace']
        mono_comp_ids = child_info['mono_comp_targets']  # Now it's a list
        
        # Check if sorted_target_logic_info needs to be processed
        sorted_target_logic_info = self._find_sorted_target_logic_info(child_id)
        has_sorted_target_logic = sorted_target_logic_info is not None and len(sorted_target_logic_info) > 0
        
        # Check if sorted_layer_logic_info needs to be processed
        sorted_layer_logic_info = self._find_sorted_layer_logic_info(child_id)
        has_sorted_layer_logic = sorted_layer_logic_info is not None and len(sorted_layer_logic_info) > 0
        
        # Check if gameobject_find_info needs to be processed
        gameobject_find_info = self._find_gameobject_find_info(child_id)
        has_gameobject_find_logic = gameobject_find_info is not None and len(gameobject_find_info) > 0
        
        # Check if gameobject_instantiate_info needs to be processed
        gameobject_instantiate_info = self._find_gameobject_instantiate_info(child_id)
        has_gameobject_instantiate_logic = gameobject_instantiate_info is not None and len(gameobject_instantiate_info) > 0
        
        if has_sorted_target_logic:
            print(f"[SEARCH] Detected child object {child_info['child_name']} has sorted_target_logic_info, using TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW...")
            
            # Handle sorted_target_logic_info logic
            if conversation_history is not None and llm_context is not None:
                conversation_history, llm_context, turn_count = self._handle_sorted_target_logic_conversation(
                    child_info, scene_name, conversation_history, sorted_target_logic_info, llm_context
                )
                print(f"[OK] Child object {child_info['child_name']}'s sorted_target_logic_info processing complete, conducted {turn_count} turns of conversation")
            
            return {
                'request': None,
                'has_sorted_target_logic': True,
                'has_sorted_layer_logic': False,
                'has_gameobject_find_logic': False,
                'has_gameobject_instantiate_logic': False,
                'message': f"This child object's information has been fully provided through sorted_target_logic_info, skipping generate_child_request",
                'turn_count': turn_count
            }
        
        if has_sorted_layer_logic:
            print(f"[SEARCH] Detected child object {child_info['child_name']} has sorted_layer_logic_info, using LAYER_LOGIC_CHILD_REQUEST_TEMPLATE...")
            
            # Handle sorted_layer_logic_info logic
            if conversation_history is not None and llm_context is not None:
                conversation_history, llm_context, turn_count = self._handle_sorted_layer_logic_conversation(
                    child_info, scene_name, conversation_history, sorted_layer_logic_info, llm_context
                )
                print(f"[OK] Child object {child_info['child_name']}'s sorted_layer_logic_info processing complete, conducted {turn_count} turns of conversation")
            
            return {
                'request': None,
                'has_sorted_target_logic': False,
                'has_sorted_layer_logic': True,
                'has_gameobject_find_logic': False,
                'has_gameobject_instantiate_logic': False,
                'message': f"This child object's information has been fully provided through sorted_layer_logic_info, skipping generate_child_request",
                'turn_count': turn_count
            }
        
        if has_gameobject_find_logic:
            print(f"[SEARCH] Detected child object {child_info['child_name']} has gameobject_find_info, using GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE...")
            
            # Handle gameobject_find_info logic
            if conversation_history is not None and llm_context is not None:
                conversation_history, llm_context, turn_count = self._handle_gameobject_find_logic_conversation(
                    child_info, scene_name, conversation_history, gameobject_find_info, llm_context
                )
                print(f"[OK] Child object {child_info['child_name']}'s gameobject_find_info processing complete, conducted {turn_count} turns of conversation")
            
            return {
                'request': None,
                'has_sorted_target_logic': False,
                'has_sorted_layer_logic': False,
                'has_gameobject_find_logic': True,
                'has_gameobject_instantiate_logic': False,
                'message': f"This child object's information has been fully provided through gameobject_find_info, skipping generate_child_request",
                'turn_count': turn_count
            }
        
        if has_gameobject_instantiate_logic:
            print(f"[SEARCH] Detected child object {child_info['child_name']} has gameobject_instantiate_info, using GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE...")
            
            # Handle gameobject_instantiate_info logic
            if conversation_history is not None and llm_context is not None:
                conversation_history, llm_context, turn_count = self._handle_gameobject_instantiate_logic_conversation(
                    child_info, scene_name, conversation_history, gameobject_instantiate_info, llm_context
                )
                print(f"[OK] Child object {child_info['child_name']}'s gameobject_instantiate_info processing complete, conducted {turn_count} turns of conversation")
            
            return {
                'request': None,
                'has_sorted_target_logic': False,
                'has_sorted_layer_logic': False,
                'has_gameobject_find_logic': False,
                'has_gameobject_instantiate_logic': True,
                'message': f"This child object's information has been fully provided through gameobject_instantiate_info, skipping generate_child_request",
                'turn_count': turn_count
            }
        
        # Child object without special logic, use normal flow
        print(f"[INFO] Child object {child_info['child_name']} has no special logic information, using normal generate_child_request flow")
        
        # Get script source code (handle multiple Mono components)
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # Get child object's scene metadata
        child_scene_meta = self._find_child_gameobject_info(child_id, scene_name, mono_comp_ids)
        
        # Generate normal request
        request = self.TEST_PLAN_CHILD_REQUEST_TEMPLATE.format(
            child_index=child_index,
            parent_name=parent_name,
            child_name=child_name,
            child_id=child_id_replace,
            script_source=combined_script_source,
            child_scene_meta=child_scene_meta['scene_meta'] if child_scene_meta else "// Scene meta data not found"
        )
        
        return {
            'request': request,
            'has_sorted_target_logic': False,
            'has_sorted_layer_logic': False,
            'has_gameobject_find_logic': False,
            'has_gameobject_instantiate_logic': False,
            'message': "Normal generated child object request",
            'turn_count': 0  # Normal request hasn't conducted conversation yet, so turn count is 0
        }
    
    def _find_sorted_target_logic_info(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Find sorted_target_logic_info for specified object"""
        for gobj_info in self.gobj_hierarchy:
            # Check main GameObject
            if gobj_info.get('gameobject_id') == object_id:
                return gobj_info.get('sorted_target_logic_info')
            
            # Check child objects
            for child_info in gobj_info.get('child_mono_comp_info', []):
                if child_info.get('child_id') == object_id:
                    return child_info.get('sorted_target_logic_info')
        return None
    
    def _find_sorted_layer_logic_info(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Find sorted_layer_logic_info for specified object"""
        for gobj_info in self.gobj_hierarchy:
            # Check main GameObject
            if gobj_info.get('gameobject_id') == object_id:
                return gobj_info.get('sorted_layer_logic_info')
            
            # Check child objects
            for child_info in gobj_info.get('child_mono_comp_info', []):
                if child_info.get('child_id') == object_id:
                    return child_info.get('sorted_layer_logic_info')
        return None
    
    def _find_gameobject_find_info(self, object_id: str) -> Optional[List[Dict[str, Any]]]:
        """Find gameobject_find_info for specified object"""
        for gobj_info in self.gobj_hierarchy:
            # Check main GameObject
            if gobj_info.get('gameobject_id') == object_id:
                return gobj_info.get('gameobject_find_info', [])
            
            # Check child objects
            for child_info in gobj_info.get('child_mono_comp_info', []):
                if child_info.get('child_id') == object_id:
                    return child_info.get('gameobject_find_info', [])
        return None
    
    def _find_gameobject_instantiate_info(self, object_id: str) -> Optional[List[Dict[str, Any]]]:
        """Find gameobject_instantiate_info for specified object"""
        for gobj_info in self.gobj_hierarchy:
            # Check main GameObject
            if gobj_info.get('gameobject_id') == object_id:
                return gobj_info.get('gameobject_instantiate_info', [])
            
            # Check child objects
            for child_info in gobj_info.get('child_mono_comp_info', []):
                if child_info.get('child_id') == object_id:
                    return child_info.get('gameobject_instantiate_info', [])
        return None
    
    def _handle_sorted_target_logic_conversation(self, child_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], sorted_target_logic_info: Dict[str, Any], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        Handle sorted_target_logic_info related conversation (supports multi-turn conversation)
        
        Args:
            child_info: Child object information
            scene_name: Scene name
            conversation_history: Conversation history
            sorted_target_logic_info: Sorted target logic information
            llm_context: LLM conversation context
        
        Returns:
            tuple: (Updated conversation history, updated LLM context, conversation turn count)
        """
        child_name = child_info['child_name']
        child_id = child_info['child_id']
        child_id_replace = child_info['child_id_replace']
        mono_comp_ids = child_info['mono_comp_targets']
        
        print(f"[PROCESS] Starting to process child object {child_name}'s sorted_target_logic_info...")
        
        # Add current child object ID to processed set
        self.processed_object_ids.add(child_id)
        
        # Get script source code
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # Get child object's scene metadata
        child_scene_meta = self._find_child_gameobject_info(child_id, scene_name, mono_comp_ids)
        
        # Get needed GameObject ID list from sorted_target_logic_info
        # sorted_target_logic_info is a list, each element contains id, gameobject_name, tag_name and other fields
        needed_gameobject_ids = []
        if isinstance(sorted_target_logic_info, list):
            self.processed_object_ids.update([item.get('id') for item in sorted_target_logic_info if item.get('id')])
            needed_gameobject_ids = [item.get('id') for item in sorted_target_logic_info if item.get('id')]
        
        # Get script source code and scene metadata for these GameObjects
        script_sources_and_meta = self._get_formatted_script_sources_and_meta(sorted_target_logic_info, scene_name)
        
        # Use TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW to generate request
        request = self.TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW.format(
            child_name=child_name,
            child_id=child_id_replace,
            parent_name=child_info['parent_info']['parent_name'],
            combined_script_source=combined_script_source,
            child_scene_meta=child_scene_meta['scene_meta'] if child_scene_meta else "// Scene meta data not found",
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # Send request to conversation history
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='sorted_target_logic_request',
            child_info=child_info,
            sorted_target_logic_info=sorted_target_logic_info
        )
        
        # Call LLM API to get response (pass conversation context)
        tag_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # Use general method to handle response
        need_more_info, turn_count = self._handle_llm_response(
            tag_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_sorted_layer_logic_conversation(self, child_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], sorted_layer_logic_info: Dict[str, Any], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        Handle sorted_layer_logic_info related conversation (supports multi-turn conversation)
        
        Args:
            child_info: Child object information
            scene_name: Scene name
            conversation_history: Conversation history
            sorted_layer_logic_info: Sorted layer logic information
            llm_context: LLM conversation context
        
        Returns:
            tuple: (Updated conversation history, updated LLM context, conversation turn count)
        """
        child_name = child_info['child_name']
        child_id = child_info['child_id']
        child_id_replace = child_info['child_id_replace']
        mono_comp_ids = child_info['mono_comp_targets']
        
        print(f"[PROCESS] Starting to process child object {child_name}'s sorted_layer_logic_info...")
        
        # Add current child object ID to processed set
        self.processed_object_ids.add(child_id)
        
        # Get script source code
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # Get child object's scene metadata
        child_scene_meta = self._find_child_gameobject_info(child_id, scene_name, mono_comp_ids)
        
        # Get needed GameObject ID list from sorted_layer_logic_info
        # sorted_layer_logic_info is a list, each element contains id, gameobject_name, layer_name and other fields
        needed_gameobject_ids = []
        if isinstance(sorted_layer_logic_info, list):
            self.processed_object_ids.update([item.get('id') for item in sorted_layer_logic_info if item.get('id')])
            needed_gameobject_ids = [item.get('id') for item in sorted_layer_logic_info if item.get('id')]
        
        # Get script source code and scene metadata for these GameObjects
        script_sources_and_meta = self._get_formatted_script_sources_and_meta(sorted_layer_logic_info, scene_name)
        
        # Use LAYER_LOGIC_CHILD_REQUEST_TEMPLATE to generate request
        request = self.LAYER_LOGIC_CHILD_REQUEST_TEMPLATE.format(
            child_name=child_name,
            child_id=child_id_replace,
            parent_name=child_info['parent_info']['parent_name'],
            combined_script_source=combined_script_source,
            child_scene_meta=child_scene_meta['scene_meta'] if child_scene_meta else "// Scene meta data not found",
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # Send request to conversation history
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='sorted_layer_logic_request',
            child_info=child_info,
            sorted_layer_logic_info=sorted_layer_logic_info
        )
        
        # Call LLM API to get response (pass conversation context)
        layer_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # Use general method to handle response
        need_more_info, turn_count = self._handle_llm_response(
            layer_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_gameobject_find_logic_conversation(self, child_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], gameobject_find_info: List[Dict[str, Any]], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        Handle gameobject_find_info related conversation (supports multi-turn conversation)
        
        Args:
            child_info: Child object information
            scene_name: Scene name
            conversation_history: Conversation history
            gameobject_find_info: GameObject Find logic information list
            llm_context: LLM conversation context
        
        Returns:
            tuple: (Updated conversation history, updated LLM context, conversation turn count)
        """
        child_name = child_info['child_name']
        child_id = child_info['child_id']
        child_id_replace = child_info['child_id_replace']
        mono_comp_ids = child_info['mono_comp_targets']
        
        print(f"[PROCESS] Starting to process child object {child_name}'s gameobject_find_info...")
        
        # Add current child object ID to processed set
        self.processed_object_ids.add(child_id)
        
        # Get script source code
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # Get child object's scene metadata
        child_scene_meta = self._find_child_gameobject_info(child_id, scene_name, mono_comp_ids)
        
        # Get needed GameObject ID list from gameobject_find_info
        # gameobject_find_info is a list, each element contains source, target, edge_type and other fields
        needed_gameobject_ids = []
        if isinstance(gameobject_find_info, list):
            # Extract all target IDs (these are GameObjects that need interaction)
            needed_gameobject_ids = [item.get('target') for item in gameobject_find_info if item.get('target')]
            self.processed_object_ids.update(needed_gameobject_ids)
        
        # Get script source code and scene metadata for these GameObjects
        script_sources_and_meta = self._get_formatted_script_sources_and_meta_for_find_logic(gameobject_find_info, scene_name)
        
        # Use GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE to generate request
        request = self.GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE.format(
            child_name=child_name,
            child_id=child_id_replace,
            parent_name=child_info['parent_info']['parent_name'],
            combined_script_source=combined_script_source,
            child_scene_meta=child_scene_meta['scene_meta'] if child_scene_meta else "// Scene meta data not found",
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # Send request to conversation history
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='gameobject_find_logic_request',
            child_info=child_info,
            gameobject_find_info=gameobject_find_info
        )
        
        # Call LLM API to get response (pass conversation context)
        find_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # Use general method to handle response
        need_more_info, turn_count = self._handle_llm_response(
            find_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_gameobject_instantiate_logic_conversation(self, child_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], gameobject_instantiate_info: List[Dict[str, Any]], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        Handle gameobject_instantiate_info related conversation (supports multi-turn conversation)
        
        Args:
            child_info: Child object information
            scene_name: Scene name
            conversation_history: Conversation history
            gameobject_instantiate_info: GameObject Instantiate logic information list
            llm_context: LLM conversation context
        
        Returns:
            tuple: (Updated conversation history, updated LLM context, conversation turn count)
        """
        child_name = child_info['child_name']
        child_id = child_info['child_id']
        child_id_replace = child_info['child_id_replace']
        mono_comp_ids = child_info['mono_comp_targets']
        
        print(f"[PROCESS] Starting to process child object {child_name}'s gameobject_instantiate_info...")
        
        # Add current child object ID to processed set
        self.processed_object_ids.add(child_id)
        
        # Get script source code
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # Get child object's scene metadata
        child_scene_meta = self._find_child_gameobject_info(child_id, scene_name, mono_comp_ids)
        
        # Get needed GameObject ID list from gameobject_instantiate_info
        # gameobject_instantiate_info is a list, each element contains source, target, edge_type and other fields
        needed_gameobject_ids = []
        if isinstance(gameobject_instantiate_info, list):
            # Extract all target IDs (these are GameObjects that need interaction)
            needed_gameobject_ids = [item.get('target') for item in gameobject_instantiate_info if item.get('target')]
            self.processed_object_ids.update(needed_gameobject_ids)
        
        # Get script source code and scene metadata for these GameObjects
        script_sources_and_meta = self._get_formatted_script_sources_and_meta_for_instantiate_logic(gameobject_instantiate_info, scene_name)
        
        # Use GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE to generate request
        request = self.GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE.format(
            child_name=child_name,
            child_id=child_id_replace,
            parent_name=child_info['parent_info']['parent_name'],
            combined_script_source=combined_script_source,
            child_scene_meta=child_scene_meta['scene_meta'] if child_scene_meta else "// Scene meta data not found",
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # Send request to conversation history
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='gameobject_instantiate_logic_request',
            child_info=child_info,
            gameobject_instantiate_info=gameobject_instantiate_info
        )
        
        # Call LLM API to get response (pass conversation context)
        instantiate_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # Use general method to handle response
        need_more_info, turn_count = self._handle_llm_response(
            instantiate_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_main_sorted_target_logic_conversation(self, gobj_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], sorted_target_logic_info: Dict[str, Any], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        处理主对象的 sorted_target_logic_info 相关的对话（支持多轮对话）
        
        Args:
            gobj_info: 主GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            sorted_target_logic_info: 排序后的目标逻辑信息
            llm_context: LLM对话上下文
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文, 对话轮数)
        """
        gobj_name = gobj_info['gameobject_name']
        gobj_id = gobj_info['gameobject_id']
        gobj_id_replace = gobj_info['gameobject_id_replace']
        mono_comp_ids = gobj_info.get('mono_comp_relations', [])
        
        print(f"[PROCESS] Starting to process main object {gobj_name}'s sorted_target_logic_info...")
        
        # 将当前主对象ID添加到已处理集合中
        self.processed_object_ids.add(gobj_id)
        
        # 获取脚本源代码
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # 获取主对象的场景元数据
        gobj_scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, mono_comp_ids)
        
        # 从sorted_target_logic_info中获取需要的GameObject ID列表
        needed_gameobject_ids = []
        if isinstance(sorted_target_logic_info, list):
            self.processed_object_ids.update([item.get('id') for item in sorted_target_logic_info if item.get('id')])
            needed_gameobject_ids = [item.get('id') for item in sorted_target_logic_info if item.get('id')]
        
        # 获取这些GameObject的脚本源代码和场景元数据
        script_sources_and_meta = self._get_formatted_script_sources_and_meta(sorted_target_logic_info, scene_name)
        
        # 使用 TAG_LOGIC_MAIN_REQUEST_TEMPLATE 生成请求
        request = self.TAG_LOGIC_MAIN_REQUEST_TEMPLATE.format(
            gobj_name=gobj_name,
            gobj_id=gobj_id_replace,
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # 发送请求到对话历史
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='main_sorted_target_logic_request',
            gobj_info=gobj_info,
            sorted_target_logic_info=sorted_target_logic_info
        )
        
        # 调用LLM API获取响应（传递对话上下文）
        tag_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # 使用通用方法处理响应
        need_more_info, turn_count = self._handle_llm_response(
            tag_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_main_sorted_layer_logic_conversation(self, gobj_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], sorted_layer_logic_info: Dict[str, Any], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        处理主对象的 sorted_layer_logic_info 相关的对话（支持多轮对话）
        
        Args:
            gobj_info: 主GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            sorted_layer_logic_info: 排序后的layer逻辑信息
            llm_context: LLM对话上下文
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文, 对话轮数)
        """
        gobj_name = gobj_info['gameobject_name']
        gobj_id = gobj_info['gameobject_id']
        gobj_id_replace = gobj_info['gameobject_id_replace']
        mono_comp_ids = gobj_info.get('mono_comp_relations', [])
        
        print(f"[PROCESS] Starting to process main object {gobj_name}'s sorted_layer_logic_info...")
        
        # 将当前主对象ID添加到已处理集合中
        self.processed_object_ids.add(gobj_id)
        
        # 获取脚本源代码
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # 获取主对象的场景元数据
        gobj_scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, mono_comp_ids)
        
        # 从sorted_layer_logic_info中获取需要的GameObject ID列表
        needed_gameobject_ids = []
        if isinstance(sorted_layer_logic_info, list):
            self.processed_object_ids.update([item.get('id') for item in sorted_layer_logic_info if item.get('id')])
            needed_gameobject_ids = [item.get('id') for item in sorted_layer_logic_info if item.get('id')]
        
        # 获取这些GameObject的脚本源代码和场景元数据
        script_sources_and_meta = self._get_formatted_script_sources_and_meta(sorted_layer_logic_info, scene_name)
        
        # 使用 LAYER_LOGIC_MAIN_REQUEST_TEMPLATE 生成请求
        request = self.LAYER_LOGIC_MAIN_REQUEST_TEMPLATE.format(
            gobj_name=gobj_name,
            gobj_id=gobj_id_replace,
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # 发送请求到对话历史
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='main_sorted_layer_logic_request',
            gobj_info=gobj_info,
            sorted_layer_logic_info=sorted_layer_logic_info
        )
        
        # 调用LLM API获取响应（传递对话上下文）
        layer_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # 使用通用方法处理响应
        need_more_info, turn_count = self._handle_llm_response(
            layer_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_main_gameobject_find_logic_conversation(self, gobj_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], gameobject_find_info: List[Dict[str, Any]], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        处理主对象的 gameobject_find_info 相关的对话（支持多轮对话）
        
        Args:
            gobj_info: 主GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            gameobject_find_info: GameObject Find逻辑信息列表
            llm_context: LLM对话上下文
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文, 对话轮数)
        """
        gobj_name = gobj_info['gameobject_name']
        gobj_id = gobj_info['gameobject_id']
        gobj_id_replace = gobj_info['gameobject_id_replace']
        mono_comp_ids = gobj_info.get('mono_comp_relations', [])
        
        print(f"[PROCESS] Starting to process main object {gobj_name}'s gameobject_find_info...")
        
        # 将当前主对象ID添加到已处理集合中
        self.processed_object_ids.add(gobj_id)
        
        # 获取脚本源代码
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # 获取主对象的场景元数据
        gobj_scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, mono_comp_ids)
        
        # 从gameobject_find_info中获取需要的GameObject ID列表
        needed_gameobject_ids = []
        if isinstance(gameobject_find_info, list):
            needed_gameobject_ids = [item.get('target') for item in gameobject_find_info if item.get('target')]
            self.processed_object_ids.update(needed_gameobject_ids)
        
        # 获取这些GameObject的脚本源代码和场景元数据
        script_sources_and_meta = self._get_formatted_script_sources_and_meta_for_find_logic(gameobject_find_info, scene_name)
        
        # 使用 GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE 生成请求
        request = self.GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE.format(
            gobj_name=gobj_name,
            gobj_id=gobj_id_replace,
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # 发送请求到对话历史
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='main_gameobject_find_logic_request',
            gobj_info=gobj_info,
            gameobject_find_info=gameobject_find_info
        )
        
        # 调用LLM API获取响应（传递对话上下文）
        find_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # 使用通用方法处理响应
        need_more_info, turn_count = self._handle_llm_response(
            find_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _handle_main_gameobject_instantiate_logic_conversation(self, gobj_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], gameobject_instantiate_info: List[Dict[str, Any]], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
        """
        处理主对象的 gameobject_instantiate_info 相关的对话（支持多轮对话）
        
        Args:
            gobj_info: 主GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            gameobject_instantiate_info: GameObject Instantiate逻辑信息列表
            llm_context: LLM对话上下文
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文, 对话轮数)
        """
        gobj_name = gobj_info['gameobject_name']
        gobj_id = gobj_info['gameobject_id']
        gobj_id_replace = gobj_info['gameobject_id_replace']
        mono_comp_ids = gobj_info.get('mono_comp_relations', [])
        
        print(f"[PROCESS] Starting to process main object {gobj_name}'s gameobject_instantiate_info...")
        
        # 将当前主对象ID添加到已处理集合中
        self.processed_object_ids.add(gobj_id)
        
        # 获取脚本源代码
        combined_script_source = self._build_script_content(mono_comp_ids)
        
        # 获取主对象的场景元数据
        gobj_scene_meta = self._extract_scene_meta_info(gobj_id, scene_name, mono_comp_ids)
        
        # 从gameobject_instantiate_info中获取需要的GameObject ID列表
        needed_gameobject_ids = []
        if isinstance(gameobject_instantiate_info, list):
            needed_gameobject_ids = [item.get('target') for item in gameobject_instantiate_info if item.get('target')]
            self.processed_object_ids.update(needed_gameobject_ids)
        
        # 获取这些GameObject的脚本源代码和场景元数据
        script_sources_and_meta = self._get_formatted_script_sources_and_meta_for_instantiate_logic(gameobject_instantiate_info, scene_name)
        
        # 使用 GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE 生成请求
        request = self.GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE.format(
            gobj_name=gobj_name,
            gobj_id=gobj_id_replace,
            needed_gameobject_ids=needed_gameobject_ids,
            script_sources_and_meta=script_sources_and_meta
        )
        
        # 发送请求到对话历史
        self._add_conversation_message(
            conversation_history, 'user', request,
            llm_context=llm_context,
            request_type='main_gameobject_instantiate_logic_request',
            gobj_info=gobj_info,
            gameobject_instantiate_info=gameobject_instantiate_info
        )
        
        # 调用LLM API获取响应（传递对话上下文）
        instantiate_response = self._call_llm_api(request, llm_context, llm_model=llm_model)
        
        # 使用通用方法处理响应
        need_more_info, turn_count = self._handle_llm_response(
            instantiate_response, conversation_history, llm_context, request,
            response_type='test_plan_response'
        )
        
        return conversation_history, llm_context, turn_count
    
    def _get_formatted_script_sources_and_meta_for_find_logic(self, gameobject_find_info: List[Dict[str, Any]], scene_name: str) -> str:
        """
        获取指定GameObject的脚本源代码和场景元数据，格式化输出（用于gameobject_find_info）
        
        Args:
            gameobject_find_info: gameobject_find_info列表，每个元素包含source、target、edge_type、target_gameobject_name等字段
            scene_name: 场景名称
        
        Returns:
            str: 格式化的脚本源代码和场景元数据
        """
        result = ""
        
        # 遍历gameobject_find_info列表，每个元素包含target和target_gameobject_name
        for i, find_item in enumerate(gameobject_find_info):
            target_id = find_item.get('target')
            target_id_replace = find_item.get('target_replace')
            target_gameobject_name = find_item.get('target_gameobject_name', 'Unknown')
            
            if not target_id:
                print(f"[WARN]  Target GameObject ID not found")
                continue
            
            # 直接使用target_gameobject_name字段
            gobj_name = target_gameobject_name
            
            # 为每个 GameObject 添加分隔符和标题
            if i > 0:
                result += "\n"
            
            result += f"""GameObject ID: "{target_id_replace}" GameObject Name: "{gobj_name}":\n"""
            
            # 获取该 GameObject 的脚本源代码
            script_source = ""
            found_mono_comp = False
            if scene_name in self.scene_meta_data:
                scene_graph = self.scene_meta_data[scene_name]   
                # 查找以target_id为source的Has_Mono_Comp关系
                for source, target, edge_data in scene_graph.edges(data=True):
                    if (edge_data.get('type') == 'Has_Mono_Comp' and 
                        source == target_id):                        
                        # 找到Has_Mono_Comp关系，使用target调用_extract_script_source_code
                        mono_comp_id = target
                        found_mono_comp = True
                        extracted_script = self._extract_script_source_code(mono_comp_id)
                        if extracted_script:
                            script_source += extracted_script
            
            if script_source:
                result += "[Source code of script files attached]\n"
                result += "'''\n"
                result += script_source
                result += "\n'''\n"
            else:
                if found_mono_comp:
                    result += "[Source code of script files attached]\n"
                    result += "// Script source code not found for this GameObject\n"
            
            result += "\n"
            
            # 获取该 GameObject 的场景元数据
            # 使用 _extract_scene_meta_info 方法获取场景元数据
            scene_meta = self._extract_scene_meta_info(target_id, scene_name, [])
            if scene_meta:
                result += "[Source code of scene meta file]\n"
                result += "'''\n"
                result += scene_meta
                result += "\n'''\n"
            else:
                result += "[Source code of scene meta file]\n"
                result += "// Scene meta data not found for this GameObject\n"
            
            result += "\n"
        
        return result
    
    def _get_formatted_script_sources_and_meta_for_instantiate_logic(self, gameobject_instantiate_info: List[Dict[str, Any]], scene_name: str) -> str:
        """
        获取指定GameObject的脚本源代码和场景元数据，格式化输出（用于gameobject_instantiate_info）
        
        Args:
            gameobject_instantiate_info: gameobject_instantiate_info列表，每个元素包含source、target、edge_type、target_gameobject_name等字段
            scene_name: 场景名称
        
        Returns:
            str: 格式化的脚本源代码和场景元数据
        """
        result = ""
        
        # 遍历gameobject_instantiate_info列表，每个元素包含target和target_gameobject_name
        for i, instantiate_item in enumerate(gameobject_instantiate_info):
            target_id = instantiate_item.get('target')
            target_id_replace = instantiate_item.get('target_replace')
            target_gameobject_name = instantiate_item.get('target_gameobject_name', 'Unknown')
            
            if not target_id:
                print(f"[WARN]  Target GameObject ID not found")
                continue
            
            # 直接使用target_gameobject_name字段
            gobj_name = target_gameobject_name
            
            # 为每个 GameObject 添加分隔符和标题
            if i > 0:
                result += "\n"
            
            result += f"""GameObject ID: "{target_id_replace}" GameObject Name: "{gobj_name}":\n"""
            
            # 获取该 GameObject 的脚本源代码
            script_source = ""
            found_mono_comp = False
            if scene_name in self.scene_meta_data:
                scene_graph = self.scene_meta_data[scene_name]   
                # 查找以target_id为source的Has_Mono_Comp关系
                for source, target, edge_data in scene_graph.edges(data=True):
                    if (edge_data.get('type') == 'Has_Mono_Comp' and 
                        source == target_id):                        
                        # 找到Has_Mono_Comp关系，使用target调用_extract_script_source_code
                        mono_comp_id = target
                        found_mono_comp = True
                        extracted_script = self._extract_script_source_code(mono_comp_id)
                        if extracted_script:
                            script_source += extracted_script
            
            if script_source:
                result += "[Source code of script files attached]\n"
                result += "'''\n"
                result += script_source
                result += "\n'''\n"
            else:
                if found_mono_comp:
                    result += "[Source code of script files attached]\n"
                    result += "// Script source code not found for this GameObject\n"
            
            result += "\n"
            
            # 获取该 GameObject 的场景元数据
            # 使用 _extract_scene_meta_info 方法获取场景元数据
            scene_meta = self._extract_scene_meta_info(target_id, scene_name, [])
            if scene_meta:
                result += "[Source code of scene meta file]\n"
                result += "'''\n"
                result += scene_meta
                result += "\n'''\n"
            else:
                result += "[Source code of scene meta file]\n"
                result += "// Scene meta data not found for this GameObject\n"
            
            result += "\n"
        
        return result
    
    def generate_test_plan_conversation(self, gobj_info: Dict[str, Any], scene_name: str, max_runs: int = 3, llm_model: str = 'gpt-5') -> List[Dict[str, Any]]:
        """
        Generate complete test plan conversation for specified GameObject (multi-turn conversation based on child object processing count)
        
        Args:
            gobj_info: GameObject information
            scene_name: Scene name
            max_runs: Maximum rounds for child object processing (will rebuild LLM connection if exceeded)
        
        Returns:
            List[Dict]: Conversation history
        """
        print(f"[START] Starting multi-turn conversation based on child object processing count, maximum child object processing rounds: {max_runs}")
        
        all_conversation_history = []
        llm_context = []  # LLM context
        conversation_turn_count = 0  # Conversation turn counter
        
        # Generate first request for main object
        first_request = self.generate_first_request(gobj_info, scene_name)
        self._add_conversation_message(
            all_conversation_history, 'user', first_request,
            llm_context=llm_context,
            request_type='first_request'
        )
        
        # Call LLM API to get first response
        print(f"[BOT] Generating first test plan for GameObject '{gobj_info['gameobject_name']}'...")
        first_response = self._call_llm_api(first_request, llm_context, llm_model=llm_model)

        need_more_info, turn_count = self._handle_llm_response(
                    first_response, all_conversation_history, llm_context, first_request,
                    response_type='test_plan_response'
                )
        
        conversation_turn_count += turn_count
        
        if first_response:
            # 将first_request和first_response添加到llm_context中
            llm_context.append({'role': 'user', 'content': first_request})
            llm_context.append({'role': 'assistant', 'content': first_response})
            
            # Check if main object has special logic information
            gobj_id = gobj_info.get('gameobject_id')
            sorted_target_logic_info = self._find_sorted_target_logic_info(gobj_id)
            sorted_layer_logic_info = self._find_sorted_layer_logic_info(gobj_id)
            gameobject_find_info = self._find_gameobject_find_info(gobj_id)
            gameobject_instantiate_info = self._find_gameobject_instantiate_info(gobj_id)
            
            has_sorted_target_logic = sorted_target_logic_info is not None and len(sorted_target_logic_info) > 0
            has_sorted_layer_logic = sorted_layer_logic_info is not None and len(sorted_layer_logic_info) > 0
            has_gameobject_find_logic = gameobject_find_info is not None and len(gameobject_find_info) > 0
            has_gameobject_instantiate_logic = gameobject_instantiate_info is not None and len(gameobject_instantiate_info) > 0
            
            # Handle main object's special logic information
            if has_sorted_target_logic:
                print(f"[SEARCH] Detected main object {gobj_info['gameobject_name']} has sorted_target_logic_info, starting processing...")
                all_conversation_history, llm_context, turn_count = self._handle_main_sorted_target_logic_conversation(
                    gobj_info, scene_name, all_conversation_history, sorted_target_logic_info, llm_context
                )
                conversation_turn_count += turn_count
                print(f"[OK] Main object {gobj_info['gameobject_name']}'s sorted_target_logic_info processing complete, conducted {turn_count} turns of conversation")
            
            if has_sorted_layer_logic:
                print(f"[SEARCH] Detected main object {gobj_info['gameobject_name']} has sorted_layer_logic_info, starting processing...")
                all_conversation_history, llm_context, turn_count = self._handle_main_sorted_layer_logic_conversation(
                    gobj_info, scene_name, all_conversation_history, sorted_layer_logic_info, llm_context
                )
                conversation_turn_count += turn_count
                print(f"[OK] Main object {gobj_info['gameobject_name']}'s sorted_layer_logic_info processing complete, conducted {turn_count} turns of conversation")
            
            if has_gameobject_find_logic:
                print(f"[SEARCH] Detected main object {gobj_info['gameobject_name']} has gameobject_find_info, starting processing...")
                all_conversation_history, llm_context, turn_count = self._handle_main_gameobject_find_logic_conversation(
                    gobj_info, scene_name, all_conversation_history, gameobject_find_info, llm_context
                )
                conversation_turn_count += turn_count
                print(f"[OK] Main object {gobj_info['gameobject_name']}'s gameobject_find_info processing complete, conducted {turn_count} turns of conversation")
            
            if has_gameobject_instantiate_logic:
                print(f"[SEARCH] Detected main object {gobj_info['gameobject_name']} has gameobject_instantiate_info, starting processing...")
                all_conversation_history, llm_context, turn_count = self._handle_main_gameobject_instantiate_logic_conversation(
                    gobj_info, scene_name, all_conversation_history, gameobject_instantiate_info, llm_context
                )
                conversation_turn_count += turn_count
                print(f"[OK] Main object {gobj_info['gameobject_name']}'s gameobject_instantiate_info processing complete, conducted {turn_count} turns of conversation")
            
            # Check if there are child object relationships
            child_relations = gobj_info.get('child_relations', [])
            has_children = len(child_relations) > 0
            
            if has_children:                
                print(f"[INFO] Has child objects, starting to process child object information...")
                
                # Process all child objects - first sort child objects, prioritize child nodes with special logic
                child_mono_comp_info = gobj_info.get('child_mono_comp_info', [])
                child_mono_comp_info = self._sort_children_by_special_logic(child_mono_comp_info)
                
                for i, child_info in enumerate(child_mono_comp_info, 1):
                    child_id = child_info['child_id']
                    child_name = child_info['child_name']
                    
                    print(f"[SEND] Processing child object {i}: {child_name}")
                    
                    # Check if this child object has already been processed and doesn't contain special logic information
                    if child_id in self.processed_object_ids:
                        # Check if it contains sorted_target_logic_info, sorted_layer_logic_info or gameobject_find_info
                        sorted_target_logic_info = self._find_sorted_target_logic_info(child_id)
                        sorted_layer_logic_info = self._find_sorted_layer_logic_info(child_id)
                        gameobject_find_info = self._find_gameobject_find_info(child_id)
                        has_special_logic = (sorted_target_logic_info is not []) or (sorted_layer_logic_info is not []) or (gameobject_find_info is not None and len(gameobject_find_info) > 0)
                        
                        if not has_special_logic:
                            print(f"[SKIP]  Skipping child object {child_name} (ID: {child_id}), already processed and doesn't contain special logic information")
                            # Add skip information to conversation history
                            self._add_conversation_message(
                                all_conversation_history, 'system',
                                f"Skipping child object {child_name} (ID: {child_id}), already processed and doesn't contain special logic information",
                                llm_context=llm_context,
                                response_type='skipped_object_info',
                                skipped_object_id=child_id,
                                skipped_object_name=child_name,
                                skip_reason='already_processed_no_special_logic'
                            )
                            continue
                        else:
                            print(f"[PROCESS] Child object {child_name} (ID: {child_id}) already processed but contains special logic information, continuing processing")
                    
                    # Check if conversation turn count exceeds max_runs
                    if conversation_turn_count >= max_runs:
                        print(f"[PROCESS] Conversation turn count has reached {max_runs}, rebuilding LLM connection...")
                        # Rebuild LLM connection, context contains conversation information of main object and remaining child objects
                        llm_context = self._rebuild_llm_context(all_conversation_history, gobj_info, child_mono_comp_info[i-1:])
                        conversation_turn_count = 0
                    
                    # Generate child object request and handle sorted_target_logic_info, sorted_layer_logic_info logic
                    child_request_result = self.generate_child_request(child_info, i, scene_name, all_conversation_history, llm_context)
                    
                    if child_request_result['has_sorted_target_logic'] or child_request_result['has_sorted_layer_logic'] or child_request_result['has_gameobject_find_logic'] or child_request_result['has_gameobject_instantiate_logic']:
                        # If has special logic information, already processed through generate_child_request
                        conversation_turn_count += child_request_result.get('turn_count', 1)
                        continue
                    
                    # Child object without special logic information, use normal flow
                    child_request = child_request_result['request']
                    
                    self._add_conversation_message(
                        all_conversation_history, 'user', child_request,
                        llm_context=llm_context,
                        request_type='child_request', child_index=i, child_info=child_info
                    )
                    
                    # Call LLM API to get child object response (pass conversation context)
                    child_response = self._call_llm_api(child_request, llm_context, llm_model=llm_model)
                    
                    # Use general method to handle response
                    need_more_info, turn_count = self._handle_llm_response(
                        child_response, all_conversation_history, llm_context, child_request,
                        response_type='test_plan_response'
                    )
                    
                    conversation_turn_count += turn_count
                
                print(f"[OK] All child objects processing complete, conducted {conversation_turn_count} turns of conversation")
    
        else:
            print(f"[ERROR] Failed to get LLM response for GameObject '{gobj_info['gameobject_name']}'")
            self._add_conversation_message(
                all_conversation_history, 'assistant',
                f"Error: Failed to get LLM response for GameObject {gobj_info['gameobject_name']}",
                llm_context=llm_context,
                response_type='error', need_more_info=True
            )
        
        print(f"[DONE] GameObject '{gobj_info['gameobject_name']}' test plan generation complete, conducted {conversation_turn_count} turns of conversation")
        return all_conversation_history
    
    def _handle_child_conversation(self, gobj_info: Dict[str, Any], scene_name: str, conversation_history: List[Dict[str, Any]], llm_context: List[Dict[str, str]], llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        处理子对象的对话（支持多轮对话）
        
        Args:
            gobj_info: GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            llm_context: LLM对话上下文
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文)
        """
        # 处理子对象的Mono组件信息 - 先对子对象进行排序，将含有特殊逻辑的子节点优先处理
        child_mono_comp_info = gobj_info.get('child_mono_comp_info', [])
        child_mono_comp_info = self._sort_children_by_special_logic(child_mono_comp_info)
        
        # 从对话历史中提取已经通过sorted_target_logic_info处理过的对象ID
        processed_object_ids = set()
        for msg in conversation_history:
            if msg.get('response_type') == 'processed_objects_info' and 'processed_object_ids' in msg:
                processed_object_ids.update(msg['processed_object_ids'])
        
        if processed_object_ids:
            print(f"[SEARCH] Found object IDs already processed through sorted_target_logic_info: {list(processed_object_ids)}")
        
        for i, child_info in enumerate(child_mono_comp_info, 1):
            child_id = child_info['child_id']
            child_name = child_info['child_name']
            
            # 检查该子对象是否已经在sorted_target_logic_info中被处理过
            if child_id in processed_object_ids:
                print(f"[SKIP]  Skipping child object {child_name} (ID: {child_id}), already processed in sorted_target_logic_info")
                conversation_history.append({
                    'role': 'system',
                    'content': f"跳过子对象 {child_name} (ID: {child_id})，已在sorted_target_logic_info中处理过",
                    'response_type': 'skipped_object_info',
                    'skipped_object_id': child_id,
                    'skipped_object_name': child_name,
                    'timestamp': datetime.now().isoformat()
                })
                continue
            
            print(f"[SEND] Providing child object {i} information: {child_name}")
            
            # 生成子对象请求，并处理sorted_target_logic_info逻辑
            child_request_result = self.generate_child_request(child_info, i, scene_name, conversation_history, llm_context)
            
            if child_request_result['has_sorted_target_logic'] or child_request_result['has_gameobject_find_logic'] or child_request_result['has_gameobject_instantiate_logic']:
                # 如果有特殊逻辑信息，已经通过generate_child_request处理完成
                print(f"[INFO] {child_request_result['message']}")
                continue
            
            # 没有特殊逻辑信息的子对象，使用正常的流程
            child_request = child_request_result['request']
            print(f"[INFO] {child_request_result['message']}")
            
            conversation_history.append({
                'role': 'user',
                'content': child_request,
                'request_type': 'child_request',
                'child_index': i,
                'child_info': child_info,
                'timestamp': datetime.now().isoformat()
            })
            
            # 调用LLM API获取子对象响应（传递对话上下文）
            child_response = self._call_llm_api(child_request, llm_context, llm_model=llm_model)
            
            if child_response:
                # 将响应添加到LLM上下文
                llm_context.append({'role': 'user', 'content': child_request})
                llm_context.append({'role': 'assistant', 'content': child_response})
                
                # 解析LLM响应
                parsed_child_response = self._parse_llm_response(child_response)
                
                # 如果子对象需要更多信息，启用多轮对话
                if parsed_child_response['need_more_info']:
                    print(f"[INFO] Child object {child_name} needs more information, enabling multi-turn conversation...")
                    # 使用多轮对话来完善子对象的测试计划
                    final_child_response, llm_context, multi_turn_count = self._handle_multi_turn_conversation(
                        child_request, max_turns=3, llm_context=llm_context
                    )
                    
                    # 记录多轮对话的最终结果
                    conversation_history.append({
                        'role': 'assistant',
                        'content': final_child_response,
                        'response_type': 'test_plan_response',
                        'need_more_info': False,  # 多轮对话后应该完成
                        'test_plan': self._parse_llm_response(final_child_response)['test_plan'],
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"[OK] Child object {child_name} multi-turn conversation complete")
                else:
                    conversation_history.append({
                        'role': 'assistant',
                        'content': child_response,
                        'response_type': 'test_plan_response',
                        'need_more_info': parsed_child_response['need_more_info'],
                        'test_plan': parsed_child_response['test_plan'],
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"[OK] Child object {child_name} has obtained sufficient information")
                
                # 继续处理下一个子对象
                if i < len(child_mono_comp_info):
                    print(f"[INFO] Continuing to process next child object...")
                    continue
                else:
                    print(f"[OK] All child objects processed, test plan generation complete")
                    break
            else:
                print(f"[ERROR] Failed to get LLM response for child object {child_name}")
                # 添加错误响应到对话历史
                conversation_history.append({
                    'role': 'assistant',
                    'content': f"Error: Failed to get LLM response for child object {child_name}",
                    'return': 'error',
                    'timestamp': datetime.now().isoformat()
                })
        
        return conversation_history, llm_context
    
    def _get_remaining_children(self, gobj_info: Dict[str, Any], processed_children: set) -> List[Dict[str, Any]]:
        """获取未处理的子对象列表，并对其进行排序，将含有特殊逻辑的子节点优先处理"""
        remaining_children = [child_info for child_info in gobj_info.get('child_mono_comp_info', [])
                              if child_info['child_id'] not in processed_children]
        return self._sort_children_by_special_logic(remaining_children)
    
    def _handle_remaining_children_conversation(self, gobj_info: Dict[str, Any], scene_name: str, 
                                             conversation_history: List[Dict[str, Any]], 
                                             llm_context: List[Dict[str, str]], 
                                             remaining_children: List[Dict[str, Any]], 
                                             run_number: int,
                                             llm_model: str = 'gpt-5') -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        处理剩余子对象的对话
        
        Args:
            gobj_info: GameObject信息
            scene_name: 场景名称
            conversation_history: 对话历史记录
            llm_context: LLM对话上下文
            remaining_children: 剩余的子对象列表
            run_number: 当前运行轮数
        
        Returns:
            tuple: (更新后的对话历史记录, 更新后的LLM上下文)
        """
        for i, child_info in enumerate(remaining_children, 1):
            child_id = child_info['child_id']
            child_name = child_info['child_name']
            
            print(f"[SEND] Round {run_number}: Providing child object {i} information: {child_name}")
            
            # 生成子对象请求，并处理sorted_target_logic_info逻辑
            child_request_result = self.generate_child_request(child_info, i, scene_name, conversation_history, llm_context)
            
            if child_request_result['has_sorted_target_logic'] or child_request_result['has_gameobject_find_logic'] or child_request_result['has_gameobject_instantiate_logic']:
                # 如果有特殊逻辑信息，已经通过generate_child_request处理完成
                print(f"[INFO] Round {run_number}: {child_request_result['message']}")
                continue
            
            # Child object without special logic information, use normal flow
            child_request = child_request_result['request']
            print(f"[INFO] Round {run_number}: {child_request_result['message']}")
            
            conversation_history.append({
                'role': 'user',
                'content': child_request,
                'request_type': 'child_request',
                'child_index': i,
                'child_info': child_info,
                'run_number': run_number,
                'timestamp': datetime.now().isoformat()
            })
            
            # 调用LLM API获取子对象响应（传递对话上下文）
            child_response = self._call_llm_api(child_request, llm_context, llm_model=llm_model)
            
            if child_response:
                # 将响应添加到LLM上下文
                llm_context.append({'role': 'user', 'content': child_request})
                llm_context.append({'role': 'assistant', 'content': child_response})
                
                # 解析LLM响应
                parsed_child_response = self._parse_llm_response(child_response)
                
                # 如果子对象需要更多信息，启用多轮对话
                if parsed_child_response['need_more_info']:
                    print(f"[INFO] Round {run_number}: Child object {child_name} needs more information, enabling multi-turn conversation...")
                    # 使用多轮对话来完善子对象的测试计划
                    final_child_response, llm_context, multi_turn_count = self._handle_multi_turn_conversation(
                        child_request, max_turns=3, llm_context=llm_context
                    )
                    
                    # 记录多轮对话的最终结果
                    conversation_history.append({
                        'role': 'assistant',
                        'content': final_child_response,
                        'response_type': 'test_plan_response',
                        'need_more_info': False,
                        'test_plan': self._parse_llm_response(final_child_response)['test_plan'],
                        'run_number': run_number,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"[OK] Round {run_number}: Child object {child_name} multi-turn conversation complete")
                else:
                    conversation_history.append({
                        'role': 'assistant',
                        'content': child_response,
                        'response_type': 'test_plan_response',
                        'need_more_info': parsed_child_response['need_more_info'],
                        'test_plan': parsed_child_response['test_plan'],
                        'run_number': run_number,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"[OK] Round {run_number}: Child object {child_name} has obtained sufficient information")
            else:
                print(f"[ERROR] Round {run_number}: Failed to get LLM response for child object {child_name}")
                conversation_history.append({
                    'role': 'assistant',
                    'content': f"Error: Failed to get LLM response for child {child_name}",
                    'response_type': 'error',
                    'need_more_info': True,
                    'run_number': run_number,
                    'timestamp': datetime.now().isoformat()
                })
        
        return conversation_history, llm_context

    def _handle_multi_turn_conversation(self, initial_prompt: str, max_turns: int = 3, llm_context: List[Dict[str, str]] = None, llm_model: str = 'gpt-5') -> tuple[str, List[Dict[str, str]], int]:
        """
        Handle multi-turn conversation, iterate based on LLM response (no feedback prompts provided)
        
        Args:
            initial_prompt: Initial prompt
            max_turns: Maximum conversation turns
            llm_context: LLM conversation context
        
        Returns:
            tuple: (Final response, updated LLM context, actual conversation turn count)
        """
        if llm_context is None:
            llm_context = []
        
        current_prompt = initial_prompt
        current_turns = 0
        
        while current_turns < max_turns:
            print(f"[PROCESS] Multi-turn conversation round {current_turns + 1}...")
            
            # Call LLM API
            response = self._call_llm_api(current_prompt, llm_context, llm_model=llm_model)
            
            if not response:
                print("[ERROR] LLM response failed, ending multi-turn conversation")
                break
            
            # Add response to LLM context
            llm_context.append({'role': 'user', 'content': current_prompt})
            llm_context.append({'role': 'assistant', 'content': response})
            
            # Parse response, check if more information is needed
            parsed_response = self._parse_llm_response(response)
            
            if not parsed_response['need_more_info']:
                print("[OK] LLM has obtained sufficient information, multi-turn conversation complete")
                return response, llm_context, current_turns + 1
            
            # If more information is needed, use simple prompt to continue conversation
            if current_turns < max_turns - 1:
                current_turns += 1
            else:
                print("[INFO] Reached maximum conversation turns, ending multi-turn conversation")
                break
        
        print(f"[INFO] Multi-turn conversation ended, conducted {current_turns + 1} turns")
        return response if 'response' in locals() else "", llm_context, current_turns + 1
    
    
    def generate_all_test_plans(self, scene_name: str = None, max_runs: int = 3, is_duplicate: bool = False, llm_model: str = 'gpt-5') -> Dict[str, Any]:
        """
        Generate test plan conversations for all GameObjects (multi-turn conversation based on child object processing count)
        
        Args:
            scene_name: Scene name, if None then use first available scene
            max_runs: Maximum rounds for child object processing (will rebuild LLM connection if exceeded)
        
        Returns:
            Dict: Results containing all test plan conversations
        """
        if scene_name is None:
            scene_name = self.scene_name
        
        print(f"[START] Starting to generate test plans for all GameObjects in scene '{scene_name}'...")
        print(f"[INFO] Maximum child object processing rounds: {max_runs} (will rebuild LLM connection if exceeded)")
        
        all_test_plans = {
            'scene_name': scene_name,
            'generated_at': datetime.now().isoformat(),
            'max_runs': max_runs,
            'gameobjects': []
        }

        safe_scene_name = self._sanitize_filename(scene_name)
        llm_responses_dir = os.path.join(self.results_dir, 'llm_responses', llm_model, safe_scene_name)
        if os.path.exists(llm_responses_dir):
            shutil.rmtree(llm_responses_dir)
        os.makedirs(llm_responses_dir, exist_ok=False)
        
        # Iterate through all GameObjects
        for gobj_index, gobj_info in enumerate(self.gobj_hierarchy, 1):
            gobj_id = gobj_info.get('gameobject_id')
            gobj_name = gobj_info.get('gameobject_name')
            
            print(f"\n[INFO] Processing GameObject {gobj_index}/{len(self.gobj_hierarchy)}: {gobj_name} (ID: {gobj_id})")
            
            # Generate test plan conversation (multi-turn conversation based on child object processing count)
            conversation_history = self.generate_test_plan_conversation(gobj_info, scene_name, max_runs)

            self._save_llm_responses(gobj_info, conversation_history, scene_name, llm_responses_dir)
            
            # Statistics for conversation information
            total_requests = len([msg for msg in conversation_history if msg['role'] == 'user'])
            has_children = len(gobj_info.get('child_relations', [])) > 0
            has_children_with_mono = any(
                child.get('mono_comp_targets') 
                for child in gobj_info.get('child_mono_comp_info', [])
            )
            
            # Statistics for child object processing turns
            child_processing_turns = len([msg for msg in conversation_history 
                                        if msg.get('request_type') == 'child_request' or 
                                           msg.get('request_type') == 'sorted_target_logic_request' or
                                           msg.get('request_type') == 'gameobject_instantiate_logic_request'])
            
            # Add to results
            gobj_plan = {
                'gameobject_id': gobj_id,
                'gameobject_name': gobj_name,
                'gameobject_type': gobj_info.get('gameobject_type', 'Unknown'),
                'total_requests': total_requests,
                'child_processing_turns': child_processing_turns,
                'has_children': has_children,
                'has_children_with_mono': has_children_with_mono,
                'conversation_history': conversation_history
            }
            
            all_test_plans['gameobjects'].append(gobj_plan)
            
            print(f"[OK] GameObject {gobj_name} test plan generation complete")
            print(f"   - Total requests: {total_requests}")
            print(f"   - Child object processing turns: {child_processing_turns}")
            
            # After processing current GameObject, continue processing next main object
            if gobj_index < len(self.gobj_hierarchy):
                print(f"[PROCESS] Continuing to process next main object...")
        
        print(f"\n[SUCCESS] All GameObjects' test plan generation complete!")
        print(f"[STATS] Statistics:")
        print(f"   - Total GameObject count: {len(all_test_plans['gameobjects'])}")
        print(f"   - Total requests: {sum(gobj['total_requests'] for gobj in all_test_plans['gameobjects'])}")
        print(f"   - Total child object processing turns: {sum(gobj['child_processing_turns'] for gobj in all_test_plans['gameobjects'])}")
        
        return all_test_plans
    
    def print_test_plans_summary(self, test_plans: Dict[str, Any]):
        """
        Print test plan summary
        
        Args:
            test_plans: Test plan results
        """
        print(f"\n[INFO] Test Plan Summary")
        print(f"Scene name: {test_plans['scene_name']}")
        print(f"Generated at: {test_plans['generated_at']}")
        print(f"GameObject count: {len(test_plans['gameobjects'])}")
        print()
        
        for i, gobj_plan in enumerate(test_plans['gameobjects'], 1):
            print(f"{i}. {gobj_plan['gameobject_name']} (ID: {gobj_plan['gameobject_id']})")
            print(f"   Type: {gobj_plan['gameobject_type']}")
            print(f"   Total requests: {gobj_plan['total_requests']}")
            print(f"   Child object processing turns: {gobj_plan.get('child_processing_turns', 0)}")
            print(f"   Child objects with Mono components: {'Yes' if gobj_plan['has_children_with_mono'] else 'No'}")
            
            # Statistics for conversation types and test plans
            request_types = {}
            test_plans_count = 0
            need_more_info_count = 0
            
            for msg in gobj_plan['conversation_history']:
                if msg['role'] == 'user':
                    req_type = msg.get('request_type', 'unknown')
                    request_types[req_type] = request_types.get(req_type, 0) + 1
                elif msg['role'] == 'assistant':
                    if msg.get('test_plan'):
                        test_plans_count += 1
                    if msg.get('need_more_info'):
                        need_more_info_count += 1
            
            print(f"   Request type distribution:")
            for req_type, count in request_types.items():
                print(f"     - {req_type}: {count}")
            
            print(f"   Generated test plan count: {test_plans_count}")
            print(f"   Times needing more information: {need_more_info_count}")
            
            # Display first test plan (if exists)
            for msg in gobj_plan['conversation_history']:
                 if msg.get('role') == 'assistant' and msg.get('test_plan'):
                     print(f"   First test plan:")
                     test_plan = msg['test_plan']
                     
                     # Check if test_plan is dict or string
                     if isinstance(test_plan, dict) and 'taskUnits' in test_plan:
                         # test_plan is dict, directly access
                         task_units = test_plan['taskUnits']
                         for j, task in enumerate(task_units):
                             if 'actionUnits' in task:
                                 actions = task['actionUnits']
                                 print(f"     Task {j+1}: {len(actions)} actions")
                                 for k, action in enumerate(actions[:3]):  # Only show first 3 actions
                                     action_type = action.get('type', 'Unknown')
                                     print(f"       - Action {k+1}: {action_type}")
                                 if len(actions) > 3:
                                     print(f"       ... {len(actions) - 3} more actions")
                     elif isinstance(test_plan, str) and 'taskUnits' in test_plan:
                         # test_plan is string, try to parse JSON
                         try:
                             import json
                             parsed_plan = json.loads(test_plan)
                             if 'taskUnits' in parsed_plan:
                                 task_units = parsed_plan['taskUnits']
                                 for j, task in enumerate(task_units):
                                     if 'actionUnits' in task:
                                         actions = task['actionUnits']
                                         print(f"     Task {j+1}: {len(actions)} actions")
                                         for k, action in enumerate(actions[:3]):  # Only show first 3 actions
                                             action_type = action.get('type', 'Unknown')
                                             print(f"       - Action {k+1}: {action_type}")
                                         if len(actions) > 3:
                                             print(f"       ... {len(actions) - 3} more actions")
                         except json.JSONDecodeError:
                             print(f"     JSON parsing failed, showing original content:")
                             print(f"     {test_plan[:200]}...")
                     else:
                         print(f"     Unknown test plan format: {type(test_plan)}")
                         if isinstance(test_plan, str):
                             print(f"     {test_plan[:200]}...")
                     break

    def consolidate_scene_test_plans(self, scene_name: str = None, llm_model: str = 'gpt-5') -> Dict[str, Any]:
        """
        Consolidate all test_plans.json files under the same scene into one file
        
        Args:
            scene_name: Scene name, if not specified then use self.scene_name
            
        Returns:
            Consolidated test plan data
        """
        scene_name = scene_name or self.scene_name
        responses_dir = os.path.join(self.results_dir, "llm_responses", llm_model)
        
        # Clean illegal characters in scene name
        safe_scene_name = self._sanitize_filename(scene_name)
        scene_path = os.path.join(responses_dir, safe_scene_name)
        
        print(f"[SEARCH] Searching for scene directory: {scene_path}")
        
        if not os.path.exists(scene_path):
            print(f"[ERROR] Scene directory does not exist: {scene_path}")
            return {'taskUnits': []}
        
        if not os.path.isdir(scene_path):
            print(f"[ERROR] Path is not a directory: {scene_path}")
            return {'taskUnits': []}
        

        
        consolidated_plans = {
            'taskUnits': []
        }
        
        total_files_processed = 0
        total_action_units = 0
        
        # Find all test_plans.json files
        test_plan_files = []
        for file in os.listdir(scene_path):
            if file.endswith('_test_plans.json') and not file.endswith('_consolidated_test_plans.json'):
                test_plan_files.append(os.path.join(scene_path, file))
                
        for file_path in test_plan_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    test_plan_data = json.load(f)
                
                # Check data format
                if 'taskUnits' in test_plan_data and isinstance(test_plan_data['taskUnits'], list):
                    # Add taskUnits to consolidated results and perform secondary validation
                    for task_unit in test_plan_data['taskUnits']:
                        if 'actionUnits' in task_unit and task_unit['actionUnits']:
                            # Validate each actionUnit
                            valid_action_units = []
                            for action_unit in task_unit['actionUnits']:
                                if self._validate_action_unit_fileids(action_unit):
                                    valid_action_units.append(action_unit)
                                else:
                                    print(f"[WARN]  Filtering out invalid actionUnit during consolidation: {action_unit.get('type', 'Unknown')}")
                            
                            # Only add taskUnit containing valid actionUnits
                            if valid_action_units:
                                task_unit_copy = task_unit.copy()
                                task_unit_copy['actionUnits'] = valid_action_units
                                consolidated_plans['taskUnits'].append(task_unit_copy)
                                total_action_units += len(valid_action_units)
                    
                    total_files_processed += 1
                    print(f"   [OK] Processed: {os.path.basename(file_path)}")
                else:
                    print(f"   [WARN]  Skipping invalid format file: {os.path.basename(file_path)}")
                    
            except Exception as e:
                print(f"   [ERROR] Failed to process file {os.path.basename(file_path)}: {e}")
        
        # Save consolidated results
        if consolidated_plans['taskUnits']:
            output_file = os.path.join(scene_path, f"{scene_name}_consolidated_test_plans.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated_plans, f, indent=2, ensure_ascii=False)
            
            print(f"\n[SUCCESS] Scene test plan consolidation complete!")
            print(f"[STATS] Statistics:")
            print(f"   - Files processed: {total_files_processed}")
            print(f"   - Consolidated taskUnits count: {len(consolidated_plans['taskUnits'])}")
            print(f"   - Total actionUnits count: {total_action_units}")
            print(f"[SAVE] Consolidated results saved to: {output_file}")
        else:
            print(f"\n[WARN]  No valid test_plans data found")
        
        return consolidated_plans


def discover_scene_names(results_dir: str) -> List[str]:
    """
    Automatically discover scene names in scene_detailed_info/mainResults under results_dir
    
    Args:
        results_dir: Results directory path
        
    Returns:
        Scene name list
    """
    scene_meta_dir = os.path.join(results_dir, 'scene_detailed_info', 'mainResults')
    scene_names = []
    
    if not os.path.exists(scene_meta_dir):
        print(f"[WARN]  Scene metadata directory does not exist: {scene_meta_dir}")
        return scene_names
    
    try:
        # Iterate through files in mainResults directory
        for filename in os.listdir(scene_meta_dir):
            # Check if ends with .unity.json_graph.gml
            if filename.endswith('.unity.json_graph.gml'):
                # Use .unity.json_graph.gml as split point, take first part as scene name
                scene_name = filename.split('.unity.json_graph.gml')[0]
                if scene_name:  # Ensure scene name is not empty
                    scene_names.append(scene_name)
                    print(f"[SEARCH] Discovered scene: {scene_name}")
        
        if not scene_names:
            print("[WARN]  No scene files found (ending with .unity.json_graph.gml)")
        else:
            print(f"[OK] Discovered {len(scene_names)} scenes in total: {', '.join(scene_names)}")
            
    except Exception as e:
        print(f"[ERROR] Error scanning scene files: {e}")
    
    return scene_names


def main():
    """
    Main function
    """
    # Ensure UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            import io
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            else:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            else:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    
    parser = argparse.ArgumentParser(description="Generate Unity GameObject test plan conversations (using sorted_target_logic_info)")
    parser.add_argument('-r', '--results-dir', required=True, 
                       help='Results directory path, containing gobj_hierarchy.json and scene data')
    parser.add_argument('-a', '--app-name', 
                       help='Application name (optional, if not specified then use default value in config.py)')
    parser.add_argument('--disable-llm', action='store_true',
                       help='Disable LLM API calls, use simulation mode (for testing)')
    parser.add_argument('--max-runs', type=int, default=4,
                       help='Maximum rounds for child object processing, will rebuild LLM connection if exceeded (default: 4)')
    parser.add_argument('--consolidate', action='store_true',
                       help='Only execute scene test plan consolidation function, do not generate new test plans')
    parser.add_argument('--duplicate', action='store_true', 
                        help='Allow generating duplicate actionUnits')
    parser.add_argument('-s', '--scene-name', 
                       help='Scene name (optional, if not specified then use default value in config.py)')
    parser.add_argument('-m', '--llm-model', type=str, default='gpt-5',
                       help='LLM model (optional)')
    parser.add_argument('-c', '--config', type=str, default='config',
                       help='Configuration module name (default: config)')
    
    args = parser.parse_args()
    results_dir = args.results_dir
    app_name = args.app_name
    enable_llm = not args.disable_llm
    max_runs = args.max_runs
    consolidate_only = args.consolidate
    is_duplicate = args.duplicate
    scene_name = args.scene_name
    llm_model = args.llm_model
    config_module_name = args.config
    
    # Dynamically import configuration module
    try:
        config_module = importlib.import_module(config_module_name)
        print(f"[OK] Successfully loaded configuration module: {config_module_name}")
    except ImportError as e:
        print(f"[ERROR] Failed to import configuration module '{config_module_name}': {e}")
        print(f"[INFO] Falling back to default 'config' module")
        try:
            config_module = importlib.import_module('config')
        except ImportError:
            print(f"[ERROR] Failed to import default 'config' module")
            return
    
    try:
        if scene_name:
            print(f"\n{'='*60}")
            print(f"[SCENE] Starting to process scene: {scene_name}")
            print(f"{'='*60}")
            
            # Create test plan generator
            generator = GenerateTestPlanModified(results_dir, scene_name, app_name, enable_llm, config_module)
            
            if consolidate_only:
                # Only execute consolidation function
                print(f"[PROCESS] Executing scene {scene_name} test plan consolidation function...")
                consolidated_plans = generator.consolidate_scene_test_plans(scene_name, llm_model)
            else:
                # Generate all test plans (multi-turn conversation based on child object processing count)
                test_plans = generator.generate_all_test_plans(scene_name, max_runs, is_duplicate, llm_model)
                
                # Print summary
                generator.print_test_plans_summary(test_plans)
                
                # Save results to file
                output_file = os.path.join(results_dir, f"test_plan_conversations_sorted_{scene_name}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(test_plans, f, indent=2, ensure_ascii=False)
                
                print(f"\n[SAVE] Test plan conversations saved to: {output_file}")
                
                # Automatically execute consolidation function
                print(f"\n[PROCESS] Automatically executing scene {scene_name} test plan consolidation...")
                consolidated_plans = generator.consolidate_scene_test_plans(scene_name, llm_model)
        else:

            # Automatically discover scene names
            print("[SEARCH] Scanning scene files...")
            scene_names = discover_scene_names(results_dir)
            
            if not scene_names:
                print("[ERROR] No scenes found, program exiting")
                return
        
            
            # Iterate through all discovered scenes
            for scene_name in scene_names:
                print(f"\n{'='*60}")
                print(f"[SCENE] Starting to process scene: {scene_name}")
                print(f"{'='*60}")
                
                # Update generator's scene name
                # Create test plan generator (without specifying specific scene name)
                generator = GenerateTestPlanModified(results_dir, scene_name, app_name, enable_llm, config_module)
                
                if consolidate_only:
                    # Only execute consolidation function
                    print(f"[PROCESS] Executing scene {scene_name} test plan consolidation function...")
                    consolidated_plans = generator.consolidate_scene_test_plans(scene_name, llm_model)
                else:
                    # Generate all test plans (multi-turn conversation based on child object processing count)
                    test_plans = generator.generate_all_test_plans(scene_name, max_runs, is_duplicate, llm_model)
                    
                    # Print summary
                    generator.print_test_plans_summary(test_plans)
                    
                    # Save results to file
                    output_file = os.path.join(results_dir, f"test_plan_conversations_sorted_{scene_name}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(test_plans, f, indent=2, ensure_ascii=False)
                    
                    print(f"\n[SAVE] Test plan conversations saved to: {output_file}")
                    
                    # Automatically execute consolidation function
                    print(f"\n[PROCESS] Automatically executing scene {scene_name} test plan consolidation...")
                    consolidated_plans = generator.consolidate_scene_test_plans(scene_name, llm_model)
                
                print(f"[OK] Scene {scene_name} processing complete")
            
            print(f"\n[SUCCESS] All scenes processing complete! Processed {len(scene_names)} scenes in total")
        
    except Exception as e:
        print(f"[ERROR] Error occurred during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
