# Kitchen_TestRoom — Oracle & Bug Injection Benchmark

> **Version**: 1.0  
> **Scene**: Kitchen_TestRoom  
> **Total Injected Bugs**: 10  
> **State Oracles**: 3  
> **Machine-readable definition**: `oracle_bugs.json`

---

## 概述

本基准测试在 Kitchen_TestRoom 场景的 C# 脚本中注入了 **10 个有意义的 bug**，覆盖 5 个类别。
每个 bug 都有明确的触发条件和检测 oracle，用于衡量 VRAgent 2.0 测试计划的缺陷发现能力。

**检测机制**：
- **Exception Oracle**: Unity Console 中的异常日志（NullReferenceException 等）
- **Marker Oracle**: 代码中 `[ORACLE:BUG-XXX:TRIGGERED]` 标记日志
- **State Oracle**: RecipeController 状态一致性检查

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

### BUG-001 — NullReferenceException in StoveController.FinishCooking

| 属性 | 值 |
|------|------|
| **类别** | Crash |
| **严重度** | High |
| **文件** | `StoveController.cs` → `FinishCooking()` |
| **注入方式** | 添加 `GetComponent<AudioSource>().Play()` — 该 GameObject 无 AudioSource 组件 |
| **触发条件** | 在灶台上完成烹饪（TryStartCooking → 等待 cookDuration → FinishCooking） |
| **检测** | Unity Console 出现 `NullReferenceException` + 调用栈含 `StoveController.FinishCooking` |
| **影响** | SetDishCooked() 已执行所以状态推进正常，但异常表明一个 crash-level bug |
| **修复** | `var audio = GetComponent<AudioSource>(); if (audio != null) audio.Play();` |

**理据**：模拟开发者添加音效反馈时忘记 null 检查——Unity 项目中最常见的运行时错误之一。

---

### BUG-002 — 灶台无碗也能开火

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `StoveController.cs` → `TryStartCooking()` |
| **注入方式** | 缺少 `hobSocket.HasBowl` 前置检查 |
| **触发条件** | 不放碗直接激活灶台 |
| **检测** | `[ORACLE:BUG-002:TRIGGERED]` |
| **影响** | 物理状态与逻辑状态不一致——没有碗也能做菜 |

**理据**：典型的"遗漏前置条件检查"。hobSocket 字段存在但未在关键路径上使用。

---

### BUG-003 — 关闭电源后 PowerEnabled 仍为 true

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `PowerSwitchController.cs` → `Toggle()` |
| **注入方式** | Toggle OFF 分支不调用状态重置 |
| **触发条件** | 先开电源再关电源（Toggle ON → Toggle OFF） |
| **检测** | `[ORACLE:BUG-003:TRIGGERED]`（IsOn=false 但 PowerEnabled=true） |
| **影响** | 下游系统（如 KitchenBadgeUnlockReceiver）仍认为有电，导致逻辑混乱 |

**理据**：单向状态传播——"设置"有但"取消"没有实现，常见于事件驱动系统。

---

### BUG-004 — 清洗计时器不重置导致瞬间完成

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `SinkWashStation.cs` → `OnIngredientPlaced()` |
| **注入方式** | 移除 `_washTimer = 0f;` 重置语句 |
| **触发条件** | 放食材到水槽 → 中途取出 → 再次放入 |
| **检测** | `[ORACLE:BUG-004:TRIGGERED]`（washTimer 携带上次累积值） |
| **影响** | 第二次放入时清洗立即或过早完成，绕过 1.5 秒清洗等待 |

**理据**：状态重置不完整——`_isWashing` 重置了但 `_washTimer` 没有。边界条件遗漏的典型案例。

---

### BUG-005 — 柜子滑动方向错误（符号错误）

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Low |
| **文件** | `LockedCabinetController.cs` → `Start()` |
| **注入方式** | 将 `new Vector3(0,0,-openDistance)` 改为 `new Vector3(0,0,openDistance)`（符号反转） |
| **触发条件** | 解锁储藏室门后打开 Cabinet_Ingredients |
| **检测** | `[ORACLE:BUG-005:TRIGGERED]`（Dot product 检测方向反转） |
| **影响** | 柜子滑入墙内而非向外打开。功能上标记为"已打开"但视觉上可能阻挡取物 |

**理据**：坐标系中符号错误是 3D 开发中极其常见的 bug，尤其在 local vs world space 转换时。

---

### BUG-006 — 装盘台接受未烹饪的菜（门控跳步）

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | High |
| **文件** | `ServingPlateSocket.cs` → `OnDishPlaced()` |
| **注入方式** | 注释掉 `DishCooked` 验证守卫 |
| **触发条件** | 将未烹饪的 Bowl_Mixing 放到 Plate_Serving 上 |
| **检测** | `[ORACLE:BUG-006:TRIGGERED]` |
| **影响** | 关键门控绕过——玩家可跳过步骤 7-8（混合+烹饪）直接装盘。任务可在不使用灶台的情况下完成 |

**理据**：模拟开发者在调试时临时注释掉验证代码并忘记恢复。在迭代开发中非常常见。

---

