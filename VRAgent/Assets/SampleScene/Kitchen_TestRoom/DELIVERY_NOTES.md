## 场景概览

**场景名称：** `Kitchen_TestRoom`  
**场景路径：** `Assets/SampleScene/Kitchen_TestRoom/Kitchen_TestRoom.unity`  
**设计目标：** 多步骤 XR 自动化测试场景，覆盖门控逻辑、状态机交互和配方序列验证

---

## 新建/修改文件清单

### 脚本（`Assets/SampleScene/Kitchen_TestRoom/`）

| 文件 | 职责 |
|------|------|
| `RecipeController.cs` | 核心状态机，持有10个测试状态字段，统一管理前置检查、事件和日志 |
| `GrabbableKeyController.cs` | 继承 `XRGrabbable`，首次抓取 Key_Pantry 时调用 `SetHasPantryKey()` |
| `PantryKeyUnlockReceiver.cs` | 钥匙插入 Socket_PantryLock 后解锁储藏间门 |
| `PowerSwitchController.cs` | 主电源开关，Toggle 控制厨房灯光和 PowerEnabled 状态 |
| `KitchenBadgeUnlockReceiver.cs` | Badge 插入时检查 PowerEnabled，无电则显示红色面板 |
| `SinkWashStation.cs` | 1.5s 计时清洗，中途移走食材则不计完成 |
| `KnifeSlotDetector.cs` | 检测 Tool_Knife 是否在切菜台插槽内 |
| `CuttingBoardController.cs` | 需要刀在插槽且食材已洗才能切割 |
| `MixingBowlController.cs` | 接收切好的食材，调用 SetIngredientsCombined() |
| `MixingBowlSocket.cs` | 检测 Bowl_Mixing 是否放在灶台 Hob 上 |
| `StoveController.cs` | 三态机（Off/Cooking/Done），3秒计时烹饪 |
| `ServingPlateSocket.cs` | 接收已烹饪的碗，调用 SetDishPlated() |
| `ServingCounterSocket.cs` | 最终交付台，收到盘子后解锁 Door_FinalExit |
| `LockedCabinetController.cs` | 容器门控柜，储藏间门开后才可打开 |
| `FinalExitTrigger.cs` | 出口触发器，校验通关状态，失败不崩溃 |

### 材质（`Assets/Materials/`）

| 材质 | 用途 |
|------|------|
| `KeyGold.mat` | Key_Pantry 金色高光 |
| `PowerSwitchOn/Off.mat` | 开关状态颜色 |
| `CabinetLocked/Unlocked.mat` | 柜子锁定状态 |
| `TomatoRed.mat` | Ingredient_Tomato |
| `BurnerOff/Cooking/Done.mat` | 炉具三态颜色 |
| `BadgePanelNoPower/Unlocked.mat` | 门禁面板反馈 |
| `CounterWaiting/Complete.mat` | 交付台状态 |
| `KitchenWall/Floor.mat` | 房间装饰材质 |

---

## Hierarchy 结构

