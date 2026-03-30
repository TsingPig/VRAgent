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
$Model      = "gpt-4o"                              # 切换模型改这里
$OutputBase = "$TPGen\Results_VRAgent2.0"          # 基目录
$OutputDir  = "$OutputBase\Kitchen_TestRoom\$Model" # 实际输出（代码自动组织）
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
  "--output",          $OutputBase,
  "--app_name",        "Kitchen_TestRoom",
  "--budget",          "100",
  "--max_repair",      "2",
  "--model",           $Model,
  "--api_key",         "<YOUR_API_KEY>",
  "--api_base",        "https://api.vectorengine.ai/v1"
)
# 实际输出路径 = $OutputBase/<scene_name>/<model> = Results_VRAgent2.0/Kitchen_TestRoom/$Model
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
# $Model = "gpt-5.2"; $OutputDir = "$OutputBase\Kitchen_TestRoom\$Model"
# 然后重新执行 $Common 赋值块，再 replay
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



## 可视化结果

```powershell
# 指定模型结果目录
& $Python -m vragent2 --visualize $OutputDir

# 指定特定 replay 文件高亮
& $Python -m vragent2 --visualize $OutputDir `
  --visualize_replay "$OutputDir\replay\replay_20260330_184707.json"

# 查看其他模型的结果（直接指定路径）
& $Python -m vragent2 --visualize "$OutputBase\Kitchen_TestRoom\gpt-5.2"

# Pipeline 内自动生成（在线/离线跑完后附加 --visualize）
& $Python -m vragent2 @Common --unity --visualize
```

输出：`$OutputDir\report.html`（自包含 HTML，无外部依赖）

### 结果目录结构

```
Results_VRAgent2.0/               ← --output 基目录
  Kitchen_TestRoom/               ← 按场景分
    gpt-4o/                       ← 按模型分（自动创建）
      test_plan.json
      summary.json
      gate_graph.json
      iteration_logs.json
      session_state.json
      execution/
      replay/
      report.html
    gpt-5.2/                      ← 换 --model 自动归入
      ...
  Home_TwoRooms/
    gpt-4o/
      ...
```

报告包含 9 个 Section：

| Section | 内容 |
|---------|------|
| Session Dashboard | 总动作数、迭代、覆盖率、Gates Solved |
| Replay Results | 执行成功/失败、Gate 统计、异常列表 |
| Action Type Breakdown | Grab/Trigger/Transform 分类 + 成功率柱状图 |
| Object Interaction Heatmap | 各对象交互频次热力图 |
| Action Timeline | 可搜索逐条动作时间线（含状态变化） |
| Gate Graph | 状态节点 + 门控边 |
| Iteration Logs | 每轮 Planner/Verifier/Observer 详情 |
| Replay History | 所有历史 replay 对比表 |
| Console Logs | Unity Console 日志（可搜索） |

> **数据修正**：内置 `_reconcile_replay()` 自动交叉校验 exceptions 与 trace success，
> 旧 replay 文件也能显示修正后的正确数据。
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
| `--visualize [DIR]` | — | 生成 HTML 报告（可独立使用） |
| `--visualize_replay PATH` | latest | 指定高亮的 replay 文件 |
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