### BUG-007 — 错误的电源前置条件（检查 hasPantryKey 而非 doorPantryUnlocked）

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `RecipeController.cs` → `SetPowerEnabled()` |
| **注入方式** | 将 `!doorPantryUnlocked` 改为 `!hasPantryKey` |
| **触发条件** | 拾取钥匙后直接开电源（不插入钥匙到储藏室锁） |
| **检测** | `[ORACLE:BUG-007:TRIGGERED]` |
| **影响** | 跳过步骤 2（解锁储藏室门）。电源可在仅拾取钥匙后就开启 |

**理据**：属性名相似（hasPantryKey vs doorPantryUnlocked）导致的条件引用错误。状态机中经常出现的"差一步"bug。

---

### BUG-008 — Badge 面板在成功扫描后仍显示红色

| 属性 | 值 |
|------|------|
| **类别** | Visual |
| **严重度** | Low |
| **文件** | `KitchenBadgeUnlockReceiver.cs` → `OnBadgeInserted()` |
| **注入方式** | 移除成功路径中的 `panelRenderer.sharedMaterial = materialUnlocked` |
| **触发条件** | 无电时扫描 badge（面板变红）→ 开电 → 再次扫描 badge |
| **检测** | `[ORACLE:BUG-008:TRIGGERED]`（面板材质仍为 materialNoPower） |
| **影响** | 视觉误导——门成功打开但面板显示失败状态。用户可能认为扫描失败 |

**理据**：UI 状态未同步——失败路径设置了错误视觉但成功路径没有清除它。多状态 UI 的常见遗漏。

---

### BUG-009 — CuttingBoard 在验证前调用 SetIngredientCut(false)

| 属性 | 值 |
|------|------|
| **类别** | Functional |
| **严重度** | Medium |
| **文件** | `CuttingBoardController.cs` → `TryCut()` |
| **注入方式** | 已存在于代码中——SetIngredientCut 调用位于 knifePresent 检查之前 |
| **触发条件** | 在刀不在槽位时与切菜板交互 |
| **检测** | `[ORACLE:BUG-009:TRIGGERED]` |
| **影响** | 产生虚假的 RecipeController FAIL 警告日志，干扰测试分析 |

**理据**：调用顺序错误——先产生副作用再验证条件。违反"先检查后执行"原则。

---

### BUG-010 — ResetAllState 不重置下游控制器

| 属性 | 值 |
|------|------|
| **类别** | State Inconsistency |
| **严重度** | Medium |
| **文件** | `RecipeController.cs` → `ResetAllState()` |
| **注入方式** | 已存在——下游控制器无重置通知 |
| **触发条件** | 调用 ResetAllState()（测试迭代间隔） |
| **检测** | `[ORACLE:BUG-010:TRIGGERED]` |
| **影响** | 状态不同步——RecipeController 已重置但 LockedCabinetController、StoveController 等保留旧状态 |

**理据**：集中式状态管理器只清除自身状态而不广播重置事件。分布式状态的经典一致性问题。

---

## State Oracle（状态断言）

| ID | 标签 | 检查内容 |
|----|------|----------|
| STATE-001 | recipe_monotonic | Recipe 标志必须严格有序设置（1→10），后续标志为 true 时前置标志也必须为 true |
| STATE-002 | completion_consistency | CompletedSuccessfully=true 时全部 10 个 RecipeController 标志必须为 true |
| STATE-003 | power_state_sync | PowerSwitchController.IsOn 必须与 RecipeController.PowerEnabled 同步 |

---

## 覆盖率指标

### Oracle Coverage（Bug 发现率）

$$\text{Oracle Coverage} = \frac{\text{Triggered Bugs}}{\text{Total Injected Bugs}} \times 100\%$$

### 按类别覆盖率

| 类别 | 总数 | 公式 |
|------|------|------|
| Crash | 1 | triggered_crash / 1 |
| Functional | 5 | triggered_functional / 5 |
| State | 3 | triggered_state / 3 |
| Visual | 1 | triggered_visual / 1 |

### 按严重度覆盖率

| 严重度 | 总数 | 权重 |
|--------|------|------|
| High | 2 | ×3 |
| Medium | 6 | ×2 |
| Low | 2 | ×1 |

$$\text{Weighted Oracle Coverage} = \frac{\sum w_i \cdot \mathbb{1}[\text{triggered}_i]}{\sum w_i}$$

---

## 如何使用

### 1. 运行已有 Test Plan

```powershell
& $Python -m vragent2 @Common --unity --replay auto
```

### 2. 查看 Oracle 覆盖率

在生成的 `report.html` 中查看 **Oracle Coverage** Section，或检查 Unity Console 日志：
- 搜索 `[ORACLE:BUG-` 查看触发的 bug
- 搜索 `NullReferenceException` 查看 BUG-001
- 搜索 `[ORACLE:STATE:` 查看状态断言

### 3. Benchmark 对比

```powershell
& $Python -m vragent2 --benchmark $OutputBase
```

Benchmark 报告中的 **Oracle Coverage** 列显示各模型的 bug 发现率。

---

## 文件清单

| 文件 | 用途 |
|------|------|
| `OracleRegistry.cs` | Bug 跟踪与日志的 C# 静态类 |
| `oracle_bugs.json` | 机器可读的 bug 定义（供 Python pipeline 解析） |
| `ORACLE_BENCHMARK.md` | 本文档 |