```
_Managers
├── RecipeController_Main     ← RecipeController（全局状态机）
└── ExperimentManager         ← EAT框架入口

_Environment
└── Directional Light

Room_A_Lobby（入口大厅，8×8m）
├── Floor/Ceiling/Walls
├── Table_A_Entry
├── Key_Pantry                ← GrabbableKeyController + Rigidbody
├── Switch_MainPower          ← PowerSwitchController + XRTriggerable
└── DoorFrame_Pantry
    ├── Door_Pantry           ← DoorController (startLocked=true)
    ├── Handle_Pantry         ← XRTriggerable → Toggle
    └── Socket_PantryLock     ← PantryKeyUnlockReceiver

Room_B_Pantry（储藏间，6×8m）
├── Floor/Ceiling/Walls
├── Cabinet_Ingredients       ← LockedCabinetController + XRTriggerable
├── Ingredient_Tomato         ← XRGrabbable + Rigidbody
├── Tool_Knife                ← XRGrabbable + Rigidbody
└── Badge_Kitchen             ← XRGrabbable + Rigidbody

Room_C_Kitchen（厨房，8×8m）
├── Floor/Ceiling/Walls
├── DoorFrame_Kitchen
│   ├── Door_Kitchen          ← DoorController (startLocked=true)
│   ├── Handle_Kitchen        ← XRTriggerable → Toggle
│   └── Socket_KitchenBadge  ← KitchenBadgeUnlockReceiver
├── Sink_WashStation
│   └── Socket_WashSlot       ← SinkWashStation（1.5s清洗计时）
├── Board_Cutting             ← CuttingBoardController + XRTriggerable
│   └── Socket_KnifeSlot      ← KnifeSlotDetector
├── Bowl_Mixing               ← XRGrabbable + MixingBowlController
├── Stove_Main                ← StoveController
│   ├── Knob_Stove            ← XRTriggerable → TryStartCooking
│   └── Socket_HobSlot        ← MixingBowlSocket
├── Plate_Serving             ← ServingPlateSocket
└── Light_C                   ← 初始关闭，PowerSwitch 控制

Room_D_Exit（终点区，8×8m）
├── Floor/Ceiling/Walls
├── DoorFrame_FinalExit
│   ├── Door_FinalExit        ← DoorController (startLocked=true)
│   └── Handle_FinalExit      ← XRTriggerable → Toggle
├── Counter_Serving
│   └── Socket_DeliverySlot   ← ServingCounterSocket（解锁终点门）
└── Trigger_FinalExit         ← FinalExitTrigger（BoxCollider isTrigger）
```

---

## 交互依赖关系（门控链）

```
[A] 抓 Key_Pantry
      └→ hasPantryKey = true
           └→ 插入 Socket_PantryLock
                └→ doorPantryUnlocked = true → Door_Pantry.Unlock()
                     └→ Cabinet_Ingredients 可开（容器门控）

[A] 触发 Switch_MainPower
      └→ powerEnabled = true（电源门控）

[B] Badge_Kitchen 插入 Socket_KitchenBadge
      └→ 检查 powerEnabled（无电 → 红色面板 FAIL）
           └→ doorKitchenUnlocked = true → Door_Kitchen.Unlock()

[C] Ingredient_Tomato 放入 Socket_WashSlot（等1.5s）
      └→ ingredientWashed = true

[C] Tool_Knife 放入 Socket_KnifeSlot → 触发 Board_Cutting
      └→ ingredientCut = true

[C] 食材放入 Bowl_Mixing（在碗里）
      └→ ingredientsCombined = true

[C] Bowl 放上 Socket_HobSlot → 转 Knob_Stove（等3s）
      └→ dishCooked = true（配方门控）

[C] 碗放入 Plate_Serving
      └→ dishPlated = true

[D] 盘子放入 Socket_DeliverySlot
      └→ finalDoorUnlocked = true → Door_FinalExit.Unlock()

[D] 玩家进入 Trigger_FinalExit → SUCCESS
```

---

## 可测试状态字段（RecipeController）

```csharp
// 全部通过 RecipeController.Instance 访问
bool HasPantryKey        // Step 1
bool DoorPantryUnlocked  // Step 2
bool PowerEnabled        // Step 3
bool DoorKitchenUnlocked // Step 4
bool IngredientWashed    // Step 5
bool IngredientCut       // Step 6
bool IngredientsCombined // Step 7
bool DishCooked          // Step 8
bool DishPlated          // Step 9
bool FinalDoorUnlocked   // Step 10
```

辅助方法：
- `RecipeController.Instance.PrintStateSnapshot()` — 打印全量快照到 Console
- `RecipeController.Instance.ResetAllState()` — 重置所有状态（测试重复执行）

---

## 失败分支（安全无崩溃）

| 场景 | 触发行为 | 日志关键字 |
|------|---------|-----------|
| 没钥匙开储藏间门 | DoorController 拒绝 | `FAIL — doorLocked` |
| 无电插 Badge | 面板变红 | `FAIL — no power` |
| 没刀切食材 | 切割被拒 | `FAIL — no knife` |
| 食材未洗就切 | 切割被拒 | `FAIL — tried to cut before washing` |
| 未烹饪就装盘 | Socket 拒绝 | `FAIL — dish is not cooked` |
| 未装盘就交付 | Counter 拒绝 | `FAIL — dish is not plated` |
| 未完成就出口 | FinalExitTrigger 重置 | `FAIL — task is incomplete` |

