# MiniGame_TowerDefense — Oracle Benchmark

> **类型**: Defense Grid VR / Cubism Tower 风格塔防  
> **Bugs**: 10  
> **状态机**: PowerOn → GoldEarned → TowerSelected → TowerPlaced → TowerUpgraded → WaveStarted → AllWavesDefeated → GameComplete

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | TowerPlacer::PlaceTower          | crash/high  | NRE 无 AudioSource |
| BUG-002 | Tower::Fire                      | functional/med | 无敌人也开火 |
| BUG-003 | WaveSpawner::StopWave            | state/med   | StopWave 不重置 IsActive |
| BUG-004 | WaveSpawner::StartWave           | functional/med | 生成计时残留 |
| BUG-005 | Tower::RotateTurret              | functional/low | 炮塔背对目标 |
| BUG-006 | StateController::TryDeclareVictory | functional/high | 未完成波数也胜利 |
| BUG-007 | ResourceManager::TryBuildExpensive | state/med | 金币不足也建 |
| BUG-008 | EnemyController::Heal            | visual/low  | 红血条不消失 |
| BUG-009 | TowerPlacer::PlaceTower          | functional/med | 放置先于金币校验 |
| BUG-010 | StateController::ResetAllState   | state/med   | 不退还金币 |
