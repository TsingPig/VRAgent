# Apartment — Oracle & Bug Injection Benchmark

> **Version**: 1.0  
> **Scene**: Apartment  
> **Total Injected Bugs**: 10  
> **State Oracles**: 3  
> **Machine-readable definition**: `oracle_bugs.json`

---

## 概述

本基准测试在 Apartment 场景的 C# 脚本中注入了 **10 个有意义的 bug**，覆盖 4 个类别。
每个 bug 都有明确的触发条件和检测 oracle，用于衡量 VRAgent 2.0 测试计划的缺陷发现能力。

**场景主题**：Smart Home Morning Routine — 玩家需要完成一个 10 步的早晨日常任务（取钥匙→开信箱→通电→开百叶窗→冲咖啡→烤面包→上早餐→看新闻→完成）。

**检测机制**：
- **Exception Oracle**: Unity Console 中的异常日志（NullReferenceException 等）
- **Marker Oracle**: 代码中 `[ORACLE:BUG-XXX:TRIGGERED]` 标记日志
- **State Oracle**: ApartmentStateController 状态一致性检查

---

## Bug 分布

| 类别 | 数量 | Bug IDs |
|------|------|---------|
| Crash / Exception | 1 | BUG-001 |
| Functional / Logic | 5 | BUG-002, BUG-004, BUG-005, BUG-006, BUG-009 |
| State Inconsistency | 3 | BUG-003, BUG-007, BUG-010 |
| Visual | 1 | BUG-008 |

| 严重度 | 数量 | Bug IDs |
|--------|------|---------|
| High | 2 | BUG-001, BUG-006 |
| Medium | 6 | BUG-002, BUG-003, BUG-004, BUG-007, BUG-009, BUG-010 |
| Low | 2 | BUG-005, BUG-008 |

---

## 详细 Bug 清单

### BUG-001 — NullReferenceException in CoffeeMachineController.FinishBrew

| 属性 | 值 |
|------|------|
| **类别** | Crash |
| **严重度** | High |
| **文件** | `CoffeeMachineController.cs` → `FinishBrew()` |
| **注入方式** | 添加 `GetComponent<AudioSource>().Play()` — 该 GameObject 无 AudioSource 组件 |
| **触发条件** | 完成咖啡冲泡（TryStartBrew → 等待 brewDuration → FinishBrew） |
| **检测** | Unity Console 出现 `NullReferenceException` + 调用栈含 `CoffeeMachineController.FinishBrew` |
| **影响** | SetCoffeeBrewed() 已执行所以状态推进正常，但异常表明一个 crash-level bug |
| **修复** | `var audio = GetComponent<AudioSource>(); if (audio != null) audio.Play();` |

**理据**：模拟开发者添加音效反馈时忘记 null 检查——Unity 项目中最常见的运行时错误之一。

---

### BUG-002 — 咖啡机无杯也能冲咖啡

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `CoffeeMachineController.cs` → `TryStartBrew()` |
| **注入方式** | 缺少 `cupSocket.HasCup` 前置检查 |
| **触发条件** | 不放杯子直接按冲泡按钮 |
| **检测** | `[ORACLE:BUG-002:TRIGGERED]` |
| **影响** | 物理状态与逻辑状态不一致——没有杯子也能冲咖啡 |

**理据**：典型的"遗漏前置条件检查"。cupSocket 字段存在但未在关键路径上使用。

---

### BUG-003 — 关闭配电箱后 PowerOn 仍为 true

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `CircuitBreakerController.cs` → `Toggle()` |
| **注入方式** | Toggle OFF 分支不调用 SetPowerOff() |
| **触发条件** | 先开配电箱再关（Toggle ON → Toggle OFF） |
| **检测** | `[ORACLE:BUG-003:TRIGGERED]`（IsOn=false 但 PowerOn=true） |
| **影响** | 下游系统（TV、咖啡机、百叶窗）仍认为有电，导致逻辑混乱 |

**理据**：单向状态传播——"设置"有但"取消"没有实现，常见于事件驱动系统。

---

### BUG-004 — 烤面包计时器不重置导致瞬间完成

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `ToasterController.cs` → `OnBreadInserted()` |
| **注入方式** | 移除 `_toastTimer = 0f;` 重置语句 |
| **触发条件** | 放面包 → 开始烤 → 中途取出 → 再次放入 |
| **检测** | `[ORACLE:BUG-004:TRIGGERED]`（toastTimer 携带上次累积值） |
| **影响** | 第二次放入时烤面包立即或过早完成，绕过 3 秒烘烤等待 |

**理据**：状态重置不完整——`IsToasting` 重置了但 `_toastTimer` 没有。边界条件遗漏的典型案例。

---

### BUG-005 — 百叶窗运动方向错误（符号错误）

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Low |
| **文件** | `WindowBlindController.cs` → `Start()` |
| **注入方式** | 将 `new Vector3(0,openDistance,0)` 改为 `new Vector3(0,-openDistance,0)`（Y 符号反转） |
| **触发条件** | 通电后打开百叶窗 |
| **检测** | `[ORACLE:BUG-005:TRIGGERED]`（Dot product 检测方向反转） |
| **影响** | 百叶窗向下滑入地板而非向上打开。功能上标记为"已打开"但视觉上窗户仍被遮挡 |

**理据**：坐标系中符号错误是 3D 开发中极其常见的 bug，尤其在 local space 偏移计算时。

