# Kitchen_TestRoom 测试命令行参考

> 所有命令均在 `d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\` 目录下执行  
> Python 使用项目 venv：`d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe`

---

## 路径定义（PowerShell 变量）

```powershell
$ProjectRoot  = "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent"
$TPGen        = "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation"
$Python       = "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe"
$ResultsDir   = "$TPGen\Results\Results_Kitchen_TestRoom"
$SceneDoc     = "$ProjectRoot\Assets\SampleScene\Kitchen_TestRoom\DELIVERY_NOTES.md"
$ScriptsDir   = "$ProjectRoot\Assets\SampleScene\Kitchen_TestRoom"
$OutputDir    = "$TPGen\Results_VRAgent2.0\Kitchen_TestRoom"

cd $TPGen
```

如果你是新开终端，必须先执行上面的变量定义；否则 `$Python`、`$ResultsDir` 等变量为空，会导致命令失败。

---

## 阶段 1：场景数据提取（ExtractSceneDependency）

一次性完成：场景 JSON 解析、脚本 meta 分析、CSharp 代码分析、Prefab 分析、GML 依赖图构建。

```powershell
& $Python ExtractSceneDependency.py `
  -p $ProjectRoot `
  -r $ResultsDir `
  --scene-path "Assets/SampleScene/Kitchen_TestRoom/Kitchen_TestRoom.unity"
```

**产出文件：**

| 文件 | 路径 |
|------|------|
| 场景 JSON | `scene_detailed_info/mainResults/Kitchen_TestRoom.unity.json` |
| 场景数据库 | `scene_detailed_info/mainResults/Kitchen_TestRoom.unity.json_database.json` |
| GML 依赖图 | `scene_detailed_info/mainResults/Kitchen_TestRoom.unity.json_graph.gml` |
| 代码分析 | `script_detailed_info/mainResults/CodeAnalysis.json` |
| 代码结构 | `script_detailed_info/mainResults/CodeStructure.json` |
| 对象标签 | `Kitchen_TestRoom_gobj_tag.json` |
| 对象层级 | `Kitchen_TestRoom_gobj_layer.json` |

---

## 阶段 2：层次结构遍历（TraverseSceneHierarchy）

基于 GML 图生成 GameObject 层次 JSON（VRAgent 2.0 管线的入口数据）。

```powershell
& $Python TraverseSceneHierarchy.py -r $ResultsDir
```

**产出文件：**

| 文件 | 路径 |
|------|------|
| 层次 JSON | `Kitchen_TestRoom_gobj_hierarchy.json` |
| 源码文件列表 | `GenerationResultsResults_Kitchen_TestRoom_source_code_files.json` |

---

## 阶段 3：VRAgent 2.0 管线

### 3a. 快速测试（限制前 2 个对象）

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --scene_doc $SceneDoc `
  --scripts_dir $ScriptsDir `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --budget 20 `
  --max_repair 2 `
  --model "gpt-4o" `
  --limit 2
```

### 3b. 完整运行（全部 7 个 GameObject）

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --scene_doc $SceneDoc `
  --scripts_dir $ScriptsDir `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --budget 100 `
  --max_repair 2 `
  --model "gpt-4o"
```

### 3c. 断点续跑（复用上次 session）

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --scene_doc $SceneDoc `
  --scripts_dir $ScriptsDir `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --budget 100 `
  --max_repair 2 `
  --model "gpt-4o" `
  --resume
```

### 3d. 连接 Unity 实时执行

需先在 Unity 中进入 Play Mode 并确保 `AgentBridge` 组件已挂载。

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --scene_doc $SceneDoc `
  --scripts_dir $ScriptsDir `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --budget 100 `
  --max_repair 2 `
  --model "gpt-4o" `
  --unity
