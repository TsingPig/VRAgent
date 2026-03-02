# VRAgent 2.0 完整使用指南（Offline + Online）

本指南面向当前仓库 `TP_Generation/vragent2`，覆盖两种主流程：

1. **从零开始完整在线构建**（前置 RAG 数据准备 + Unity 在线闭环执行）
2. **基于已有离线结果快速在线执行**（复用已生成的 hierarchy/gml/test plan 资产）

同时包含断点续跑、结果落盘到 Unity 场景目录、常见故障排查。

---

## 0. 你会得到什么

执行后将得到以下核心能力：

- 多 Agent 闭环：`Planner -> Verifier -> Executor -> Observer`
- 支持 **Offline（不连 Unity）** 和 **Online（连 Unity Play Mode）**
- 支持 `--resume` 断点续跑，避免重复消耗 token
- 结果自动同步到 Unity：
  - `Assets/SampleScene/<SceneName>/VRAgent2_Results/`

---

## 1. 目录与关键组件

- Python 入口：`TP_Generation/vragent2/main.py`
- Controller：`TP_Generation/vragent2/controller.py`
- Unity Bridge 客户端：`TP_Generation/vragent2/bridge/unity_bridge.py`
- Unity 在线执行器：`VRAgent/Assets/Package/VRAgent/Online/VRAgentOnline.cs`
- Unity TCP 服务：`VRAgent/Assets/Package/VRAgent/Online/AgentBridge.cs`

前置数据（RAG 输入）主要是：

- `*_gobj_hierarchy.json`（来自 `TraverseSceneHierarchy.py`）
- `*.unity.json_graph.gml`（来自 `ExtractSceneDependency.py`）

---

## 2. 环境准备

### 2.1 Python

虚拟环境**只需要创建一次**，后续每次开发只需要“激活”它，不要重复新建。

首次初始化（仅一次）：

```powershell
cd d:\--UnityProject\HenryLabXR\VRAgent
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install networkx matplotlib requests openai
```

日常使用（每次新开终端执行）：

```powershell
cd d:\--UnityProject\HenryLabXR\VRAgent
& .\.venv\Scripts\Activate.ps1
```

验证当前解释器是否是 `.venv`：

```powershell
python -c "import sys; print(sys.executable)"
python -m pip show networkx
```

### 2.2 API 配置

任选其一：

- 环境变量：`OPENAI_API_KEY`（可选 `OPENAI_API_BASE`）
- 或使用 `TP_Generation/config.py` 中现有配置（兼容旧逻辑）

### 2.3 Unity 场景准备（Online 必需）

- 打开 Unity Project：`VRAgent/VRAgent`
- 打开目标场景（示例：`Home_TwoRooms.unity`）
- 场景中确保有：
  - `VRAgentOnline`（挂载了 `AgentBridge` + `StateCollector`）
- 点击 **Play Mode**
- 默认端口：`6400`

---

## 3. 路线 A：从零开始完整在线构建（推荐）

> 适用于新项目/新场景，尚未准备 hierarchy 与 gml。

### Step A1：抽取场景依赖（RAG 底座）

```powershell
cd d:\--UnityProject\HenryLabXR\VRAgent\TP_Generation
python .\ExtractSceneDependency.py -p "<Unity项目根目录>" -r "Results\Results_<SceneName>"
```

输出关键目录（示例）：

- `Results/Results_<SceneName>/scene_detailed_info/`
- `Results/Results_<SceneName>/script_detailed_info/`

### Step A2：遍历层级，生成 hierarchy

```powershell
python .\TraverseSceneHierarchy.py -r "Results\Results_<SceneName>"
```

关键输出：

- `Results/Results_<SceneName>/<SceneName>_gobj_hierarchy.json`

### Step A3：特殊逻辑预处理（建议）

```powershell
python .\SpecialLogicPreprocessor.py -r "Results\Results_<SceneName>" -s "<SceneName>" -a "<AppName>"
```

作用：补充 `sorted_target_logic_info`、`sorted_layer_logic_info`，提高规划质量与稳定性。

### Step A4：启动 VRAgent2.0 Online 闭环

```powershell
python -m vragent2 `
  --unity `
  --unity_host 127.0.0.1 `
  --unity_port 6400 `
  --scene_name <SceneName> `
  --hierarchy_json "Results\Results_<SceneName>\<SceneName>_gobj_hierarchy.json" `
  --scene_gml "Results\Results_<SceneName>\scene_detailed_info\mainResults\<SceneName>.unity.json_graph.gml" `
  --output "Results\Results_<SceneName>\vragent2_output_online" `
  --unity_project "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent\Assets" `
  --model gpt-4o `
  --budget 50
```

执行完成后输出：

- Python 输出目录：`--output` 指向目录
- Unity 场景目录：`Assets/SampleScene/<SceneName>/VRAgent2_Results/`

---

## 4. 路线 B：复用已有离线资产进行在线执行

> 适用于你已经有 `hierarchy + gml`，甚至已有历史输出目录。

### Step B1：直接在线运行（最短路径）

```powershell
python -m vragent2 `
  --unity `
  --scene_name Home_TwoRooms `
  --hierarchy_json "Results\Results_Home_TwoRooms\Home_TwoRooms_gobj_hierarchy.json" `
  --scene_gml "Results\Results_Home_TwoRooms\scene_detailed_info\mainResults\Home_TwoRooms.unity.json_graph.gml" `
  --output "Results\Results_Home_TwoRooms\vragent2_output_online_gpt4o_retry" `
  --unity_project "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent\Assets" `
  --model gpt-4o `
  --budget 10
```

### Step B2：断点续跑（避免重复 token）

