# MiniGame_SandboxBuilder — Delivery Notes

## 类型
沙盒建造。核心循环：选工具 → 抓方块 → 放置 → 旋转 → 验证 → 保存 → 发布。

## 文件清单
```
MiniGame_SandboxBuilder/
├── MiniGame_SandboxBuilder.unity
├── Editor/SandboxSceneBuilder.cs
├── SandboxControllers.cs           # 6 controllers + 10 bugs
├── SandboxOracleRegistry.cs
├── oracle_bugs.json
├── ORACLE_BENCHMARK.md
├── DELIVERY_NOTES.md
├── TESTING_COMMANDS.md
└── gold_standard_test_plan.json
```

## 搭建
1. 打开 `.unity` → `Tools/MiniGame SandboxBuilder/Build Scene` → File→Save
2. Hierarchy: StateController / BlockPlacer / Block_00..05 / Toolbox / SaveLoad / HighlightOutline(+OutlineMesh)
