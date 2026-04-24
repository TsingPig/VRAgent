# VR Mini-Game Benchmark Suite

> 在 Kitchen_TestRoom / Apartment 之外，新增 7 个主流 VR 小游戏类型的 Oracle Benchmark 场景。
> 全部对齐 **10-bug × 同分类配比** 的注入模板，便于 VRAgent 2.0 横向对比覆盖能力。

## 场景索引

| # | 文件夹 | 类型原型 | 核心交互 | 状态机长度 |
|---|--------|----------|----------|------------|
| 1 | `MiniGame_ShootingRange/`  | Pistol Whip / SuperHot | Grab 武器 → 装弹 → 射击靶子 → 计分    | 8 |
| 2 | `MiniGame_RhythmBeat/`     | Beat Saber             | Grab 光剑 → 节奏挥砍方块 → Combo      | 7 |
| 3 | `MiniGame_EscapeRoom/`     | I Expect You To Die    | 拨密码 → 拿钥匙 → 解保险箱 → 开门      | 9 |
| 4 | `MiniGame_BowlingSports/`  | Eleven Table Tennis 类  | Grab 球 → 投掷 → 倒瓶 → 分数 → 复位   | 8 |
| 5 | `MiniGame_HorrorSurvival/` | Resident Evil 4 VR     | 手电筒 → 装电池 → 找钥匙 → 躲怪 → 逃出 | 9 |
| 6 | `MiniGame_SandboxBuilder/` | Rec Room / Minecraft   | 选工具 → 放方块 → 旋转 → 保存 → 发布   | 8 |
| 7 | `MiniGame_TowerDefense/`   | Vampire / Cards & Tankards | 选塔 → 放置 → 升级 → 防御波次 → 胜利 | 8 |

## 标准目录结构（每个场景）

```
MiniGame_<Name>/
├── <Name>.unity                # 最小 Unity 场景（Camera + Light + SceneSetup root）
├── Editor/
│   └── <Name>SceneBuilder.cs   # [MenuItem "Tools/<Name>/Build Scene"] 一键搭建
├── <Name>StateController.cs    # 中央状态机（含 oracle markers）
├── <Theme>Controller_*.cs      # 5-7 个主题脚本（共注入 10 个 bug）
├── OracleRegistry.cs           # 注册 10 个 bug + 状态 oracle
├── oracle_bugs.json            # 机器可读 bug 清单（同 Kitchen 格式）
├── ORACLE_BENCHMARK.md         # 中文 bug 详解文档
├── DELIVERY_NOTES.md           # 场景说明 + Hierarchy
├── TESTING_COMMANDS.md         # vragent2 / VRAgent 1.0 测试命令
└── gold_standard_test_plan.json # 手工对齐 10 bug 的金标 test plan（FileID 占位）
```

## 10-Bug 注入模板（所有场景对齐 Kitchen/Apartment）

| Bug | 类别        | 严重度 | 模式                                             |
|-----|-------------|--------|--------------------------------------------------|
| 001 | crash       | high   | NullReferenceException（GetComponent 缺 null 检查） |
| 002 | functional  | medium | 缺少前置条件检查（直接执行）                        |
| 003 | state       | medium | OFF 状态不重置下游标志（单向状态传播）              |
| 004 | functional  | medium | 计时器/累加器在重试时不归零                         |
| 005 | functional  | low    | 方向/符号错误（坐标轴反向）                         |
| 006 | functional  | high   | 跳过验证门（uncooked / 未达成条件却推进）           |
| 007 | state       | medium | 错误的前置条件字段（用了 hasKey 而非 keyInserted）  |
| 008 | visual      | low    | UI 指示灯/颜色不复位                                |
| 009 | functional  | medium | 副作用先于校验（先扣资源再判断合法）                |
| 010 | state       | medium | ResetAllState 不级联清理下游控制器                  |

## 使用工作流

1. 打开任意 `.unity` 场景
2. 顶部菜单 `Tools/<Scene>/Build Scene` → 自动生成 GameObject 层级与组件（含 XR Sockets）
3. `File → Save` 保存场景
4. `Tools/VR Explorer/Import Test Plan` → 选择对应 `gold_standard_test_plan.json` 验证
5. 跑 vragent2 pipeline，参考各场景 `TESTING_COMMANDS.md`

## Oracle 检测协议（与 Kitchen/Apartment 完全一致）

- **Exception oracle**: console grep `NullReferenceException`
- **Marker oracle**: console grep `\[ORACLE:BUG-XXX:TRIGGERED\]`
- **State oracle**: console grep `\[ORACLE:STATE:label\]`

## 场景间公共脚本

每个场景的 `OracleRegistry.cs` 类名带场景前缀（避免 namespace 冲突），如：
- `ShootingRangeOracleRegistry`
- `RhythmBeatOracleRegistry`
- ...

## Python 端配置

每个场景跑测试时只需在 vragent2 命令中切换 `--scene_name` 与对应的 `gobj_hierarchy.json`。
oracle 评估器（`vragent2/utils/oracle.py`）已自动 grep 所有 `[ORACLE:*]` 标记，无需修改。
