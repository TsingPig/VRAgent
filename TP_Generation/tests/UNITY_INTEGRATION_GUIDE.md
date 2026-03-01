# VRAgent 2.0 Unity 端集成测试指南

> **核心理念**：从"单 LLM 一次性生成"升级为**在线闭环系统**
> 即：**RAG Layer → Multi-Agent Pipeline → Plan→Verify→Execute→Observe** 

## 目录
1. [环境准备](#环境准备)
2. [场景配置](#场景配置)
3. [数据准备：生成 RAG 索引](#数据准备生成-rag-索引)
4. [Phase 1：RAG 层初始化](#phase-1rag-层初始化)
5. [Phase 2：Agents 初始化与主控制器](#phase-2agents-初始化与主控制器)
6. [Phase 3：在线执行闭环](#phase-3在线执行闭环)
7. [调试技巧](#调试技巧)

---

## 环境准备

### 前提条件
- **Unity Version**: 2021.3+ LTS (建议 2022.3+)
- **XR Interaction Toolkit**: 2.0.4+ (已在项目中)
- **已安装组件**: HenryLab.VRExplorer, Newtonsoft.Json

### 检查导入
在 Unity 中验证以下命名空间可用：
```csharp
using HenryLab.VRAgent.Online;
using HenryLab.VRExplorer;
// 无编译错误表示导入正确
```

---

## 场景配置

### 步骤 1: 创建测试场景

1. 在 `Assets/Scenes/` 中创建新场景 `TestOnlineAgent.unity`
2. 按 Ctrl+Shift+S 保存

### 步骤 2: 搭建最小场景

**创建场景对象**:
```
- Plane (3D Primitive, 地面)
- Cube_A (3D Primitive, 用于测试 Grab)
- Cube_B (3D Primitive, 移动目标)
- TestGameObject (空对象, 放 VRAgentOnline 组件)
```

**配置每个对象**:

#### Plane (地面)
- Position: (0, 0, 0)
- Scale: (5, 1, 5)
- Tag: "Ground"

#### Cube_A (源对象)
- Position: (-2, 0.5, 0)
- Scale: (0.5, 0.5, 0.5)
- 添加 Rigidbody (Body Type: Dynamic, Mass: 1)
- Tag: "GrabbableA"
- **记下其 FileID**（稍后需要）

#### Cube_B (目标)
- Position: (2, 0.5, 0)
- Scale: (0.5, 0.5, 0.5)
- 添加 Rigidbody (Body Type: Static)
- Tag: "Target"
- **记下其 FileID**

#### TestGameObject
- Position: (0, 0, 0)
- 添加脚本组件: `VRAgentOnline`
- 「自动」添加组件: `AgentBridge` (port 6400) 和 `StateCollector`

### 步骤 3: 记录 FileIDs

通过菜单获取 FileIDs：
```
Tools → VR Explorer → Copy FileID
```

对于每个对象（Cube_A, Cube_B）：
1. 选中对象
2. 右键 → Copy Component → VRAgent.FileID (或使用菜单工具)
3. 记录输出的 FileID (格式: `file_xxxxx`)

**示例输出**:
```
Cube_A FileID: d4c2a1f5e9b8c7d6
Cube_B FileID: a1b2c3d4e5f6g7h8
```

---

## 数据准备：生成 RAG 索引

在启动在线执行之前，**必须先准备好 RAG 层所需的索引数据**。这些数据来自 Unity 场景分析。

### 前置条件

确保你的 Unity 项目已通过以下工具执行过分析：
- `TraverseSceneHierarchy.py` - 生成 `gobj_hierarchy.json` (对象树)
- `ExtractSceneDependency.py` - 生成 scene dependency GML 和详细信息 (场景图)
- `CSharpScriptAnalyzer/` - 索引 C# 脚本文件

### 查看现有预生成数据

如果你在使用现有项目（如 Maze, EscapeRoom 等），数据已经在 `Results/` 目录中：

```bash
ls Results/Results_maze/
# 输出:
#   gobj_hierarchy.json               ← RAG 索引需要的对象树
#   scene_detailed_info/              ← RAG 索引需要的场景数据
#   script_detailed_info/             ← RAG 索引需要的脚本数据
#   llm_responses/                    ← (可选) 历史 LLM 响应
```

### 为新场景生成数据

如果你想用**新场景**，需要先运行数据提取：

```bash
cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation

# 1. 提取对象层级
python TraverseSceneHierarchy.py --scene_name YourScene --app_name YourApp

# 2. 提取场景依赖关系
python ExtractSceneDependency.py --scene_name YourScene --app_name YourApp

# 3. 分析 C# 脚本（如果你有自定义脚本）
python CSharpScriptAnalyzer/run_analyzer.py --source_dir /path/to/your/scripts
```

输出将保存到 `Results/Results_YourScene/` 下。

---

## Phase 1：RAG 层初始化

RAG (Retrieval-Augmented Generation) 层是**整个 Multi-Agent 系统的知识基础**。它负责：
- 加载并解析场景图（GML 格式的依赖关系）
- 构建对象层级索引 
- 索引 C# 脚本代码
- 为 Planner/Verifier/Observer 提供"局部上下文包"（token-控制）

### RetrievalLayer 初始化

在 Python 端，这一步通常由 `vragent2.main` 自动处理，**但你需要理解它的依赖**：

```python
from vragent2.retrieval.retrieval_layer import RetrievalLayer

# 前置条件：必须有以下文件/目录
# - results_dir/gobj_hierarchy.json
# - results_dir/scene_detailed_info/mainResults/*.gml
# - results_dir/script_detailed_info/

retrieval = RetrievalLayer(
    results_dir="Results/Results_maze",
    scene_name="Maze"
)

# 验证初始化成功
print(f"Scene graph loaded: {retrieval.scene.graph is not None}")
print(f"Objects indexed: {len(retrieval.scene.graph.nodes)}")
print(f"Scripts indexed: {len(retrieval.scripts.index)}")
```

### 检查 RAG 索引

验证 RAG 层已正确初始化：

```bash
# 从 Python REPL：
from vragent2.retrieval.retrieval_layer import RetrievalLayer

retrieval = RetrievalLayer("Results/Results_maze", "Maze")

# 检查对象是否被正确索引
obj_exists = retrieval.object_exists("some_file_id")
obj_name = retrieval.get_object_name("some_file_id")
print(f"Object found: {obj_exists}, Name: {obj_name}")

# 检查特定对象的上下文
from vragent2.utils.file_utils import load_json
hierarchy = load_json("Results/Results_maze/gobj_hierarchy.json")
if hierarchy:
    first_obj = hierarchy[0] if isinstance(hierarchy, list) else list(hierarchy.values())[0]
    context = retrieval.build_context_for_gameobject(first_obj)
    print(f"Context keys: {context.keys()}")
```

---

## Phase 2：Agents 初始化与主控制器

一旦 RAG 层初始化成功，VRAgentController 会自动创建和配置四个 Agents。

### 主控制器的初始化参数

```python
from vragent2.controller import VRAgentController
from vragent2.utils.llm_client import LLMClient
from vragent2.utils.config_loader import load_config
from vragent2.retrieval.retrieval_layer import RetrievalLayer
from vragent2.bridge.unity_bridge import UnityBridge

# 1. 配置
config = load_config()

# 2. LLM 客户端（需要有效的 API 密钥）
llm = LLMClient(
    api_key="your-openai-api-key",
    base_url=None  # 或你的自定义 endpoint
)

# 3. RAG 层（Phase 1 的成果）
retrieval = RetrievalLayer("Results/Results_maze", "Maze")

# 4. [可选] Unity 在线执行桥
unity_bridge = UnityBridge(host="127.0.0.1", port=6400)
try:
    unity_bridge.connect()
    if unity_bridge.ping():
        print("✓ Unity Bridge 连接成功")
    else:
        print("⚠ Unity 未响应，将使用模拟模式")
        unity_bridge = None
except Exception as e:
    print(f"✗ Unity 连接失败: {e}，使用模拟模式")
    unity_bridge = None

# 5. 创建主控制器
controller = VRAgentController(
    config=config,
    llm=llm,
    retrieval=retrieval,
    output_dir="results_online",
    app_name="Maze",
    scene_name="Maze",
    total_budget=50,              # 总探索步数
    max_repair_rounds=2,          # Verifier 最多修复次数
    llm_model="gpt-4",            # 或 "gpt-5"
    unity_bridge=unity_bridge     # None 表示模拟模式
)

print("✓ Controller 初始化成功，包含四个 Agents:")
print(f"  - Planner Agent")
print(f"  - Verifier Agent")
print(f"  - Executor Agent")  
print(f"  - Observer Agent + ExplorationController")
```

### 四个 Agents 的职责

| Agent | 输入 | 输出 | 目的 |
|-------|------|------|------|
| **PlannerAgent** | IIG 子图 + 目标 | 候选 ActionUnits | 生成候选动作 |
| **VerifierAgent** | ActionUnits | 可执行性评分 + 错误定位 | 合规检查 |
| **ExecutorAgent** | 验证通过的 AAU | 执行轨迹 + 覆盖增量 | 在 Unity 执行或模拟 |
| **ObserverAgent** | 执行轨迹 + 日志 | Coverage delta + bug signals | 评估和规划下一阶段 |

---

## Phase 3：在线执行闭环

### 模式 A：验证 RAG 层 + 模拟执行（无 Unity）

**场景**：你还在开发或调试，暂时不需要真实 Unity 执行。

**步骤**：

1. 配置 Python 环境和 API 密钥：
   ```bash
   cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation
   
   # 设置 OpenAI API 密钥（或在 config.py 中配置）
   $env:OPENAI_API_KEY = "your-api-key"
   ```

2. 运行 vragent2 **不连接 Unity**（模拟执行）：
   ```bash
   python -m vragent2 \
       --scene_name Maze \
       --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
       --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
       --output results_online_sim \
       --budget 20 \
       --model gpt-4
   ```

**预期输出**：
```
[MAIN] Scene: Maze
[MAIN] Objects: 42
[MAIN] Budget: 20
[MAIN] Unity Bridge: OFF (dry-run)

[CONTROLLER] Iteration 1/20
[PLANNER] Generated 3 action candidates
[VERIFIER] 3/3 actions passed verification
[EXECUTOR] Simulating 3 actions (Unity not connected)
[OBSERVER] Coverage delta: +5 (LC), +2 (MC)

[CONTROLLER] Iteration 2/20
...

[MAIN] VRAgent 2.0 Complete
  Total actions : 57
  Iterations    : 20
  Coverage      : 0.7234
```

**成功标志**：
- ✓ 无连接错误（因为不连接 Unity）
- ✓ 每轮都有 Planner → Verifier → Executor → Observer 日志
- ✓ 生成 `results_online_sim/` 目录，包含轨迹和覆盖统计

---

### 模式 B：基础 Unity 连接测试（无闭环）

**场景**：验证 Unity 端 AgentBridge 能接收连接，但不运行完整闭环。

**前置条件**：
- Unity 已启动 Play 模式（TestOnlineAgent 场景或任何含 AgentBridge 的场景）
- 查看 Console 输出确认 `[AgentBridge] Server started on 127.0.0.1:6400`

**步骤**：

1. 在 Python 中测试连接：
   ```python
   from vragent2.bridge.unity_bridge import UnityBridge
   
   bridge = UnityBridge(host="127.0.0.1", port=6400)
   bridge.connect()
   
   # Test 1: Ping
   if bridge.ping():
       print("✓ Ping successful")
   else:
       print("✗ Ping failed")
   
   # Test 2: List objects
   objects = bridge.list_objects()
   print(f"✓ Objects in scene: {len(objects)}")
   
   # Test 3: Query state
   state = bridge.query_state()
   print(f"✓ State snapshot retrieved: {len(state)} objects")
   
   bridge.close()
   ```

**预期 Unity Console 输出**：
```
[AgentBridge] Client connected
[AgentBridge] Handling: list_objects
[AgentBridge] Response sent: 256 bytes
[AgentBridge] Handling: query_state
[AgentBridge] Response sent: 512 bytes
[AgentBridge] Client disconnected
```

**成功标志**：
- ✓ 无连接拒绝
- ✓ Ping 成功
- ✓ state 返回非空

---

### 模式 C：完整在线闭环（RAG + Multi-Agent + 实时执行）

**场景**：完整的 VRAgent 2.0 工作流 — RAG 层 + 四个 Agents协作 + 实时 Unity 执行。

**前置条件**：
1. ✓ 数据已准备（RAG 索引）
2. ✓ Unity Play 模式运行中
3. ✓ AgentBridge 完成初始化
4. ✓ OpenAI API 密钥已配置

**步骤**：

1. **确保 Unity Bridge 就绪**：
   在 Unity Console 看到：
   ```
   [AgentBridge] Server started on 127.0.0.1:6400
   [AgentBridge] Listening for connections...
   ```

2. **从 Python 启动完整闭环**：
   ```bash
   cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation
   
   python -m vragent2 \
       --unity \
       --unity_host 127.0.0.1 \
       --unity_port 6400 \
       --scene_name Maze \
       --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
       --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
       --output results_online_maze \
       --budget 50 \
       --max_repair 2 \
       --model gpt-4
   ```

3. **观察执行过程**：
   
   **Python 终端** — 应看到四层 Agent 的协作：
   ```
   [MAIN] Unity connected at 127.0.0.1:6400
   [MAIN] Objects: 42
   [MAIN] Budget: 50
   
   [CONTROLLER] === Iteration 1 ===
   [PLANNER] Goal: Explore new rooms | Generated 4 candidates
   [VERIFIER] Candidate 1: ✓ PASS (score: 0.95)
   [VERIFIER] Candidate 2: ✓ PASS (score: 0.87)
   [VERIFIER] Candidate 3: ✗ FAIL (object not found)
   [VERIFIER] Candidate 4: ✗ FAIL (missing component)
   [EXECUTOR] Executing 2 verified actions...
     [ACTION] Grab door handle → position (1.2, 1.5, 0)
     [ACTION] Trigger lock event
   [OBSERVER] State snapshot captured: 42 objects
   [OBSERVER] Coverage delta: +3 (LC), +1 (MC), +2 (CoIGO)
   [EXPLORER] Gate: room_2 → unlocked ✓
   
   [CONTROLLER] === Iteration 2 ===
   ...
   ```

   **Unity Console** — 应看到：
   ```
   [AgentBridge] Client connected
   [VRAgentOnline] Command received: Execute
   [VRAgentOnline] Executing 2 actions
   [VRAgentOnline]   Grab(door_handle → 1.2,1.5,0) ✓
   [VRAgentOnline]   Trigger(lock_event) ✓
   [StateCollector] Collected 42 object states
   [AgentBridge] Response sent: 2048 bytes
   ```

4. **等待完成** — Controller 在 50 次迭代后自动停止

5. **检查输出**：
   ```bash
   ls -la results_online_maze/
   # execution/
   #   - traces.json       ← 所有执行轨迹
   #   - actions.json      ← 所有生成的 actions
   # gate_graph.json       ← 最终的门控图
   # coverage_report.json  ← 覆盖统计
   # summary.json          ← 最终统计
   ```

**成功标志**：
- ✓ 无 TCP 连接错误
- ✓ 每轮都看到四个 Agent 的输出
- ✓ Coverage 逐步增加
- ✓ 动作在 Unity 中执行（对象移动/事件触发）
- ✓ 完成后生成 results_online_maze 目录

---

## 快速开始（copy & paste）

对于 **Maze 场景** 的第一次测试，只需运行：

```bash
cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation

# （可选）先验证模拟模式
python -m vragent2 \
    --scene_name Maze \
    --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
    --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
    --output results_online_maze_sim \
    --budget 20

# 然后启动 Unity（Play 模式），再运行实时模式
python -m vragent2 \
    --unity \
    --scene_name Maze \
    --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
    --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
    --output results_online_maze \
    --budget 50
```

> **提示**：第一次建议用 `--budget 20` 做快速验证，成功后再用 `--budget 100` 做完整探索。

---

## 调试技巧

### 问题 1: "RetrievalLayer 初始化失败: 找不到 GML 文件"

**原因**: RAG 索引数据不完整或路径错误

**解决**:
```bash
# 检查数据结构
ls Results/Results_maze/scene_detailed_info/mainResults/
# 应该看到: Maze.gml, Maze_dependencies.json 等

# 如果没有，需要重新运行数据提取
python ExtractSceneDependency.py --scene_name Maze --app_name Maze
```

### 问题 2: "Verifier 所有候选都失败: object not found"

**原因**: FileID 不匹配或场景与数据不一致，或 Planner 生成了过时的引用

**检查**:
1. 确认 gobj_hierarchy.json 和当前 Unity 场景来自同一次分析
2. 如果改了场景，需要重新运行 TraverseSceneHierarchy
3. 在 RAG 层验证对象：
   ```python
   from vragent2.retrieval.retrieval_layer import RetrievalLayer
   retrieval = RetrievalLayer("Results/Results_maze", "Maze")
   
   # 列出所有已知对象
   for node_id in list(retrieval.scene.graph.nodes)[:10]:
       name = retrieval.get_object_name(node_id)
       print(f"{node_id}: {name}")
   ```

### 问题 3: "Address already in use (port 6400)"

**原因**: 上次 Unity 未正停止，或另一进程占用端口

**解决**:
```powershell
# 查看占用 6400 的进程
netstat -ano | findstr :6400
# 杀死该进程 (pid 为查出的进程ID)
taskkill /PID <pid> /F
```

### 问题 4: "Connection refused" (from Python)

**原因**: Unity Play 模式未启动，或 Bridge 未初始化

**检查清单**:
1. ☐ Unity 处于 Play 模式
2. ☐ 场景中有 AgentBridge 组件
3. ☐ Console 显示 "[AgentBridge] Server started on..."
4. ☐ 防火墙未阻止 localhost:6400

### 问题 5: "Executor 报错: Action execution failed in Unity"

**原因**: XRGrabbable 配置问题、Rigidbody 缺失、或运行时对象被销毁

**调试**:
1. 查看 Unity Console 中的详细错误
2. 检查对象是否有 Rigidbody：
   ```python
   retrieval = RetrievalLayer("Results/Results_maze", "Maze")
   obj_info = retrieval.scene.find_gameobject("some_object_id")
   print(f"Has Rigidbody: {retrieval.has_component('some_object_id', 'Rigidbody')}")
   ```
3. 启用详细日志：
   ```python
   # 在 controller.py 中设置
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### 问题 6: "Coverage 增长停滞，一直在 Explore 模式"

**原因**：门控图中许多路径被锁定（需要条件满足），但 Planner 没有生成通往这些条件的动作

**解决**:
1. 检查 Observer 输出的 `next_exploration_suggestion`
2. 手动增加 `--budget` 以给予更多探索时间
3. 检查 gate_graph.json 看是否有很多 "need_item" / "need_state" 的失败
4. 考虑调整 Planner 的提示词以更好地处理条件依赖

---

## 完整最小示例（端到端测试）

假设你想快速验证整个管道都能工作：

### 步骤 1：启动 Unity（模拟场景）

```csharp
// Assets/Scripts/MinimalTestScene.cs
using UnityEngine;

public class MinimalTestScene : MonoBehaviour
{
    void Start()
    {
        // 创建简单的对象用于测试
        GameObject cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.tag = "GrabbableObject";
        cube.name = "TestCube";
    }
}
```

- 创建新场景，挂上这个脚本
- 加载 AgentBridge + StateCollector
- 进入 Play 模式

### 步骤 2：运行 RAG 初始化验证

```bash
cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation

python << 'EOF'
from vragent2.retrieval.retrieval_layer import RetrievalLayer

# 假设数据在 Results/Results_maze
retrieval = RetrievalLayer("Results/Results_maze", "Maze")
print(f"✓ RAG initialized")
print(f"  Scene graph nodes: {len(retrieval.scene.graph.nodes)}")
print(f"  Scripts indexed: {len(retrieval.scripts.index)}")

# 尝试为第一个对象构建上下文
from vragent2.utils.file_utils import load_json
hierarchy = load_json("Results/Results_maze/gobj_hierarchy.json")
if hierarchy and len(hierarchy) > 0:
    first_obj = hierarchy[0] if isinstance(hierarchy, list) else list(hierarchy.values())[0]
    ctx = retrieval.build_context_for_gameobject(first_obj)
    print(f"✓ Context built for first object: {len(ctx.keys())} sections")
EOF
```

### 步骤 3：运行模拟模式（无 Unity）

```bash
python -m vragent2 \
    --scene_name Maze \
    --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
    --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
    --output test_sim \
    --budget 5 \
    --model gpt-4
```

### 步骤 4：运行实时模式（需要 Unity 运行中）

```bash
python -m vragent2 \
    --unity \
    --scene_name Maze \
    --hierarchy_json Results/Results_maze/gobj_hierarchy.json \
    --scene_gml Results/Results_maze/scene_detailed_info/mainResults/Maze.gml \
    --output test_online \
    --budget 5 \
    --model gpt-4
```

### 验证输出

```bash
# 检查模拟模式的输出
ls -la test_sim/
cat test_sim/summary.json | jq .

# 检查实时模式的输出
ls -la test_online/
cat test_online/summary.json | jq .
```

**如果都成功，你已经验证了整个 VRAgent 2.0 管道！**

---

## 下一步

基础流程验证成功后，你可以：

### 性能与覆盖优化
1. **调整 Planner 提示词** - 提高生成动作的质量和多样性
2. **微调 Verifier 规则** - 提高错误检测的准确性
3. **优化探索策略** - 调整 Expand/Exploit/Recover 模式的切换条件
4. **监控覆盖增长** - 分析 gate_graph.json 中哪些路径仍未被探索

### 扩展到其他场景
1. 使用 `TraverseSceneHierarchy.py` 和 `ExtractSceneDependency.py` 为新场景生成数据
2. 在新场景的 RAG 数据上运行 VRAgent 2.0
3. 收集覆盖和缺陷发现指标，对标 v1.0

### 集成与部署
1. **纳入 CI/CD** - 在构建流程中自动运行 VRAgent 2.0 探索
2. **生成报告** - 从 coverage_report.json 和 gate_graph.json 生成可视化报告
3. **缺陷跟踪** - 将 Observer 的 `bug_signals` 转发到缺陷管理系统

### 评估与研究
对比 VRAgent 2.0 与 v1.0 的性能：
```bash
# 在相同配置下对比
python compare_results.py \
    --v1_results Results_action_no_dup/ \
    --v2_results results_online_maze/ \
    --metrics coverage,steps,bugs_found
```

---

## 参考

### 核心架构
- [VRAgent 2.0 设计文档](../../.github/copilot-instructions.md) (§B2 - VRAgent 2.0 规范)
- [Multi-Agent Pipeline Contract](../vragent2/contracts.py)
- [RetrievalLayer 文档](../vragent2/retrieval/retrieval_layer.py)

### 实现代码
- [main.py](../vragent2/main.py) - CLI 入口点
- [controller.py](../vragent2/controller.py) - 主调度器
- [agents/planner.py](../vragent2/agents/planner.py) - Planner Agent
- [agents/verifier.py](../vragent2/agents/verifier.py) - Verifier Agent
- [agents/executor.py](../vragent2/agents/executor.py) - Executor Agent
- [agents/observer.py](../vragent2/agents/observer.py) - Observer Agent

### Unity 端
- [AgentBridge.cs](../../VRAgent/Assets/Package/VRAgent/Online/AgentBridge.cs) - TCP 桥接
- [VRAgentOnline.cs](../../VRAgent/Assets/Package/VRAgent/Online/VRAgentOnline.cs) - 执行器
- [StateCollector.cs](../../VRAgent/Assets/Package/VRAgent/Online/StateCollector.cs) - 状态收集

### 通讯协议
- [unity_bridge.py](../vragent2/bridge/unity_bridge.py) - Python 端桥接
- [Protocol 定义](../vragent2/bridge/protocol.py) (消息格式)

---

## 快速参考表

| 任务 | 命令 |
|------|------|
| 为新场景生成 RAG 数据 | `python TraverseSceneHierarchy.py --scene_name MyScene` |
| 验证 RAG 层初始化 | `python` + 运行 Phase 1 验证代码 |
| 运行模拟模式 | `python -m vragent2 --scene_name X --hierarchy_json Y --scene_gml Z --output out --budget 20` |
| 运行实时模式 | 同上 + `--unity --unity_host 127.0.0.1 --unity_port 6400` |
| 清理端口 | `taskkill /PID <pid> /F` (after `netstat -ano \| findstr :6400`) |
| 查看最终报告 | `cat results_online_maze/summary.json \| jq .` |

----

> **最后提醒**：VRAgent 2.0 的核心优势在于 **RAG + Multi-Agent 闭环**。一定要优先完成 Phase 1（RAG 初始化），再进行 Phase 3（在线执行）。这样系统才能充分利用项目知识和执行反馈来优化探索策略。
