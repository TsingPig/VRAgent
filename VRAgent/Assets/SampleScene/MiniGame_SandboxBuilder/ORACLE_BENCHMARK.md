# MiniGame_SandboxBuilder — Oracle Benchmark

> **类型**: Minecraft VR / Rec Room 风格沙盒建造  
> **Bugs**: 10  
> **状态机**: PowerOn → ToolSelected → BlockGrabbed → BlockPlaced → BlockRotated → StructureValidated → SavedLocally → Published → GameComplete

| ID | 文件::方法 | 类别/严重度 | 说明 |
|----|-----------|-------------|------|
| BUG-001 | BlockPlacer::PlaceBlock          | crash/high  | NRE 无 AudioSource |
| BUG-002 | BuildingBlock::StackOn           | functional/med | 无支撑也能堆叠 |
| BUG-003 | ToolboxController::DeselectTool  | state/med   | 反选不重置工具激活 |
| BUG-004 | ToolboxController::TriggerCooldown | functional/med | 冷却计时残留 |
| BUG-005 | BuildingBlock::Rotate90          | functional/low | 绕 X 轴旋转 |
| BUG-006 | StateController::TryPublish      | functional/high | 不到最小方块也能发布 |
| BUG-007 | SaveLoadController::SaveLevel    | state/med   | 接受空关卡名 |
| BUG-008 | HighlightOutline::Update         | visual/low  | 高亮不消失 |
| BUG-009 | BlockPlacer::PlaceBlock          | functional/med | 放置先于网格校验 |
| BUG-010 | StateController::ResetAllState   | state/med   | 不清理 SaveLoad |
