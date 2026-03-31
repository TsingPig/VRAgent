# Apartment 测试命令参考

> 在 `TP_Generation/` 下执行所有命令

## 环境变量

```powershell
$Python     = "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe"
$ProjectRoot= "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent"
$TPGen      = "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation"
$ResultsDir = "$TPGen\Results\Results_Apartment"
$SceneDoc   = "$ProjectRoot\Assets\SampleScene\Apartment\DELIVERY_NOTES.md"
$ScriptsDir = "$ProjectRoot\Assets\SampleScene\Apartment"
$Model      = "gpt-5.4"                              # 切换模型改这里
$OutputBase = "$TPGen\Results_VRAgent2.0"          # 基目录
$OutputDir  = "$OutputBase\Apartment\$Model"       # 实际输出（代码自动组织）
cd $TPGen
```

---

## Stage 1 — 场景数据提取

```powershell
& $Python ExtractSceneDependency.py `
  -p $ProjectRoot -r $ResultsDir `
  --scene-path "Assets/SampleScene/Apartment/Apartment.unity"
```

## Stage 2 — 层次结构遍历

```powershell
& $Python TraverseSceneHierarchy.py -r $ResultsDir
```

---

## Stage 3 — VRAgent 2.0 管线

公共参数（后续命令均复用）：

```powershell
$Common = @(
  "--scene_name",      "Apartment",
  "--hierarchy_json",  "$ResultsDir\Apartment_gobj_hierarchy.json",
  "--scene_gml",       "$ResultsDir\scene_detailed_info\mainResults\Apartment.unity.json_graph.gml",
  "--scene_doc",       $SceneDoc,
  "--scripts_dir",     $ScriptsDir,
  "--output",          $OutputBase,
  "--app_name",        "Apartment",
  "--budget",          "100",
  "--max_repair",      "2",
  "--model",           $Model,
  "--api_key",         "<YOUR_API_KEY>",
  "--api_base",        "https://api.vectorengine.ai/v1"
)
# 实际输出路径 = $OutputBase/<scene_name>/<model> = Results_VRAgent2.0/Apartment/$Model
# 切换模型只需改顶部 $Model 变量并重新执行环境变量块
```

```powershell
# 快速测试（前 2 个对象）
& $Python -m vragent2 @Common --limit 2

# 完整运行
& $Python -m vragent2 @Common

# 断点续跑（恢复 SharedWorldState 黑板）
& $Python -m vragent2 @Common --resume

# 连接 Unity（需先 Play Mode + AgentBridge）
& $Python -m vragent2 @Common --unity
```

---

## Stage 4 — 重放（不调 LLM，需 Unity Play Mode）

```powershell
& $Python -m vragent2 @Common --unity --replay auto
& $Python -m vragent2 @Common --unity --replay "$OutputDir\test_plan.json"

# 切换模型重放：先改 $Model 再重新设 $Common
# $Model = "gpt-5.2"; $OutputDir = "$OutputBase\Apartment\$Model"
# 然后重新执行 $Common 赋值块，再 replay
```

---

## Stage 5 — Oracle 基准评估

```powershell
& $Python -m vragent2 --benchmark $OutputBase   # 含 Per-Bug Detection Matrix
```

---

## Stage 6 — 清除旧结果

```powershell
& $Python -m vragent2 @Common --clean llm        # 仅 LLM 输出
& $Python -m vragent2 @Common --clean analysis    # 仅分析结果（需重跑 Stage 1&2）
& $Python -m vragent2 @Common --clean all         # 全部
```

> `--clean` 不可与 `--resume` / `--replay` 同时使用。

---
