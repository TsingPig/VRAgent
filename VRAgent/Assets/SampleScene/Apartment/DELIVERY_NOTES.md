## 场景概览

**场景名称：** `Apartment`  
**场景路径：** `Assets/SampleScene/Apartment/Apartment.unity`  
**设计目标：** 多步骤 XR 自动化测试场景，覆盖智能家居日常任务链、门控逻辑和状态机交互

---

## 新建/修改文件清单

### 脚本（`Assets/SampleScene/Apartment/`）

| 文件 | 职责 | Bug |
|------|------|----|
| `ApartmentStateController.cs` | 核心状态机，持有 10 个进度标志，统一管理前置检查、事件和日志 | BUG-007, BUG-010 |
| `MailboxKeyController.cs` | 首次抓取 Key_Mailbox 时调用 `SetHasMailKey()` | — |
| `MailboxLockReceiver.cs` | 钥匙插入 Socket_MailboxLock 后解锁信箱 | — |
| `CircuitBreakerController.cs` | 主配电箱开关，Toggle 控制全屋电器和 PowerOn 状态 | BUG-003 |
| `WindowBlindController.cs` | 电动百叶窗，需电驱动，平滑上下动画 | BUG-005 |
| `CoffeeMachineController.cs` | 三态咖啡机（Idle/Brewing/Done），2 秒冲泡计时 | BUG-001, BUG-002 |
| `CoffeeCupSocket.cs` | 检测 Cup_Coffee 是否在咖啡机插槽内 | — |
| `ToasterController.cs` | 放面包→按杠杆→3 秒计时→弹出 | BUG-004 |
| `DiningTableSocket.cs` | 接收早餐物品，检查咖啡和吐司完成后才接受 | — |
| `FaucetController.cs` | 水龙头开关 + 热水洗碗功能（需电） | BUG-006 |
| `FridgeDoorController.cs` | 冰箱门铰链动画 + 内灯 + 开门报警（5 秒） | BUG-008 |
| `TVController.cs` | 电视开关 + 频道切换（需电） + 状态上报 | BUG-009 |
| `StoveBurnerController.cs` | 炉灶开关（需电才能点火） | — |
| `TableLampController.cs` | 台灯开关（需电才能开灯） | — |
| `ApartmentOracleRegistry.cs` | Oracle 注册表，跟踪 10 个注入 bug 的触发状态 | — |

### 文档

| 文件 | 用途 |
|------|------|
| `DELIVERY_NOTES.md` | 场景概览、文件清单、Hierarchy 结构 |
| `TESTING_COMMANDS.md` | 测试环境变量和 Stage 1-5 测试命令 |
| `ORACLE_BENCHMARK.md` | 10 个 bug 的详细规格说明 |
| `oracle_bugs.json` | 机器可读的 bug 定义 |

---

## Hierarchy 结构

```
_Managers
├── ApartmentState_Main       ← ApartmentStateController（全局状态机）
└── ExperimentManager         ← EAT 框架入口

_Environment
└── Directional Light

Room_Entryway（入口区）
├── Floor / Ceiling / Walls
├── KeyHook_Main
│   └── Key_Mailbox           ← MailboxKeyController + Rigidbody
├── Mailbox_Main
│   └── Socket_MailboxLock    ← MailboxLockReceiver + XRSocketInteractor
└── Switch_CircuitBreaker     ← CircuitBreakerController + XRTriggerable

Room_LivingRoom（客厅）
├── Floor / Ceiling / Walls
├── TV_Main                   ← TVController
│   ├── Button_Power          ← XRTriggerable → TogglePower
│   └── Button_Channel        ← XRTriggerable → CycleChannel
├── Lamp_Table                ← TableLampController + XRTriggerable
├── Window_Main
│   └── Blind_Motorized       ← WindowBlindController + XRTriggerable
└── Table_Dining
    └── Socket_DiningPlate    ← DiningTableSocket + XRSocketInteractor

Room_Kitchen（厨房）
├── Floor / Ceiling / Walls
├── Fridge_Main
│   └── Door_Fridge           ← FridgeDoorController + XRTriggerable
├── Sink_Main
│   └── Faucet_Handle         ← FaucetController + XRTriggerable
├── Stove_Top
│   └── Burner_Main           ← StoveBurnerController + XRTriggerable
├── CoffeeMachine_Main        ← CoffeeMachineController
│   ├── Button_Brew           ← XRTriggerable → TryStartBrew
│   └── Socket_CupSlot        ← CoffeeCupSocket + XRSocketInteractor
├── Toaster_Main              ← ToasterController
│   ├── Lever_Toast           ← XRTriggerable → PushLever
│   └── Socket_BreadSlot      ← XRSocketInteractor → OnBreadInserted/OnBreadRemoved
├── Cup_Coffee                ← XRGrabbable + Rigidbody
└── Bread_Slice               ← XRGrabbable + Rigidbody
```

---

## 任务流程（Morning Routine）

```
Step 1:  抓取钥匙 (Key_Mailbox)          → hasMailKey
Step 2:  插入钥匙到信箱锁                  → mailboxUnlocked
Step 3:  翻转配电箱开关                     → powerOn
Step 4:  打开电动百叶窗（需电）              → blindsOpened
Step 5:  放杯子到咖啡机插槽                  → cupPlaced
Step 6:  按冲泡按钮（需电 + 杯子）           → coffeeBrewed
Step 7:  放面包 + 按烤面包杠杆（需电）        → toastMade
Step 8:  将早餐放到餐桌（需咖啡 + 吐司）      → breakfastServed
Step 9:  开电视看新闻（需电）                → tvNewsWatched
Step 10: 自动检测完成                       → routineComplete
```

---
