# MiniGame_EscapeRoom — Testing Commands

## VRAgent 1.0
`Tools/VR Explorer/Import Test Plan` → `MiniGame_EscapeRoom/gold_standard_test_plan.json`

## VRAgent 2.0
```powershell
python -m vragent2 `
  --scene_name MiniGame_EscapeRoom `
  --output ".\TP_Generation\Results_VRAgent2.0\MiniGame_EscapeRoom\opus4.6-default" `
  --budget 80 --model claude-opus-4.6 --unity
```

## Oracle 评估
```powershell
Get-Content console_logs.txt | Select-String "\[ORACLE:BUG-\d{3}:TRIGGERED\]"
Get-Content console_logs.txt | Select-String "NullReferenceException.*KeySafeController"
```
