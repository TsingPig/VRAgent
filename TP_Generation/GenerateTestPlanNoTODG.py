#!/usr/bin/env python3
"""
Modified GenerateTestPlan.py - Generate test plans without TODG (Test Object Dependency Graph)

This file is a modified version of GenerateTestPlan.py with the following main changes:
1. Each GameObject sends a single request using TEST_PLAN_NO_TODG_REQUEST_TEMPLATE
2. No conversation context, no special logic processing
3. All test plans are merged into a single consolidated result
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
THINK_RE = re.compile(r'<\s*think\s*>.*?<\s*/\s*think\s*>', re.IGNORECASE | re.DOTALL)


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
        self.TEST_PLAN_NO_TODG_REQUEST_TEMPLATE = getattr(config_module, 'TEST_PLAN_NO_TODG_REQUEST_TEMPLATE', None)
        self.DEFAULT_APP_NAME = getattr(config_module, 'DEFAULT_APP_NAME', 'UnityApp')
        self.basicUrl_gpt35 = getattr(config_module, 'basicUrl_gpt35', None)
        self.OPENAI_API_KEY = getattr(config_module, 'OPENAI_API_KEY_1', None)
        
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
        # Load GameObjects directly from JSON file
        self.json_data = self._load_unity_json_file(scene_name)
    
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
        """Load scene metadata (from .unity.json files)"""
        scene_meta_data = {}
        
        if not os.path.exists(self.scene_meta_dir):
            print(f"Warning: Scene metadata directory does not exist: {self.scene_meta_dir}")
            return scene_meta_data
        
        # Find .unity.json files
        for file in os.listdir(self.scene_meta_dir):
            if file.endswith('.unity.json'):
                json_file_path = os.path.join(self.scene_meta_dir, file)
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    scene_name = file.split(".unity.json")[0]
                    scene_meta_data[scene_name] = data
                    print(f"Loaded scene JSON file: {scene_name}")
                except Exception as e:
                    print(f"Failed to load JSON file {file}: {e}")
        
        return scene_meta_data
    
    def _load_unity_json_file(self, scene_name: str) -> Optional[Dict[str, Any]]:
        """
        Load Unity JSON file directly
        
        Args:
            scene_name: Scene name
            
        Returns:
            Dict: JSON data from {scene_name}.unity.json file, None if not found
        """
        json_file_path = os.path.join(self.scene_meta_dir, f"{scene_name}.unity.json")
        
        if not os.path.exists(json_file_path):
            print(f"[WARN]  Unity JSON file not found: {json_file_path}")
            return None
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[OK] Loaded Unity JSON file: {json_file_path}")
                return data
        except Exception as e:
            print(f"[ERROR] Failed to load Unity JSON file {json_file_path}: {e}")
            return None
    
    def _sanitize_keys(self, set: Dict[str, Any]) -> Dict[str, Any]:
        string_to_clean = json.dumps(set)
        if '"- ' in string_to_clean or '" ' in string_to_clean:
            string_to_clean = string_to_clean.replace('"- ', '"').replace('" ', '"')
        
        # Remove leading "_" characters from keys
        # Pattern to match keys that start with "_" and remove the leading "_"
        pattern = r'"(_[^"]*)"\s*:'
        def remove_leading_underscore(match):
            key = match.group(1)
            cleaned_key = key[1:]  # Remove the first character (the leading "_")
            return f'"{cleaned_key}":'
        string_to_clean = re.sub(pattern, remove_leading_underscore, string_to_clean)

        return json.loads(string_to_clean)
    

    
    def _extract_monobehaviour_components_from_json(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all MonoBehaviour components from Unity JSON file
        
        Args:
            json_data: JSON data from Unity JSON file
            
        Returns:
            List[Dict]: List of MonoBehaviour component information dictionaries
        """
        mono_components = []
        components = json_data.get("COMPONENTS", [])
        seen_mono_ids = set()  # 用于去重
        
        for component in components:
            if "MonoBehaviour" in component:
                mono_id = component.get("id", "")
                
                # 去重：检查 mono_id 是否已存在
                if mono_id in seen_mono_ids:
                    continue
                seen_mono_ids.add(mono_id)
                
                mono_data = component.get("MonoBehaviour", [])
                
                # 查找对应的GameObject信息
                gobj_id = None
                gobj_name = "Unknown"
                
                # 从MonoBehaviour的m_GameObject字段获取GameObject ID
                for prop in mono_data:
                    if isinstance(prop, dict) and "m_GameObject" in prop:
                        game_obj_ref = prop["m_GameObject"]
                        if isinstance(game_obj_ref, list) and len(game_obj_ref) > 0:
                            fileid_item = game_obj_ref[0]
                            if isinstance(fileid_item, dict) and "fileID" in fileid_item:
                                gobj_id = fileid_item.get("fileID", "")
                                break
                
                # 如果找到了GameObject ID，尝试获取GameObject名称
                if gobj_id:
                    for comp in components:
                        if "GameObject" in comp:
                            comp_id = comp.get("id", "")
                            if str(comp_id).split(" stripped")[0] == str(gobj_id).split(" stripped")[0]:
                                gobj_data = comp.get("GameObject", [])
                                if isinstance(gobj_data, list):
                                    for prop in gobj_data:
                                        if isinstance(prop, dict) and "m_Name" in prop:
                                            name_val = prop["m_Name"]
                                            if isinstance(name_val, list) and len(name_val) > 0:
                                                if isinstance(name_val[0], dict):
                                                    gobj_name = name_val[0].get("value", "Unknown")
                                                else:
                                                    gobj_name = str(name_val[0])
                                            elif isinstance(name_val, str):
                                                gobj_name = name_val
                                            if gobj_name != "Unknown":
                                                break
                                break
                
                # 检查GameObject名称是否在禁止列表中
                if any(forbid in gobj_name for forbid in forbid_lis):
                    continue
                
                # 检查是否有script（通过m_Script字段）
                has_script = False
                for prop in mono_data:
                    if isinstance(prop, dict) and "m_Script" in prop:
                        has_script = True
                        break
                
                # 只添加有script的MonoBehaviour
                if has_script:
                    mono_components.append({
                        'mono_id': mono_id,
                        'mono_component': component,
                    })
        
        print(f"[OK] Extracted {len(mono_components)} MonoBehaviour components with scripts from JSON file")
        return mono_components
    
    def _extract_monobehaviour_scene_meta(self, mono_id: str, scene_graph: nx.Graph) -> Dict[str, Any]:
        """
        Extract scene meta information for a MonoBehaviour component from graph file
        
        Args:
            mono_id: MonoBehaviour component ID
            scene_graph: Scene graph (GML file data)
            
        Returns:
            Dict: Scene meta information for the MonoBehaviour component
        """
        mono_meta = {}
        
        # 在场景图中查找MonoBehaviour节点
        if mono_id in scene_graph.nodes:
            node_data = scene_graph.nodes[mono_id]
            mono_meta['MonoBehaviour'] = {
                'id': mono_id,
                'properties': node_data.get('properties', {}),
                'type': node_data.get('type', 'MonoBehaviour')
            }
        else:
            # 如果图中找不到，尝试通过ID匹配（处理stripped后缀）
            for node in scene_graph.nodes:
                if str(node).split("stripped")[0] == str(mono_id).split("stripped")[0]:
                    node_data = scene_graph.nodes[node]
                    if node_data.get('type') == 'MonoBehaviour' or 'MonoBehaviour' in str(node_data.get('type', '')):
                        mono_meta['MonoBehaviour'] = {
                            'id': node,
                            'properties': node_data.get('properties', {}),
                            'type': node_data.get('type', 'MonoBehaviour')
                        }
                        break
        
        return mono_meta
    
    
    def _extract_script_from_monobehaviour_json(self, mono_component: Dict[str, Any], json_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract script source code from MonoBehaviour component in JSON data
        
        Args:
            mono_component: MonoBehaviour component dictionary
            json_data: Full JSON data from Unity JSON file
            
        Returns:
            str: Script source code, None if not found
        """
        mono_data = mono_component.get('component_data', {}).get("MonoBehaviour", [])
        
        # Find m_Script field in MonoBehaviour
        script_guid = None
        for prop in mono_data:
            if isinstance(prop, dict) and "m_Script" in prop:
                script_ref = prop["m_Script"]
                if isinstance(script_ref, list):
                    for item in script_ref:
                        if isinstance(item, dict) and "guid" in item:
                            script_guid = item.get("guid")
                            break
        
        if not script_guid:
            return None
        
        # Search through scene graphs to find script_file node by GUID
        for scene_name, scene_graph in self.scene_graphs.items():
            for node in scene_graph.nodes:
                node_data = scene_graph.nodes[node]
                if node_data.get('type') == 'script_file':
                    properties = node_data.get('properties', {})
                    if properties.get('guid') == script_guid:
                        # Found script_file node, extract file_path and load script
                        file_path = properties.get('file_path', '')
                        if file_path:
                            # Remove .meta suffix if present
                            if file_path.endswith('.meta'):
                                file_path = file_path[:-5]
                            # Load script file
                            script_content = self._load_script_file(file_path)
                            if script_content:
                                return script_content
                            else:
                                print(f"[WARN]  Failed to load script file: {file_path}")
                                return None
        
        return None
    
    def _has_script_source(self, gobj_info: Dict[str, Any], json_data: Dict[str, Any]) -> bool:
        """
        Check if GameObject has any script source code
        
        Args:
            gobj_info: GameObject information from JSON
            json_data: Full JSON data
            
        Returns:
            bool: True if GameObject has script source, False otherwise
        """
        for mono_comp in gobj_info.get('mono_components', []):
            script_source = self._extract_script_from_monobehaviour_json(mono_comp, json_data)
            if script_source:
                return True
        return False
    
    def generate_prompt_for_monobehaviour(self, mono_info: Dict[str, Any], scene_name: str, json_data: Dict[str, Any]) -> str:
        """
        Generate prompt for a MonoBehaviour component from JSON data using TEST_PLAN_NO_TODG_REQUEST_TEMPLATE
        
        Args:
            mono_info: MonoBehaviour component information from JSON
            scene_name: Scene name
            json_data: Full JSON data
            
        Returns:
            str: Generated prompt string
        """
        mono_id = mono_info.get('mono_id')
        
        # Extract scene meta information for MonoBehaviour only
        scene_meta = {}
        for scene_name_key, scene_graph in self.scene_graphs.items():
            mono_meta = self._extract_monobehaviour_scene_meta(mono_id, scene_graph)
            if mono_meta:
                scene_meta.update(mono_meta)
                break
        
        scene_meta_str = str(scene_meta) if scene_meta else "{}"
        
        # Extract script source code for this MonoBehaviour
        mono_component_dict = {
            'component_data': mono_info.get('mono_component', {})
        }
        script_source = self._extract_script_from_monobehaviour_json(mono_component_dict, json_data)
        script_source_str = script_source if script_source else "// No script source code found"
        
        # Use TEST_PLAN_NO_TODG_REQUEST_TEMPLATE
        # Note: gobj_name and gobj_id are set to empty strings as they are not needed
        template = getattr(self.config, 'TEST_PLAN_NO_TODG_REQUEST_TEMPLATE', None)
        return template.format(
            app_name=self.app_name,
            scene_name=scene_name,
            scene_meta=scene_meta_str,
            script_source=script_source_str
        )
  
    
    def _call_llm_api(self, prompt: str, max_retries: int = 5, llm_model: str = 'gpt-5') -> Optional[str]:
        """
        Call LLM API to get response (single request without context)
        
        Args:
            prompt: Prompt to send to LLM
            max_retries: Maximum retry count
            llm_model: LLM model to use
        
        Returns:
            str: LLM response content, returns None if failed
        """
        # If LLM API is disabled, use simulation mode
        if not self.enable_llm:
            return self._generate_simulated_response(prompt)
        
        # Build message list (single request, no context)
        messages = [{"role": "user", "content": prompt}]
        
        for attempt in range(max_retries):
            try:
                print(f"[PROCESS] Calling LLM API (attempt {attempt + 1}/{max_retries})...")
                
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
  ]
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
  ]
}'''
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        try:
            if 'taskUnits' in response:
                # Try to parse JSON
                try:
                    parsed_response = json.loads(response)
                    return {'test_plan': parsed_response}
                except json.JSONDecodeError:
                    return {'test_plan': response}
            else:
                return {'test_plan': None}
        except Exception as e:
            print(f"[WARN]  Failed to parse LLM response: {e}")
            return {'test_plan': None}
    
    
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
    
    def strip_think(self, text: str) -> str:
        # Filter out <think></think> tags
        text = THINK_RE.sub('', text)
        return text
    
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

    def generate_all_test_plans(self, scene_name: str = None, max_runs: int = 3, is_duplicate: bool = False, llm_model: str = 'gpt-5') -> Dict[str, Any]:
        """
        Generate test plans for all MonoBehaviour components using TEST_PLAN_NO_TODG_REQUEST_TEMPLATE
        Each MonoBehaviour component sends one request without context, all test plans are merged
        
        Args:
            scene_name: Scene name, if None then use first available scene
            max_runs: Not used (kept for compatibility)
            is_duplicate: Not used (kept for compatibility)
            llm_model: LLM model to use
        
        Returns:
            Dict: Results containing merged test plans
        """
        if scene_name is None:
            scene_name = self.scene_name
        
        print(f"[START] Starting to generate test plans for all MonoBehaviour components in scene '{scene_name}'...")
        print(f"[INFO] Mode: Single request per MonoBehaviour component, no conversation context, merging all test plans")
        
        # Load JSON data
        json_data = None
        if scene_name:
            json_data = self._load_unity_json_file(scene_name)
        else:
            print(f"[ERROR] Scene name is required")
            return {'taskUnits': []}
        
        # Extract all MonoBehaviour components from JSON
        mono_components = self._extract_monobehaviour_components_from_json(json_data)
        
        if not mono_components:
            print(f"[WARN]  No MonoBehaviour components with scripts found in JSON file")
            return {'taskUnits': []}
        
        print(f"[INFO] Found {len(mono_components)} MonoBehaviour components with scripts in JSON file")
        
        safe_scene_name = self._sanitize_filename(scene_name)
        llm_responses_dir = os.path.join(self.results_dir, 'llm_responses', llm_model, safe_scene_name)
        if os.path.exists(llm_responses_dir):
            shutil.rmtree(llm_responses_dir)
        os.makedirs(llm_responses_dir, exist_ok=False)
        
        # Store all test plans for merging
        all_action_units = []
        processed_count = 0
        failed_count = 0
        
        # Iterate through all MonoBehaviour components
        skipped_count = 0
        for mono_index, mono_info in enumerate(mono_components, 1):
            mono_id = mono_info.get('mono_id')
            
            if not mono_id:
                continue
            
            print(f"\n[INFO] Processing MonoBehaviour {mono_index}/{len(mono_components)}: (ID: {mono_id})")
            
            # Generate prompt using TEST_PLAN_NO_TODG_REQUEST_TEMPLATE (via generate_prompt_for_monobehaviour)
            prompt = self.generate_prompt_for_monobehaviour(mono_info, scene_name, json_data)
            
            # Call LLM API (single request per MonoBehaviour, no context)
            print(f"[BOT] Sending request to LLM for MonoBehaviour (ID: {mono_id})...")
            
            response = self._call_llm_api(prompt, llm_model=llm_model)
            
            if response:
                # Parse response
                response = self.strip_think(response)
                # Extract JSON content from ```json code blocks if present
                if '```json' in response:
                    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                    if json_match:
                        response = json_match.group(1).strip()
                parsed_response = self._parse_llm_response(response)
                test_plan = parsed_response.get('test_plan')
                
                if test_plan:
                    # Extract actionUnits from test plan
                    if isinstance(test_plan, dict) and 'taskUnits' in test_plan:
                        for task_unit in test_plan['taskUnits']:
                            if 'actionUnits' in task_unit:
                                for action_unit in task_unit['actionUnits']:
                                    # Validate and add to merged list
                                    if self._validate_action_unit_fileids(action_unit):
                                        all_action_units.append(action_unit)
                                    else:
                                        print(f"[WARN]  Filtered out invalid actionUnit for MonoBehaviour {mono_id}")
                    elif isinstance(test_plan, str) and 'taskUnits' in test_plan:
                        try:
                            parsed_plan = json.loads(test_plan)
                            if 'taskUnits' in parsed_plan:
                                for task_unit in parsed_plan['taskUnits']:
                                    if 'actionUnits' in task_unit:
                                        for action_unit in task_unit['actionUnits']:
                                            if self._validate_action_unit_fileids(action_unit):
                                                all_action_units.append(action_unit)
                        except json.JSONDecodeError:
                            print(f"[WARN]  Failed to parse test plan JSON for MonoBehaviour {mono_id}")
                    
                    processed_count += 1
                    print(f"[OK] MonoBehaviour {mono_id} test plan generated and merged")
                else:
                    failed_count += 1
                    print(f"[WARN]  No valid test plan in response for MonoBehaviour {mono_id}")
            else:
                failed_count += 1
                print(f"[ERROR] Failed to get LLM response for MonoBehaviour {mono_id}")
        
        # Create merged test plan
        merged_test_plan = {
            'taskUnits': [{
                'actionUnits': all_action_units
            }]
        }
        
        # Save merged test plan
        if all_action_units:
            output_file = os.path.join(llm_responses_dir, f"{scene_name}_consolidated_test_plans.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_test_plan, f, indent=2, ensure_ascii=False)
            print(f"\n[SAVE] Merged test plan saved to: {output_file}")
        
        print(f"\n[SUCCESS] All MonoBehaviour components' test plan generation complete!")
        print(f"[STATS] Statistics:")
        print(f"   - Total MonoBehaviour component count: {len(mono_components)}")
        print(f"   - Skipped: {skipped_count}")
        print(f"   - Successfully processed: {processed_count}")
        print(f"   - Failed: {failed_count}")
        print(f"   - Total action units merged: {len(all_action_units)}")
        
        return merged_test_plan
    
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
            # Check if ends with .unity.json
            if filename.endswith('.unity.json'):
                # Use .unity.json as split point, take first part as scene name
                scene_name = filename.split('.unity.json')[0]
                if scene_name:  # Ensure scene name is not empty
                    scene_names.append(scene_name)
                    print(f"[SEARCH] Discovered scene: {scene_name}")
        
        if not scene_names:
            print("[WARN]  No scene files found (ending with .unity.json)")
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
    
    parser = argparse.ArgumentParser(description="Generate Unity GameObject test plans without TODG (single request per GameObject)")
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
                # Generate all test plans (single request per GameObject, merged)
                merged_test_plans = generator.generate_all_test_plans(scene_name, max_runs, is_duplicate, llm_model)
                
                # Print summary
                print(f"\n[INFO] Merged Test Plan Summary")
                print(f"Scene name: {scene_name}")
                print(f"Total taskUnits: {len(merged_test_plans.get('taskUnits', []))}")
                total_actions = sum(len(tu.get('actionUnits', [])) for tu in merged_test_plans.get('taskUnits', []))
                print(f"Total actionUnits: {total_actions}")
                
                # Save merged results to file
                output_file = os.path.join(results_dir, f"test_plan_conversations_sorted_{scene_name}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(merged_test_plans, f, indent=2, ensure_ascii=False)
                
                print(f"\n[SAVE] Merged test plan saved to: {output_file}")
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
                    # Generate all test plans (single request per GameObject, merged)
                    merged_test_plans = generator.generate_all_test_plans(scene_name, max_runs, is_duplicate, llm_model)
                    
                    # Print summary
                    print(f"\n[INFO] Merged Test Plan Summary")
                    print(f"Scene name: {scene_name}")
                    print(f"Total taskUnits: {len(merged_test_plans.get('taskUnits', []))}")
                    total_actions = sum(len(tu.get('actionUnits', [])) for tu in merged_test_plans.get('taskUnits', []))
                    print(f"Total actionUnits: {total_actions}")
                    
                    # Save merged results to file
                    output_file = os.path.join(results_dir, f"test_plan_merged_{scene_name}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(merged_test_plans, f, indent=2, ensure_ascii=False)
                    
                    print(f"\n[SAVE] Merged test plan saved to: {output_file}")
                
                print(f"[OK] Scene {scene_name} processing complete")
            
            print(f"\n[SUCCESS] All scenes processing complete! Processed {len(scene_names)} scenes in total")
        
    except Exception as e:
        print(f"[ERROR] Error occurred during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
