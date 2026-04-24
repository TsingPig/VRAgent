# MiniGame_RhythmBeat — Delivery Notes

## 类型
Beat Saber 风格节奏游戏，核心循环：选难度 → 加载歌 → 抓光剑 → 切方块 → 计分

## 文件清单

```
MiniGame_RhythmBeat/
├── MiniGame_RhythmBeat.unity            # 最小场景 (Camera + Light)
├── Editor/RhythmBeatSceneBuilder.cs     # [MenuItem] 一键搭建
├── RhythmBeatControllers.cs             # 全部 7 个控制器（含 10 bugs）
├── RhythmBeatOracleRegistry.cs          # Oracle 注册表
├── oracle_bugs.json                     # 机器可读 bug 清单
├── ORACLE_BENCHMARK.md                  # bug 详细文档
├── DELIVERY_NOTES.md                    # 本文件
├── TESTING_COMMANDS.md                  # 测试命令
└── gold_standard_test_plan.json         # 金标 test plan
```

## 搭建步骤
1. 打开 `MiniGame_RhythmBeat.unity`
2. `Tools/MiniGame RhythmBeat/Build Scene`
3. `File → Save`
4. Hierarchy 包含: StateController / ComboCounter / SongController / ScoreBoard / DifficultySelector(+SelectedIndicator) / Saber_Blue / Saber_Red / BeatBlock_00..07

## 关键点
- BUG-001: `Saber_Blue/Red` 上**不要**手动添加 AudioSource
- BUG-005: 方块在 Update 自动向 +Z 飞，进入 Play 后立即触发
- 多个 bug 需要 Trigger 显式调用 (ForceSlashWrongDirection / Stop / TryFinishSong / Clear / ResetAllState 等)