```

如果出现报错：

- `表达式或语句中包含意外的标记“-m”`：通常是少了开头的 `&`
- `管道元素中的“&”后面的表达式生成无效的对象`：通常是 `$Python` 未定义

可用下面两步快速修复：

```powershell
$Python = "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe"
& $Python --version
```

也可以直接使用绝对路径（不依赖变量）：

```powershell
& "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe" -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results\Results_Kitchen_TestRoom\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results\Results_Kitchen_TestRoom\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --scene_doc "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent\Assets\SampleScene\Kitchen_TestRoom\DELIVERY_NOTES.md" `
  --scripts_dir "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent\Assets\SampleScene\Kitchen_TestRoom" `
  --output "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results_VRAgent2.0\Kitchen_TestRoom" `
  --app_name "Kitchen_TestRoom" `
  --budget 100 `
  --max_repair 2 `
  --model "gpt-4o" `
  --unity
```

---

## 可选参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--budget N` | 100 | 探索迭代总预算 |
| `--max_repair N` | 2 | Verifier→Planner 修复循环上限 |
| `--model M` | gpt-4o | 全局 LLM 模型 |
| `--planner_model M` | — | 单独指定 Planner 模型 |
| `--verifier_model M` | — | 单独指定 Verifier 模型 |
| `--observer_model M` | — | 单独指定 Observer 模型 |
| `--limit N` | 0(全部) | 只处理前 N 个对象 |
| `--resume` | off | 续接上次 session |
| `--unity` | off | 连接 Unity 实时执行 |
| `--replay PATH` | — | 重放已有 test_plan.json（不调 LLM），需配合 `--unity` |
| `--clean` | off | 清除 output 目录下的所有旧结果后再执行（不可与 --resume/--replay 同时使用） |
| `--no_verifier_llm` | — | 关闭 Verifier LLM（仅规则检查） |
| `--no_info_sharing` | — | 关闭 Agent 间信息共享（消融实验用） |

---

## 阶段 4：重放已有 Test Plan（不调 LLM）

LLM 生成一次 test_plan 后，后续可直接在 Unity 中重放，无需再调用 LLM。

需先在 Unity 中进入 Play Mode 并确保 `AgentBridge` 组件已挂载。

### 4a. 自动使用 output 目录下的 test_plan.json

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --unity `
  --replay auto
```

### 4b. 指定任意 test_plan.json 路径

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --unity `
  --replay "$OutputDir\test_plan.json"
```

### 4c. 直接使用绝对路径（不依赖变量）

```powershell
& "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe" -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results\Results_Kitchen_TestRoom\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results\Results_Kitchen_TestRoom\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --output "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation\Results_VRAgent2.0\Kitchen_TestRoom" `
  --app_name "Kitchen_TestRoom" `
  --unity `
  --replay auto
```

重放结果保存在 `<output>/replay/replay_<timestamp>.json`，包含每个 action 的执行成功/失败、状态变化、Console 日志。

---

## 阶段 5：清除旧结果后重新执行

在 output 目录已有旧结果的情况下，加 `--clean` 可一键清除后重新跑 LLM：

```powershell
& $Python -m vragent2 `
  --scene_name "Kitchen_TestRoom" `
  --hierarchy_json "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json" `
  --scene_gml "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml" `
  --output $OutputDir `
  --app_name "Kitchen_TestRoom" `
  --clean
```

`--clean` 会在管线启动前删除 output 目录下的所有 JSON 结果文件以及 `execution/`、`replay/` 子目录。

> **注意**：`--clean` 不可与 `--resume`（会删掉 session_state）或 `--replay`（会删掉 test_plan）同时使用。

---

## 单独工具命令（手动补跑用）

### CSharpAnalyzer（代码分析）

```powershell
& "$TPGen\CSharpScriptAnalyzer\CSharpAnalyzer.exe" `
  -p "$ProjectRoot\Assets" `
  -r "$ResultsDir\script_detailed_info\mainResults"
```

### CodeStructureAnalyzer（代码结构）

```powershell
& "$TPGen\CodeStructureAnalyzer\CodeStructureAnalyzer.exe" `
  -d "$ResultsDir\script_detailed_info\mainResults\CodeAnalysis.json" `
  -r "$ResultsDir\script_detailed_info\mainResults"
```

### UnityDataAnalyzer（场景/资产解析）

```powershell
& "$TPGen\UnityDataAnalyzer\UnityDataAnalyzer.exe" `
  -a "$ProjectRoot\Assets\SampleScene\Kitchen_TestRoom\Kitchen_TestRoom.unity" `
  -r "$ResultsDir\scene_detailed_info"
```
