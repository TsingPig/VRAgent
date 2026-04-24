# MiniGame_TowerDefense — Delivery Notes

## 类型
塔防。核心循环：选塔 → 放置 → 升级 → 抗波 → 胜利。

## 文件清单
```
MiniGame_TowerDefense/
├── MiniGame_TowerDefense.unity
├── Editor/TowerDefenseSceneBuilder.cs
├── TowerDefenseControllers.cs      # 6 controllers + 10 bugs
├── TowerDefenseOracleRegistry.cs
├── oracle_bugs.json
├── ORACLE_BENCHMARK.md
├── DELIVERY_NOTES.md
├── TESTING_COMMANDS.md
└── gold_standard_test_plan.json
```

## 搭建
1. 打开 `.unity` → `Tools/MiniGame TowerDefense/Build Scene` → File→Save
2. Hierarchy: StateController / ResourceManager / TowerPlacer / Tower_00..03 / WaveSpawner / Enemy_00..02(+RedHP)