如果上一轮中断或你只想继续未完成对象：

```powershell
python -m vragent2 `
  --unity --resume `
  --scene_name Home_TwoRooms `
  --hierarchy_json "Results\Results_Home_TwoRooms\Home_TwoRooms_gobj_hierarchy.json" `
  --scene_gml "Results\Results_Home_TwoRooms\scene_detailed_info\mainResults\Home_TwoRooms.unity.json_graph.gml" `
  --output "Results\Results_Home_TwoRooms\vragent2_output_online_gpt4o_retry" `
  --unity_project "d:\--UnityProject\HenryLabXR\VRAgent\VRAgent\Assets" `
  --budget 10
```

`--resume` 会读取 `session_state.json`，跳过已处理对象，继续剩余探索。

---

## 5. Offline 模式（不连接 Unity）

> 用于仅验证规划/验证链路，或在无 Play Mode 时跑冒烟。

只需去掉 `--unity`：

```powershell
python -m vragent2 `
  --scene_name Home_TwoRooms `
  --hierarchy_json "Results\Results_Home_TwoRooms\Home_TwoRooms_gobj_hierarchy.json" `
  --scene_gml "Results\Results_Home_TwoRooms\scene_detailed_info\mainResults\Home_TwoRooms.unity.json_graph.gml" `
  --output "Results\Results_Home_TwoRooms\vragent2_output_offline" `
  --model gpt-4o `
  --budget 20
```

Offline 下 Executor 会走 dry-run，仍会生成：

- `all_actions.json`
- `iteration_logs.json`
- `test_plan.json`
- `summary.json`
- `gate_graph.json`

---

## 6. 输出文件说明

在 `--output` 目录下：

- `all_actions.json`：全部动作序列
- `test_plan.json`：VRAgent 兼容格式（taskUnits/actionUnits）
- `iteration_logs.json`：每轮对象、verifier 分数、bug signal 等
- `gate_graph.json`：门控图探索状态
- `summary.json`：总览统计
- `session_state.json`：续跑状态
- `execution/trace_*.json`：执行 trace

在 Unity 侧（若传 `--unity_project`）：

- `Assets/SampleScene/<SceneName>/VRAgent2_Results/`（镜像以上关键结果）

---

## 7. 关键参数建议

- `--budget`：先小后大，建议 5 -> 20 -> 50
- `--max_repair`：默认 2，通常足够
- `--limit`：可用于小样本快速验证
- `--model`：当前建议 `gpt-4o`
- `--resume`：中断恢复必开

---

## 8. 常见问题排查

### 8.1 无法连接 Unity

现象：`Cannot connect to Unity` / `connection refused`

检查：

1. Unity 是否在 Play Mode
2. 场景是否包含 `VRAgentOnline` + `AgentBridge`
3. 端口是否一致（默认 6400）
4. 本机防火墙是否拦截 127.0.0.1:6400

### 8.1.1 `TraverseSceneHierarchy` 提示“未找到任何GML文件”

这通常表示前一步 `ExtractSceneDependency.py` 没有产出场景 `.gml`。常见根因是 `EditorBuildSettings.asset` 里 `m_Scenes` 为空。

可直接指定场景路径绕过 Build Settings：

```powershell
python .\ExtractSceneDependency.py -p "D:\--UnityProject\HenryLabXR\VRAgent\VRAgent" -r "Results\Results_Home_TwoRooms" --scene-path "Assets/SampleScene/Home_TwoRooms/Home_TwoRooms.unity"
```

或指定场景名自动检索：

```powershell
python .\ExtractSceneDependency.py -p "D:\--UnityProject\HenryLabXR\VRAgent\VRAgent" -r "Results\Results_Home_TwoRooms" -s "Home_TwoRooms"
```

### 8.2 触发动作无效果 / NO_STATE_CHANGE

先确认：

- 动作目标是否真实可交互对象（非系统对象）
- 对应方法是否需要前置状态（钥匙/开关/门锁）
- 查看 `iteration_logs.json` + Unity Console logs

### 8.3 恢复跑没有跳过对象

确认：

- `--output` 与上次完全一致
- 该目录下存在 `session_state.json`
- 本轮使用了 `--resume`

### 8.4 场景目录没有同步结果

确认：

- 传了 `--unity_project <.../Assets>`
- `scene_name` 与 `Assets/SampleScene/<scene_name>/` 目录一致

---

## 9. 推荐工作流（团队）

1. 新场景首次接入：走 **路线 A**
2. 日常回归：走 **路线 B + --resume**
3. 先用 Offline 快速看策略，再切 Online 验证真实交互
4. 统一保留 `VRAgent2_Results` 作为场景内可追溯执行记录

---

## 10. 最小可用命令模板

### Online

```powershell
python -m vragent2 --unity --scene_name <SceneName> --hierarchy_json "<..._gobj_hierarchy.json>" --scene_gml "<...gml>" --output "<output_dir>" --unity_project "<.../Assets>" --budget 10
```

### Resume

```powershell
python -m vragent2 --unity --resume --scene_name <SceneName> --hierarchy_json "<..._gobj_hierarchy.json>" --scene_gml "<...gml>" --output "<same_output_dir>" --unity_project "<.../Assets>" --budget 10
```

### Offline

```powershell
python -m vragent2 --scene_name <SceneName> --hierarchy_json "<..._gobj_hierarchy.json>" --scene_gml "<...gml>" --output "<output_dir>" --budget 20
```

---

如需，我可以下一步把这份 Guide 再拆成两份：

- `Guide_QuickStart.md`（10 分钟上手）
- `Guide_Advanced.md`（RAG 细节、调参、调试）
