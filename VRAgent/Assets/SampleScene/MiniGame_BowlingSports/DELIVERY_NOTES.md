# MiniGame_BowlingSports — Delivery Notes

## 类型
保龄球 VR 运动模拟。核心循环：抓球 → 投掷 → 倒瓶 → 计分 → 复位。

## 文件清单
```
MiniGame_BowlingSports/
├── MiniGame_BowlingSports.unity
├── Editor/BowlingSceneBuilder.cs
├── BowlingControllers.cs           # 6 controllers + 10 bugs
├── BowlingOracleRegistry.cs
├── oracle_bugs.json
├── ORACLE_BENCHMARK.md
├── DELIVERY_NOTES.md
├── TESTING_COMMANDS.md
└── gold_standard_test_plan.json
```

## 搭建
1. 打开 `.unity` → `Tools/MiniGame BowlingSports/Build Scene` → File→Save
2. Hierarchy: StateController / Scoreboard / Lane / BowlingBall (Rigidbody+SphereCollider) / Pin_00..09 (CapsuleCollider) / PinResetLight(+Bulb)

## 关键
- BUG-001: BowlingBall 不要加 AudioSource
- BUG-005: 任何 pin OnFall 都会触发
