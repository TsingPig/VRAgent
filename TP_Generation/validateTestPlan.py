import json
import os
from typing import Dict, Any, List, Optional, Union
from jsonschema import Draft202012Validator, exceptions as js_exceptions
import networkx as nx
import argparse

# -----------------------------
# 场景索引结构（基于GML文件的graph查询）
# -----------------------------
# SceneIndex 现在是一个包含 graph 对象的字典，从 gml 文件加载
# 结构：
# scene_index = {
#   "graph": nx.Graph,  # NetworkX图对象，从gml文件加载
#   "gml_file_path": str  # GML文件路径（可选，用于调试）
# }
SceneIndex = Dict[str, Any]

# -----------------------------
# 基础 JSON Schema（可按需强化）
# -----------------------------
TEST_PLAN_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "taskUnits": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["actionUnits"],
                "properties": {
                    "actionUnits": {
                        "type": "array",
                        "items": {
                            "oneOf": [
                                {
                                    # Grab action format1: with target_object
                                    "type": "object",
                                    "required": ["type", "source_object_name", "source_object_fileID", "target_object_name", "target_object_fileID"],
                                    "properties": {
                                        "type": {"type": "string", "const": "Grab"},
                                        "source_object_name": {"type": "string"},
                                        "source_object_fileID": {"type": "integer"},
                                        "target_object_name": {"type": "string"},
                                        "target_object_fileID": {"type": "integer"}
                                    },
                                    "additionalProperties": False
                                },
                                {
                                    # Grab action format2: with delta_position
                                    "type": "object",
                                    "required": ["type", "source_object_name", "source_object_fileID", "target_position"],
                                    "properties": {
                                        "type": {"type": "string", "const": "Grab"},
                                        "source_object_name": {"type": "string"},
                                        "source_object_fileID": {"type": "integer"},
                                        "target_position": {
                                            "type": "object",
                                            "required": ["x", "y", "z"],
                                            "properties": {
                                                "x": {"type": "number"},
                                                "y": {"type": "number"},
                                                "z": {"type": "number"}
                                            },
                                            "additionalProperties": False
                                        }
                                    },
                                    "additionalProperties": False
                                },
                                {
                                    # Trigger action
                                    "type": "object",
                                    "required": ["type", "source_object_name", "triggerring_time", "source_object_fileID", "condition"],
                                    "properties": {
                                        "type": {"type": "string", "const": "Trigger"},
                                        "source_object_name": {"type": "string"},
                                        "triggerring_time": {"type": "number"},
                                        "source_object_fileID": {"type": "integer"},
                                        "condition": {"type": "string"},
                                        "triggerring_events": {
                                            "type": "array",
                                            "minItems": 0,  # 允许空数组（0 or more event units）
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "methodCallUnits": {
                                                        "type": "array",
                                                        "minItems": 0,  # methodCallUnits 也可以为空
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["script_fileID", "method_name", "parameter_fileID"],
                                                            "properties": {
                                                                "script_fileID": {"type": "integer"},
                                                                "method_name": {"type": "string"},
                                                                "parameter_fileID": {"type": "array", "items": {}}
                                                            },
                                                            "additionalProperties": False
                                                        }
                                                    }
                                                },
                                                "additionalProperties": False
                                            }
                                        },
                                        "triggerred_events": {
                                            "type": "array",
                                            "minItems": 0,  # 允许空数组（0 or more event units）
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "methodCallUnits": {
                                                        "type": "array",
                                                        "minItems": 0,  # methodCallUnits 也可以为空
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["script_fileID", "method_name", "parameter_fileID"],
                                                            "properties": {
                                                                "script_fileID": {"type": "integer"},
                                                                "method_name": {"type": "string"},
                                                                "parameter_fileID": {"type": "array", "items": {}}
                                                            },
                                                            "additionalProperties": False
                                                        }
                                                    }
                                                },
                                                "additionalProperties": False
                                            }
                                        }
                                    },
                                    "additionalProperties": False
                                },
                                {
                                    # Transform action
                                    "type": "object",
                                    "required": ["type", "source_object_name", "source_object_fileID", "delta_position", "delta_rotation", "delta_scale"],
                                    "properties": {
                                        "type": {"type": "string", "const": "Transform"},
                                        "source_object_name": {"type": "string"},
                                        "source_object_fileID": {"type": "integer"},
                                        "delta_position": {
                                            "type": "object",
                                            "required": ["x", "y", "z"],
                                            "properties": {
                                                "x": {"type": "number"},
                                                "y": {"type": "number"},
                                                "z": {"type": "number"}
                                            },
                                            "additionalProperties": False
                                        },
                                        "delta_rotation": {
                                            "type": "object",
                                            "required": ["x", "y", "z"],
                                            "properties": {
                                                "x": {"type": "number"},
                                                "y": {"type": "number"},
                                                "z": {"type": "number"}
                                            },
                                            "additionalProperties": False
                                        },
                                        "delta_scale": {
                                            "type": "object",
                                            "required": ["x", "y", "z"],
                                            "properties": {
                                                "x": {"type": "number"},
                                                "y": {"type": "number"},
                                                "z": {"type": "number"}
                                            },
                                            "additionalProperties": False
                                        },
                                        "triggerring_events": {
                                            "type": "array",
                                            "minItems": 0,  # 允许空数组（0 or more event units）
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "methodCallUnits": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["script_fileID", "method_name", "parameter_fileID"],
                                                            "properties": {
                                                                "script_fileID": {"type": "integer"},
                                                                "method_name": {"type": "string"},
                                                                "parameter_fileID": {"type": "array", "items": {}}
                                                            },
                                                            "additionalProperties": False
                                                        }
                                                    }
                                                },
                                                "additionalProperties": False
                                            }
                                        },
                                        "triggerred_events": {
                                            "type": "array",
                                            "minItems": 0,  # 允许空数组（0 or more event units）
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "methodCallUnits": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["script_fileID", "method_name", "parameter_fileID"],
                                                            "properties": {
                                                                "script_fileID": {"type": "integer"},
                                                                "method_name": {"type": "string"},
                                                                "parameter_fileID": {"type": "array", "items": {}}
                                                            },
                                                            "additionalProperties": False
                                                        }
                                                    }
                                                },
                                                "additionalProperties": False
                                            }
                                        },
                                        "triggerring_time": {"type": "number"}
                                    },
                                    "additionalProperties": False
                                }
                            ]
                        }
                    }
                },
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": False
}

