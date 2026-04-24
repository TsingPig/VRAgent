# MiniGame_ShootingRange — Oracle & Bug Injection Benchmark

> **Version**: 1.0  
> **Type**: FPS Shooting Range (Pistol Whip / SuperHot 风格)  
> **Total Injected Bugs**: 10  
> **State Oracles**: 5 (Power / Magazine / Hit / Submit / GameComplete)  
> **Machine-readable**: `oracle_bugs.json`

## 概述

在 ShootingRange 场景的核心控制器（武器/弹匣/靶子/计分/波次）中注入 10 个有意义的 bug，
覆盖与 Kitchen_TestRoom / Apartment 相同的 5 个类别 + 同样的严重度配比，
便于 VRAgent 2.0 横向对比"非家居场景"的 oracle 覆盖。

## Bug 分布

| 类别 | 数量 | Bug IDs |
|------|------|---------|
| Crash / Exception | 1 | BUG-001 |
| Functional / Logic | 5 | BUG-002, BUG-004, BUG-005, BUG-006, BUG-009 |
| State Inconsistency | 3 | BUG-003, BUG-007, BUG-010 |
| Visual | 1 | BUG-008 |

## 详细 Bug 清单

### BUG-001 — NullReferenceException in WeaponController.Fire
- **类别**: Crash / High
- **位置**: `WeaponController.cs::Fire()`
- **注入**: `GetComponent<AudioSource>().Play()` — 武器 GameObject 上无 AudioSource
- **触发**: 抓武器 → 装弹 → 触发 Fire()
- **检测**: console grep `NullReferenceException.*WeaponController`

### BUG-002 — Target 无子弹也能记分
- **类别**: Functional / Medium
- **位置**: `TargetController.cs::OnHit(bool wasRealBulletHit)`
- **注入**: 缺少 `if (!wasRealBulletHit) return;`
- **触发**: 调用 `ForceTriggerHitWithoutBullet()`（VRAgent Trigger Action）
- **检测**: `[ORACLE:BUG-002:TRIGGERED]`

### BUG-003 — StopWave 不重置 IsActive
- **类别**: State / Medium
- **位置**: `WaveSpawner.cs::StopWave()`
- **注入**: 仅清零 timer，未清 IsActive
- **触发**: StartWave() → StopWave()
- **检测**: `[ORACLE:BUG-003:TRIGGERED]`

### BUG-004 — Magazine 装填计时器不归零
- **类别**: Functional / Medium
- **位置**: `AmmoMagazine.cs::OnInsert()`
- **注入**: 缺少 `_reloadTimer = 0f`
- **触发**: OnInsert → 中途 OnRemove → OnInsert（瞬间完成）
- **检测**: `[ORACLE:BUG-004:TRIGGERED]`

### BUG-005 — 靶子转向反了
- **类别**: Functional / Low
- **位置**: `TargetController.cs::Activate()`
- **注入**: `Quaternion.Euler(-popupAngle, ...)` 应为 `+popupAngle`
- **触发**: 任意 Activate()
- **检测**: `[ORACLE:BUG-005:TRIGGERED]`

### BUG-006 — 游戏未达成条件就结束
- **类别**: Functional / High
- **位置**: `ShootingRangeStateController.cs::TryFinishGame()`
- **注入**: 缺少 `TargetsHit >= TargetsRequired` 与 `ScoreSubmitted` 校验
- **触发**: 直接 TryFinishGame() 而不击中所有靶子
- **检测**: `[ORACLE:BUG-006:TRIGGERED]`

### BUG-007 — AwardPoints 用错前置字段
- **类别**: State / Medium
- **位置**: `ScoreManager.cs::AwardPoints()`
- **注入**: 校验 `target.IsActive` 而非 `target.IsHit`
- **触发**: Activate target 后外部直接 AwardPoints
- **检测**: `[ORACLE:BUG-007:TRIGGERED]`

### BUG-008 — 枪口火焰不消失
- **类别**: Visual / Low
- **位置**: `MuzzleFlashController.cs::Update()`
- **注入**: 计时结束后未 SetActive(false)
- **触发**: Flash() 后等待 > visibleDuration
- **检测**: `[ORACLE:BUG-008:TRIGGERED]`

### BUG-009 — Reload 先副作用后校验
- **类别**: Functional / Medium
- **位置**: `WeaponController.cs::Reload()`
- **注入**: 先 `ChamberRounds = 6` 再判断 magazine
- **触发**: Reload() 时 magazine 为空或 null
- **检测**: `[ORACLE:BUG-009:TRIGGERED]`

### BUG-010 — ResetAllState 不级联清理
- **类别**: State / Medium
- **位置**: `ShootingRangeStateController.cs::ResetAllState()`
- **注入**: 不调用 ScoreManager.ResetCombo / WaveSpawner.StopWave / MuzzleFlash.ForceHide
- **触发**: 累积 combo → ResetAllState
- **检测**: `[ORACLE:BUG-010:TRIGGERED]`

## 状态机流程

```
PowerOn → MagazineLoaded → WeaponEquipped → SafetyOff →
  WaveStarted → AllTargetsHit → ScoreSubmitted → GameComplete
```

## 检测命令

```bash
# Marker oracles
grep -E "\[ORACLE:BUG-[0-9]{3}:TRIGGERED\]" console_logs.txt

# State oracles
grep -E "\[ORACLE:STATE:[A-Za-z]+\]" console_logs.txt

# Crash detection
grep -E "NullReferenceException.*WeaponController" console_logs.txt
```
