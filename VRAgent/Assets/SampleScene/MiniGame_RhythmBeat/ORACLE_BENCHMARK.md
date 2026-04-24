# MiniGame_RhythmBeat — Oracle Benchmark

> **类型**: Beat Saber 风格节奏切方块  
> **Bugs**: 10 (1 crash / 5 functional / 3 state / 1 visual)  
> **状态机**: PowerOn → SongLoaded → DifficultySelected → SaberHeld → SongPlaying → AllBlocksHit → ScoreSubmitted

## Bug 速查

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | BeatSaberWeapon::Slash       | crash/high     | NRE — 无 AudioSource 也调 GetComponent.Play |
| BUG-002 | BeatBlock::OnSlash           | functional/med | 切错方向也加分 |
| BUG-003 | SongController::Stop         | state/med      | Stop 不重置 IsPlaying |
| BUG-004 | ComboCounter::IncrementCombo | functional/med | 上一次 combo 计时残留 |
| BUG-005 | BeatBlock::Update            | functional/low | 方块向 +Z 飞（远离玩家） |
| BUG-006 | StateController::TryFinishSong | functional/high | 未达成 BlocksRequired 也能完成 |
| BUG-007 | SongController::Play         | state/med      | 用 SongLoaded 代替 DifficultySelected |
| BUG-008 | DifficultySelector::Clear    | visual/low     | 已选指示灯不复位 |
| BUG-009 | BeatSaberWeapon::RegisterSwing | functional/med | combo 先++再校验方向 |
| BUG-010 | StateController::ResetAllState | state/med    | 不级联清理 combo/song/difficulty |

## 检测命令

```bash
grep -E "\[ORACLE:BUG-[0-9]{3}:TRIGGERED\]" console_logs.txt
grep -E "NullReferenceException.*BeatSaberWeapon" console_logs.txt
```
