# MiniGame_HorrorSurvival — Delivery Notes

## 类型
生存恐怖。核心循环：手电筒 → 装电池 → 找 3 把钥匙 → 开门 → 躲怪物 → 逃出。

## 文件清单
```
MiniGame_HorrorSurvival/
├── MiniGame_HorrorSurvival.unity
├── Editor/HorrorSceneBuilder.cs
├── HorrorControllers.cs            # 7 controllers + 10 bugs
├── HorrorOracleRegistry.cs
├── oracle_bugs.json
├── ORACLE_BENCHMARK.md
├── DELIVERY_NOTES.md
├── TESTING_COMMANDS.md
└── gold_standard_test_plan.json
```

## 搭建
1. 打开 `.unity` → `Tools/MiniGame HorrorSurvival/Build Scene` → File→Save
2. Hierarchy: StateController / Flashlight(+LightCone) / Battery / ExitDoor / EnemyAI / HealthSystem(+RedOverlay) / Key_00..02

## 关键
- BUG-001: Flashlight 不要加 AudioSource
- BUG-005: 任何 ApplyToFlashlight 都触发
