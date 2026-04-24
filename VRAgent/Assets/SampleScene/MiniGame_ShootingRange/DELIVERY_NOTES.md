# MiniGame_ShootingRange — Delivery Notes

## 场景类型
- 原型: Pistol Whip / SuperHot 风格 FPS 靶场
- 核心机制: Grab 武器 → Insert Magazine → Trigger Fire → 击中 Target → 计分 → 结束游戏

## 文件清单

```
MiniGame_ShootingRange/
├── MiniGame_ShootingRange.unity          # 最小场景 (Camera + Light + 空 root)
├── Editor/
│   └── ShootingRangeSceneBuilder.cs      # [MenuItem] 一键搭建场景
├── ShootingRangeStateController.cs       # 中央状态机
├── WeaponController.cs                    # 手枪 (含 BUG-001, BUG-009)
├── AmmoMagazine.cs                        # 弹匣 (含 BUG-004)
├── TargetController.cs                    # 靶子 (含 BUG-002, BUG-005)
├── ScoreManager.cs                        # 计分 (含 BUG-007)
├── WaveSpawner.cs                         # 波次 (含 BUG-003)
├── MuzzleFlashController.cs               # 枪口火焰 (含 BUG-008)
├── ShootingRangeOracleRegistry.cs         # Oracle 注册表
├── oracle_bugs.json                       # 机器可读 bug 清单
├── ORACLE_BENCHMARK.md                    # 详细 bug 文档
├── DELIVERY_NOTES.md                      # 本文件
├── TESTING_COMMANDS.md                    # 测试命令
└── gold_standard_test_plan.json           # 金标 test plan (10 bug 全覆盖)
```

## 场景搭建步骤

1. 在 Unity 中打开 `MiniGame_ShootingRange.unity`
2. 顶部菜单 → `Tools/MiniGame ShootingRange/Build Scene`
3. `File → Save` 保存场景
4. 此时 Hierarchy 包含：
   - `ShootingRange_Root`
     - `StateController` (ShootingRangeStateController)
     - `Floor`
     - `ScoreManager`
     - `PowerSwitch`
     - `Pistol` (WeaponController + Rigidbody + BoxCollider + MuzzlePoint child)
     - `Magazine` (AmmoMagazine)
     - `MuzzleFlash` (MuzzleFlashController + FlashQuad child)
     - `WaveSpawner` (WaveSpawner)
     - `Target_00` ... `Target_04` (TargetController + BoxCollider)

## VRAgent 集成步骤

1. `Tools/VR Explorer/Generate Scene Hierarchy` 导出 `gobj_hierarchy.json`
2. `Tools/VR Explorer/Export Scene Dependency` 导出 `scene.gml`
3. `Tools/VR Explorer/Import Test Plan` → 加载 `gold_standard_test_plan.json`
4. 进入 Play Mode → VRAgent 顺序执行 → 控制台应触发 10 个 ORACLE 标记

## 注意事项

- **BUG-001 注入需要确认**: `Pistol` GameObject 上**不要**手动添加 AudioSource，否则 BUG-001 不触发
- **Socket 模拟**: AmmoMagazine 的 OnInsert / OnRemove 需要由 SocketAction 触发；如未配置 XRSocketInteractor，可在 test plan 中通过 Trigger 调用
- **场景中并未自动添加 XR Origin / Player**: 真实 VR 测试需手动加入 XR Origin 与 XRSocketInteractor

## 已知限制

- BUG-002 / BUG-007 / BUG-009 / BUG-010 需通过 Trigger Action 显式调用对应 public 方法（`ForceTriggerHitWithoutBullet`、`AwardPoints`、`Reload`、`ResetAllState`）
- BUG-003 / BUG-006 通过 Trigger 调用 `StopWave` / `TryFinishGame`
- BUG-004 需要 SocketAction 的 Insert→Remove→Insert 序列
- BUG-005 / BUG-008 在 Activate / Flash 后被动检测，无需特殊操作
