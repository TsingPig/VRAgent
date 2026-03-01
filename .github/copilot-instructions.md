<!-- This file is auto-loaded by VS Code Copilot as persistent system context -->

# VRAgent Development Guide (v1.0 + v2.0 Roadmap)

---

## Part A: VRAgent 1.0 — 现有架构与关键模式

### Architecture Overview

VRAgent is a Unity package for automated VR testing that transforms JSON test plans into executable VR interactions. The system uses:

- **FileID-based object resolution** for stable scene references across Unity sessions
- **Dynamic component attachment** (XRGrabbable, XRTriggerable, XRTransformable) at runtime
- **LLM-generated test plans** imported as JSON and executed sequentially

### Core Components

- `VRAgent.cs` - Main test executor, inherits from `BaseExplorer` (VRExplorer framework)
- `FileIdManager.cs` - Runtime mapping between FileIDs and GameObjects/MonoBehaviours
- `FileIdResolver.cs` - Static utilities for FileID/GUID resolution and UnityEvent creation
- `JSON/` - Action/Task definitions with Newtonsoft.Json polymorphic deserialization

### Key Patterns

#### FileID Resolution System
```csharp
// Always use FileIdManager for runtime lookups, not direct resolution
var manager = Object.FindAnyObjectByType<FileIdManager>();
GameObject obj = manager.GetObject(fileId);
MonoBehaviour component = manager.GetComponent(scriptFileId);
```

FileIDs are extracted from Unity's `GlobalObjectId` with different parsing for prefab instances vs scene objects.

#### Test Plan Structure
JSON test plans contain `taskUnits` → `actionUnits` with three action types:
- **Grab**: Move objects to positions or other objects (`GrabActionUnit`)
- **Trigger**: Execute UnityEvents with timing (`TriggerActionUnit`)
- **Transform**: Apply position/rotation/scale deltas (`TransformActionUnit`)

#### Dynamic Component Management
Components are added at test execution time, not design time:
```csharp
// Pattern: Add component → Configure → Generate BaseAction tasks
XRGrabbable grabbable = objA.AddComponent<XRGrabbable>();
grabbable.destination = targetTransform;
task.AddRange(GrabTask(grabbable)); // Returns BaseAction sequence
```

#### UnityEvent Serialization for Methods with Return Values
The system automatically wraps non-void methods using `SerializableMethodWrapper` components. When `CreateUnityEvent()` encounters methods with return values, it:
1. Adds a `SerializableMethodWrapper` to the target GameObject
2. Configures the wrapper with target component and method name
3. Binds the wrapper's `InvokeWrappedMethod()` to the UnityEvent

### Development Workflows

#### Test Plan Import/Export
1. **Tools → VR Explorer → Import Test Plan** - Main entry point
2. **FileID Discovery**: Use `TestPlanImporterWindow` to select objects and copy FileIDs
3. **Validation**: Check that `FileIdManager` exists in scene and all referenced objects resolve correctly

#### Editor-Only Features
All core resolution logic is wrapped in `#if UNITY_EDITOR` - only works in editor mode for test authoring.

#### Component Lifecycle
- **Import**: Dynamically attach XR components based on test plan
- **Execute**: Run sequential tasks with async/await pattern
- **Cleanup**: `RemoveTestPlan()` strips all added components and temp objects

### Critical Dependencies

- **Unity XR Interaction Toolkit 2.0.4+** for XRGrabbable/XRTriggerable base classes
- **Newtonsoft.Json** for polymorphic ActionUnit deserialization
- **HenryLab.VRExplorer** base framework (external dependency)

### Anti-Patterns to Avoid

- Never use `FindComponentByFileID()` directly - always go through `FileIdManager`
- Don't manually add XR components at design time - managed by test execution system
- Avoid hardcoded object references - use FileID strings for cross-session stability
- Don't call Unity's `Object.FindObjectOfType()` in hot paths - cache in FileIdManager

### Debugging Tools

- **Rich Text Logging**: Use `new RichText().Add(text, color, bold)` for structured debug output
- **Test Metrics**: `TestPlanCounter` tracks object resolution success rates
- **Inspector Validation**: FileIdManager shows live object/component mappings in Inspector

---

## Part B: VRAgent 2.0 — 开发路线图与设计规范

> **核心升级**：从"单 LLM 一次性生成 test plan"升级为**在线闭环系统**
> 即：**Plan → Verify → Execute → Observe** 多 Agent 协作闭环
> 每一步都能利用项目知识（检索增强）与执行反馈（coverage/错误/状态变化）持续改进后续动作。

### B1. 核心痛点（所有改动必须围绕这三个痛点）

1. **一致性与可执行性错误**：对象找不到、组件缺失、方法/参数不匹配、UI 状态不对、运行态对象动态生成导致引用失效
2. **冗余与低收益**：重复动作多、覆盖增量低、探索策略贪心，容易陷入局部循环
3. **缺乏可测的闭环**：生成失败时往往"重写整段计划"，缺少结构化修复与可追踪的责任划分

### B2. 总体架构：RAG + Multi-Agent Pipeline

#### B2.1 Project Retrieval Layer（检索增强底座）

为 Planner/Verifier/Observer 提供"项目可查询知识"：

| 索引类型 | 内容 |
|---------|------|
| 资产/场景/Prefab/组件索引 | 对象路径、tag/layer、组件字段 |
| UI 索引 | Canvas/Panel 树、按钮事件绑定、可见性条件线索 |
| 脚本索引 | 类/方法/事件订阅、关键 API（Instantiate/Destroy/Find/SetActive/LoadScene） |
| 运行时日志与 trace 索引 | 最近 N 秒事件链、异常栈、Console 日志 |