# -----------------------------
# GML图加载函数
# -----------------------------
def load_scene_index_from_gml(gml_file_path: str) -> SceneIndex:
    """
    从GML文件加载场景索引
    
    Args:
        gml_file_path: GML文件路径
    
    Returns:
        SceneIndex: 包含graph的场景索引
    """
    if not os.path.exists(gml_file_path):
        raise FileNotFoundError(f"GML文件未找到: {gml_file_path}")
    
    try:
        graph = nx.read_gml(gml_file_path)
        return {
            "graph": graph,
            "gml_file_path": gml_file_path
        }
    except Exception as e:
        raise Exception(f"加载GML文件失败: {e}")

def get_gameobject_name_from_node(node_data: Dict[str, Any]) -> str:
    """
    从节点数据中提取GameObject名称
    
    Args:
        node_data: 节点数据字典
    
    Returns:
        str: GameObject名称，如果未找到则返回"Unknown"
    """
    if 'properties' in node_data:
        props = node_data['properties']
        
        # GML文件中的properties通常是list格式
        if isinstance(props, list):
            for prop_set in props:
                if isinstance(prop_set, dict):
                    # 检查m_Name字段
                    if 'm_Name' in prop_set:
                        name_value = prop_set['m_Name']
                        if isinstance(name_value, str):
                            return name_value.strip('"\'')
                        elif isinstance(name_value, list) and len(name_value) > 0:
                            # 有时m_Name可能是列表格式
                            return str(name_value[0]).strip('"\'')
        elif isinstance(props, dict):
            # 直接字典格式
            if 'm_Name' in props:
                name_value = props['m_Name']
                if isinstance(name_value, str):
                    return name_value.strip('"\'')
                elif isinstance(name_value, list) and len(name_value) > 0:
                    return str(name_value[0]).strip('"\'')
            
            # 检查PrefabInstance的m_Modifications
            if node_data.get('type') == 'PrefabInstance' and 'PrefabInstance' in props:
                prefab_inst = props['PrefabInstance']
                if isinstance(prefab_inst, list):
                    for item in prefab_inst:
                        if isinstance(item, dict) and 'm_Modification' in item:
                            mod = item['m_Modification']
                            if isinstance(mod, list):
                                for mod_item in mod:
                                    if isinstance(mod_item, dict) and 'm_Modifications' in mod_item:
                                        mods = mod_item['m_Modifications']
                                        if isinstance(mods, list):
                                            for i in range(len(mods)):
                                                mod_set = mods[i]
                                                if isinstance(mod_set, dict) and mod_set.get('propertyPath') == 'm_Name':
                                                    if i + 1 < len(mods):
                                                        m_name_value = mods[i+1].get('value', '')
                                                        if isinstance(m_name_value, str):
                                                            return m_name_value.strip('"\'')
    return "Unknown"