---

## 典型自动测试用例

| 测试ID | 名称 | 断言 |
|--------|------|------|
| TC01 | HappyPath完整通关 | `FinalDoorUnlocked == true` |
| TC02 | 无钥匙尝试开门 | `DoorPantryUnlocked == false` + WARN log |
| TC03 | 无电插徽章 | `DoorKitchenUnlocked == false` + 红色面板 |
| TC04 | 无刀切食材 | `IngredientCut == false` + WARN log |
| TC05 | 食材未洗就切 | `IngredientCut == false` |
| TC06 | 跳过烹饪直接装盘 | `DishPlated == false` |
| TC07 | 未完成就走出口 | `FinalExitTrigger.CompletedSuccessfully == false` |
| TC08 | ResetAllState后重跑 | 所有状态重置为 false，可二次通关 |

---

## Player（测试用）

**场景内 GameObject：** `Player_KitchenTest`（已在 Room A 入口，位置 `(0, 0, 2.5)` 朝向房间内部）

**组件清单：**
- `CharacterController` — 胶囊体碰撞（高 1.8m，半径 0.25）
- `BNG.BNGPlayerController` — BNG 框架主控制器
- `BNG.SmoothLocomotion` — 移动系统（速度 3 m/s）
- `EditorPlayerController` — 编辑器键鼠控制器（见下方）
- `Rigidbody (isKinematic=true)` — 防止被碰撞推出

**子节点结构：**
```
Player_KitchenTest          ← CharacterController / BNGPlayerController / EditorPlayerController
└── TrackingSpace
    ├── CameraRig            ← 旋转节点
    │   └── CenterEyeAnchor  ← Camera（FOV 90）
    ├── LeftHand
    └── RightHand
```

**键鼠操作（EditorPlayerController）：**

| 按键 | 操作 |
|------|------|
| `W/A/S/D` 或方向键 | 水平移动 |
| `Q` / `E` | 下降 / 上升 |
| 右键按住拖动 | 视角旋转（Yaw + Pitch）|
| `Space` | 小跳（0.8m）|

**标签设置（手动）：** 在 Inspector 中将 `Player_KitchenTest` 的 Tag 设置为 `Player`（`FinalExitTrigger` 依赖此 Tag 判断玩家进入）

**保存 Prefab（手动）：** 将场景内 `Player_KitchenTest` 拖拽到 `Assets/Package/VRAgent2.0-PVEO/` 目录下即可生成 Prefab 供其他场景复用。

---

## 场景美化说明

### 每个房间新增装饰元素

| 房间 | 新增内容 |
|------|---------|
| Room A 大厅 | 装饰柱 × 2、L 形接待台、等候沙发组、地毯、踢脚线、信息板、壁龛 |
| Room B 储藏间 | 三层金属货架（含立柱）、储物箱 × 3、工具挂架（5 挂钩）、操作台、垃圾桶 |
| Room C 厨房 | 下方橱柜组（西墙 + 北墙）、上方吊柜、中央岛台、抽油烟机 + 烟管、冰箱、调料架、水槽台面、切菜台底座 |
| Room D 终点 | 展示台（北墙）、等候椅 × 2、装饰植物 × 2、门口指示灯 × 2、踢脚线 |

### 材质方案（共 30+ 个材质）

| 分类 | 材质 |
|------|------|
| 墙面 | `Wall_Lobby`（米白暖色）/ `Wall_Pantry`（棕灰）/ `Wall_Kitchen`（冷瓷蓝白）/ `Wall_Exit`（淡绿）|
| 地板 | A=木地板、B=石材、C=白瓷砖、D=大理石 |
| 天花板 | 统一 `Ceiling_White` |
| 家具 | `Wood_Dark`（深色木）/ `Counter_Top`（台面米色）/ `Sofa_Gray` / `Shelf_Oak` |
| 金属 | `Metal_Stainless`（不锈钢高光）/ `Handle_Brass`（黄铜门把手）/ `Knife_Steel` |
| 状态 | 开关 ON/OFF、柜子 Locked/Unlocked、炉具 Off/Cooking/Done、门禁 NoPower/Unlocked |
