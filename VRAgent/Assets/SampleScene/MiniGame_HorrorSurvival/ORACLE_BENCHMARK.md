# MiniGame_HorrorSurvival — Oracle Benchmark

> **类型**: Resident Evil 4 VR / Phasmophobia 风格生存恐怖  
> **Bugs**: 10  
> **状态机**: PowerOn → FlashlightHeld → BatteryInserted → KeyFound → DoorUnlocked → EnemyEscaped → SafeRoomReached → ExtractionCalled → GameComplete

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | FlashlightController::ToggleLight  | crash/high  | NRE 无 AudioSource |
| BUG-002 | BatteryItem::ApplyToFlashlight     | functional/med | 没抓也能装 |
| BUG-003 | DoorLockController::ToggleLockOff  | state/med   | Toggle 不重置 IsLocked |
| BUG-004 | EnemyAI::StartChase                | functional/med | 追击计时残留 |
| BUG-005 | BatteryItem::ApplyToFlashlight     | functional/low | 电池倒插 |
| BUG-006 | StateController::TryEscape         | functional/high | 钥匙不够也能逃 |
| BUG-007 | DoorLockController::TryUnlock      | state/med   | 用 KeyFound 替代数量 |
| BUG-008 | HealthSystem::Heal                 | visual/low  | 红血条不复位 |
| BUG-009 | FlashlightController::ToggleLight  | functional/med | 先 toggle 后校验电池 |
| BUG-010 | StateController::ResetAllState     | state/med   | 不级联清理 EnemyAI |