def find_node_by_fileid(graph: nx.Graph, file_id: int) -> Optional[Union[int, str]]:
    """
    通过fileID查找图中的节点ID
    
    Args:
        graph: NetworkX图对象
        file_id: GameObject或Component的fileID
    
    Returns:
        Union[int, str]: 节点ID，如果未找到则返回None
    """
    file_id_str = str(file_id)
    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        
        # 首先检查label字段（gml文件中label通常就是fileID）
        if 'label' in node_data:
            label_str = str(node_data['label']).strip('"\'')
            # 移除可能的"stripped"后缀
            label_clean = label_str.split('stripped')[0].strip()
            if label_clean == file_id_str:
                return node_id
        
        # 检查properties中的id字段
        if 'properties' in node_data:
            props = node_data['properties']
            if isinstance(props, dict):
                if 'id' in props:
                    prop_id = str(props['id']).strip('"\'')
                    prop_id_clean = prop_id.split('stripped')[0].strip()
                    if prop_id_clean == file_id_str:
                        return node_id
            elif isinstance(props, list):
                for prop in props:
                    if isinstance(prop, dict):
                        if 'id' in prop:
                            prop_id = str(prop['id']).strip('"\'')
                            prop_id_clean = prop_id.split('stripped')[0].strip()
                            if prop_id_clean == file_id_str:
                                return node_id
        
        # 最后检查节点ID本身（处理stripped情况）
        node_id_str = str(node_id)
        node_id_clean = node_id_str.split('stripped')[0].strip()
        if node_id_clean == file_id_str:
            return node_id
    
    return None

