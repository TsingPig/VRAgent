# Kitchen_TestRoom 测试命令参考

> 在 `TP_Generation/` 下执行所有命令

## 环境变量

```powershell
$Python     = "d:\--UnityProject\HenryLabXR\VRAgent\.venv\Scripts\python.exe"
$ProjectRoot= "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent"
$TPGen      = "d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation"
$ResultsDir = "$TPGen\Results\Results_Kitchen_TestRoom"
$SceneDoc   = "$ProjectRoot\Assets\SampleScene\Kitchen_TestRoom\DELIVERY_NOTES.md"
$ScriptsDir = "$ProjectRoot\Assets\SampleScene\Kitchen_TestRoom"
$OutputDir  = "$TPGen\Results_VRAgent2.0\Kitchen_TestRoom"
cd $TPGen
```

---

## Stage 1 — 场景数据提取

```powershell
& $Python ExtractSceneDependency.py `
  -p $ProjectRoot -r $ResultsDir `
  --scene-path "Assets/SampleScene/Kitchen_TestRoom/Kitchen_TestRoom.unity"
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
  "--scene_name",      "Kitchen_TestRoom",
  "--hierarchy_json",  "$ResultsDir\Kitchen_TestRoom_gobj_hierarchy.json",
  "--scene_gml",       "$ResultsDir\scene_detailed_info\mainResults\Kitchen_TestRoom.unity.json_graph.gml",
  "--scene_doc",       $SceneDoc,
  "--scripts_dir",     $ScriptsDir,
  "--output",          $OutputDir,
  "--app_name",        "Kitchen_TestRoom",
  "--budget",          "100",
  "--max_repair",      "2",
  "--model",           "gpt-4o"
)
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
```

---

## Stage 5 — 清除旧结果

```powershell
& $Python -m vragent2 @Common --clean llm        # 仅 LLM 输出
& $Python -m vragent2 @Common --clean analysis    # 仅分析结果（需重跑 Stage 1&2）
& $Python -m vragent2 @Common --clean all         # 全部
```

> `--clean` 不可与 `--resume` / `--replay` 同时使用。

---

## 烟雾测试（42 tests）

```powershell
& $Python -m tests.test_vragent2_smoke
```

---

## 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--budget N` | 100 | 探索总预算 |
| `--max_repair N` | 2 | V1 修复循环上限 |
| `--model M` | gpt-4o | 全局 LLM 模型 |
| `--planner_model/temp` | — | Planner 专用模型/温度 |
| `--verifier_model/temp` | — | V1 Verifier 专用 |
| `--observer_model/temp` | — | Observer 专用 |
| `--scene_model/temp` | — | SceneUnderstanding 专用 |
| `--limit N` | 0 | 只处理前 N 个对象 |
| `--resume` | off | 续接上次 session（含黑板状态） |
| `--unity` | off | 连接 Unity 实时执行 |
| `--replay PATH/auto` | — | 重放已有 test_plan（需 `--unity`） |
| `--clean llm/analysis/all` | — | 清除旧结果 |
| `--no_verifier_llm` | — | 关闭 V1 LLM（仅规则检查） |
| `--no_observer_llm` | — | 关闭 Observer LLM（仅规则 O1/O2） |
| `--no_info_sharing` | — | 关闭 Agent 间信息共享 |
| `--scene_doc PATH` | — | DELIVERY_NOTES.md 路径 |

---

## 架构概览

```
SceneUnderstanding → [Scheduler → Planner → V1(Static) → V2(Semantic)
                      → Executor → Observer → Blackboard]*
```

- **SharedWorldState** 黑板：所有 Agent 共享读写，`--resume` 持久化恢复
- **V2 SemanticVerifier**：LLM 评审员，verdict = accept / reject / revise + counter-plan
- **Observer O1/O2/O3**：状态差分 → 失败假设 → 策略推荐（含 scheduler_bias）
- **Scheduler**：接收黑板 scheduler_bias + failure_counts 自适应选对象
