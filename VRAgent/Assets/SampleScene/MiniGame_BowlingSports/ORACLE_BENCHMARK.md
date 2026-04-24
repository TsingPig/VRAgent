# MiniGame_BowlingSports — Oracle Benchmark

> **类型**: 保龄球运动 (Eleven Table Tennis 风格运动模拟)  
> **Bugs**: 10  
> **状态机**: PowerOn → BallGrabbed → BallReleased → BallRolled → PinsKnocked → FrameScored → LaneReset → GameComplete

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | BowlingBall::RollBall            | crash/high     | NRE 无 AudioSource |
| BUG-002 | BowlingPin::OnFall               | functional/med | 无碰撞也判倒 |
| BUG-003 | LaneController::EndFrame         | state/med      | EndFrame 不重置 IsActive |
| BUG-004 | LaneController::StartReset       | functional/med | 重置计时器残留 |
| BUG-005 | BowlingPin::OnFall               | functional/low | 瓶子向 -X 倾倒 |
| BUG-006 | StateController::TryFinishGame   | functional/high | 未完成 10 局也能结束 |
| BUG-007 | FrameScoreboard::AddFrameScore   | state/med      | 用 BallGrabbed 替代 BallReleased |
| BUG-008 | PinResetLight::Update            | visual/low     | 重置灯不熄灭 |
| BUG-009 | BowlingBall::RegisterFrameResult | functional/med | 先加分后校验 |
| BUG-010 | StateController::ResetAllState   | state/med      | 不级联清理 Scoreboard |
