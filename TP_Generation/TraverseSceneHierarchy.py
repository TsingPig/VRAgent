import os
import json
import networkx as nx
import argparse
from typing import List, Dict, Any

def GenerateTestPlan(G, results_dir, scene_name):
    """
    生成测试计划，筛选出所有需要进行测试的GameObject列表
    
    Args:
        G: NetworkX图对象，包含所有节点和边
        results_dir: 结果目录路径
    
    Returns:
        List[Dict]: 包含测试对象的字典列表
    """
    
    # 存储测试对象的列表
    test_objects = []
    processed_nodes = set()  # 用于跟踪已处理的节点
    
    # 存储所有源代码文件名列表
    all_source_code_files = set()
    
    # 加载 gobj_tag.json 文件
    gobj_tag_file = os.path.join(results_dir, f'{scene_name}_gobj_tag.json')
    gobj_tag_data = {}
    if os.path.exists(gobj_tag_file):
        try:
            with open(gobj_tag_file, 'r', encoding='utf-8') as f:
                gobj_tag_data = json.load(f)
            print(f"成功加载 gobj_tag.json 文件")
        except Exception as e:
            print(f"加载 gobj_tag.json 文件失败: {e}")
    
    # 加载 gobj_layer.json 文件
    gobj_layer_file = os.path.join(results_dir, f'{scene_name}_gobj_layer.json')
    gobj_layer_data = {}
    if os.path.exists(gobj_layer_file):
        try:
            with open(gobj_layer_file, 'r', encoding='utf-8') as f:
                gobj_layer_data = json.load(f)
            print(f"成功加载 gobj_layer.json 文件")
        except Exception as e:
            print(f"加载 gobj_layer.json 文件失败: {e}")
    
    def get_tag_info_from_gobj_tag(node_id):
        """
        从 gobj_tag.json 中获取指定节点ID的tag信息
        
        Args:
            node_id: 节点ID
        
        Returns:
            str: tag名称，如果未找到则返回None
        """
        if not gobj_tag_data:
            return None
        
        # 检查 gobj_tag.json 的数据结构
        # 如果第一个元素是字典且包含 'id' 字段，说明是旧格式
        # 如果第一个元素是字符串，说明是新格式（tag名称 -> GameObject ID列表）
        first_key = next(iter(gobj_tag_data), None)
        if first_key and isinstance(gobj_tag_data[first_key], list):
            first_item = gobj_tag_data[first_key][0] if gobj_tag_data[first_key] else None
            
            if isinstance(first_item, dict) and 'id' in first_item:
                # 旧格式：场景文件 -> GameObject列表
                for scene_file, gameobjects in gobj_tag_data.items():
                    if isinstance(gameobjects, list):
                        for gobj_info in gameobjects:
                            if isinstance(gobj_info, dict) and gobj_info.get('id') == node_id:
                                tag_name = gobj_info.get('tag')
                                if tag_name:  # 只返回非空的tag名称
                                    return tag_name
            else:
                # 新格式：tag名称 -> GameObject ID列表
                for tag_name, gameobject_ids in gobj_tag_data.items():
                    if isinstance(gameobject_ids, list) and node_id in gameobject_ids:
                        return tag_name
        
        return None
    
    def get_layer_info_from_gobj_layer(node_id):
        """
        从 gobj_layer.json 中获取指定节点ID的layer信息
        
        Args:
            node_id: 节点ID
        
        Returns:
            str: layer名称，如果未找到则返回None
        """
        if not gobj_layer_data:
            return None
        
        # gobj_layer.json 格式：layer名称 -> GameObject ID列表
        for layer_name, gameobject_ids in gobj_layer_data.items():
            if isinstance(gameobject_ids, list) and node_id in gameobject_ids:
                return layer_name
        
        return None
    
    def check_valid_source_code_file(target_node_id):
        """
        检查target节点是否有有效的Source_Code_File关系
        
        有效的Source_Code_File需要满足：
        1. target节点存在Source_Code_File关系
        2. 如果file_path包含"PackageCache"（Unity包缓存）且不包含"Interactable"或"Interaction"，则忽略该关系
        3. 如果file_path包含"Interactable"或"Interaction"，需要检查m_PersistentCalls中的m_Calls
        4. 只有当存在其他符合条件的Source_Code_File时，才返回True
        
        Args:
            target_node_id: 目标节点ID（Mono组件节点）
        
        Returns:
            bool: 是否存在有效的Source_Code_File关系
        """
        # 找到所有Source_Code_File关系的目标节点
        valid_targets = []
        for s, t, edge_data in G.edges(data=True):
            if s == target_node_id and edge_data.get('type') == 'Source_Code_File':
                script_node_id = t
                # 检查script节点的properties
                if script_node_id in G.nodes:
                    script_node_data = G.nodes[script_node_id]
                    properties = script_node_data.get('properties', {})
                    file_path = properties.get('file_path', '')
                    
                    # 如果file_path包含"PackageCache"（Unity包缓存）且不包含"Interactable"或"Interaction"，则忽略
                    # 注意：项目资源中的Library文件夹（如Assets\_Course Library）不应该被过滤
                    if "PackageCache" in file_path and "Interaction" not in file_path:
                        continue
                    
                    # 如果file_path包含"Interactable"或"Interaction"，需要额外检查m_PersistentCalls
                    if "Interaction" in file_path:
                        # 检查Mono组件（target_node_id）的m_PersistentCalls
                        if check_persistent_calls_empty(target_node_id):
                            # 如果所有的m_Calls都是'[]'，则忽略
                            continue
                    
                    # 其他情况都认为是有效的Source_Code_File
                    valid_targets.append(script_node_id)
        
        # 只有当存在有效的Source_Code_File时，才返回True
        return len(valid_targets) > 0
    
    def check_persistent_calls_empty(mono_component_id):
        """
        检查Mono组件中的m_PersistentCalls字段，判断是否所有的m_Calls都为'[]'
        
        Args:
            mono_component_id: Mono组件节点ID
        
        Returns:
            bool: True表示所有m_Calls都是'[]'（需要过滤），False表示存在非空的m_Calls（应该保留）
        """
        if mono_component_id not in G.nodes:
            return False
        
        mono_node_data = G.nodes[mono_component_id]
        properties = mono_node_data.get('properties', {})
        
        # 如果properties是空，不需要过滤
        if not properties:
            return False
        
        # 如果存在非空的m_Calls，返回False（不需要过滤）
        # 如果所有m_Calls都是'[]'，返回True（需要过滤）
        has_non_empty = has_non_empty_calls(properties)
        
        # 返回相反的bool值：如果存在非空的m_Calls（has_non_empty=True），则不应该过滤（返回False）
        # 如果所有m_Calls都是'[]'（has_non_empty=False），则应该过滤（返回True）
        return not has_non_empty
    
    def has_non_empty_calls(data):
        """
        递归搜索数据结构中是否存在非空的m_Calls字段
        
        Args:
            data: 要搜索的数据结构（可能是dict、list或其他类型）
        
        Returns:
            bool: True表示至少存在一个非空的m_Calls，False表示所有m_Calls都是'[]'或不存在
        """
        if isinstance(data, dict):
            for key, value in data.items():
                # 查找m_Calls字段
                if key == 'm_Calls':
                    # 找到了m_Calls字段，检查其值
                    if isinstance(value, str):
                        # 如果是字符串，检查是否为'[]'
                        if value.strip() != '[]':
                            return True  # 存在非空的m_Calls
                    elif isinstance(value, list):
                        # 如果是列表，检查是否为空
                        if len(value) > 0:
                            return True  # 存在非空的m_Calls
                        # 如果列表不为空，递归检查每个元素
                        for item in value:
                            if has_non_empty_calls(item):
                                return True
                    elif isinstance(value, dict):
                        # 如果是字典，尝试获取value字段
                        if 'value' in value:
                            call_value = value['value']
                            if isinstance(call_value, str):
                                if call_value.strip() != '[]':
                                    return True  # 存在非空的m_Calls
                            elif isinstance(call_value, list) and len(call_value) > 0:
                                return True  # 存在非空的m_Calls
                        else:
                            # 递归检查
                            if has_non_empty_calls(value):
                                return True
                    else:
                        # 对于其他类型，认为可能是非空的
                        return True
                # 查找m_PersistentCalls字段（然后递归检查其中的内容）
                elif key == 'm_PersistentCalls':
                    if isinstance(value, (list, dict)):
                        if has_non_empty_calls(value):
                            return True
                # 查找包含"event"或"on"或"On"的字段（Unity事件字段，如m_OnClick, m_OnValueChanged等）
                elif isinstance(key, str) and (key.startswith('m_') and ('On' in key or 'event' in key.lower() or 'on' in key.lower())):
                    if isinstance(value, (list, dict, str)):
                        if isinstance(value, str):
                            # 如果是字符串，可能是占位符，不需要检查
                            continue
                        if has_non_empty_calls(value):
                            return True
                else:
                    # 递归搜索
                    if has_non_empty_calls(value):
                        return True
        elif isinstance(data, list):
            for item in data:
                if has_non_empty_calls(item):
                    return True
        elif isinstance(data, str):
            # 如果是字符串，不是m_Calls的值
            pass
        
        # 没有找到非空的m_Calls，返回False（意味着所有m_Calls都是'[]'或不存在）
        return False
    
    def get_valid_source_code_files(target_node_id):
        """
        获取target节点所有有效的Source_Code_File关系的script节点列表
        
        有效的Source_Code_File需要满足：
        1. file_path不包含"PackageCache"（Unity包缓存），或者
        2. file_path包含"PackageCache"但同时包含"Interactable"或"Interaction"
        3. 如果file_path包含"Interactable"或"Interaction"，则需要检查m_PersistentCalls中的m_Calls
        
        Args:
            target_node_id: 目标节点ID（Mono组件节点）
        
        Returns:
            list: 有效的script节点ID列表
        """
        valid_targets = []
        for s, t, edge_data in G.edges(data=True):
            if s == target_node_id and edge_data.get('type') == 'Source_Code_File':
                script_node_id = t
                # 检查script节点的properties
                if script_node_id in G.nodes:
                    script_node_data = G.nodes[script_node_id]
                    properties = script_node_data.get('properties', {})
                    file_path = properties.get('file_path', '')
                    
                    # 如果file_path包含"PackageCache"（Unity包缓存）且不包含"Interactable"或"Interaction"，则忽略
                    # 注意：项目资源中的Library文件夹（如Assets\_Course Library）不应该被过滤
                    if "PackageCache" in file_path and "Interaction" not in file_path:
                        continue
                    
                    # 如果file_path包含"Interactable"或"Interaction"，需要额外检查m_PersistentCalls
                    if  "Interaction" in file_path:
                        # 检查Mono组件（target_node_id）的m_PersistentCalls
                        if check_persistent_calls_empty(target_node_id):
                            # 如果所有的m_Calls都是'[]'，则忽略
                            continue
                    
                    # 其他情况都认为是有效的Source_Code_File
                    valid_targets.append(script_node_id)
        
        return valid_targets
    
    def filter_valid_mono_targets(target_node_id):
        """
        过滤Mono组件目标节点，只返回那些有有效Source_Code_File的节点
        
        Args:
            target_node_id: Mono组件节点ID
        
        Returns:
            bool: 是否有有效的Source_Code_File
        """
        valid_scripts = get_valid_source_code_files(target_node_id)
        return len(valid_scripts) > 0
    
    def collect_all_descendant_mono_info(node_id, current_depth):
        """
        递归收集指定节点的所有后代节点的Mono组件信息
        
        Args:
            node_id: 起始节点ID
            current_depth: 当前深度
        
        Returns:
            List[Dict]: 包含所有后代节点Mono组件信息的列表
        """
        descendant_mono_info = []
        
        # 查找该节点的所有子节点
        child_edges = [(s, t) for s, t, d in G.edges(data=True) 
                       if s == node_id and d.get('type') == 'Has_Child']
        
        for source, child_id in child_edges:
            if child_id in G.nodes:
                child_node_data = G.nodes[child_id]
                
                # 检查子节点是否有Mono组件
                child_mono_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                   if s == child_id and d.get('type') == 'Has_Mono_Comp']
                
                # 收集所有有效的Mono组件target节点
                valid_mono_targets = []
                for source, target in child_mono_edges:
                    # 检查target节点是否包含有效的Source_Code_File关系
                    has_source_code_file = check_valid_source_code_file(target)
                    
                    # 只有当target节点包含有效的Source_Code_File关系时才添加到有效列表
                    if has_source_code_file:
                        valid_mono_targets.append(target)
                
                # 如果有有效的Mono组件target节点，则记录信息
                if valid_mono_targets:
                    # 收集源代码文件信息
                    for target in valid_mono_targets:
                        collect_source_code_files(target)
                    # 查找母节点信息
                    parent_info = None
                    for s, t, edge_data in G.edges(data=True):
                        if t == child_id and edge_data.get('type') == 'Has_Child':
                            if s in G.nodes:
                                parent_node_data = G.nodes[s]
                                parent_info = {
                                    'parent_id': s,
                                    'parent_name': get_gameobject_name_with_prefab_check(s, parent_node_data, G)
                                }
                            break
                    
                    # 检查是否有 Tag_Logic_Relation 关系
                    tag_logic_info_list = []
                    tag_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                      if s == child_id and d.get('type') == 'Tag_Logic_Relation']
                    if tag_logic_edges:
                        for source, target in tag_logic_edges:
                            tag_name = get_tag_info_from_gobj_tag(target)
                            if tag_name:
                                tag_logic_info_list.append({
                                    'id': target,
                                    'id_replace': replace_instance_id(target, G),
                                    'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                                    'tag_name': tag_name
                                })
                    
                    # 检查是否有 Layer_Logic_Relation 关系
                    layer_logic_info_list = []
                    layer_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                        if s == child_id and d.get('type') == 'Layer_Logic_Relation']
                    if layer_logic_edges:
                        for source, target in layer_logic_edges:
                            layer_name = get_layer_info_from_gobj_layer(target)
                            if layer_name:
                                layer_logic_info_list.append({
                                    'id': target,
                                    'id_replace': replace_instance_id(target, G),
                                    'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                                    'layer_name': layer_name
                                })
                    
                    # 检查是否有 Gameobject_Find_Logic_Relation 关系
                    gameobject_find_info_list = []
                    gameobject_find_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                            if s == child_id and d.get('type') == 'Gameobject_Find_Logic_Relation']
                    if gameobject_find_edges:
                        for source, target in gameobject_find_edges:
                            gameobject_find_info_list.append({
                                'source': source,
                                'source_replace': replace_instance_id(source, G),
                                'target': target,
                                'target_replace': replace_instance_id(target, G),
                                'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                                'edge_type': 'Gameobject_Find_Logic_Relation'
                            })
                    
                    # 检查是否有 Instantiate_Logic_Relation 关系
                    gameobject_instantiate_info_list = []
                    gameobject_instantiate_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                                   if s == child_id and d.get('type') == 'Instantiate_Logic_Relation']
                    if gameobject_instantiate_edges:
                        for source, target in gameobject_instantiate_edges:
                            gameobject_instantiate_info_list.append({
                                'source': source,
                                'source_replace': replace_instance_id(source, G),
                                'target': target,
                                'target_replace': replace_instance_id(target, G),
                                'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                                'edge_type': 'Instantiate_Logic_Relation'
                            })
                    
                    # 为每个target添加有效的Source_Code_File信息
                    mono_comp_targets_list = []
                    for target in valid_mono_targets:
                        valid_source_code_files = get_valid_source_code_files(target)
                        mono_comp_targets_list.append({
                            'source': child_id,
                            'source_replace': replace_instance_id(child_id, G),
                            'target': target,
                            'target_replace': replace_instance_id(target, G),
                            'edge_type': 'Has_Mono_Comp',
                            'mono_property': G.nodes[target].get('properties', {}) if target in G.nodes else {},
                            'valid_source_code_files': [{
                                'script_id': script_id,
                                'file_path': G.nodes[script_id].get('properties', {}).get('file_path', '') if script_id in G.nodes else ''
                            } for script_id in valid_source_code_files]
                        })
                    
                    descendant_mono_info.append({
                        'child_id': child_id,
                        'child_id_replace': replace_instance_id(child_id, G),
                        'child_name': get_gameobject_name_with_prefab_check(child_id, child_node_data, G),
                        'mono_comp_targets': mono_comp_targets_list,
                        'depth': current_depth + 1,
                        'parent_info': parent_info,
                        'tag_logic_info': tag_logic_info_list,
                        'layer_logic_info': layer_logic_info_list,
                        'gameobject_find_info': gameobject_find_info_list,
                        'gameobject_instantiate_info': gameobject_instantiate_info_list
                    })
                
                # 递归检查子节点的子节点
                child_descendant_info = collect_all_descendant_mono_info(child_id, current_depth + 1)
                if child_descendant_info:
                    descendant_mono_info.extend(child_descendant_info)
        
        return descendant_mono_info
    
    def collect_child_mono_comp_info(child_id, child_node_data, depth):
        """
        收集子节点的Mono组件信息（公共辅助函数）
        
        Args:
            child_id: 子节点ID
            child_node_data: 子节点数据
            depth: 当前深度
        
        Returns:
            List[Dict]: 包含子节点Mono组件信息的列表，如果没有则返回空列表
        """
        child_mono_comp_info_list = []
        
        # 首先收集子节点的Mono组件信息
        child_mono_targets = []
        for source, target, edge_data in G.edges(data=True):
            if source == child_id and edge_data.get('type') == 'Has_Mono_Comp':
                # 检查target节点是否包含有效的Source_Code_File关系
                has_source_code_file = check_valid_source_code_file(target)
                
                # 只有当target节点包含有效的Source_Code_File关系时才添加
                if has_source_code_file:
                    child_mono_targets.append(target)
        
        # 如果有有效的Mono组件target节点，则记录信息
        if child_mono_targets:
            # 收集源代码文件信息
            for mono_target in child_mono_targets:
                collect_source_code_files(mono_target)
            # 查找母节点信息
            parent_info = None
            for s, t, edge_data2 in G.edges(data=True):
                if t == child_id and edge_data2.get('type') == 'Has_Child':
                    if s in G.nodes:
                        parent_node_data = G.nodes[s]
                        parent_info = {
                            'parent_id': s,
                            'parent_name': get_gameobject_name_with_prefab_check(s, parent_node_data, G)
                        }
                    break
            
            # 检查子节点是否有 Tag_Logic_Relation 关系
            child_tag_logic_info_list = []
            child_tag_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                   if s == child_id and d.get('type') == 'Tag_Logic_Relation']
            if child_tag_logic_edges:
                for source, target in child_tag_logic_edges:
                    tag_name = get_tag_info_from_gobj_tag(target)
                    if tag_name:
                        child_tag_logic_info_list.append({
                            'id': target,
                            'id_replace': replace_instance_id(target, G),
                            'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                            'tag_name': tag_name
                        })
            
            # 检查子节点是否有 Layer_Logic_Relation 关系
            child_layer_logic_info_list = []
            child_layer_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                     if s == child_id and d.get('type') == 'Layer_Logic_Relation']
            if child_layer_logic_edges:
                for source, target in child_layer_logic_edges:
                    layer_name = get_layer_info_from_gobj_layer(target)
                    if layer_name:
                        child_layer_logic_info_list.append({
                            'id': target,
                            'id_replace': replace_instance_id(target, G),
                            'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                            'layer_name': layer_name
                        })
            
            # 检查子节点是否有 Gameobject_Find_Logic_Relation 关系
            child_gameobject_find_info_list = []
            child_gameobject_find_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                          if s == child_id and d.get('type') == 'Gameobject_Find_Logic_Relation']
            if child_gameobject_find_edges:
                for source, target in child_gameobject_find_edges:
                    child_gameobject_find_info_list.append({
                        'source': source,
                        'source_replace': replace_instance_id(source, G),
                        'target': target,
                        'target_replace': replace_instance_id(target, G),
                        'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                        'edge_type': 'Gameobject_Find_Logic_Relation'
                    })
            
            # 检查子节点是否有 Instantiate_Logic_Relation 关系
            child_gameobject_instantiate_info_list = []
            child_gameobject_instantiate_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                                  if s == child_id and d.get('type') == 'Instantiate_Logic_Relation']
            if child_gameobject_instantiate_edges:
                for source, target in child_gameobject_instantiate_edges:
                    child_gameobject_instantiate_info_list.append({
                        'source': source,
                        'source_replace': replace_instance_id(source, G),
                        'target': target,
                        'target_replace': replace_instance_id(target, G),
                        'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                        'edge_type': 'Instantiate_Logic_Relation'
                    })
            
            # 为每个child_mono_target添加有效的Source_Code_File信息
            mono_comp_targets_list = []
            for mono_target in child_mono_targets:
                valid_source_code_files = get_valid_source_code_files(mono_target)
                mono_comp_targets_list.append({
                    'source': child_id,
                    'source_replace': replace_instance_id(child_id, G),
                    'target': mono_target,
                    'target_replace': replace_instance_id(mono_target, G),
                    'edge_type': 'Has_Mono_Comp',
                    'mono_property': G.nodes[mono_target].get('properties', {}) if mono_target in G.nodes else {},
                    'valid_source_code_files': [{
                        'script_id': script_id,
                        'file_path': G.nodes[script_id].get('properties', {}).get('file_path', '') if script_id in G.nodes else ''
                    } for script_id in valid_source_code_files]
                })
            
            child_mono_comp_info_list.append({
                'child_id': child_id,
                'child_id_replace': replace_instance_id(child_id, G),
                'child_name': get_gameobject_name_with_prefab_check(child_id, child_node_data, G),
                'mono_comp_targets': mono_comp_targets_list,
                'depth': depth + 1,
                'parent_info': parent_info,
                'tag_logic_info': child_tag_logic_info_list,
                'layer_logic_info': child_layer_logic_info_list,
                'gameobject_find_info': child_gameobject_find_info_list,
                'gameobject_instantiate_info': child_gameobject_instantiate_info_list
            })
        
        return child_mono_comp_info_list
    
    def replace_instance_id(node_id, G):
        """
        替换节点ID中的"stripped"字段
        """
        if "stripped" in node_id:
            for source, target, edge_data in G.edges(data=True):
                if source == node_id and edge_data.get('type') == 'PrefabInstance_INFO':
                    node_instance_id = target
                    return node_instance_id
        return node_id
    
    def collect_source_code_files(mono_node_id):
        """
        收集指定Mono组件节点的源代码文件信息
        
        Args:
            mono_node_id: Mono组件节点ID
        
        Returns:
            List[Dict]: 包含源代码文件信息的列表
        """
        source_code_info = []
        
        # 查找以该Mono组件节点为source，edge为Source_Code_File的target节点
        source_code_edges = [(s, t) for s, t, d in G.edges(data=True) 
                           if s == mono_node_id and d.get('type') == 'Source_Code_File']
        
        for source, target in source_code_edges:
            if target in G.nodes:
                target_node_data = G.nodes[target]
                # 从properties中提取name值
                source_file_name = None
                if 'properties' in target_node_data:
                    properties = target_node_data['properties']
                    if isinstance(properties, dict) and 'name' in properties:
                        source_file_name = properties['name']
                    elif isinstance(properties, list):
                        for prop in properties:
                            if isinstance(prop, dict) and 'name' in prop:
                                source_file_name = prop['name']
                                break
                
                if source_file_name:
                    source_code_info.append({
                        'mono_node_id': mono_node_id,
                        'source_code_node_id': target,
                        'source_file_name': source_file_name
                    })
                    # 添加到全局集合中
                    all_source_code_files.add(source_file_name)
        
        return source_code_info
            
    def process_gameobject_node(node_id, node_data, parent_id=None, depth=0):
        """
        递归处理GameObject节点及其子节点，支持多层递归查询Mono组件
        
        Args:
            node_id: 节点ID
            node_data: 节点数据
            parent_id: 父节点ID（如果有的话）
            depth: 当前递归深度
        """
        # 如果节点已经处理过，直接返回
        if node_id in processed_nodes:
            return None
        
        # 检查节点类型是否为GameObject相关
        if node_data.get('type') not in ['GameObject', 'Prefab GameObject', 'PrefabInstance']:
            return None

        mono_comp_relations = []
        # 查找该节点的Has_Mono_Comp关系

        for source, target, edge_data in G.edges(data=True):
            if source == node_id and edge_data.get('type') == 'Has_Mono_Comp':
                # 检查target节点是否包含有效的Source_Code_File关系
                has_source_code_file = check_valid_source_code_file(target)
                
                # 只有当target节点包含有效的Source_Code_File关系时才添加
                if has_source_code_file:
                    # 从图中获取source节点的属性
                    target_properties = {}
                    if target in G.nodes:
                        target_node_data = G.nodes[target]
                        target_properties = target_node_data.get('properties', {})
                    
                    # 收集源代码文件信息（只收集有效的script）
                    collect_source_code_files(target)
                    
                    # 获取有效的Source_Code_File并只添加有效的script信息
                    valid_source_code_files = get_valid_source_code_files(target)
                    
                    mono_comp_relations.append({
                        'source': source,
                        'source_replace': replace_instance_id(source, G),
                        'target': target,
                        'target_replace': replace_instance_id(target, G),
                        'edge_type': 'Has_Mono_Comp',
                        'mono_property': target_properties,
                        'valid_source_code_files': [{
                            'script_id': script_id,
                            'file_path': G.nodes[script_id].get('properties', {}).get('file_path', '') if script_id in G.nodes else ''
                        } for script_id in valid_source_code_files]
                    })
        
        # 检查是否有 Tag_Logic_Relation 关系
        tag_logic_info_list = []
        tag_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                        if s == node_id and d.get('type') == 'Tag_Logic_Relation']
        if tag_logic_edges:
            for source, target in tag_logic_edges:
                tag_name = get_tag_info_from_gobj_tag(target)
                if tag_name:
                    tag_logic_info_list.append({
                        'id': target,
                        'id_replace': replace_instance_id(target, G),
                        'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                        'tag_name': tag_name
                    })
        
        # 检查是否有 Layer_Logic_Relation 关系
        layer_logic_info_list = []
        layer_logic_edges = [(s, t) for s, t, d in G.edges(data=True) 
                            if s == node_id and d.get('type') == 'Layer_Logic_Relation']
        if layer_logic_edges:
            for source, target in layer_logic_edges:
                layer_name = get_layer_info_from_gobj_layer(target)
                if layer_name:
                    layer_logic_info_list.append({
                        'id': target,
                        'id_replace': replace_instance_id(target, G),
                        'gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                        'layer_name': layer_name
                    })
        
        # 检查是否有 Gameobject_Find_Logic_Relation 关系
        gameobject_find_info_list = []
        gameobject_find_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                if s == node_id and d.get('type') == 'Gameobject_Find_Logic_Relation']
        if gameobject_find_edges:
            for source, target in gameobject_find_edges:
                gameobject_find_info_list.append({
                    'source': source,
                    'source_replace': replace_instance_id(source, G),
                    'target': target,
                    'target_replace': replace_instance_id(target, G),
                    'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                    'edge_type': 'Gameobject_Find_Logic_Relation'
                })
        
        # 检查是否有 Instantiate_Logic_Relation 关系
        gameobject_instantiate_info_list = []
        gameobject_instantiate_edges = [(s, t) for s, t, d in G.edges(data=True) 
                                    if s == node_id and d.get('type') == 'Instantiate_Logic_Relation']
        if gameobject_instantiate_edges:
            for source, target in gameobject_instantiate_edges:
                gameobject_instantiate_info_list.append({
                    'source': source,
                    'source_replace': replace_instance_id(source, G),
                    'target': target,
                    'target_replace': replace_instance_id(target, G),
                    'target_gameobject_name': get_gameobject_name_with_prefab_check(target, G.nodes[target], G),
                    'edge_type': 'Instantiate_Logic_Relation'
                })
        
        node_instance_id = replace_instance_id(node_id, G)

                # 查找该节点的Has_Child关系
        child_relations = []
        for source, target, edge_data in G.edges(data=True):
            if source == node_id and edge_data.get('type') == 'Has_Child':
                child_relations.append({
                    'source': source,
                    'target': target,
                    'edge_type': 'Has_Child'
                })
        
        # 如果该节点有Has_Mono_Comp关系，则添加到测试对象列表
        if mono_comp_relations:
            test_object = {
                'gameobject_id': node_id,
                'gameobject_id_replace': node_instance_id,
                'gameobject_type': node_data.get('type', 'Unknown'),
                'gameobject_name': get_gameobject_name_with_prefab_check(node_id, node_data, G),
                'mono_comp_relations': mono_comp_relations,
                'child_relations': child_relations,
                'child_mono_comp_info': [],
                'parent_id': parent_id,
                'depth': depth,
                'tag_logic_info': tag_logic_info_list,
                'layer_logic_info': layer_logic_info_list,
                'gameobject_find_info': gameobject_find_info_list,
                'gameobject_instantiate_info': gameobject_instantiate_info_list
            }
            
            # 标记节点为已处理
            processed_nodes.add(node_id)
            
            # 递归处理子节点
            for child_rel in child_relations:
                child_id = child_rel['target']
                if child_id in G.nodes():
                    child_node_data = G.nodes[child_id]
                    # 递归处理子节点
                    child_result = process_gameobject_node(child_id, child_node_data, node_id, depth + 1)
                    
                    # 如果子节点有Mono组件，收集其信息
                    if child_result:
                        child_mono_comp_info = collect_child_mono_comp_info(child_id, child_node_data, depth)
                        
                        if child_mono_comp_info:
                            test_object['child_mono_comp_info'].extend(child_mono_comp_info)
                        
                        # 递归收集子节点的子节点（孙节点）的Mono组件信息
                        child_child_mono_info = collect_all_descendant_mono_info(child_id, depth + 1)
                        if child_child_mono_info:
                            test_object['child_mono_comp_info'].extend(child_child_mono_info)
            
            return test_object
        
        # 如果该节点没有Has_Mono_Comp关系，但子节点可能有
        # 递归处理子节点，看是否有子节点包含Mono组件（支持多层递归）
        has_child_with_mono = False
        child_mono_comp_info = []
        
        for child_rel in child_relations:
            child_id = child_rel['target']
            if child_id in G.nodes():
                child_node_data = G.nodes[child_id]
                # 递归处理子节点
                child_result = process_gameobject_node(child_id, child_node_data, node_id, depth + 1)
                
                if child_result:
                    has_child_with_mono = True
                    # 收集子节点的Mono组件信息
                    child_mono_comp_info_fragment = collect_child_mono_comp_info(child_id, child_node_data, depth)
                    
                    if child_mono_comp_info_fragment:
                        child_mono_comp_info.extend(child_mono_comp_info_fragment)
                    
                    # 递归收集子节点的子节点（孙节点）的Mono组件信息
                    child_child_mono_info = collect_all_descendant_mono_info(child_id, depth + 1)
                    if child_child_mono_info:
                        child_mono_comp_info.extend(child_child_mono_info)
        
        # 如果子节点中有Mono组件，也将该节点加入列表
        if has_child_with_mono:
            test_object = {
                'gameobject_id': node_id,
                'gameobject_id_replace': replace_instance_id(node_id, G),
                'gameobject_type': node_data.get('type', 'Unknown'),
                'gameobject_name': get_gameobject_name_with_prefab_check(node_id, node_data, G),
                'mono_comp_relations': [],
                'child_relations': child_relations,
                'child_mono_comp_info': child_mono_comp_info,
                'parent_id': parent_id,
                'note': 'Added because child nodes contain Mono components',
                'depth': depth,
                'tag_logic_info': tag_logic_info_list,
                'layer_logic_info': layer_logic_info_list,
                'gameobject_find_info': gameobject_find_info_list,
                'gameobject_instantiate_info': gameobject_instantiate_info_list
            }
            
            # 标记节点为已处理
            processed_nodes.add(node_id)
            return test_object
        
        return None
    
    # 首先找到所有根节点（没有父节点的节点）
    root_nodes = []
    for node_id, node_data in G.nodes(data=True):
        if node_data.get('type') in ['GameObject', 'Prefab GameObject', 'PrefabInstance']:
            # 检查是否有其他节点指向这个节点作为子节点
            has_parent = False
            for source, target, edge_data in G.edges(data=True):
                if target == node_id and edge_data.get('type') == 'Has_Child':
                    has_parent = True
                    break
            
            if not has_parent:
                root_nodes.append((node_id, node_data))
    
    # 按层次顺序处理节点：从根节点开始，然后是子节点
    def process_nodes_in_order():
        """按层次顺序处理节点"""
        ordered_results = []
        
        # 处理根节点
        for root_id, root_data in root_nodes:
            if root_id not in processed_nodes:
                result = process_gameobject_node(root_id, root_data, depth=0)
                if result:
                    ordered_results.append(result)
        
        # 处理其他节点（按层次顺序）
        while True:
            new_nodes_added = False
            for node_id, node_data in G.nodes(data=True):
                if (node_id not in processed_nodes and 
                    node_data.get('type') in ['GameObject', 'Prefab GameObject', 'PrefabInstance']):
                    
                    # 检查是否所有父节点都已经处理过
                    all_parents_processed = True
                    for source, target, edge_data in G.edges(data=True):
                        if target == node_id and edge_data.get('type') == 'Has_Child':
                            if source not in processed_nodes:
                                all_parents_processed = False
                                break
                    
                    if all_parents_processed:
                        result = process_gameobject_node(node_id, node_data, depth=0)
                        if result:
                            ordered_results.append(result)
                            new_nodes_added = True
            
            # 如果没有新节点被添加，说明所有节点都已处理
            if not new_nodes_added:
                break
        
        return ordered_results
    
    # 按层次顺序处理节点
    test_objects = process_nodes_in_order()
    
    # 输出测试对象列表
    print(f"找到 {len(test_objects)} 个需要测试的GameObject（按层次顺序排列）:")
    print("=" * 80)
    
    # 创建层次显示信息
    def get_hierarchy_level(obj):
        """获取对象的层次级别"""
        level = 0
        current_parent = obj.get('parent_id')
        while current_parent:
            level += 1
            # 查找当前父节点的父节点
            for test_obj in test_objects:
                if test_obj['gameobject_id'] == current_parent:
                    current_parent = test_obj.get('parent_id')
                    break
            else:
                break
        return level
    
    for i, obj in enumerate(test_objects, 1):
        hierarchy_level = get_hierarchy_level(obj)
        indent = "  " * hierarchy_level
        
        print(f"\n{i}. {indent}GameObject ID: {obj['gameobject_id']}")
        print(f"{indent}   名称: {obj['gameobject_name']}")
        print(f"{indent}   类型: {obj['gameobject_type']}")
        print(f"{indent}   层次级别: {hierarchy_level}")
        
        # 显示父节点信息（如果有）
        if obj.get('parent_id'):
            print(f"{indent}   父节点ID: {obj['parent_id']}")
        
        # 显示备注信息（如果有）
        if obj.get('note'):
            print(f"{indent}   备注: {obj['note']}")
        
        print(f"{indent}   Mono组件关系数量: {len(obj['mono_comp_relations'])}")
        print(f"{indent}   子对象关系数量: {len(obj['child_relations'])}")
        print(f"{indent}   子对象Mono组件信息数量: {len(obj['child_mono_comp_info'])}")
        
        # 输出Mono组件关系详情
        if obj['mono_comp_relations']:
            print(f"{indent}   Mono组件关系:")
            for rel in obj['mono_comp_relations']:
                print(f"{indent}     - {rel['source']} -> {rel['target']} ({rel['edge_type']})")
        
        # 输出Tag_Logic_Relation信息（如果有）
        if obj.get('tag_logic_info') and len(obj['tag_logic_info']) > 0:
            print(f"{indent}   Tag_Logic_Relation:")
            for i, tag_info in enumerate(obj['tag_logic_info']):
                print(f"{indent}     {i+1}. ID: {tag_info['id']}")
                print(f"{indent}        Tag名称: {tag_info['tag_name']}")
                if i < len(obj['tag_logic_info']) - 1:  # 不是最后一个元素时添加空行
                    print()
        
        # 输出Layer_Logic_Relation信息（如果有）
        if obj.get('layer_logic_info') and len(obj['layer_logic_info']) > 0:
            print(f"{indent}   Layer_Logic_Relation:")
            for i, layer_info in enumerate(obj['layer_logic_info']):
                print(f"{indent}     {i+1}. ID: {layer_info['id']}")
                print(f"{indent}        Layer名称: {layer_info['layer_name']}")
                if i < len(obj['layer_logic_info']) - 1:  # 不是最后一个元素时添加空行
                    print()
        
        # 输出Gameobject_Find_Logic_Relation信息（如果有）
        if obj.get('gameobject_find_info') and len(obj['gameobject_find_info']) > 0:
            print(f"{indent}   Gameobject_Find_Logic_Relation:")
            for i, find_info in enumerate(obj['gameobject_find_info']):
                print(f"{indent}     {i+1}. {find_info['source']} -> {find_info['target']} ({find_info['edge_type']})")
                if i < len(obj['gameobject_find_info']) - 1:  # 不是最后一个元素时添加空行
                    print()
        
        # 输出Instantiate_Logic_Relation信息（如果有）
        if obj.get('gameobject_instantiate_info') and len(obj['gameobject_instantiate_info']) > 0:
            print(f"{indent}   Instantiate_Logic_Relation:")
            for i, instantiate_info in enumerate(obj['gameobject_instantiate_info']):
                print(f"{indent}     {i+1}. {instantiate_info['source']} -> {instantiate_info['target']} ({instantiate_info['edge_type']})")
                if i < len(obj['gameobject_instantiate_info']) - 1:  # 不是最后一个元素时添加空行
                    print()
        
        # 输出子对象关系详情
        if obj['child_relations']:
            print(f"{indent}   子对象关系:")
            for rel in obj['child_relations']:
                print(f"{indent}     - {rel['source']} -> {rel['target']} ({rel['edge_type']})")
        
        # 输出子对象Mono组件信息详情
        if obj['child_mono_comp_info']:
            print(f"{indent}   子对象Mono组件信息:")
            for info in obj['child_mono_comp_info']:
                print(f"{indent}     - 子对象: {info['child_name']} (ID: {info['child_id']})")
                print(f"{indent}       Mono组件:")
                for target_info in info['mono_comp_targets']:
                    print(f"{indent}         - {target_info['source']} -> {target_info['target']} ({target_info['edge_type']})")
                
                # 输出Tag_Logic_Relation信息（如果有）
                if info.get('tag_logic_info') and len(info['tag_logic_info']) > 0:
                    print(f"{indent}       Tag_Logic_Relation:")
                    for i, tag_info in enumerate(info['tag_logic_info']):
                        print(f"{indent}       {i+1}. ID: {tag_info['id']}")
                        print(f"{indent}          Tag名称: {tag_info['tag_name']}")
                        if i < len(info['tag_logic_info']) - 1:  # 不是最后一个元素时添加空行
                            print()
                
                # 输出Layer_Logic_Relation信息（如果有）
                if info.get('layer_logic_info') and len(info['layer_logic_info']) > 0:
                    print(f"{indent}       Layer_Logic_Relation:")
                    for i, layer_info in enumerate(info['layer_logic_info']):
                        print(f"{indent}       {i+1}. ID: {layer_info['id']}")
                        print(f"{indent}          Layer名称: {layer_info['layer_name']}")
                        if i < len(info['layer_logic_info']) - 1:  # 不是最后一个元素时添加空行
                            print()
                
                # 输出Gameobject_Find_Logic_Relation信息（如果有）
                if info.get('gameobject_find_info') and len(info['gameobject_find_info']) > 0:
                    print(f"{indent}       Gameobject_Find_Logic_Relation:")
                    for i, find_info in enumerate(info['gameobject_find_info']):
                        print(f"{indent}       {i+1}. {find_info['source']} -> {find_info['target']} ({find_info['edge_type']})")
                        if i < len(info['gameobject_find_info']) - 1:  # 不是最后一个元素时添加空行
                            print()
                
                # 输出Instantiate_Logic_Relation信息（如果有）
                if info.get('gameobject_instantiate_info') and len(info['gameobject_instantiate_info']) > 0:
                    print(f"{indent}       Instantiate_Logic_Relation:")
                    for i, instantiate_info in enumerate(info['gameobject_instantiate_info']):
                        print(f"{indent}       {i+1}. {instantiate_info['source']} -> {instantiate_info['target']} ({instantiate_info['edge_type']})")
                        if i < len(info['gameobject_instantiate_info']) - 1:  # 不是最后一个元素时添加空行
                            print()
    
    # 保存测试计划到JSON文件
    test_plan_file = os.path.join(results_dir, f'{scene_name}_gobj_hierarchy.json')
    with open(test_plan_file, 'w', encoding='utf-8') as f:
        json.dump(test_objects, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试计划已保存到: {test_plan_file}")
    
    # 保存源代码文件名列表
    source_code_files_list = sorted(list(all_source_code_files))
    project_name = str(results_dir).replace('\\', '').split('_')[1]
    source_code_file = os.path.join(results_dir, f'{project_name}_{scene_name}_source_code_files.json')
    with open(source_code_file, 'w', encoding='utf-8') as f:
        json.dump(source_code_files_list, f, indent=2, ensure_ascii=False)
    
    print(f"源代码文件列表已保存到: {source_code_file}")
    print(f"共找到 {len(source_code_files_list)} 个源代码文件")
    
    return test_objects

def get_gameobject_name(node_data: Dict[str, Any]) -> str:
    """
    从节点数据中提取GameObject名称
    
    Args:
        node_data: 节点数据字典
    
    Returns:
        str: GameObject名称，如果未找到则返回"Unknown"
    """
    # 首先检查是否有直接的m_Name字段

    if 'properties' in node_data:
        for prop_set in node_data['properties']:
            if isinstance(prop_set, dict) and 'm_Name' in prop_set:
                return prop_set['m_Name']
    
    # 如果没有直接的m_Name字段，检查m_Modifications中的m_Name
    if 'properties' in node_data:
        prop_set = node_data['properties']
        
        if isinstance(prop_set, dict):                               
            if node_data['type'] == 'PrefabInstance':
                prop_set_lis = prop_set['PrefabInstance']
                for prop_set_child in prop_set_lis:
                    if 'm_Modification' in prop_set_child:
                        mod_prefab_set = prop_set_child['m_Modification']
                        for mod_set in mod_prefab_set:
                            if 'm_Modifications' in mod_set:
                                for i in range(len(mod_set['m_Modifications'])):
                                    mod_set_child = mod_set['m_Modifications'][i]
                                    if 'propertyPath' in mod_set_child:
                                        if mod_set_child['propertyPath'] == 'm_Name':
                                            # 找到m_Name修改，下一个元素包含值
                                            if i + 1 < len(mod_set['m_Modifications']):
                                                m_name_value = mod_set['m_Modifications'][i+1]['value']
                                                if isinstance(m_name_value, str):
                                                    return m_name_value.strip()

        elif isinstance(prop_set, list):
            for prop_set_child in prop_set:
                if 'm_Modification' in prop_set_child:
                    mod_prefab_set = prop_set_child['m_Modification']
                    for mod_set in mod_prefab_set:
                        if 'm_Modifications' in mod_set:
                            for i in range(len(mod_set['m_Modifications'])):
                                mod_set_child = mod_set['m_Modifications'][i]
                                if 'propertyPath' in mod_set_child:
                                    if mod_set_child['propertyPath'] == 'm_Name':
                                        # 找到m_Name修改，下一个元素包含值
                                        if i + 1 < len(mod_set['m_Modifications']):
                                            m_name_value = mod_set['m_Modifications'][i+1]['value']
                                            if isinstance(m_name_value, str):
                                                return m_name_value.strip()
    
    return "Unknown"

def get_gameobject_name_with_prefab_check(node_id: str, node_data: Dict[str, Any], G: nx.Graph) -> str:
    """
    从节点数据中提取GameObject名称，对包含"stripped"字段的节点特殊处理
    
    Args:
        node_id: 节点ID
        node_data: 节点数据字典
        G: NetworkX图对象
    
    Returns:
        str: GameObject名称，如果未找到则返回"Unknown"
    """
    # 如果节点ID包含"stripped"字段，查找PrefabInstance_INFO关系
    if "stripped" in node_id:
        # 查找该节点是否有"PrefabInstance_INFO"关系
        prefab_info_edges = [(s, t) for s, t, d in G.edges(data=True) 
                            if s == node_id and d.get('type') == 'PrefabInstance_INFO']
        
        if prefab_info_edges:
            # 找到PrefabInstance_INFO关系，使用target节点的名称
            for source, target in prefab_info_edges:
                if target in G.nodes:
                    target_node_data = G.nodes[target]
                    target_name = get_gameobject_name(target_node_data)
                    if target_name != "Unknown":
                        return target_name

    if node_data['type'] == 'PrefabInstance':
        source_prefab_info = [(s, t) for s, t, d in G.edges(data=True) 
                            if s == node_id and d.get('type') == 'PrefabInstance_INFO']
        
        target_name = get_gameobject_name(node_data)
        if target_name != "Unknown":
            return target_name
        else:
            for source, target in source_prefab_info:
                if target in G.nodes:
                    target_node_data = G.nodes[target]
                    target_name = get_gameobject_name(target_node_data)
                    if target_name != "Unknown":
                        return target_name

    # 如果上述条件不满足，使用原来的逻辑
    return get_gameobject_name(node_data)

def load_graph_from_gml(gml_file_path: str) -> nx.Graph:
    """
    从GML文件加载图
    
    Args:
        gml_file_path: GML文件路径
    
    Returns:
        nx.Graph: 加载的图对象
    """
    if not os.path.exists(gml_file_path):
        raise FileNotFoundError(f"GML文件未找到: {gml_file_path}")
    
    try:
        graph = nx.read_gml(gml_file_path)
        print(f"成功加载图: {gml_file_path}")
        print(f"节点数量: {graph.number_of_nodes()}")
        print(f"边数量: {graph.number_of_edges()}")
        return graph
    except Exception as e:
        raise Exception(f"加载GML文件失败: {e}")

def find_gml_files(results_dir: str) -> List[str]:
    """
    在结果目录中查找所有GML文件
    
    Args:
        results_dir: 结果目录路径
    
    Returns:
        List[str]: GML文件路径列表
    """
    gml_files = []
    
    # 遍历目录查找GML文件
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith('.gml'):
                gml_files.append(os.path.join(root, file))
    
    return gml_files

def main():
    """
    主函数：查找GML文件并生成测试计划
    """
    # 设置参数解析
    parser = argparse.ArgumentParser(description="生成Unity场景依赖图的测试计划")
    parser.add_argument('-r', '--results-dir', required=True, 
                       help='结果目录路径，包含GML文件')
    
    args = parser.parse_args()
    results_dir = args.results_dir
    
    # 查找所有GML文件
    gml_files = find_gml_files(results_dir)
    
    if not gml_files:
        print("未找到任何GML文件")
        return
    
    print(f"找到 {len(gml_files)} 个GML文件:")
    for gml_file in gml_files:
        print(f"  - {gml_file}")
    
    # 处理每个GML文件
    for gml_file in gml_files:
        print(f"\n处理文件: {gml_file}")
        print("-" * 60)
        
        
        # 加载图
        graph = load_graph_from_gml(gml_file)
        scene_name = os.path.basename(gml_file).split('.')[0]
        
        # 生成测试计划
        test_objects = GenerateTestPlan(graph, results_dir, scene_name)
        
        print(f"文件 {gml_file} 处理完成，找到 {len(test_objects)} 个测试对象")
            
if __name__ == "__main__":
    main()