import os
import json
import subprocess
import argparse
from networkx.algorithms.bipartite.cluster import latapy_clustering
from openai import file_from_path
import config
import networkx as nx
import matplotlib.pyplot as plt

def get_editor_build_settings_path(project_path):
    """Find the EditorBuildSettings.asset file within the given Unity project path."""
    asset_path = os.path.join(project_path, 'ProjectSettings', 'EditorBuildSettings.asset')
    if not os.path.exists(asset_path):
        raise FileNotFoundError(f"EditorBuildSettings.asset not found at {asset_path}")
    return asset_path


def analyze_asset(asset_path, asset_results_dir):
    """Execute UnityDataAnalyzer to analyze the specified asset file."""
    if not os.path.exists(config.unity_analyzer_path):
        raise FileNotFoundError(f"UnityDataAnalyzer.exe not found at {config.unity_analyzer_path}")

    if not os.path.exists(asset_results_dir):
        os.makedirs(asset_results_dir)
    
    try:
        command = f'"{config.unity_analyzer_path}" -a "{asset_path}" -r "{asset_results_dir}"'
        print(f"Executing command: {command}")

        subprocess.run(command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except Exception as e:
        print(f"Error analyzing asset {asset_path}: {e}")

def analyze_tagManager(tagManager_path, tagManager_results_dir):
    analyze_asset(tagManager_path, tagManager_results_dir)
    asset_name = os.path.basename(tagManager_path)
    json_file = os.path.join(tagManager_results_dir, 'mainResults', asset_name+'.json')
    scene_layers_list = []

    with open(json_file, 'r') as f:
        data = json.load(f)
        tag_manager_data = data.get("COMPONENTS", [])[0].get("TagManager", [])
        for item in tag_manager_data:
            if 'layers' in item:
                scene_layers = item['layers']
                for layer in scene_layers:
                    layer_name = list(layer.values())[0].split('-')[1].strip()
                    if layer_name != '':
                        scene_layers_list.append(layer_name)
        return scene_layers_list
    

def analyze_script(script_path, script_results_dir):
    if not os.path.exists(config.csharp_analyzer_path):
        raise FileNotFoundError(f"csharp_analyzer_path.exe not found at {config.csharp_analyzer_path}")

    script_analysis_dir = os.path.join(script_results_dir, 'script_detailed_info', 'mainResults')

    command = f'"{config.csharp_analyzer_path}" -p "{script_path}" -r "{script_analysis_dir}"'
    print(f"Executing command: {command}")

    subprocess.run(command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def analyze_structure_script(script_results_dir):
    if not os.path.exists(config.structure_analyzer_path):
        raise FileNotFoundError(f"structure_analyzer_path.exe not found at {config.structure_analyzer_path}")

    analyze_file = os.path.join(script_results_dir, 'script_detailed_info', 'mainResults', 'CodeAnalysis.json')
    script_analysis_dir = os.path.join(script_results_dir, 'script_detailed_info', 'mainResults')

    command = f'"{config.structure_analyzer_path}" -d "{analyze_file}" -r "{script_analysis_dir}"'
    print(f"Executing command: {command}")

    subprocess.run(command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def extract_scene_paths_from_json(json_file_path):
    """Extract scene paths from the JSON file produced by UnityDataAnalyzer."""
    with open(json_file_path, 'r') as json_file:
        scene_paths = []
        data = json.load(json_file)
        scenes = data.get("COMPONENTS", [])[0].get("EditorBuildSettings", [])[2].get("m_Scenes", [])
        for i in range(len(scenes)):
            if " enabled" in scenes[i]:
                if scenes[i][" enabled"] == "1":
                    scene_paths.append(scenes[i+1]["path"])
            
    return scene_paths

def analyze_scenes(project_path, scene_paths, results_dir):
    """Analyze each scene file using UnityDataAnalyzer."""
    scene_results_dir = os.path.join(results_dir, 'scene_detailed_info')
    if not os.path.exists(scene_results_dir):
        os.makedirs(scene_results_dir)

    for scene_path in scene_paths:
        full_scene_path = os.path.join(project_path, scene_path)
        if not os.path.exists(full_scene_path):
            print(f"Scene file not found: {full_scene_path}")
            continue

        command = f'"{config.unity_analyzer_path}" -a "{full_scene_path}" -r "{scene_results_dir}"'
        print(f"Analyzing scene: {full_scene_path}")

        subprocess.run(command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)


def sanitize_keys(set):
    string_to_clean = json.dumps(set)
    if '"- ' in string_to_clean or '" ' in string_to_clean:
        string_to_clean = string_to_clean.replace('"- ', '"').replace('" ', '"')
    
    # Remove leading "_" characters from keys
    import re
    # Pattern to match keys that start with "_" and remove the leading "_"
    pattern = r'"(_[^"]*)"\s*:'
    def remove_leading_underscore(match):
        key = match.group(1)
        cleaned_key = key[1:]  # Remove the first character (the leading "_")
        return f'"{cleaned_key}":'
    string_to_clean = re.sub(pattern, remove_leading_underscore, string_to_clean)

    return json.loads(string_to_clean)

def extract_scene_settings(scene_json_path):
    """Extract GameObject information from the scene JSON file."""
    with open(scene_json_path, 'r') as json_file:
        data = json.load(json_file)

    all_scene_json = {
        "GameObjects": [],
        "MonoBehaviours": [],
        "PrefabInstances": [],
        "Other_Comps": []
    }

    # Iterate over each component in the JSON data
    for component in data.get("COMPONENTS", []):
        if "GameObject" in component:
            game_object = {
                "id": component.get("id", ""),
                "GameObject": []
            }

            # Extract GameObject properties
            for key, value in component.items():
                if key == "GameObject":
                    for set in value:
                        for key_child, val_child in set.items():
                            if key_child == 'm_Component':
                                m_component = {"m_Component": []}
                                for comp in val_child:
                                    m_component["m_Component"].append({
                                        "component":  # Changed key to a valid GML key
                                            [{
                                                "fileID": comp[key][0].get("fileID", "") for key in comp.keys()
                                            }]
                                    })
                                game_object["GameObject"].append(m_component)
                            else:
                                game_object["GameObject"].append(set)

            all_scene_json["GameObjects"].append(game_object)

        else:
            if "MonoBehaviour" in component:
                mono_behavior = {
                    "id": component.get("id", ""),
                    "MonoBehaviour": []
                }
                for key, value in component.items():
                    if key == "MonoBehaviour":
                        for set in value:
                            set_store = sanitize_keys(set)
                            mono_behavior["MonoBehaviour"].append(set_store)

                all_scene_json["MonoBehaviours"].append(mono_behavior)

            else:
                if "PrefabInstance" in component.keys():
                    prefab_instance = {
                        "id": component.get("id", ""),
                        "PrefabInstance": []
                    }
                    for key, value in component.items():
                        if key == "PrefabInstance":
                            for set in value:
                                set_store = sanitize_keys(set)
                                prefab_instance["PrefabInstance"].append(set_store)

                    all_scene_json["PrefabInstances"].append(prefab_instance)
                else:
                    other_comp = {}
                    for key, value in component.items():
                        if key == 'id':
                            other_comp[key] = value
                        else:
                            for set in value:
                                set_store = sanitize_keys(set)
                                if key in other_comp:
                                    other_comp[key].append(set_store)
                                else:
                                    other_comp[key] = []
                                    other_comp[key].append(set_store)

                    all_scene_json["Other_Comps"].append(other_comp)

    return all_scene_json

def analyze_csharp_meta(asset_paths, results_dir):
    script_results_dir = os.path.join(results_dir, 'script_detailed_info')

    for root, dirs, files in os.walk(asset_paths):
        for file in files:
            if "cs.meta" in file:
                analyze_asset(os.path.join(root, file), script_results_dir)

    script_lis = []
    for root, dirs, files in os.walk(os.path.join(script_results_dir, 'metaResults')):
        for file in files:
            if "TextMesh" in file:
                continue
            else:
                with open(os.path.join(root, file), 'r') as f:
                    script_dic = json.load(f)
                    script_lis.append(script_dic)
    return script_lis

def AddChildRelation(G):
    """
    Add child relationships between GameObjects based on Transform components.
    For each GameObject -> Transform edge of type "Has_Other_Comp",
    look for child Transform IDs and find their corresponding GameObjects.
    
    Args:
        G: NetworkX graph object
    """
    edges_to_add = []
    
    # First, find all GameObject -> Transform relationships
    for source, target, edge_data in G.edges(data=True):
        # Check if this is a GameObject -> Transform edge
        if edge_data.get('type') == "Has_Other_Comp":
            source_gameobject_id = source  # This is the parent GameObject ID
            transform_node = G.nodes[target]
            
            # Verify this is a Transform node
            if transform_node.get('type') == 'Transform':
                # Get the transform properties
                if 'properties' in transform_node:
                    transform_data = transform_node['properties']['Transform']
                    for transform_set in transform_data:
                        if 'm_Children' in transform_set:
                            children = transform_set['m_Children']
                            # For each child Transform ID
                            for child in children:
                                if isinstance(child, dict) and 'fileID' in child:
                                    child_transform_id = child['fileID']
                                    # Find the GameObject that has this Transform as a component
                                    for child_source, child_target, child_edge_data in G.edges(data=True):
                                        if child_edge_data.get('type') == "Has_Other_Comp":
                                            # Get the target node
                                            child_target_node = G.nodes[child_target]
                                            # Check if this is a Transform node and compare label
                                            if (child_target_node.get('type') == 'Transform' and 
                                                str(child_target_node['properties']['id']).split(' stripped')[0] == str(child_transform_id)):
                                                # child_source is the child GameObject ID
                                                edges_to_add.append((source_gameobject_id, child_source, "Has_Child"))
                                                break

    # Add all collected parent-child relationships to the graph
    for parent_id, child_id, edge_type in edges_to_add:
        G.add_edge(parent_id, child_id, type=edge_type)

def AddmonoRelation(G, results_dir):
    codeAnalysis_json = os.path.join(results_dir, 'script_detailed_info', 'mainResults', 'CodeAnalysis.json')
    inheritance_lis = []
    edges_to_add = []
    nodes_to_add = []
    
    with open(codeAnalysis_json, 'r', encoding='utf-8') as f:
        read_json = json.load(f)
        codeAnalysis_lis = read_json["Project"]
        for project in codeAnalysis_lis:
            script_file = project["FileName"]
            for class_item in project["Classes"]:
                inheritance_dic = {}
                inheritance = class_item["FullInheritanceName"]
                if inheritance != "MonoBehaviour":
                    for project_item in codeAnalysis_lis:
                        search_file = project_item["FileName"]
                        for class_search in project_item["Classes"]:
                            if class_search["Name"] == inheritance:
                                inheritance_dic["origin_class"] = class_item["Name"]
                                inheritance_dic["inheritance_class"] = inheritance
                                inheritance_dic["origin_file_path"] = script_file
                                inheritance_dic["inheritance_file_path"] = search_file
                                break

                    if inheritance_dic != {}:
                        inheritance_lis.append(inheritance_dic)
    
    for inheri_item in inheritance_lis:
        inheritance_id = None
        origin_id = None
        
        for node_id, properties in G.nodes(data=True):
            if properties['type'] == "script_file":
                for prop, value in properties.items():
                    if prop == "properties":
                        if value["file_path"] == inheri_item["inheritance_file_path"] + ".meta":
                            inheritance_id = node_id
                        
                        if value["file_path"] == inheri_item["origin_file_path"] + ".meta":
                            origin_id = node_id
        
        if origin_id:
            if inheritance_id:
                edges_to_add.append((origin_id, inheritance_id, "Inheritance_Relation"))
            else:
                inheritance_lis = {}
                inheritance_lis["file_path"] = inheri_item["inheritance_file_path"] + ".meta"
                inheritance_lis["name"] = inheri_item["inheritance_class"]
                nodes_to_add.append((inheritance_lis["name"], "script_file", inheritance_lis))
                edges_to_add.append((origin_id, inheritance_lis["name"], "Inheritance_Relation"))

    
    for node_id, node_type, node_properties in nodes_to_add:
        G.add_node(node_id, type=node_type, properties=node_properties)

    for source_id, target_id, edge_type in edges_to_add:
        G.add_edge(source_id, target_id, type=edge_type)

 
def AddLogicRelation(G, results_dir, scene_name, layer_lis):
    """
    Add logic relationships between GameObjects based on tag comparisons.
    For each CompareTag structure found in CodeStructure.json,
    find GameObjects with matching tags and create relationships.
    
    Args:
        G: NetworkX graph object
        results_dir: Path to the results directory containing gobj_tag.json
    """
    codeStructure_json = os.path.join(results_dir, 'script_detailed_info', 'mainResults', 'CodeStructure.json')
    gobj_tag_json = os.path.join(results_dir, f'{scene_name}_gobj_tag.json')
    gobj_layer_json = os.path.join(results_dir, f'{scene_name}_gobj_layer.json')
    
    # Check if gobj_tag.json exists, if not, generate it first
    #if not os.path.exists(gobj_tag_json):
       # print("gobj_tag.json not found. Generating it first...")
    ExtractAllGameObjectTags(G, results_dir, scene_name)
    ExtractAllGameObjectLayers(G, results_dir, scene_name, layer_lis)
    
    # Load the tag mapping from gobj_tag.json
    try:
        with open(gobj_tag_json, 'r', encoding='utf-8') as f:
            tag_to_gobj_ids = json.load(f)
        print(f"Loaded tag mapping from {gobj_tag_json}")
        with open(gobj_layer_json, 'r', encoding='utf-8') as f:
            layer_to_gobj_ids = json.load(f)
        print(f"Loaded layer mapping from {gobj_layer_json}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading gobj_tag.json: {e}")
        return
    
    with open(codeStructure_json, 'r') as f:
        read_json = json.load(f)
        structure_lis = read_json["StructureList"]
        edges_to_add = []
        nodes_to_add = []
        gobj_tag = None
        gobj_layer = None

        for struct in structure_lis:
            if struct["Name"] == "CompareTag" or struct["Name"] == "GameObjectFindGameObjectsWithTag" or struct["Name"] == "GameObjectFindWithTag":
                detail_struct = struct["Structure"]
                for detail in detail_struct:
                    is_literal_flag = False  # Reset for each detail to ensure independent processing
                    script_path = detail["Script"]
                    if len(detail["Arguments"]) > 0:
                        gobj_tag = detail["Arguments"][0]["Argument"]
                    else:
                        gobj_tag = detail["Invocation"].split("(")[1].split(",")[0]
                    # Clean the gobj_tag by removing quotes if present
                    if isinstance(gobj_tag, str):
                        if gobj_tag.count('"') >= 2:
                            gobj_tag = gobj_tag.strip('"\'')
                            is_literal_flag = True 
                            
                    script_id = None
                    
                    # Find the script node ID
                    for node_id, properties in G.nodes(data=True):
                        if properties['type'] == "script_file":
                            for prop, value in properties.items():
                                if prop == "properties":
                                    # Extract filename from script_path and compare with file_path
                                    script_filename = os.path.basename(script_path)
                                    if value["name"] == script_filename:
                                        script_id = node_id
                                        break
                    
                    if script_id:
                        for source, target, edge_data in G.edges(data=True):
                            if target == script_id and edge_data.get('type') == "Source_Code_File":
                                # Found the Mono_Component, now find its GameObject
                                mono_comp_id = source
                                if not is_literal_flag:
                                    prop = G.nodes[mono_comp_id]["properties"]["MonoBehaviour"]
                                    for p in prop:
                                        if gobj_tag in p:
                                            gobj_tag = p[gobj_tag]
                                            break
                                        
                                for gobj_source, gobj_target, gobj_edge_data in G.edges(data=True):
                                    gobj_source_id = None
                                    if gobj_target == mono_comp_id and gobj_edge_data.get('type') == "Has_Mono_Comp":
                                        gobj_source_id = gobj_source
  
                                    if gobj_source_id:
                                        # Find all GameObjects with matching tag using gobj_tag.json
                                        matching_gobj_ids = []
                                        if gobj_tag in tag_to_gobj_ids:
                                            matching_gobj_ids = tag_to_gobj_ids[gobj_tag]
                                            print(f"Found {len(matching_gobj_ids)} GameObjects with tag '{gobj_tag}'")
                                        else:
                                            print(f"No GameObjects found with tag '{gobj_tag}'")

                                        # Create relationships between source GameObject and all matching tagged GameObjects
                                        for matching_gobj_id in matching_gobj_ids:
                                            # Verify the matching GameObject exists in the graph
                                            if matching_gobj_id in G.nodes():
                                                # Special handling for Source Prefab GameObject
                                                if G.nodes[matching_gobj_id]['type'] == "Source Prefab GameObject":
                                                    # Search for PrefabInstance_INFO edge to find the actual instance
                                                    actual_source_id = []
                                                    for source, target, edge_data in G.edges(data=True):
                                                        if target == matching_gobj_id and edge_data.get('type') == "PrefabInstance_INFO" and source not in matching_gobj_ids:
                                                            actual_source_id.append(source)
                                                    
                                                    if actual_source_id != []:
                                                        for each_id in actual_source_id:
                                                            # Use the actual instance as the target for Tag_Logic_Relation
                                                            edges_to_add.append((gobj_source_id, each_id, "Tag_Logic_Relation"))

                                                else:
                                                    # Regular GameObject or Prefab GameObject
                                                    edges_to_add.append((gobj_source_id, matching_gobj_id, "Tag_Logic_Relation"))

            if struct["Name"] == "GameObjectFind":
                script_id = None
                source_id = None
                detail_struct = struct["Structure"]
                for detail in detail_struct:
                    script_path = detail["Script"]
                    if len(detail["Arguments"]) > 0:
                        gobj_name = detail["Arguments"][0]["Argument"]
                    else:
                        gobj_name = detail["Invocation"].split("(")[1].split(",")[0]
                    
                    for node_id, properties in G.nodes(data=True):
                        if properties['type'] == "script_file":
                            for prop, value in properties.items():
                                if prop == "properties":
                                    # Extract filename from script_path and compare with file_path
                                    script_filename = os.path.basename(script_path)
                                    if value["name"] == script_filename:
                                        script_id = node_id
                                        break
                    
                    if script_id:
                        for source, target, edge_data in G.edges(data=True):
                            if target == script_id and edge_data.get('type') == "Source_Code_File":
                                # Found the Mono_Component, now find its GameObject
                                mono_comp_id = source
                                for gobj_source, gobj_target, gobj_edge_data in G.edges(data=True):
                                    gobj_source_id = None
                                    if gobj_target == mono_comp_id and gobj_edge_data.get('type') == "Has_Mono_Comp":
                                        gobj_source_id = gobj_source
  
                                    if gobj_source_id:
                                        for node, properties in G.nodes(data=True):
                                            if "GameObject" in properties['type']:
                                                for prop, value in properties.items():
                                                    if prop == "properties":
                                                        for v in value:
                                                            if "m_Name" in v:
                                                                if str(v["m_Name"]) == str(gobj_name).strip('"\''):
                                                                    edges_to_add.append((gobj_source_id, node, "Gameobject_Find_Logic_Relation"))
                                                                    break

            if struct["Name"] == "AllInstantiate":
                detail_struct = struct["Structure"]
                for detail in detail_struct:
                    script_path = detail["Script"]
                    if len(detail["Arguments"]) > 0:
                        gobj_name = detail["Arguments"][0]["Argument"]
                    else:
                        gobj_name = detail["Invocation"].split("(")[1].split(",")[0]
                    argument_type = detail["FirstArgumentType"]
                    if argument_type != "GameObject":
                        continue
                    else:
                        script_id = None
                        source_id = None
                        for node_id, properties in G.nodes(data=True):
                            if properties['type'] == "script_file":
                                for prop, value in properties.items():
                                    if prop == "properties":
                                        # Extract filename from script_path and compare with file_path
                                        script_filename = os.path.basename(script_path)
                                        if value["name"] == script_filename:
                                            script_id = node_id
                                            break
                        


                        if script_id:
                            for source, target, edge_data in G.edges(data=True):
                                if target == script_id and edge_data.get('type') == "Source_Code_File":
                                    # Found the Mono_Component, now find its GameObject
                                    mono_comp_id = source
                                    for gobj_source, gobj_target, gobj_edge_data in G.edges(data=True):
                                        gobj_source_id = None
                                        if gobj_target == mono_comp_id and gobj_edge_data.get('type') == "Has_Mono_Comp":
                                            gobj_source_id = gobj_source
                                            gobj_target_id = gobj_target
                                        
                                        if gobj_source_id:
                                            for node_id, properties in G.nodes(data=True):
                                                if node_id == gobj_target_id:
                                                    properties = properties['properties']
                                                    if "MonoBehaviour" in properties:
                                                        mono_lis = properties["MonoBehaviour"]
                                                        for mono in mono_lis:
                                                            if gobj_name in mono:
                                                                fileID = mono[gobj_name][0]['fileID']
                                                                guid = mono[gobj_name][1]['guid']
                                                                gobj_info = FindPrefabInfo(fileID, guid, results_dir)
                                                                if gobj_info:
                                                                    for key in gobj_info.keys():
                                                                        if key != "id":
                                                                            comp_name = key
                                                                    gobj_id = gobj_info["id"]
                                                                    nodes_to_add.append((gobj_id, "Source Prefab GameObject", gobj_info[comp_name]))
                                                                    edges_to_add.append((gobj_source_id, gobj_id, "Instantiate_Logic_Relation"))
                                                                    break
                                                                else:
                                                                    for node, properties in G.nodes(data=True):
                                                                        if node == fileID:
                                                                            edges_to_add.append((gobj_source_id, node, "Instantiate_Logic_Relation"))
                                                                            break
            if struct["Name"] == "NameToLayer":
                detail_struct = struct["Structure"]
                for detail in detail_struct:
                    script_path = detail["Script"]
                    if len(detail["Arguments"]) > 0:
                        gobj_layer = detail["Arguments"][0]["Argument"]
                    # Clean the gobj_tag by removing quotes if present
                    if isinstance(gobj_layer, str):
                        gobj_layer = gobj_layer.strip('"\'')
                    script_id = None
                    
                    # Find the script node ID
                    for node_id, properties in G.nodes(data=True):
                        if properties['type'] == "script_file":
                            for prop, value in properties.items():
                                if prop == "properties":
                                    # Extract filename from script_path and compare with file_path
                                    script_filename = os.path.basename(script_path)
                                    if value["name"] == script_filename:
                                        script_id = node_id
                                        break
                    
                    if script_id:
                        for source, target, edge_data in G.edges(data=True):
                            if target == script_id and edge_data.get('type') == "Source_Code_File":
                                # Found the Mono_Component, now find its GameObject
                                mono_comp_id = source
                                for gobj_source, gobj_target, gobj_edge_data in G.edges(data=True):
                                    gobj_source_id = None
                                    if gobj_target == mono_comp_id and gobj_edge_data.get('type') == "Has_Mono_Comp":
                                        gobj_source_id = gobj_source
                                    
                                    if gobj_source_id:
                                        # Find all GameObjects with matching tag using gobj_tag.json
                                        matching_gobj_ids = []
                                        if gobj_layer in layer_to_gobj_ids:
                                            matching_gobj_ids = layer_to_gobj_ids[gobj_layer]
                                            print(f"Found {len(matching_gobj_ids)} GameObjects with layer '{gobj_layer}'")
                                        else:
                                            print(f"No GameObjects found with layer '{gobj_layer}'")

                                        # Create relationships between source GameObject and all matching tagged GameObjects
                                        for matching_gobj_id in matching_gobj_ids:
                                            # Verify the matching GameObject exists in the graph
                                            if matching_gobj_id in G.nodes():
                                                # Special handling for Source Prefab GameObject
                                                if G.nodes[matching_gobj_id]['type'] == "Source Prefab GameObject":
                                                    # Search for PrefabInstance_INFO edge to find the actual instance
                                                    actual_source_id = []
                                                    for source, target, edge_data in G.edges(data=True):
                                                        if target == matching_gobj_id and edge_data.get('type') == "PrefabInstance_INFO" and source not in matching_gobj_ids:
                                                            actual_source_id.append(source)
                                                    
                                                    if actual_source_id != []:
                                                        for each_id in actual_source_id:
                                                            # Use the actual instance as the target for Tag_Logic_Relation
                                                            edges_to_add.append((gobj_source_id, each_id, "Layer_Logic_Relation"))

                                                else:
                                                    # Regular GameObject or Prefab GameObject
                                                    edges_to_add.append((gobj_source_id, matching_gobj_id, "Layer_Logic_Relation"))
               


        for node_id, type, properties in nodes_to_add:
            G.add_node(node_id, type=type, properties=properties)

        # Add all collected tag-based relationships to the graph
        for source_id, target_id, edge_type in edges_to_add:
            G.add_edge(source_id, target_id, type=edge_type)


def AddGobjRelation(G, results_dir):
    codeStructure_json = os.path.join(results_dir, 'script_detailed_info', 'mainResults', 'CodeStructure.json')

    with open(codeStructure_json, 'r') as f:
        read_json = json.load(f)
        structure_lis = read_json["StructureList"]
        edges_to_add = []
        for struct in structure_lis:
            if struct["Name"] == "AllInstantiate":
                detail_struct = struct["Structure"]
                for detail in detail_struct:
                    script_path = detail["Script"]
                    if len(detail["Arguments"]) > 0:
                        gobj = detail["Arguments"][0]["Argument"]
                    else:
                        gobj = detail["Invocation"].split("(")[1].split(",")[0]
                    script_id = None
                    source_id = None
                    for node_id, properties in G.nodes(data=True):
                        if properties['type'] == "script_file":
                            for prop, value in properties.items():
                                if prop == "properties":
                                    if value["file_path"] == script_path + ".meta":
                                        script_id = node_id
                    if script_id:
                        for source, target, edge_data in G.edges(data=True):
                        # Check if the current edge matches the target_id and edge_type
                            if target == script_id and edge_data.get('type') == "Source_Code_File":
                                source_id = source
                        
                        if source_id:
                            for node_id, properties in G.nodes(data=True):
                                if node_id == source_id:
                                    for prop, value in properties.items():
                                        if prop == "properties":
                                            mono_lis = value["MonoBehaviour"]
                                            for mono in mono_lis:
                                                if gobj in mono.keys():
                                                    gobj_id = mono[gobj][0]['fileID']
                                                    for node, properties in G.nodes(data=True):
                                                        if properties.get('id') == gobj_id:
                                                            edges_to_add.append((source_id, gobj_id, "Mono_Comp_Attached_Gobj"))
                                                            break                        
                        # Add collected edges
                        for source_id, gobj_id, edge_type in edges_to_add:
                            G.add_edge(source_id, gobj_id, type=edge_type)

def analyze_prefab_asset(asset_path, results_dir):
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Walk through all directories under asset_path
    for root, dirs, files in os.walk(asset_path):
        for file in files:
            # Check if file is a prefab
            if file.endswith('.prefab') or file.endswith('.prefab.meta'):
                print(f"Analyzing prefab: {file}")
                prefab_path = os.path.join(root, file)

                # Create command to analyze the prefab
                command = f'"{config.unity_analyzer_path}" -a "{prefab_path}" -r "{results_dir}"'
                print(f"Analyzing prefab: {prefab_path}")
                
                # Execute the command
                try:
                    subprocess.run(command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    print(f"Error analyzing prefab {prefab_path}: {e}")
                    continue


def extract_gobj_settings(scene_json_path):
    """Extract GameObject information from the scene JSON file."""
    with open(scene_json_path, 'r') as json_file:
        data = json.load(json_file)

    all_scene_json = {
        "GameObjects": []
    }

    # Iterate over each component in the JSON data
    for component in data.get("COMPONENTS", []):
        if "GameObject" in component:
            game_object = {
                "id": component.get("id", ""),
                "GameObject": []
            }

            # Extract GameObject properties
            for key, value in component.items():
                if key == "GameObject":
                    for set in value:
                        set_store = sanitize_keys(set)
                        game_object["GameObject"].append(set_store)

            all_scene_json["GameObjects"].append(game_object)

    return all_scene_json

                            

def FindPrefabInfo(fileid, guid, results_dir):
    prefab_tag_dir = os.path.join(results_dir, 'scene_detailed_info', 'prefabResults')
    prefab_meta_dir = os.path.join(prefab_tag_dir, 'metaResults')
    prefab_main_dir = os.path.join(prefab_tag_dir, 'mainResults')
    
    for file in os.listdir(prefab_meta_dir):
        if file.endswith('.json'):
            meta_file_path = os.path.join(prefab_meta_dir, file)
            if True:
                with open(meta_file_path, 'r') as f:
                    meta_data = json.load(f)
                    if meta_data.get("guid") == guid:
                        prefab_name = meta_data.get("name")
                        with open(os.path.join(prefab_main_dir, prefab_name+".json"), 'r') as f:
                            prefab_data = json.load(f)
                            for component in prefab_data.get("COMPONENTS", []):
                                prefab_id = component.get("id", "")
                                if str(prefab_id).split(' stripped')[0] == str(fileid):
                                    return component
    return None


def AddColliderRelation(G, scene_settings):
    edges_to_add = []
    nodes_to_add = []
    other_comps = scene_settings["Other_Comps"]
    
    for other in other_comps:
        if "Collider" in other.keys():
            for key in other.keys():
                if key != 'id':
                    comp_name = key
            transform_lis = other[comp_name]
            transform_id = other["id"]
            if "stripped" in transform_id:
                for transform_set in transform_lis:
                    if "m_PrefabInstance" in transform_set:
                        instance = transform_set["m_PrefabInstance"][0]["fileID"]
                        for node, properties in G.nodes(data=True):
                            if "id" in properties and properties["id"] == str(instance):
                                nodes_to_add.append((node, comp_name, transform_lis))
                                edges_to_add.append((node, transform_id, "Has_Collider"))

    for node_id, node_type, node_properties in nodes_to_add:
        G.add_node(node_id, type=node_type, properties=node_properties)
        
    for source_id, target_id, edge_type in edges_to_add:
        G.add_edge(source_id, target_id, type=edge_type)

def FindAllPrefabComponents(guid, results_dir):
    prefab_tag_dir = os.path.join(results_dir, 'scene_detailed_info', 'prefabResults')
    prefab_meta_dir = os.path.join(prefab_tag_dir, 'metaResults')
    prefab_main_dir = os.path.join(prefab_tag_dir, 'mainResults')
    all_scene_json = {}
    
    for file in os.listdir(prefab_meta_dir):
        if file.endswith('.json'):
            meta_file_path = os.path.join(prefab_meta_dir, file)
            if True:
                with open(meta_file_path, 'r') as f:
                    meta_data = json.load(f)
                    if meta_data.get("guid") == guid:
                        prefab_name = meta_data.get("name")
                        with open(os.path.join(prefab_main_dir, prefab_name+".json"), 'r') as f:
                            prefab_data = json.load(f)
                            all_components = prefab_data.get("COMPONENTS", [])
                            all_scene_json = {
                                "GameObjects": [],
                                "MonoBehaviours": [],
                                "Other_Comps": []
                            }

                            # Iterate over each component in the JSON data
                            for component in all_components:
                                if "GameObject" in component:
                                    game_object = {
                                        "id": component.get("id", ""),
                                        "GameObject": []
                                    }

                                    # Extract GameObject properties
                                    for key, value in component.items():
                                        if key == "GameObject":
                                            for set in value:
                                                for key_child, val_child in set.items():
                                                    if key_child == 'm_Component':
                                                        m_component = {"m_Component": []}
                                                        for comp in val_child:
                                                            m_component["m_Component"].append({
                                                                "component":  # Changed key to a valid GML key
                                                                    [{
                                                                        "fileID": comp[key][0].get("fileID", "") for key in comp.keys()
                                                                    }]
                                                            })
                                                        game_object["GameObject"].append(m_component)
                                                    else:
                                                        game_object["GameObject"].append(set)

                                    all_scene_json["GameObjects"].append(game_object)

                                else:
                                    if "MonoBehaviour" in component:
                                        mono_behavior = {
                                            "id": component.get("id", ""),
                                            "MonoBehaviour": []
                                        }
                                        for key, value in component.items():
                                            if key == "MonoBehaviour":
                                                for set in value:
                                                    set_store = sanitize_keys(set)
                                                    mono_behavior["MonoBehaviour"].append(set_store)

                                        all_scene_json["MonoBehaviours"].append(mono_behavior)

                                    else:
                                        other_comp = {}
                                        for key, value in component.items():
                                            if key == 'id':
                                                other_comp[key] = value
                                            else:
                                                for set in value:
                                                    set_store = sanitize_keys(set)
                                                    if key in other_comp:
                                                        other_comp[key].append(set_store)
                                                    else:
                                                        other_comp[key] = []
                                                        other_comp[key].append(set_store)

                                        all_scene_json["Other_Comps"].append(other_comp)
                                        
                            return all_scene_json
                            
    return all_scene_json

def AddPrefabRelation(G, scene_settings, results_dir, prefab_id_lis, script_lis):
    edges_to_add = []
    nodes_to_add = []
    other_comps = scene_settings["Other_Comps"]
    prefab_instances = scene_settings["PrefabInstances"]

    for other in other_comps:
        prefab_id = []
        mono_lis = []
        collider_lis = []
        rigidbody_lis = []
                

        if "Transform" in other.keys():
            transform_lis = other["Transform"]
            transform_id = other["id"]
            
            if "stripped" in transform_id:
                for transform_set in transform_lis:
                    if "m_PrefabInstance" in transform_set:
                        instance = transform_set["m_PrefabInstance"][0]["fileID"]

                        if instance in prefab_id_lis:
                            for source, target, edge_data in G.edges(data=True):
                                if "id" in G.nodes[target]["properties"]:
                                    if G.nodes[target]["properties"]["id"] == str(instance) and edge_data.get('type') == "PrefabInstance_INFO":
                                        nodes_to_add.append((transform_id, "Transform", other))
                                        edges_to_add.append((source, transform_id, "Has_Other_Comp"))
                    
                        else:
                            if len(transform_lis[0]["m_CorrespondingSourceObject"]) > 1:
                                if "fileID" in transform_lis[0]["m_CorrespondingSourceObject"][0] and "guid" in transform_lis[0]["m_CorrespondingSourceObject"][1]:
                                    prefab_source_fileid = transform_lis[0]["m_CorrespondingSourceObject"][0]["fileID"]
                                    prefab_source_guid = transform_lis[0]["m_CorrespondingSourceObject"][1]["guid"]
                                    prefab_source_info = FindPrefabInfo(prefab_source_fileid, prefab_source_guid, results_dir)
                                    

                                    if prefab_source_info:
                                        prefab_source_lis = prefab_source_info["Transform"]
                                        prefab_source_id = prefab_source_info["id"]
                                        
                                        if "stripped" in prefab_source_id:
                                            for prefab_source_set in prefab_source_lis:
                                                if "m_CorrespondingSourceObject" in prefab_source_set:
                                                    if len(prefab_source_set["m_CorrespondingSourceObject"]) > 1:
                                                        if "fileID" in prefab_source_set["m_CorrespondingSourceObject"][0] and "guid" in prefab_source_set["m_CorrespondingSourceObject"][1]:
                                                            prefab_guid = prefab_source_set["m_CorrespondingSourceObject"][1]["guid"]
                                                            comp_fileid = prefab_source_set["m_CorrespondingSourceObject"][0]["fileID"]
                                                            origin_prefab_info = FindPrefabInfo(comp_fileid, prefab_guid, results_dir)
                                                            

                                                            if origin_prefab_info:
                                                                for key in origin_prefab_info.keys():
                                                                    if key != 'id':
                                                                        comp_name = key
                                                                if "GameObject" in comp_name:
                                                                    comp_lis = origin_prefab_info["GameObject"]
                                                                    comp_gobj_id = origin_prefab_info["id"]
                                                                    set_store = sanitize_keys(comp_lis)
                                                                    for set in set_store:
                                                                        if "m_Component" in set:
                                                                            comp_lis = set["m_Component"]
                                                                            for comp in comp_lis:
                                                                                fileid = comp["component"][0].get("fileID")
                                                                                prefab_id.append((comp_gobj_id, fileid, comp_lis))

                                                if "m_PrefabInstance" in prefab_source_set:
                                                    instance_prefab = prefab_source_set["m_PrefabInstance"][0]["fileID"]
                                                    prefab_instance_source = FindPrefabInfo(instance_prefab, prefab_source_guid, results_dir)


                                                    if 'PrefabInstance' in prefab_instance_source:
                                                        prefab_comp = sanitize_keys(prefab_instance_source["PrefabInstance"])
                                                        prefab_comp_id = prefab_instance_source["id"]
                                                        nodes_to_add.append((prefab_comp_id, "Source Prefab GameObject", prefab_comp))
                                                        nodes_to_add.append((transform_id, "Transform", other))
                                                        for prefab in prefab_comp:
                                                            if "m_Modification" in prefab:
                                                                for mod in prefab["m_Modification"]:
                                                                    if "m_AddedComponents" in mod:
                                                                        if mod["m_AddedComponents"] != "[]":
                                                                            added_components = mod["m_AddedComponents"]
                                                                            for added_comp in added_components:
                                                                                if "addedObject" in added_comp.keys():
                                                                                    added_file_id = \
                                                                                    added_comp["addedObject"][0][
                                                                                        "fileID"]
                                                                                    prefab_id.append((prefab_comp_id, added_file_id))

                                                                    if "m_RemovedComponents" in mod:
                                                                        if mod["m_RemovedComponents"] != "[]":
                                                                            for i in range(
                                                                                    len(mod["m_RemovedComponents"])):
                                                                                if "fileID" in \
                                                                                        mod["m_RemovedComponents"][
                                                                                            i].keys():
                                                                                    remove_fileid = \
                                                                                    mod["m_RemovedComponents"][i][
                                                                                        "fileID"]
                                                                                    if remove_fileid in prefab_id:
                                                                                        prefab_id.remove((prefab_comp_id, remove_fileid))
                                                    
                                                    for comp in prefab_instances:
                                                        other_id = comp["id"]
                                                        if str(other_id) == str(instance):
                                                            prefab_id_lis.append(other_id)
                                                            edges_to_add.append((other_id, transform_id, "Has_Other_Comp"))

                                                            for prefab, fileid in prefab_id:
                                                                origin_comp = FindPrefabInfo(fileid, prefab_source_guid, results_dir)
                                                                if "MonoBehaviour" in origin_comp:
                                                                    prefab_mono_lis = sanitize_keys(origin_comp)
                                                                    prefab_mono_id = origin_comp["id"]
                                                                    for mono in prefab_mono_lis["MonoBehaviour"]:
                                                                        if "m_Script" in mono:
                                                                            mono_guid = mono["m_Script"][1]["guid"]
                                                                            nodes_to_add.append((prefab_mono_id, "Mono_Component", prefab_mono_lis))
                                                                            edges_to_add.append((other_id, prefab, "PrefabInstance_INFO"))
                                                                            

                                                                            if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                                                                edges_to_add.append((other_id, prefab_mono_id, "Has_Event_Trigger"))
                                                                            
                                                                            else:
                                                                                edges_to_add.append((other_id, prefab_mono_id, "Has_Mono_Comp"))


                                                                            for script in script_lis:
                                                                                for key, value in script.items():
                                                                                    if value == None:
                                                                                        script[key] = ""

                                                                                if str(mono_guid) == str(script["guid"]):
                                                                                    nodes_to_add.append((mono_guid, "script_file", script))
                                                                                    edges_to_add.append((prefab_mono_id, mono_guid, "Source_Code_File"))

                                                                else:
                                                                    for key in origin_comp.keys():
                                                                        if key != 'id':
                                                                            comp_name = key
                                                                    if "Collider" in comp_name:                                                                            
                                                                        prefab_collider_lis = sanitize_keys(origin_comp[comp_name])
                                                                        prefab_collider_id = origin_comp["id"]
                                                                        
                                                                        nodes_to_add.append((prefab_collider_id, comp_name, prefab_collider_lis))
                                                                        edges_to_add.append((other_id, prefab_collider_id, "Has_Collider"))
                                                                    if "Rigidbody" in comp_name:
                                                                        prefab_rigidbody_lis = sanitize_keys(origin_comp[comp_name])
                                                                        prefab_rigidbody_id = origin_comp["id"]
                                                                        nodes_to_add.append((prefab_rigidbody_id, comp_name, prefab_rigidbody_lis))
                                                                        edges_to_add.append((other_id, prefab_rigidbody_id, "Has_Rigidbody"))

                                        else:
                                            mono_removed = []                 
                                            for prefab_source_set in prefab_source_lis:
                                                if "m_GameObject" in prefab_source_set:
                                                    prefab_source_gameobject = prefab_source_set["m_GameObject"][0]["fileID"]
                                                    prefab_source_gameobject_info = FindPrefabInfo(prefab_source_gameobject, prefab_source_guid, results_dir)

                                                    if prefab_source_gameobject_info:
                                                        prefab_source_gameobject_lis = sanitize_keys(prefab_source_gameobject_info["GameObject"])
                                                        nodes_to_add.append((prefab_source_gameobject, "Source Prefab GameObject", prefab_source_gameobject_lis))
                                                        nodes_to_add.append((transform_id, "Transform", other))
                                                        
                                                        for prefab_source_comp in prefab_source_gameobject_lis:
                                                            if "m_Component" in prefab_source_comp:
                                                                comp_lis = sanitize_keys(prefab_source_comp["m_Component"])
                                                                for comp in comp_lis:
                                                                    comp_id = comp["component"][0].get("fileID")
                                                                    comp_source_info = FindPrefabInfo(comp_id, prefab_source_guid, results_dir)
                                                                    if "MonoBehaviour" in comp_source_info:
                                                                        prefab_mono_lis = comp_source_info
                                                                        prefab_mono_id = comp_source_info["id"]
                                                                        for mono in prefab_mono_lis["MonoBehaviour"]:
                                                                            if "m_Script" in mono:
                                                                                mono_guid = mono["m_Script"][1]["guid"]
                                                                                nodes_to_add.append((prefab_mono_id, "Mono_Component", prefab_mono_lis))
                                                                                if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                                                                    edges_to_add.append((prefab_source_gameobject, comp_id, "Has_Event_Trigger"))
                                                                                    mono_lis.append((prefab_mono_id, "Has_Event_Trigger"))
                                                                                else:
                                                                                    edges_to_add.append((prefab_source_gameobject, comp_id, "Has_Mono_Comp"))
                                                                                    mono_lis.append((prefab_mono_id, "Has_Mono_Comp"))

                                                                                for script in script_lis:
                                                                                    if str(mono_guid) == str(script["guid"]):
                                                                                        nodes_to_add.append((mono_guid, "script_file", script))
                                                                                        edges_to_add.append((comp_id, mono_guid, "Source_Code_File"))
                                                                                        
                                                                    else:
                                                                        for key in comp_source_info.keys():
                                                                            if key != 'id':
                                                                                comp_name = key
                                                                        if "Collider" in comp_name:
                                                                            prefab_collider_lis = sanitize_keys(comp_source_info)
                                                                            prefab_collider_id = comp_source_info["id"]
                                                                            collider_lis.append(prefab_collider_id)
                                                                            nodes_to_add.append((prefab_collider_id, comp_name, prefab_collider_lis))
                                                                            edges_to_add.append((prefab_source_gameobject, prefab_collider_id, "Has_Collider"))
                                                                        
                                                                        if "Rigidbody" in comp_name:
                                                                            prefab_rigidbody_lis = sanitize_keys(comp_source_info)
                                                                            prefab_rigidbody_id = comp_source_info["id"]
                                                                            rigidbody_lis.append(prefab_rigidbody_id)
                                                                            nodes_to_add.append((prefab_rigidbody_id, comp_name, prefab_rigidbody_lis))
                                                                            edges_to_add.append((prefab_source_gameobject, prefab_rigidbody_id, "Has_Rigidbody"))
                                          

                                                        for comp in prefab_instances:
                                                            other_id = comp["id"]
                                                            if str(other_id) == str(instance):
                                                                prefab_id_lis.append(other_id)
                                                                edges_to_add.append((other_id, prefab_source_gameobject, "PrefabInstance_INFO"))
                                                                edges_to_add.append((other_id, transform_id, "Has_Other_Comp"))
                                                                nodes_to_add.append((other_id, comp_name, sanitize_keys(comp)))
                                                                prefab_comp = comp["PrefabInstance"]
                                                                prefab_comp_id = comp["id"]

                                                                for prefab in prefab_comp:
                                                                    if "m_Modification" in prefab:
                                                                        for mod in prefab["m_Modification"]:
                                                                            if "m_RemovedComponents" in mod:
                                                                                if mod["m_RemovedComponents"] != "[]":
                                                                                    for i in range(
                                                                                            len(mod["m_RemovedComponents"])):
                                                                                        if "fileID" in \
                                                                                                mod["m_RemovedComponents"][
                                                                                                    i].keys():
                                                                                            remove_fileid = \
                                                                                            mod["m_RemovedComponents"][i][
                                                                                                "fileID"]
                                                                                            mono_removed.append(remove_fileid)
                                                                
                                                                if mono_lis:
                                                                    for mono_id, mono_type in mono_lis:
                                                                        if mono_id not in mono_removed:
                                                                            edges_to_add.append((other_id, mono_id, mono_type))
                                                                if collider_lis:
                                                                    for collider_id in collider_lis:
                                                                        if collider_id not in mono_removed:
                                                                            edges_to_add.append((other_id, collider_id, "Has_Collider"))
                                                                if rigidbody_lis:
                                                                    for rigidbody_id in rigidbody_lis:
                                                                        if rigidbody_id not in mono_removed:
                                                                            edges_to_add.append((other_id, rigidbody_id, "Has_Rigidbody"))

                                                        break          
                                                       
                                        
    for node_id, node_type, node_properties in nodes_to_add:
        G.add_node(node_id, type=node_type, properties=node_properties)
        
    for source_id, target_id, edge_type in edges_to_add:
        G.add_edge(source_id, target_id, type=edge_type)

def CombinePrefabRelation(G, results_dir):
    edges_to_add = []
    already_processed = []
    has_mono_comp = []
    relations_to_add = ["Has_Collider", "Has_Rigidbody", "Has_Event_Trigger"]
    for ss, tt, ee in G.edges(data=True):
        if ee.get('type') == "Has_Mono_Comp":
            has_mono_comp.append(ss)

    for s, t, e in G.edges(data=True):
        if e.get('type') == "PrefabInstance_INFO" and s not in already_processed and s in has_mono_comp:
            already_processed.append(s)
            for source, target, edge_data in G.edges(data=True):
                if source != s and target == t and edge_data.get('type') == "PrefabInstance_INFO":
                    for s_n, s_p, s_e in G.edges(data=True):
                        if s_n == source and s_e.get('type') in relations_to_add:
                            edges_to_add.append((s, s_p, s_e.get('type')))
            
    for source, target, edge_type in edges_to_add:
        G.add_edge(source, target, type=edge_type)


def create_scene_database(scene_paths, project_path, results_dir, script_lis, layer_lis):
    """Create a database in JSON format for each scene file."""
    scene_db_dir = os.path.join(results_dir, 'scene_detailed_info', 'mainResults')
    
    for scene_path in scene_paths:
        print(f"Creating scene database for {scene_path}")
        scene_json_path = os.path.join(scene_db_dir, os.path.basename(scene_path))
        if not os.path.exists(scene_json_path):
            print(f"Scene JSON file not found: {scene_json_path}")
            continue

        # Extract GameObject information
        scene_settings = extract_scene_settings(scene_json_path)
        # Create a directed graph using networkx
        G = nx.DiGraph()

        # Save the extracted data in a new JSON file
        db_file_path = os.path.join(scene_db_dir, os.path.basename(scene_path) + '_database.json')
        with open(db_file_path, 'w') as db_file:
            json.dump(scene_settings, db_file, indent=2)

        game_objects = scene_settings["GameObjects"]
        mono_behaviours = scene_settings["MonoBehaviours"]
        other_comps = scene_settings["Other_Comps"]
        prefab_instances = scene_settings["PrefabInstances"]

        added_fileid_lis = []
        remove_fileid_lis = []
        for prefab_instance in prefab_instances:
            prefab_instance_id = prefab_instance["id"]
            prefab_instance_lis = prefab_instance["PrefabInstance"]
            G.add_node(prefab_instance_id, type="PrefabInstance", properties=sanitize_keys(prefab_instance_lis))

            for prefab in prefab_instance_lis:
                if "m_Modification" in prefab:
                    for mod_set in prefab["m_Modification"]:
                        if "m_Modifications" in mod_set:
                            for mod in mod_set["m_Modifications"]:
                                if "m_AddedComponents" in mod:
                                    if mod["m_AddedComponents"] != "[]":
                                        added_components = mod["m_AddedComponents"]
                                        for added_comp in added_components:
                                            if "addedObject" in added_comp.keys():
                                                added_file_id = added_comp["addedObject"][0]["fileID"]
                                                added_fileid_lis.append(added_file_id)

                                if "m_RemovedComponents" in mod:
                                    if mod["m_RemovedComponents"] != "[]":
                                        for i in range(len(mod["m_RemovedComponents"])):
                                            if "fileID" in mod["m_RemovedComponents"][i].keys():
                                                remove_fileid = mod["m_RemovedComponents"][i]["fileID"]
                                                remove_fileid_lis.append(remove_fileid)
                                
                                if added_fileid_lis:
                                    for mono_comp in mono_behaviours:
                                        if mono_comp["id"] in added_fileid_lis:
                                            nodes_to_add.append((mono_comp["id"], "Mono_Component", mono_comp))
                                            edges_to_add.append((prefab_instance_id, mono_comp["id"], "Has_Mono_Comp"))
                                            mono_set = sanitize_keys(mono_comp["MonoBehaviour"])
                                            for mono in mono_set:
                                                if "m_Script" in mono:
                                                    mono_guid = mono["m_Script"][1]["guid"]
                                                    if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                                        edges_to_add.append((prefab_instance_id, mono_comp["id"], "Has_Event_Trigger"))
                                                    else:
                                                        edges_to_add.append((prefab_instance_id, mono_comp["id"], "Has_Mono_Comp"))
                                                    for script in script_lis:
                                                        if str(mono_guid) == str(script["guid"]):
                                                            nodes_to_add.append((mono_guid, "script_file", script))
                                                            edges_to_add.append((mono_comp["id"], mono_guid, "Source_Code_File"))

                            for mod_1 in mod_set["m_Modifications"]:    
                                if "target" in mod_1:
                                    target_fileID = mod_1["target"][0]["fileID"]
                                    target_guid = mod_1["target"][1]["guid"]
                                    prefab_info = FindPrefabInfo(target_fileID, target_guid, results_dir)
                                    if prefab_info:
                                        gameobject_id = ""
                                        gameobject_info_set = None
                                        if "GameObject" in prefab_info:
                                            gameobject_info_set = sanitize_keys(prefab_info["GameObject"])
                                            gameobject_id = prefab_info["id"]
                                            G.add_node(gameobject_id, type="Source Prefab GameObject", properties=gameobject_info_set)
                                            G.add_edge(prefab_instance_id, gameobject_id, type="PrefabInstance_INFO")
                                            
                                        if "Transform" in prefab_info:
                                            transform_lis = prefab_info["Transform"]
                                            transform_id = prefab_info["id"]
                                            for transform in transform_lis:
                                                if "m_GameObject" in transform:
                                                    gameobject_id = transform["m_GameObject"][0]["fileID"]
                                                    gameobject_info = FindPrefabInfo(gameobject_id, target_guid, results_dir)
                                                    if gameobject_info:
                                                        gameobject_info_set = sanitize_keys(gameobject_info["GameObject"])
                                                        G.add_node(gameobject_id, type="Source Prefab GameObject", properties=gameobject_info_set)
                                                        G.add_edge(prefab_instance_id, gameobject_id, type="PrefabInstance_INFO")
                                                
                                        if gameobject_info_set and gameobject_id:
                                            gameobject_set = gameobject_info_set
                                            for gobj in gameobject_set:
                                                if "m_Component" in gobj:
                                                    comp_lis = gobj["m_Component"]
                                                    for comp in comp_lis:
                                                        file_id = comp["component"][0].get("fileID")
                                                        comp_info = FindPrefabInfo(file_id, target_guid, results_dir)
                                                        if comp_info:
                                                            other_id = comp_info["id"]
                                                            if 'MonoBehaviour' in comp_info:
                                                                mono_lis = comp_info["MonoBehaviour"]
                                                                mono_id = comp_info["id"]
                                                                G.add_node(mono_id, type="Mono_Component", properties=sanitize_keys(mono_lis))
                                                                
                                                                for mono in mono_lis:
                                                                    if "m_Script" in mono:
                                                                        mono_guid = mono["m_Script"][1]["guid"]
                                                                        if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                                                            G.add_edge(gameobject_id, other_id, type="Has_Event_Trigger")
                                                                            if mono_id not in remove_fileid_lis:
                                                                                G.add_edge(prefab_instance_id, mono_id, type="Has_Mono_Comp")
                                                                        else:
                                                                            G.add_edge(gameobject_id, other_id, type="Has_Mono_Comp")
                                                                            if mono_id not in remove_fileid_lis:
                                                                                G.add_edge(prefab_instance_id, mono_id, type="Has_Mono_Comp")
                                                                        for script in script_lis:
                                                                            if str(mono_guid) == str(script["guid"]):
                                                                                G.add_node(mono_guid, type="script_file", properties=script)
                                                                                G.add_edge(other_id, mono_guid, type="Source_Code_File")
                                                            else:
                                                                for key in comp_info.keys():
                                                                    if key != 'id':
                                                                        comp_name = key
                                                                if "Collider" in comp_name:
                                                                    prefab_collider_lis = sanitize_keys(comp_info[comp_name])
                                                                    prefab_collider_id = comp_info["id"]
                                                                    G.add_node(prefab_collider_id, type=comp_name, properties=prefab_collider_lis)
                                                                    G.add_edge(gameobject_id, prefab_collider_id, type="Has_Collider")
                                                                    if prefab_collider_id not in remove_fileid_lis:
                                                                        G.add_edge(prefab_instance_id, prefab_collider_id, type="Has_Collider")
                                                                
                                                                if "Rigidbody" in comp_name:
                                                                    prefab_rigidbody_lis = sanitize_keys(comp_info[comp_name])
                                                                    prefab_rigidbody_id = comp_info["id"]
                                                                    G.add_node(prefab_rigidbody_id, type=comp_name, properties=prefab_rigidbody_lis)
                                                                    G.add_edge(gameobject_id, prefab_rigidbody_id, type="Has_Rigidbody")
                                                                    if prefab_rigidbody_id not in remove_fileid_lis:
                                                                        G.add_edge(prefab_instance_id, prefab_rigidbody_id, type="Has_Rigidbody")

                                                                if comp_name == "Transform":
                                                                    transform_lis = sanitize_keys(comp_info["Transform"])
                                                                    transform_id = comp_info["id"]
                                                                    G.add_node(transform_id, type=comp_name, properties=sanitize_keys(comp_info))
                                                                    G.add_edge(gameobject_id, transform_id, type="Has_Other_Comp")
                                                                    if transform_id not in remove_fileid_lis:
                                                                        G.add_edge(prefab_instance_id, transform_id, type="Has_Other_Comp")
                                        break                            


        for gobjs in game_objects:
            fileid_lis = []
            prefab_id = []
            gobj_set = gobjs["GameObject"]
            gobj_id = gobjs["id"]
            if "stripped" in gobj_id:
                G.add_node(gobj_id, type="Prefab GameObject", properties=gobj_set)
            else:
                G.add_node(gobj_id, type="GameObject", properties=gobj_set)

            for set in gobj_set:
                if "m_Component" in set:
                    comp_lis = set["m_Component"]
                    for comp in comp_lis:
                        file_id = comp["component"][0].get("fileID")
                        fileid_lis.append(file_id)
                    
                    for monos in mono_behaviours:
                        mono_id = monos["id"]
                        mono_guid = None
                        for mono_set in monos["MonoBehaviour"]:
                            if "m_Script" in mono_set.keys():
                                mono_guid_set = mono_set["m_Script"]
                                for guid_set in mono_guid_set:
                                    if "guid" in guid_set.keys():
                                        mono_guid = guid_set["guid"]
                        
                        if mono_id in fileid_lis:
                            G.add_node(mono_id, type="Mono_Component", properties=monos)

                            if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                G.add_edge(gobj_id, mono_id, type="Has_Event_Trigger")
                            else:
                                G.add_edge(gobj_id, mono_id, type="Has_Mono_Comp")

                            for script in script_lis:
                                for key, value in script.items():
                                    if value ==  None:
                                        script[key] = ""

                                if mono_guid == script["guid"]:
                                    G.add_node(mono_guid, type="script_file", properties=script)
                                    G.add_edge(mono_id, mono_guid, type="Source_Code_File")

                    for other in other_comps:
                        other_id = other["id"]
                        if other_id in fileid_lis:
                            comp_name = ''
                            for key in other.keys():
                                if key != 'id':
                                    comp_name = key
                            if 'Transform' in comp_name:
                                G.add_node(other_id, type=comp_name, properties=other)
                                G.add_edge(gobj_id, other_id, type="Has_Other_Comp")
                            
                            if 'Collider' in comp_name:
                                G.add_node(other_id, type=comp_name, properties=other)
                                G.add_edge(gobj_id, other_id, type="Has_Collider")
                            
                            if 'Rigidbody' in comp_name:
                                G.add_node(other_id, type=comp_name, properties=other)
                                G.add_edge(gobj_id, other_id, type="Has_Rigidbody")
                

                if "m_PrefabInstance" in set:
                    instance = set["m_PrefabInstance"][0]["fileID"]

                    for other in prefab_instances:
                        comp_id = other["id"]
                        if str(comp_id) == str(instance):
                            comp_name = ''
                            for key in other.keys():
                                if key != 'id':
                                    comp_name = key
                            if 'PrefabInstance' in comp_name:
                                G.add_edge(gobj_id, comp_id, type="PrefabInstance_INFO")

                    for other in other_comps:
                        other_id = other["id"]
                        for key in other.keys():
                            if key != 'id':
                                comp_name = key
                                if "stripped" in other["id"]:
                                    for detail in other[comp_name]:
                                        if "m_PrefabInstance" in detail:
                                            transform_instance = detail["m_PrefabInstance"][0]["fileID"]
                                            if str(transform_instance) == str(instance):
                                                G.add_node(other_id, type=comp_name, properties=other)
                                                G.add_edge(gobj_id, other_id, type="Has_Other_Comp")
                                else:
                                    for detail in other[comp_name]:
                                        if "m_GameObject" in detail:
                                            gameobject_id = detail["m_GameObject"][0]["fileID"]
                                            gobj_id_base = gobj_id.split("stripped")[0].strip()
                                            if str(gameobject_id).strip() == gobj_id_base:                                         
                                                if 'Collider' in comp_name:
                                                    G.add_node(other_id, type=comp_name, properties=other)
                                                    G.add_edge(gobj_id, other_id, type="Has_Collider")
                                                
                                                if 'Rigidbody' in comp_name:
                                                    G.add_node(other_id, type=comp_name, properties=other)
                                                    G.add_edge(gobj_id, other_id, type="Has_Rigidbody")

                                                    
                
            if prefab_id:
                for monos in mono_behaviours:
                    mono_id = monos["id"]
                    for mono_set in monos["MonoBehaviour"]:
                        if "m_Script" in mono_set.keys():
                            mono_guid_set = mono_set["m_Script"]
                            for guid_set in mono_guid_set:
                                if "guid" in guid_set.keys():
                                    mono_guid = guid_set["guid"]

                        if mono_id in prefab_id:
                            G.add_node(mono_id, type="Mono_Component", properties=monos)

                            if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                                G.add_edge(gobj_id, mono_id, type="Has_Event_Trigger")
                            else:
                                G.add_edge(gobj_id, mono_id, type="Has_Mono_Comp")

                            for script in script_lis:
                                for key, value in script.items():
                                    if value == None:
                                        script[key] = ""

                                if mono_guid == script["guid"]:
                                    G.add_node(mono_guid, type="script_file", properties=script)
                                    G.add_edge(mono_id, mono_guid, type="Source_Code_File")
 
        edges_to_add = []
        nodes_to_add = []
        for mono in mono_behaviours:
            mono_id = mono["id"]
            found_mono_gameobject = False
            
            for mono_set in mono["MonoBehaviour"]:
                if 'm_GameObject' in mono_set.keys():
                    mono_gameobject = mono_set["m_GameObject"][0]["fileID"]
                    for node, properties in G.nodes(data=True):
                        if str(node).split(" stripped")[0] == str(mono_gameobject):
                            nodes_to_add.append((mono_id, "Mono_Component", mono))
                            found_mono_gameobject = True
                            break

                if 'm_Script' in mono_set.keys():
                    mono_script = mono_set["m_Script"]
                    for script in mono_script:
                        if "guid" in script.keys():
                            mono_guid = script["guid"]
            
            if found_mono_gameobject:
                if mono_guid == "d0b148fe25e99eb48b9724523833bab1":
                    edges_to_add.append((node, mono_id, "Has_Event_Trigger"))
                else:
                    edges_to_add.append((node, mono_id, "Has_Mono_Comp"))

                for script in script_lis:
                    for key, value in script.items():
                        if value == None:
                            script[key] = ""

                    if mono_guid == script["guid"]:
                        nodes_to_add.append((mono_guid, "script_file", script))
                        edges_to_add.append((mono_id, mono_guid, "Source_Code_File"))
            
            
            for node_id, node_type, node_properties in nodes_to_add:
                G.add_node(node_id, type=node_type, properties=node_properties)
            
            for source_id, target_id, edge_type in edges_to_add:
                G.add_edge(source_id, target_id, type=edge_type)

        AddGobjRelation(G, results_dir)
        AddColliderRelation(G, scene_settings)

        scene_name = os.path.basename(scene_path).split('.')[0]

        AddLogicRelation(G, results_dir, scene_name, layer_lis)
        AddChildRelation(G)
        AddmonoRelation(G, results_dir)

        CombinePrefabRelation(G, results_dir)

        # Clean up graph keys before saving to GML
        sanitize_graph_keys(G)

        # Save the graph in a file
        graph_file_path = os.path.join(scene_db_dir, os.path.basename(scene_path) + '_graph.gml')
        nx.write_gml(G, graph_file_path)
        print(f"Scene database created: {db_file_path}")


def sanitize_graph_keys(G):
    """
    Clean up invalid keys in graph node and edge attributes for GML export.
    First applies Unity-specific sanitization (sanitize_keys), then GML format sanitization.
    GML format requires valid identifier keys without spaces or special characters.
    """
    def clean_dict_keys(data):
        """Recursively clean keys in nested dictionaries and lists for GML format"""
        if isinstance(data, dict):
            cleaned_data = {}
            for key, value in data.items():
                # Clean the key for GML format
                cleaned_key = key.strip().replace(' ', '_').replace('-', '_')
                if cleaned_key and cleaned_key != '_':
                    # Recursively clean nested values
                    cleaned_data[cleaned_key] = clean_dict_keys(value)
            return cleaned_data
        elif isinstance(data, list):
            # Clean each item in the list
            return [clean_dict_keys(item) for item in data]
        else:
            # Return primitive values as-is
            return data
    
    def apply_unity_sanitization(data):
        """Apply Unity-specific sanitization to data"""
        if isinstance(data, dict):
            # Apply sanitize_keys to each dictionary in the data
            sanitized_data = {}
            for key, value in data.items():
                sanitized_data[key] = apply_unity_sanitization(value)
            return sanitize_keys(sanitized_data)
        elif isinstance(data, list):
            # Apply sanitization to each item in the list
            return [apply_unity_sanitization(item) for item in data]
        else:
            # Return primitive values as-is
            return data
    
    # Clean node attributes
    for node_id, node_data in G.nodes(data=True):
        if 'properties' in node_data:
            # First apply Unity-specific sanitization, then GML format sanitization
            node_data['properties'] = apply_unity_sanitization(node_data['properties'])
            node_data['properties'] = clean_dict_keys(node_data['properties'])
    
    # Clean edge attributes
    for source, target, edge_data in G.edges(data=True):
        # First apply Unity-specific sanitization, then GML format sanitization
        cleaned_edge_data = apply_unity_sanitization(edge_data)
        cleaned_edge_data = clean_dict_keys(cleaned_edge_data)
        # Update edge data
        G[source][target].clear()
        G[source][target].update(cleaned_edge_data)


def ExtractAllGameObjectLayers(G, results_dir, scene_name, layer_lis):
    layer_to_gobj_ids = {}

    # Iterate through all nodes in the graph
    for node_id, properties in G.nodes(data=True):
        if properties['type'] in ["GameObject", "Prefab GameObject"]:
            # For regular GameObject and Prefab GameObject, check m_TagString directly
            if 'properties' in properties:
                for prop_set in properties['properties']:
                    if isinstance(prop_set, dict) and 'm_Layer' in prop_set:
                        layer_index = prop_set['m_Layer']
                        # Convert to int if it's a string (GML读取时会将数字转为字符串)
                        try:
                            if isinstance(layer_index, str):
                                layer_index = int(layer_index)
                            if isinstance(layer_index, int) and 0 <= layer_index < len(layer_lis):
                                layer_name = layer_lis[layer_index]
                                if layer_name not in layer_to_gobj_ids:
                                    layer_to_gobj_ids[layer_name] = []
                                if node_id not in layer_to_gobj_ids[layer_name]:
                                    layer_to_gobj_ids[layer_name].append(node_id)
                        except (ValueError, IndexError):
                            pass  # Skip invalid layer index
                        break
          
        
        elif properties['type'] == "PrefabInstance":
            # For PrefabInstance, first check m_Modifications for m_TagString
            tag_found = False
            if 'properties' in properties and 'PrefabInstance' in properties['properties']:
                prefab_info_lis = properties["properties"]["PrefabInstance"]
                for prefab_set in prefab_info_lis:
                    if "m_Modification" in prefab_set:
                        mod_prefab_set = prefab_set["m_Modification"]
                        for mod_set in mod_prefab_set:
                            if "m_Modifications" in mod_set:
                                for i in range(len(mod_set["m_Modifications"])):
                                    mod_set_child = mod_set["m_Modifications"][i]
                                    if "propertyPath" in mod_set_child:
                                        if mod_set_child["propertyPath"] == "m_Layer":
                                            # Found m_Layer modification
                                            if i + 1 < len(mod_set["m_Modifications"]):
                                                m_layer_index = mod_set["m_Modifications"][i+1]["value"]
                                                try:
                                                    if isinstance(m_layer_index, str):
                                                        m_layer_index = int(m_layer_index)
                                                    if isinstance(m_layer_index, int) and 0 <= m_layer_index < len(layer_lis):
                                                        m_layer_name = layer_lis[m_layer_index]
                                                        if m_layer_name not in layer_to_gobj_ids:
                                                            layer_to_gobj_ids[m_layer_name] = []
                                                        # Add node_id only if it's not already in the list (avoid duplicates)
                                                        if node_id not in layer_to_gobj_ids[m_layer_name]:
                                                            layer_to_gobj_ids[m_layer_name].append(node_id)
                                                        tag_found = True
                                                except (ValueError, IndexError):
                                                    pass  # Skip invalid layer index
                                                break
                                    if tag_found:
                                        break
                                if tag_found:
                                    break
                        if tag_found:
                            break
            
            # If no tag found in modifications, look for Source Prefab GameObject
            if not tag_found:
                # Find Source Prefab GameObject connected via PrefabInstance_INFO edge
                for source, target, edge_data in G.edges(data=True):
                    if source == node_id and edge_data.get('type') == "PrefabInstance_INFO":
                        source_prefab_id = target
                        # Check if source is Source Prefab GameObject
                        if source_prefab_id in G.nodes() and G.nodes[source_prefab_id]['type'] == "Source Prefab GameObject":
                            # Get tag from Source Prefab GameObject
                            if 'properties' in G.nodes[source_prefab_id]:
                                for prop_set in G.nodes[source_prefab_id]['properties']:
                                    if isinstance(prop_set, dict):
                                        if 'm_Layer' in prop_set:
                                            layer_index = prop_set['m_Layer']
                                            try:
                                                if isinstance(layer_index, str):
                                                    layer_index = int(layer_index)
                                                if isinstance(layer_index, int) and 0 <= layer_index < len(layer_lis):
                                                    layer_name = layer_lis[layer_index]
                                                    
                                                    if layer_name not in layer_to_gobj_ids:
                                                        layer_to_gobj_ids[layer_name] = []
                                                    # Add node_id only if it's not already in the list (avoid duplicates)
                                                    if node_id not in layer_to_gobj_ids[layer_name]:
                                                        layer_to_gobj_ids[layer_name].append(node_id)
                                            except (ValueError, IndexError):
                                                pass  # Skip invalid layer index
                                            break

                                        elif 'm_Modification' in prop_set:
                                            mod_prefab_set = prop_set['m_Modification']
                                            for mod_set in mod_prefab_set:
                                                if 'm_Modifications' in mod_set:
                                                    for i in range(len(mod_set['m_Modifications'])):
                                                        mod_set_child = mod_set['m_Modifications'][i]
                                                        if 'propertyPath' in mod_set_child:
                                                            if mod_set_child['propertyPath'] == 'm_Layer':
                                                                m_layer_index = mod_set['m_Modifications'][i+1]['value']
                                                                try:
                                                                    if isinstance(m_layer_index, str):
                                                                        m_layer_index = int(m_layer_index)
                                                                    if isinstance(m_layer_index, int) and 0 <= m_layer_index < len(layer_lis):
                                                                        m_layer_name = layer_lis[m_layer_index]
                                                                        if m_layer_name not in layer_to_gobj_ids:
                                                                            layer_to_gobj_ids[m_layer_name] = []
                                                                        # Add node_id only if it's not already in the list (avoid duplicates)
                                                                        if node_id not in layer_to_gobj_ids[m_layer_name]:
                                                                            layer_to_gobj_ids[m_layer_name].append(node_id)
                                                                except (ValueError, IndexError):
                                                                    pass  # Skip invalid layer index
                                                                break
                                                    break
                                            break
                                                    
                                                                    
    # Save the results to gobj_tag.json
    gobj_tag_file = os.path.join(results_dir, f'{scene_name}_gobj_layer.json')
    with open(gobj_tag_file, 'w', encoding='utf-8') as f:
        json.dump(layer_to_gobj_ids, f, indent=2, ensure_ascii=False)
    
    print(f"GameObject layers extracted and saved to: {gobj_tag_file}")
    print(f"Total layers found: {len(layer_to_gobj_ids)}")
    
    return layer_to_gobj_ids


def ExtractAllGameObjectTags(G, results_dir, scene_name):
    """
    Extract all GameObject tags from the graph G and save to gobj_tag.json.
    If gobj_tag.json already exists, merge new data with existing data.
    
    Args:
        G: NetworkX graph object containing all nodes and edges
        results_dir: Path to the results directory where gobj_tag.json will be saved
    
    Returns:
        dict: Dictionary mapping tag strings to lists of GameObject IDs
    """
    # Check if gobj_tag.json already exists and load existing data
    gobj_tag_file = os.path.join(results_dir, f'{scene_name}_gobj_tag.json')
    tag_to_gobj_ids = {}
    
    if os.path.exists(gobj_tag_file):
        try:
            with open(gobj_tag_file, 'r', encoding='utf-8') as f:
                tag_to_gobj_ids = json.load(f)
            print(f"Loaded existing tag mapping from {gobj_tag_file}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading existing gobj_tag.json: {e}. Starting with empty mapping.")
            tag_to_gobj_ids = {}
    
    
    # Iterate through all nodes in the graph
    for node_id, properties in G.nodes(data=True):
        # Skip nodes without a 'type' key
        if 'type' not in properties:
            print(f"Node {node_id} has no 'type' key, properties: {properties}")

        if properties['type'] in ["GameObject", "Prefab GameObject"]:
            # For regular GameObject and Prefab GameObject, check m_TagString directly
            if 'properties' in properties:
                for prop_set in properties['properties']:
                    if isinstance(prop_set, dict) and 'm_TagString' in prop_set:
                        tag = prop_set['m_TagString']
                        if isinstance(tag, str):
                            tag = tag.strip()
                            if tag and tag != "Untagged":
                                if tag not in tag_to_gobj_ids:
                                    tag_to_gobj_ids[tag] = []
                                # Add node_id only if it's not already in the list (avoid duplicates)
                                if node_id not in tag_to_gobj_ids[tag]:
                                    tag_to_gobj_ids[tag].append(node_id)
                        break
        
        elif properties['type'] == "PrefabInstance":
            # For PrefabInstance, first check m_Modifications for m_TagString
            tag_found = False
            if 'properties' in properties and 'PrefabInstance' in properties['properties']:
                prefab_info_lis = properties["properties"]["PrefabInstance"]
                for prefab_set in prefab_info_lis:
                    if "m_Modification" in prefab_set:
                        mod_prefab_set = prefab_set["m_Modification"]
                        for mod_set in mod_prefab_set:
                            if "m_Modifications" in mod_set:
                                for i in range(len(mod_set["m_Modifications"])):
                                    mod_set_child = mod_set["m_Modifications"][i]
                                    if "propertyPath" in mod_set_child:
                                        if mod_set_child["propertyPath"] == "m_TagString":
                                            # Found m_TagString modification
                                            if i + 1 < len(mod_set["m_Modifications"]):
                                                m_tag_string = mod_set["m_Modifications"][i+1]["value"]
                                                if isinstance(m_tag_string, str):
                                                    m_tag_string = m_tag_string.strip()
                                                    if m_tag_string and m_tag_string != "Untagged":
                                                        if m_tag_string not in tag_to_gobj_ids:
                                                            tag_to_gobj_ids[m_tag_string] = []
                                                        # Add node_id only if it's not already in the list (avoid duplicates)
                                                        if node_id not in tag_to_gobj_ids[m_tag_string]:
                                                            tag_to_gobj_ids[m_tag_string].append(node_id)
                                                        tag_found = True
                                                break
                                    if tag_found:
                                        break
                                if tag_found:
                                    break
                        if tag_found:
                            break
            
            # If no tag found in modifications, look for Source Prefab GameObject
            if not tag_found:
                # Find Source Prefab GameObject connected via PrefabInstance_INFO edge
                for source, target, edge_data in G.edges(data=True):
                    if source == node_id and edge_data.get('type') == "PrefabInstance_INFO":
                        source_prefab_id = target
                        # Check if source is Source Prefab GameObject
                        if source_prefab_id in G.nodes() and G.nodes[source_prefab_id]['type'] == "Source Prefab GameObject":
                            # Get tag from Source Prefab GameObject
                            if 'properties' in G.nodes[source_prefab_id]:
                                for prop_set in G.nodes[source_prefab_id]['properties']:
                                    if isinstance(prop_set, dict):
                                        if 'm_TagString' in prop_set:
                                            tag = prop_set['m_TagString']
                                            if isinstance(tag, str):
                                                tag = tag.strip()
                                                if tag and tag != "Untagged":
                                                    if tag not in tag_to_gobj_ids:
                                                        tag_to_gobj_ids[tag] = []
                                                    # Add node_id only if it's not already in the list (avoid duplicates)
                                                    if node_id not in tag_to_gobj_ids[tag]:
                                                        tag_to_gobj_ids[tag].append(node_id)
                                            break
                                        elif 'm_Modification' in prop_set:
                                            mod_prefab_set = prop_set['m_Modification']
                                            for mod_set in mod_prefab_set:
                                                if 'm_Modifications' in mod_set:
                                                    for i in range(len(mod_set['m_Modifications'])):
                                                        mod_set_child = mod_set['m_Modifications'][i]
                                                        if 'propertyPath' in mod_set_child:
                                                            if mod_set_child['propertyPath'] == 'm_TagString':
                                                                m_tag_string = mod_set['m_Modifications'][i+1]['value']
                                                                if isinstance(m_tag_string, str):
                                                                    m_tag_string = m_tag_string.strip()
                                                                    if m_tag_string and m_tag_string != "Untagged":
                                                                        if m_tag_string not in tag_to_gobj_ids:
                                                                            tag_to_gobj_ids[m_tag_string] = []
                                                                        # Add node_id only if it's not already in the list (avoid duplicates)
                                                                        if node_id not in tag_to_gobj_ids[m_tag_string]:
                                                                            tag_to_gobj_ids[m_tag_string].append(node_id)
                                                                    break
                                                    break
                                            break
                                                    
                                                                    
    # Save the results to gobj_tag.json
    gobj_tag_file = os.path.join(results_dir, f'{scene_name}_gobj_tag.json')
    with open(gobj_tag_file, 'w', encoding='utf-8') as f:
        json.dump(tag_to_gobj_ids, f, indent=2, ensure_ascii=False)
    
    print(f"GameObject tags extracted and saved to: {gobj_tag_file}")
    print(f"Total tags found: {len(tag_to_gobj_ids)}")
    
    return tag_to_gobj_ids


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Analyze Unity project settings.")
    parser.add_argument('-p', '--project-path', required=True, help='Path to the Unity project.')
    parser.add_argument('-r', '--results-dir', required=True, help='Path to the results directory.')
    parser.add_argument('-s', '--scene-name', required=False, help='Specific scene name to analyze (e.g., HomeScene)')

    args = parser.parse_args()

    if True:
        layer_lis = []
        # Find the EditorBuildSettings.asset
        asset_path = get_editor_build_settings_path(args.project_path)
        
        # Analyze the asset
        analyze_asset(asset_path, os.path.join(args.results_dir, "BuildAsset_info"))

        tagManager_path = os.path.join(args.project_path, 'ProjectSettings', 'TagManager.asset')
        layer_lis = analyze_tagManager(tagManager_path, os.path.join(args.results_dir, "TagManager_info"))
        
        # Determine the correct results directory
        asset_name = os.path.basename(asset_path)
        results_subdir = 'mainResults' if not asset_name.endswith('.meta') else 'metaResults'
        json_file_path = os.path.join(args.results_dir, 'BuildAsset_info', results_subdir, f'{asset_name}.json')

        # Extract scene paths from the JSON file or use specified scene
        scene_paths = []
        if args.scene_name:
            # If scene name is specified, use it directly
            print(f"Using specified scene: {args.scene_name}")
            scene_paths = [f"Assets/Scenes/{args.scene_name}.unity"]
        elif os.path.exists(json_file_path):
            scene_paths = extract_scene_paths_from_json(json_file_path)
            print("Extracted Scene Paths:")
        else:
            raise FileNotFoundError(f"Analysis result JSON file not found at {json_file_path}")
            
        if scene_paths:
            analyze_scenes(args.project_path, scene_paths, args.results_dir)
        else:
            print("Warning: No scenes to analyze")

        
        print("Analyzing Script Meta File:")
        script_lis = analyze_csharp_meta(os.path.join(args.project_path, 'Assets'), args.results_dir)

        print("Analyzing Script CSharp File:")
        analyze_script(os.path.join(args.project_path, 'Assets'), args.results_dir)

        print("Analyzing script structure File:")
        analyze_structure_script(args.results_dir)

        print("Analyzing Prefab Asset:")
        prefab_tag_dir = os.path.join(args.results_dir, 'scene_detailed_info', 'prefabResults')
        asset_path = os.path.join(args.project_path, 'Assets')
        analyze_prefab_asset(asset_path, prefab_tag_dir)
        

        print("Creating Scene Database:")
        # Determine the scene JSON files path
        scene_db_dir = os.path.join(args.results_dir, 'scene_detailed_info', 'mainResults')
        if os.path.exists(scene_db_dir):
            scene_json_files = [f for f in os.listdir(scene_db_dir) if f.endswith('.unity.json')]
            # Create databases for each scene
            if scene_json_files:
                create_scene_database(scene_json_files, args.project_path, args.results_dir, script_lis, layer_lis)
            else:
                print("Warning: No scene JSON files found")
        else:
            print("Warning: Scene database directory not found")

if __name__ == "__main__":
    main()
