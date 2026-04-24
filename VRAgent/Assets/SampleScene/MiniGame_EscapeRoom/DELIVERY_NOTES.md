# MiniGame_EscapeRoom — Delivery Notes

## 类型
I Expect You To Die 风格密室。核心循环：拨密码 → 开保险箱 → 拿钥匙 → 解谜 → 开门 → 逃出。

## 文件清单
```
MiniGame_EscapeRoom/
├── MiniGame_EscapeRoom.unity
├── Editor/EscapeRoomSceneBuilder.cs
├── EscapeRoomControllers.cs        # 7 controllers + 10 bugs
├── EscapeRoomOracleRegistry.cs
├── oracle_bugs.json
├── ORACLE_BENCHMARK.md
├── DELIVERY_NOTES.md
├── TESTING_COMMANDS.md
└── gold_standard_test_plan.json
```

## 搭建
1. 打开 `.unity` → `Tools/MiniGame EscapeRoom/Build Scene` → File→Save
2. Hierarchy: StateController / CombinationLock / KeySafe / Key (Rigidbody+Collider) / ExitDoor / HintLight(+Bulb) / PuzzlePanel

## 关键
- BUG-001: KeySafe GameObject 不要加 AudioSource
- BUG-005: dial 一旋转就触发
- 多数 bug 通过 Trigger 显式调用对应方法
