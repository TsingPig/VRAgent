# MiniGame_ShootingRange — Testing Commands

## 1. 生成场景元数据

```powershell
# Unity Editor 中执行
Tools/VR Explorer/Generate Scene Hierarchy   # → gobj_hierarchy.json
Tools/VR Explorer/Export Scene Dependency    # → scene.gml
```

## 2. VRAgent 1.0 — 直接执行金标 test plan

```powershell
# Unity Editor 中
Tools/VR Explorer/Import Test Plan
# 选择: VRAgent/Assets/SampleScene/MiniGame_ShootingRange/gold_standard_test_plan.json
# 进入 Play Mode 自动执行
```

## 3. VRAgent 2.0 — LLM 在线生成

```powershell
cd D:\--UnityProject\HenryLabXR\VRAgent\TP_Generation
.\.venv\Scripts\Activate.ps1

python -m vragent2 `
  --scene_name MiniGame_ShootingRange `
  --hierarchy_json ".\TP_Generation\Results_VRAgent2.0\MiniGame_ShootingRange\gobj_hierarchy.json" `
  --scene_gml ".\TP_Generation\Results_VRAgent2.0\MiniGame_ShootingRange\scene.gml" `
  --output ".\TP_Generation\Results_VRAgent2.0\MiniGame_ShootingRange\opus4.6-default" `
  --budget 80 `
  --model claude-opus-4.6 `
  --unity
```

## 4. Oracle 评估

```powershell
python -m vragent2.utils.oracle `
  --scene MiniGame_ShootingRange `
  --console_logs ".\TP_Generation\Results_VRAgent2.0\MiniGame_ShootingRange\opus4.6-default\console_logs.txt" `
  --oracle_def ".\VRAgent\Assets\SampleScene\MiniGame_ShootingRange\oracle_bugs.json"
```

## 5. 多模型 benchmark

```powershell
python -m vragent2.benchmark `
  --scenes MiniGame_ShootingRange `
  --models gpt-4o claude-opus-4.6 gemini-2.0 `
  --output ".\TP_Generation\Results_VRAgent2.0"
```

## 6. 可视化报告

```powershell
python -m vragent2.visualize `
  --benchmark_dir ".\TP_Generation\Results_VRAgent2.0" `
  --scene MiniGame_ShootingRange `
  --html_out shooting_range_report.html
```

## 7. 控制台 oracle grep（手动验证）

```powershell
# Bug markers
Get-Content "console_logs.txt" | Select-String -Pattern "\[ORACLE:BUG-\d{3}:TRIGGERED\]"

# State oracles
Get-Content "console_logs.txt" | Select-String -Pattern "\[ORACLE:STATE:[A-Za-z]+\]"

# Crash signals
Get-Content "console_logs.txt" | Select-String -Pattern "NullReferenceException.*WeaponController"
```