---

### BUG-006 — 水龙头无电也能洗碗（门控跳步）

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | High |
| **文件** | `FaucetController.cs` → `TryWashDishes()` |
| **注入方式** | 注释掉 PowerOn 验证守卫 |
| **触发条件** | 未开配电箱时打开水龙头并洗碗 |
| **检测** | `[ORACLE:BUG-006:TRIGGERED]` |
| **影响** | 关键门控绕过——无需通电即可使用热水洗碗。绕过配电箱步骤 |

**理据**：模拟开发者在调试时临时注释掉验证代码并忘记恢复。在迭代开发中非常常见。

---

### BUG-007 — 错误的电源前置条件（检查 hasMailKey 而非 mailboxUnlocked）

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `ApartmentStateController.cs` → `SetPowerOn()` |
| **注入方式** | 将 `!mailboxUnlocked` 改为 `!hasMailKey` |
| **触发条件** | 拾取钥匙后直接开电（不插入钥匙到信箱锁） |
| **检测** | `[ORACLE:BUG-007:TRIGGERED]` |
| **影响** | 跳过步骤 2（解锁信箱）。电源可在仅拾取钥匙后就开启 |

**理据**：属性名相似（hasMailKey vs mailboxUnlocked）导致的条件引用错误。状态机中经常出现的"差一步"bug。

---

### BUG-008 — 冰箱警报指示灯在关门后仍亮着

| 属性 | 值 |
|------|------|
| **类别** | Visual |
| **严重度** | Low |
| **文件** | `FridgeDoorController.cs` → `Toggle()` |
| **注入方式** | 移除成功关门路径中的 `alarmRenderer.sharedMaterial = materialNormal` |
| **触发条件** | 开门超过 5 秒（警报触发→指示灯变红）→ 关门 |
| **检测** | `[ORACLE:BUG-008:TRIGGERED]`（指示灯材质仍为 materialAlarm） |
| **影响** | 视觉误导——门已关闭但警报指示灯显示仍在报警。用户可能认为冰箱有问题 |

**理据**：UI 状态未同步——警报路径设置了错误视觉但关门路径没有清除它。多状态 UI 的常见遗漏。

---

### BUG-009 — TV CycleChannel 在验证前调用 SetTvNewsWatched

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `TVController.cs` → `CycleChannel()` |
| **注入方式** | SetTvNewsWatched(IsPowered) 调用位于 IsPowered 检查之前 |
| **触发条件** | 在 TV 未开机时调用 CycleChannel |
| **检测** | `[ORACLE:BUG-009:TRIGGERED]` |
| **影响** | 产生虚假的 ApartmentStateController FAIL 警告日志，干扰测试分析 |

**理据**：调用顺序错误——先产生副作用再验证条件。违反"先检查后执行"原则。

---

### BUG-010 — ResetAllState 不重置下游控制器

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `ApartmentStateController.cs` → `ResetAllState()` |
| **注入方式** | 已存在——下游控制器无重置通知 |
| **触发条件** | 调用 ResetAllState()（测试迭代间隔） |
| **检测** | `[ORACLE:BUG-010:TRIGGERED]` |
| **影响** | 状态不同步——ApartmentStateController 已重置但 CircuitBreakerController、CoffeeMachineController、ToasterController 等保留旧状态 |

**理据**：集中式状态管理器只清除自身状态而不广播重置事件。分布式状态的经典一致性问题。

---

## State Oracles

### STATE-001 — routine_monotonic
- **描述**：日常任务标志必须按严格顺序设置（1→10）。不应出现后续标志为 true 而前驱标志为 false。
- **检查**：如 coffeeBrewed=true 则 cupPlaced 必须为 true；如 breakfastServed=true 则 coffeeBrewed 和 toastMade 必须都为 true。

### STATE-002 — completion_consistency
- **描述**：routineComplete=true 意味着 breakfastServed 和 tvNewsWatched 都为 true。
- **检查**：报告 routineComplete 时两者必须都为 true。

### STATE-003 — power_state_sync
- **描述**：CircuitBreakerController.IsOn 必须与 ApartmentStateController.PowerOn 匹配（不能失步）。
- **检查**：在任何观测点两者必须同为 true 或同为 false。

---

## 与 Kitchen_TestRoom 的对标

| Bug | Apartment | Kitchen 对标 | 共同模式 |
|-----|-----------|-------------|---------|
| BUG-001 | CoffeeMachine NullRef | StoveController NullRef | 缺 null 检查的音频调用 |
| BUG-002 | 无杯冲咖啡 | 无碗开火 | 遗漏物理前置检查 |
| BUG-003 | 配电箱不重置 | 电源不重置 | 单向状态传播 |
| BUG-004 | 烤面包计时器 | 清洗计时器 | 状态重置不完整 |
| BUG-005 | 百叶窗方向反 | 柜子方向反 | 坐标符号错误 |
| BUG-006 | 无电洗碗 | 跳过烹饪 | 门控守卫缺失 |
| BUG-007 | 错误前置条件 | 错误前置条件 | 相似属性名混淆 |
| BUG-008 | 警报灯不复位 | Badge面板不复位 | 视觉状态未同步 |
| BUG-009 | 副作用先于验证 | 副作用先于验证 | 调用顺序错误 |
| BUG-010 | 重置不通知下游 | 重置不通知下游 | 分布式一致性 |