**输出原则**：可检索的"局部子图/局部上下文包"，严格控制 token——只喂与当前目标强相关的片段。

#### B2.2 四角色 Agent 系统

**Agent 1: Planner Agent（生成）**
- 输入：IIG/TODG 子图 + 目标（覆盖/触发 COI/探索未覆盖区域）
- 输出：候选 HAU/AAU（或 stepwise action units），声明意图与预期收益

**Agent 2: Verifier Agent（合规/一致性审查）**
- 强制跑 Correctness / Consistency / Duplication 规则
- 输出：可执行性评分 + 错误定位（Grab 目标缺 Rigidbody 属于 MC；方法不存在是 IMS）
- 如果 fail：把具体错误反馈给 Planner 进行"结构化修复"（不是重写全计划）

**Agent 3: Executor Agent（执行）**
- 只做 deterministic execution（AAU Manager + EAT actions），不参与生成
- 实时记录：动作 → 状态变更 → 事件链 → 覆盖增量

**Agent 4: Observer/Oracle Agent（判定与策略）**
- 面向 VR 的"弱 oracle"：异常日志、Unity Console、关键事件是否触发、对象状态是否达成
- 输出：coverage delta、bug signals、下一轮探索建议

#### B2.3 Controller（调度器）

1. 设定当前 goal（覆盖/触发某类交互/打开某 UI/到达房间）
2. 调 Planner → Verifier → Executor → Observer
3. 根据 Verifier/Observer 输出更新 goal 与上下文检索范围
4. 直到预算耗尽或达到覆盖/bug 发现目标

#### B2.4 角色契约（Contract-based Interaction Protocol）

每个 agent 输出必须满足 schema，把协作从"聊天"变成"可测 pipeline"：

```json
// Planner output
{ "actions": ["AAU..."], "intent": "string", "expected_reward": 0.0 }

// Verifier output
{ "executable_score": 0.0, "errors": [{"type":"", "location":"", "fix_suggestion":""}], "pass": false }

// Executor output
{ "trace": [{"action":"", "state_before":"", "state_after":"", "events":[]}], "coverage_delta": {"LC":0, "MC":0, "CoIGO":0}, "exceptions": [] }

// Observer output
{ "coverage_delta": 0.0, "bug_signals": [], "next_exploration_suggestion": "" }
```

#### B2.5 Coverage-guided LLM Planning

- LC/MC/CoIGO 增量作为 reward signal
- 可用 heuristic bandit：选带来更大覆盖增量的 action pattern
- 利用"w/o TODG 覆盖崩掉"的结论：上下文 + 反馈对生成质量是关键

### B3. 算法创新：门控图 + 失败驱动反推

#### B3.1 Gate Graph（门控图）

维护在线更新的图：
- **节点**：状态签名 S（或 room-level 状态）
- **边**：动作 a（交互/移动/UI 操作）
- **边标注**：成功/失败 + 失败类型（locked / need_item / need_state / ui_hidden / unknown）+ 失败证据

#### B3.2 Failure-to-Condition 反推

当出现"门打不开/按钮不可见/谜题无响应"：
1. Observer 把失败证据丢给 RAG 检索层，搜索相关脚本与 UI 绑定
2. 输出结构化结论：`{need_item: "BlueKey"}` 或 `{need_flag: "SwitchA=true"}`
3. 提供条件的候选获得路径

**效果**：黑盒探索 → 白盒 guided

### B4. 探索控制器（三模式 PFSM 变体）

| 模式 | 目标 | 触发信号 |
|------|------|---------|
| **Expand** | 发现新房间/新 UI 分支 | 初始化 或 解锁成功进入新 room/UI |
| **Exploit** | 集中解决 gate 缺失条件 | 发现 lock/need_item 提示 |
| **Recover** | 回退与重检索 | 连续 K 步 novelty=0 或 重复失败 |

### B5. 核心对比

| 维度 | v1.0 | v2.0 |
|------|------|------|
| 生成方式 | 单 LLM 一次性 | Multi-Agent 闭环 |
| 反馈机制 | 无 | Coverage + 错误反馈 |
| 错误处理 | 重写整计划 | 结构化修复 + Verify |
| 探索策略 | 贪心 | 门控图 + 模式切换 |
| 可测性 | 低 | 契约式 pipeline |

### B6. 实施阶段

**Phase 1: 基础设施搭建**
- [ ] Project Retrieval Layer（资产/脚本/UI 索引）
- [ ] 四 Agent 的 schema 契约定义
- [ ] Controller 调度逻辑

**Phase 2: Agent 实现**
- [ ] Planner Agent
- [ ] Verifier Agent
- [ ] Executor Agent
- [ ] Observer Agent

**Phase 3: 算法增强**
- [ ] Gate Graph（门控图）
- [ ] 失败→条件反推（RAG 检索）
- [ ] 探索控制器（Expand/Exploit/Recover）

**Phase 4: 评估与优化**
- [ ] TODG benchmark 覆盖增量 (LC/MC/CoIGO)
- [ ] 对比 SOTA fuzzing / RL-based 方案
- [ ] 性能优化（token 控制、检索速度）

### B7. 评估指标

- **覆盖**：LC、MC、CoIGO
- **缺陷发现**：bug signals、异常捕获率
- **效率**：步数、冗余度、token 消耗
- **对标**：SOTA fuzzing、RL-based、Xiaoyin Wang ICSE19 benchmark
