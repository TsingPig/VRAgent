# MiniGame_EscapeRoom — Oracle Benchmark

> **类型**: I Expect You To Die 风格密室解谜  
> **Bugs**: 10 (1 crash / 5 functional / 3 state / 1 visual)  
> **状态机**: PowerOn → CombinationDialed → SafeUnlocked → KeyGrabbed → KeyInserted → DoorUnlocked → DoorOpened → ExitReached → GameComplete

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | KeySafeController::TryUnlock     | crash/high     | NRE 无 AudioSource |
| BUG-002 | PuzzlePanelController::SubmitAnswer | functional/med | 任何答案都判对 |
| BUG-003 | DoorController::CloseDoor        | state/med      | CloseDoor 不重置 IsOpen |
| BUG-004 | KeyController::OnInsert          | functional/med | 插入计时器残留 |
| BUG-005 | CombinationLock::RotateDial      | functional/low | 拨轮反向 |
| BUG-006 | StateController::TryEscape       | functional/high | 不验证解谜数量 |
| BUG-007 | DoorController::OpenDoor         | state/med      | 用 SafeUnlocked 替代 KeyInserted |
| BUG-008 | HintLight::OnSolved              | visual/low     | 提示灯不熄灭 |
| BUG-009 | KeySafeController::TryUnlock     | functional/med | 先开后校验 |
| BUG-010 | StateController::ResetAllState   | state/med      | 不级联清理 |

```bash
grep -E "\[ORACLE:BUG-[0-9]{3}:TRIGGERED\]" console_logs.txt
grep -E "NullReferenceException.*KeySafeController" console_logs.txt
```