# -----------------------------
# 便捷函数（修改为从graph查询）
# -----------------------------
def get_obj(scene: SceneIndex, file_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    从场景图中获取GameObject信息
    
    Args:
        scene: 场景索引（包含graph）
        file_id: GameObject的fileID
    
    Returns:
        Dict: GameObject信息，如果未找到则返回None
    """
    if file_id is None:
        return None
    
    graph = scene.get("graph")
    if graph is None:
        return None
    
    # 查找GameObject节点
    gobj_node_id = find_node_by_fileid(graph, file_id)
    if gobj_node_id is None:
        return None
    
    node_data = graph.nodes[gobj_node_id]
    if node_data.get('type') not in ['GameObject', 'PrefabInstance', 'Source Prefab GameObject']:
        return None
    
    # 构建GameObject信息
    gobj_info = {
        "name": get_gameobject_name_from_node(node_data),
        "components": [],
        "scripts": [],
        "prefab_instance_fileID": None,
        "tags": [],
        "is_xr_controller": False,
        "is_test_agent": False
    }
    
    # 查找组件和脚本
    for source, target, edge_data in graph.edges(data=True):
        if str(source) == str(gobj_node_id):
            edge_type = edge_data.get('type', '')
            target_node = graph.nodes[target]
            target_type = target_node.get('type', '')
            
            if edge_type == 'Has_Mono_Comp':
                # 查找脚本信息
                mono_comp_id = target
                for s, t, e in graph.edges(data=True):
                    if str(s) == str(mono_comp_id) and e.get('type') == 'Source_Code_File':
                        script_node = graph.nodes[t]
                        script_info = {
                            "fileID": int(str(t).split()[0]) if str(t).split()[0].isdigit() else None,
                            "class": script_node.get('properties', {}).get('name', 'Unknown') if isinstance(script_node.get('properties'), dict) else 'Unknown',
                            "inherits": ["MonoBehaviour"],  # 默认继承MonoBehaviour
                            "methods": []  # 需要从代码分析中获取，这里先留空
                        }
                        gobj_info["scripts"].append(script_info)
                gobj_info["components"].append("MonoBehaviour")
            elif edge_type == 'Has_Other_Comp':
                if target_type == 'Transform':
                    gobj_info["components"].append("Transform")
                elif 'Collider' in target_type:
                    gobj_info["components"].append("Collider")
            elif edge_type == 'Has_Rigidbody':
                gobj_info["components"].append("Rigidbody")
            elif edge_type == 'Has_Collider':
                gobj_info["components"].append("Collider")
            elif edge_type == 'Has_Event_Trigger':
                gobj_info["components"].append("EventTrigger")
            elif edge_type == 'PrefabInstance_INFO':
                # 获取Prefab实例的fileID
                prefab_fileid = int(str(target).split()[0]) if str(target).split()[0].isdigit() else None
                gobj_info["prefab_instance_fileID"] = prefab_fileid
    
    # 检查是否是XR Controller
    for comp in gobj_info["components"]:
        if comp.startswith("XR") or "Controller" in comp:
            gobj_info["is_xr_controller"] = True
            break
    
    # 检查是否是TestAgent（通过tag或名称）
    if gobj_info["name"].lower() == "testagent" or "TestAgent" in gobj_info["tags"]:
        gobj_info["is_test_agent"] = True
    
    return gobj_info

def has_component(obj: Dict[str, Any], comp: str) -> bool:
    return obj and comp in (obj.get("components") or [])

def is_player_name(name: Optional[str]) -> bool:
    return name is not None and name.lower() == "player"

def is_xr_controller(obj: Optional[Dict[str, Any]]) -> bool:
    return bool(obj and (obj.get("is_xr_controller") or any(c.startswith("XR") for c in obj.get("components", []))))

def is_test_agent(obj: Optional[Dict[str, Any]]) -> bool:
    return bool(obj and (obj.get("is_test_agent") or "TestAgent" in obj.get("tags", [])))

def inherits_unity_events(script_meta: Dict[str, Any]) -> bool:
    inherits = [s.lower() for s in (script_meta.get("inherits") or [])]
    return ("unityengine.events" in inherits) or ("unityevent" in inherits)

def coverage_gobj_ratio(plan: Dict[str, Any], hierarchy_index: List[Dict[str, Any]]) -> float:
    """
    计算测试计划覆盖的GameObject比例
    
    将plan中的source_object_fileID的测试物体列表与hierarchy中gameobject_id的
    mono_comp_relations的source ID以及child_mono_comp_info中所有的mono_comp_targets的
    source ID的集合进行对比，计算可互动物体的覆盖率。
    
    Args:
        plan: 测试计划，包含taskUnits列表
        hierarchy_index: GameObject层次索引，每个元素包含gameobject_id、mono_comp_relations和child_mono_comp_info
    
    Returns:
        float: 覆盖率比例，范围0.0-1.0。如果没有可互动物体，返回0.0
    """
    # 1. 从plan中提取所有source_object_fileID
    plan_source_ids = set()
    for task_unit in plan.get("taskUnits", []):
        for action_unit in task_unit.get("actionUnits", []):
            source_file_id = action_unit.get("source_object_fileID")
            if source_file_id is not None:
                # 转换为字符串以便与hierarchy中的ID比较
                plan_source_ids.add(str(source_file_id))
    
    # 2. 从hierarchy中收集所有可互动物体的source ID
    hierarchy_source_ids = set()
    
    for gobj_info in hierarchy_index:
        # 2.1 从mono_comp_relations中收集source ID
        for mono_comp_relation in gobj_info.get("mono_comp_relations", []):
            source_id = mono_comp_relation.get("source_replace")
            if source_id is not None:
                hierarchy_source_ids.add(str(source_id))
        
        # 2.2 从child_mono_comp_info中收集所有mono_comp_targets的source ID
        for child_info in gobj_info.get("child_mono_comp_info", []):
            mono_comp_targets = child_info.get("mono_comp_targets", [])
            for mono_comp_target in mono_comp_targets:
                source_id = mono_comp_target.get("source_replace")
                if source_id is not None:
                    hierarchy_source_ids.add(str(source_id))
    
    # 3. 计算覆盖率
    if len(hierarchy_source_ids) == 0:
        # 如果没有可互动物体，返回0.0
        return 0.0
    
    # 计算交集：plan中覆盖的source ID
    covered_ids = plan_source_ids & hierarchy_source_ids
    
    # 覆盖率 = 覆盖的数量 / 总可互动物体数量
    coverage_ratio = len(covered_ids) / len(hierarchy_source_ids)
    
    return coverage_ratio

def find_script_meta(scene: SceneIndex, script_file_id: int) -> Optional[Dict[str, Any]]:
    """
    从场景图中查找脚本元数据
    
    Args:
        scene: 场景索引（包含graph）
        script_file_id: 脚本的fileID
    
    Returns:
        Dict: 脚本元数据，如果未找到则返回None
    """
    graph = scene.get("graph")
    if graph is None:
        return None
    
    # 查找脚本节点
    script_node_id = find_node_by_fileid(graph, script_file_id)
    if script_node_id is None:
        return None
    
    node_data = graph.nodes[script_node_id]
    if node_data.get('type') != 'script_file':
        return None
    
    # 构建脚本元数据
    props = node_data.get('properties', {})
    if isinstance(props, dict):
        script_name = props.get('name', 'Unknown')
    else:
        script_name = 'Unknown'
    
    return {
        "class": script_name,
        "inherits": ["MonoBehaviour"],  # 默认继承MonoBehaviour
        "methods": []  # 需要从代码分析中获取，这里先留空
    }

def method_signature_ok(script_meta: Dict[str, Any], method_name: str) -> bool:
    methods = script_meta.get("methods") or []
    for m in methods:
        if m.get("name") == method_name and m.get("public") and len(m.get("params") or []) == 0:
            return True
    return False

# -----------------------------
# 规则评估器
# -----------------------------
def validate_schema(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """使用 JSON Schema 做基础结构校验。"""
    findings = []
    validator = Draft202012Validator(TEST_PLAN_SCHEMA)
    for err in sorted(validator.iter_errors(plan), key=lambda e: e.path):
        findings.append({
            "level": "ERROR",
            "type": "schema_error",
            "path": "/".join(map(str, err.path)),
            "message": f"Schema validation: {err.message}"
        })
    return findings

def rule_allowed_action_types(action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if action.get("type") not in {"Grab", "Trigger", "Transform"}:
        return {"level": "ERROR", "type": "invalid_action_type", "path": "action.type", "message": "Action type must be one of ['Grab','Trigger','Transform']"}
    return None

def rule_no_actions_on_xr_or_agent(obj: Dict[str, Any], path_prefix: str) -> List[Dict[str, Any]]:
    findings = []
    if is_xr_controller(obj):
        findings.append({"level": "ERROR", "type": "action_on_forbidden_object", "path": path_prefix, "message": "Do not directly perform actions on XR Interaction Toolkit controllers"})
    if is_test_agent(obj):
        findings.append({"level": "ERROR", "type": "action_on_forbidden_object", "path": path_prefix, "message": "Do not directly perform actions on the test agent"})
    return findings

def rule_prefab_instance_reference(obj: Dict[str, Any], provided_file_id: int, path_prefix: str) -> Optional[Dict[str, Any]]:
    pref_id = obj.get("prefab_instance_fileID")
    if pref_id is not None and provided_file_id != pref_id:
        return {"level": "WARN", "type": "prefab_reference_suggestion", "path": path_prefix, "message": f"Use m_PrefabInstance fileID ({pref_id}) for referencing this object instead of {provided_file_id}"}
    return None

def rule_grab(action: Dict[str, Any], scene: SceneIndex, action_path: str) -> List[Dict[str, Any]]:
    findings = []
    src = get_obj(scene, action.get("source_object_fileID"))
    tgt = get_obj(scene, action.get("target_object_fileID"))
    # 基础检查
    f = rule_allowed_action_types(action)
    if f: findings.append(f)
    findings += rule_no_actions_on_xr_or_agent(src, f"{action_path}/source_object_fileID")
    # 两种格式：format1（有target）或 format2（delta_position）
    if tgt:  # format1
        findings += rule_no_actions_on_xr_or_agent(tgt, f"{action_path}/target_object_fileID")
        # Player限制：不要对名为Player的对象做Grab
        if is_player_name(tgt.get("name")):
            findings.append({"level": "CONSISTENCY", "type": "action_on_forbidden_object", "path": f"{action_path}/target_object_name", "message": "Do not use 'Grab' on Player"})
        # 目标必须有Rigidbody
        if not has_component(tgt, "Rigidbody"):
            findings.append({"level": "CONSISTENCY", "type": "missing_component", "path": f"{action_path}/target_object_fileID", "message": "Grab target must have a Rigidbody component"})
        # Prefab引用建议
        pf = rule_prefab_instance_reference(tgt, action.get("target_object_fileID"), f"{action_path}/target_object_fileID")
        if pf: findings.append(pf)
    else:  # format2
        # 使用delta_position时，源对象是被移动的对象，必须有Rigidbody
        if not src or not has_component(src, "Rigidbody"):
            findings.append({"level": "CONSISTENCY", "type": "missing_component", "path": f"{action_path}/source_object_fileID", "message": "Grab with delta_position requires source object to have a Rigidbody"})
    # Prefab引用建议（源对象）
    if src and action.get("source_object_fileID") is not None:
        pf = rule_prefab_instance_reference(src, action.get("source_object_fileID"), f"{action_path}/source_object_fileID")
        if pf: findings.append(pf)
    return findings

def rule_transform(action: Dict[str, Any], scene: SceneIndex, action_path: str) -> List[Dict[str, Any]]:
    findings = []
    src = get_obj(scene, action.get("source_object_fileID"))
    f = rule_allowed_action_types(action)
    if f: findings.append(f)
    findings += rule_no_actions_on_xr_or_agent(src, f"{action_path}/source_object_fileID")
    # Player限制：不要对名为Player的对象做Transform
    if src and is_player_name(src.get("name")):
        findings.append({"level": "CONSISTENCY", "type": "action_on_forbidden_object", "path": f"{action_path}/source_object_name", "message": "Do not use 'Transform' on Player"})
    # Transform对象必须有Rigidbody
    if not src or not has_component(src, "Rigidbody"):
        findings.append({"level": "CONSISTENCY", "type": "missing_component", "path": f"{action_path}/source_object_fileID", "message": "Transform requires source object to have a Rigidbody"})
    # 触发事件的参数必须为空数组
    for ev_list_name in ["triggerring_events", "triggerred_events"]:
        for i, ev in enumerate(action.get(ev_list_name, [])):
            for j, m in enumerate(ev.get("methodCallUnits", [])):
                params = m.get("parameter_fileID", [])
                if params:
                    findings.append({"level": "CORRECTNESS", "type": "invalid_method_parameters", "path": f"{action_path}/{ev_list_name}[{i}]/methodCallUnits[{j}]/parameter_fileID", "message": "Transform-embedded Trigger only supports parameterless methods (parameter_fileID must be empty)"})
    # Prefab引用建议
    if src and action.get("source_object_fileID") is not None:
        pf = rule_prefab_instance_reference(src, action.get("source_object_fileID"), f"{action_path}/source_object_fileID")
        if pf: findings.append(pf)
    return findings

def rule_trigger(action: Dict[str, Any], scene: SceneIndex, action_path: str) -> List[Dict[str, Any]]:
    findings = []
    src = get_obj(scene, action.get("source_object_fileID"))
    f = rule_allowed_action_types(action)
    if f: findings.append(f)
    findings += rule_no_actions_on_xr_or_agent(src, f"{action_path}/source_object_fileID")
    # 触发对象必须具有 Rigidbody 或 Collider 或 EventTrigger，或其脚本继承 UnityEngine.Events
    ok = False
    if src:
        ok = any(has_component(src, comp) for comp in ["Rigidbody", "Collider", "EventTrigger"])
        if not ok:
            # 检查脚本是否继承 UnityEngine.Events
            for s in (src.get("scripts") or []):
                if inherits_unity_events(s):
                    ok = True
                    break
    if not ok:
        findings.append({"level": "CONSISTENCY", "type": "missing_component", "path": f"{action_path}/source_object_fileID", "message": "Trigger requires source object to have Rigidbody or Collider or EventTrigger, or scripts inheriting UnityEngine.Events"})
    # 方法调用检查：MonoBehaviour 公共无参方法，且 parameter_fileID 必须为空
    for ev_list_name in ["triggerring_events", "triggerred_events"]:
        for i, ev in enumerate(action.get(ev_list_name, [])):
            for j, m in enumerate(ev.get("methodCallUnits", [])):
                script_id = m.get("script_fileID")
                method_name = m.get("method_name")
                params = m.get("parameter_fileID", [])
                if params:
                    findings.append({"level": "CORRECTNESS", "type": "invalid_method_parameters", "path": f"{action_path}/{ev_list_name}[{i}]/methodCallUnits[{j}]/parameter_fileID", "message": "Trigger only supports parameterless methods (parameter_fileID must be empty)"})
                script_meta = find_script_meta(scene, script_id)
                if not script_meta:
                    findings.append({"level": "CONSISTENCY", "type": "script_not_found", "path": f"{action_path}/{ev_list_name}[{i}]/methodCallUnits[{j}]/script_fileID", "message": f"Script fileID {script_id} not found in scene index"})
                    continue
                # 必须继承 MonoBehaviour 且方法签名满足要求
                if "MonoBehaviour" not in (script_meta.get("inherits") or []):
                    findings.append({"level": "CONSISTENCY", "type": "invalid_script_inheritance", "path": f"{action_path}/{ev_list_name}[{i}]/methodCallUnits[{j}]/script_fileID", "message": "Target script must inherit from MonoBehaviour"})
                if not method_signature_ok(script_meta, method_name):
                    findings.append({"level": "CONSISTENCY", "type": "invalid_method_signature", "path": f"{action_path}/{ev_list_name}[{i}]/methodCallUnits[{j}]/method_name", "message": "Method must be public and have no parameters"})
    # Prefab引用建议
    if src and action.get("source_object_fileID") is not None:
        pf = rule_prefab_instance_reference(src, action.get("source_object_fileID"), f"{action_path}/source_object_fileID")
        if pf: findings.append(pf)
    return findings

def _get_action_signature(action: Dict[str, Any], action_type: str) -> Dict[str, Any]:
    """
    根据动作类型提取用于比较的签名（排除source_object_fileID，因为已经按此分组）
    
    Args:
        action: 动作字典
        action_type: 动作类型 ("Trigger", "Grab", "Transform")
    
    Returns:
        Dict: 用于比较的签名字典
    """
    if action_type == "Trigger":
        return {
            "source_object_fileID": action.get("source_object_fileID"),
            "triggerring_events": action.get("triggerring_events", []),
            "triggerred_events": action.get("triggerred_events", [])
        }
    elif action_type == "Grab":
        signature = action.copy()
        signature.pop("source_object_name", None)  # name可能不同但实际是同一个对象
        signature.pop("target_object_name", None)
        return signature
    elif action_type == "Transform":
        has_trigger_events = bool(action.get("triggerring_events") or action.get("triggerred_events"))
        if has_trigger_events:
            return {
                "source_object_fileID": action.get("source_object_fileID"),
                "triggerring_events": action.get("triggerring_events", []),
                "triggerred_events": action.get("triggerred_events", [])
            }
        else:
            signature = action.copy()
            signature.pop("source_object_name", None)
            signature.pop("triggerring_events", None)
            signature.pop("triggerred_events", None)
            signature.pop("triggerring_time", None)
            return signature

def rule_duplicate_plan(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    检测测试计划中的重复动作
    
    对于同一个source_object_fileID的物体，如果有多个相同的action，则判定为重复：
    - Trigger动作：如果triggerring_events和triggerred_events中的参数完全一样，则判定为重复
    - Grab动作：如果其他参数完全一样，则判定为重复
    - Transform动作：如果有triggerring_events或triggerred_events字段，则比较这两个字段的参数；
      如果没有，则比较其他所有参数来判定是否重复
    
    Args:
        plan: 测试计划，包含taskUnits列表
    
    Returns:
        List[Dict]: findings列表，包含重复动作的警告信息
    """
    findings = []
    
    # 按source_object_fileID分组所有的actionUnits
    actions_by_source_id: Dict[int, List[tuple]] = {}  # source_id -> [(task_idx, action_idx, action)]
    
    for task_idx, task_unit in enumerate(plan.get("taskUnits", [])):
        for action_idx, action in enumerate(task_unit.get("actionUnits", [])):
            source_file_id = action.get("source_object_fileID")
            if source_file_id is not None:
                if source_file_id not in actions_by_source_id:
                    actions_by_source_id[source_file_id] = []
                actions_by_source_id[source_file_id].append((task_idx, action_idx, action))
    
    # 对每个source_object_fileID，检查是否有重复的动作
    for source_file_id, actions in actions_by_source_id.items():
        if len(actions) < 2:
            continue  # 只有一个动作，不可能重复
        
        # 按动作类型分组
        actions_by_type: Dict[str, List[tuple]] = {}
        for task_idx, action_idx, action in actions:
            action_type = action.get("type", "Unknown")
            if action_type not in actions_by_type:
                actions_by_type[action_type] = []
            actions_by_type[action_type].append((task_idx, action_idx, action))
        
        # 对每种动作类型，检查重复
        for action_type, type_actions in actions_by_type.items():
            if len(type_actions) < 2:
                continue  # 该类型只有一个动作，不可能重复
            
            # 计算每个动作的签名
            action_signatures = []
            for task_idx, action_idx, action in type_actions:
                signature = _get_action_signature(action, action_type)
                action_signatures.append((task_idx, action_idx, action, signature))
            
            # 检查是否有重复的签名
            seen_signatures = {}  # signature_str -> first occurrence (task_idx, action_idx)
            
            for task_idx, action_idx, action, signature in action_signatures:
                # 将签名转换为可比较的字符串（使用JSON序列化）
                signature_key = json.dumps(signature, sort_keys=True)
                
                if signature_key in seen_signatures:
                    # 发现重复
                    first_task_idx, first_action_idx = seen_signatures[signature_key]
                    findings.append({
                        "level": "DUPLICATE",
                        "type": "duplicate_action",
                        "path": f"taskUnits[{task_idx}]/actionUnits[{action_idx}]",
                        "message": f"Duplicate {action_type} action detected for source_object_fileID {source_file_id}. "
                                 f"This action is identical to the one at taskUnits[{first_task_idx}]/actionUnits[{first_action_idx}]. "
                                 f"Consider removing the duplicate action."
                    })
                else:
                    seen_signatures[signature_key] = (task_idx, action_idx)
    
    return findings

def evaluate_policies(plan: Dict[str, Any], scene: SceneIndex) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    findings.extend(validate_schema(plan))
    # 检查重复动作
    findings.extend(rule_duplicate_plan(plan))
    action_num = 0
    # 若Schema报错，可选择直接返回；这里继续执行以收集尽可能多的问题
    for tu_idx, task in enumerate(plan.get("taskUnits", [])):
        for au_idx, action in enumerate(task.get("actionUnits", [])):
            action_type = action.get("type")
            path_prefix = f"taskUnits[{tu_idx}]/actionUnits[{au_idx}]"
            action_num += 1
            if action_type == "Grab":
                findings.extend(rule_grab(action, scene, path_prefix))
            elif action_type == "Transform":
                findings.extend(rule_transform(action, scene, path_prefix))
            elif action_type == "Trigger":
                findings.extend(rule_trigger(action, scene, path_prefix))
            else:
                findings.append({"level": "CORRECTNESS", "type": "unknown_action_type", "path": f"{path_prefix}/type", "message": "Unknown action type"})
            # 通用额外规则：名称与索引匹配（可选）
            src_obj = get_obj(scene, action.get("source_object_fileID"))
            if src_obj and action.get("source_object_name") and action["source_object_name"] != src_obj["name"]:
                findings.append({"level": "CONSISTENCY", "type": "name_mismatch", "path": f"{path_prefix}/source_object_name", "message": f"Name does not match scene index (expected '{src_obj['name']}')"})
            tgt_obj = get_obj(scene, action.get("target_object_fileID"))
            if tgt_obj and action.get("target_object_name") and action["target_object_name"] != tgt_obj["name"]:
                findings.append({"level": "CONSISTENCY", "type": "name_mismatch", "path": f"{path_prefix}/target_object_name", "message": f"Name does not match scene index (expected '{tgt_obj['name']}')"})
    return findings, len([i for i in findings if i["level"] == "CORRECTNESS"]), len([i for i in findings if i["level"] == "CONSISTENCY"]), len([i for i in findings if i["level"] == "DUPLICATE"]), action_num

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估测试计划")
    parser.add_argument('-r', '--results-dir', required=True, 
                       help='结果目录路径，包含test_plan.json')
    parser.add_argument('-m', '--llm-model', type=str, default='gpt-5',
                       help='LLM模型（可选)')
    
    args = parser.parse_args()
    results_dir = args.results_dir
    llm_model = args.llm_model
    llm_responses_dir = os.path.join(results_dir, "llm_responses", llm_model)
    scene_info_dir = os.path.join(results_dir, "scene_detailed_info", "mainResults")
    evaluate_dic = {}
    for dir_name in os.listdir(llm_responses_dir):
        test_plan_dir = os.path.join(llm_responses_dir, dir_name)
        for file in os.listdir(test_plan_dir):
            if file.endswith("consolidated_test_plans.json"):
                plan = json.load(open(os.path.join(test_plan_dir, file)))
                scene_index = load_scene_index_from_gml(os.path.join(scene_info_dir, dir_name+".unity.json_graph.gml"))
                hierarchy_index = json.load(open(os.path.join(results_dir, dir_name+"_gobj_hierarchy.json")))
                gobj_ratio = coverage_gobj_ratio(plan, hierarchy_index)
                findings, correctness_number, consistency_number, duplicate_number, action_num = evaluate_policies(plan, scene_index)
                evaluate_dic["CER@100AU"] = correctness_number / action_num * 100
                evaluate_dic["CVR@100AU"] = consistency_number / action_num * 100
                evaluate_dic["DR@100AU"] = duplicate_number / action_num * 100
                
                evaluate_dic["gobj_coverage_ratio"] = gobj_ratio
                evaluate_dic["AU"] = action_num
                evaluate_dic["consistency_number"] = consistency_number
                evaluate_dic["correctness_number"] = correctness_number
                evaluate_dic["duplicate_number"] = duplicate_number
                evaluate_dic["smells"] = findings
                
                
                with open(os.path.join(test_plan_dir, file.replace("consolidated_test_plans.json", "evaluate_findings.json")), 'w', encoding='utf-8') as f:
                    json.dump(evaluate_dic, f, indent=2, ensure_ascii=False)