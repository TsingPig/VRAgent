## 场景概览

**场景名称：** `Home_TwoRooms`  
**场景路径：** `Assets/SampleScene/Home_TwoRooms/Home_TwoRooms.unity`  
**设计目标：** 双房间门控 XR 交互场景，覆盖钥匙解锁、抓取、灯光开关、抽屉搜索等基础家居交互，适合 VRAgent 导航与物体操作的基准测试

---

## 新建/修改文件清单

### 脚本（`Assets/SampleScene/Home_TwoRooms/`）

| 文件 | 职责 |
|------|------|
| `DoorController.cs` | 门旋转动画控制器，支持锁定/解锁状态。`Unlock()` 后 `Toggle()` 才可开关门 |
| `KeyUnlockReceiver.cs` | 挂载于 `XRSocketInteractor`，物品插入时调用 `DoorController.Unlock()` + 更新插座指示材质 |
| `DrawerController.cs` | 抽屉沿 -Z 轴滑动开关，`Toggle()` 切换开合状态 |
| `LightSwitchController.cs` | 灯光开关，`Toggle()` 切换目标 `Light.enabled` + 开关材质 |

---

## Hierarchy 结构

```
Directional Light

VRAgent（旧版 Agent，activeSelf=false）
├── Camera / LeftControllerAnchor / ...

VRAgent2.0-PVEO（当前使用的 Agent，Tag=Player）
├── Camera
├── LeftControllerAnchor
│   └── LeftController / ModelsLeft / Grabber / ...
└── ...
    位置: (-4.48, 0.94, 1.96)  朝向: Y=89.86°

Room1（左侧房间）
├── Floor / Ceiling
├── WallWest / WallNorth / WallSouth
├── Room1Light                       ← Point Light
├── Table_Room1（桌子）
│   ├── TableTop
│   └── TableLeg × 4
├── Key                              ← XRGrabbable + Rigidbody + CapsuleCollider
│   位置: (-5.5, 0.92, -2)             放在桌子上
├── GrabbableBox_Room1               ← XRGrabbable + Rigidbody
│   位置: (-5, 0.25, 0)
├── Bookshelf                        ← 4层书架 + 3本装饰书
│   ├── Back / Shelf_0..3
│   └── Book1 / Book2 / Book3
└── LightSwitch_Room1                ← LightSwitchController + XRSimpleInteractable
    位置: (-6.5, 1.4, 3.88)

SharedWall（两房间共享隔墙，含门洞）
├── WallLeft / WallRight / WallTop
├── DoorFrameLeft / DoorFrameRight / DoorFrameTop

DoorPivot                            ← DoorController (startLocked=true) + Rigidbody
├── DoorPanel                        ← BoxCollider + NavMeshObstacle
│   └── DoorHandle               ← XRSimpleInteractable → DoorController.Toggle()

KeySocket                            ← XRSocketInteractor + KeyUnlockReceiver
├── SocketIndicator                  ← 视觉指示（插入后变色）
└── SocketBase
    位置: (-0.3, 1.15, -0.9)         门旁插座

Room2（右侧房间）
├── Floor / Ceiling
├── WallEast / WallNorth / WallSouth
├── Room2Light                       ← Point Light
├── Table_Room2（桌子）
│   ├── TableTop
│   └── TableLeg × 4
├── MagicOrb                         ← XRGrabbable + Rigidbody
│   位置: (5.5, 0.93, -2)              放在桌子上
├── GrabbableBox_Room2               ← XRGrabbable + Rigidbody
│   位置: (5, 0.25, 0)
├── Cabinet（柜子）
│   ├── CabinetBody
│   ├── Drawer                       ← DrawerController + XRSimpleInteractable
│   ├── DrawerHandle
│   └── HiddenGem                    ← XRGrabbable + Rigidbody（抽屉内隐藏宝石）
└── LightSwitch_Room2                ← LightSwitchController + XRSimpleInteractable
    位置: (7.88, 1.4, 1)

CelestialTotem                       ← 大型装饰图腾
├── BaseStep1..3 / Columns / Arch / Spires / Rings ...
    位置: (-3, 0, 1)

XR Interaction Manager               ← XR 交互系统管理器
XR Origin                            ← XR Origin (备用)
├── Camera Offset / Main Camera / LeftHand / RightHand

FileIdManager                        ← 文件ID管理
HenryLab.EntityManager (Singleton)   ← EAT 框架实体管理器
```

---

## 交互依赖关系（门控链）

```
[Room1] 抓取 Key（桌上钥匙）
         └→ 移动到 KeySocket 并插入
              └→ KeyUnlockReceiver 触发
                   └→ DoorController.Unlock()
                        └→ DoorPivot 解锁，可通过 DoorHandle Toggle()
                             └→ 门打开 → 玩家进入 Room2

[Room1] Toggle LightSwitch_Room1
         └→ Room1Light 开/关

[Room2] Toggle LightSwitch_Room2
         └→ Room2Light 开/关

[Room2] 拉开 Cabinet/Drawer（DrawerController.Toggle）
         └→ 发现 HiddenGem（可抓取宝石）

[Room2] 抓取 MagicOrb（桌上魔法球）
         └→ 自由操作
```

---

## 交互元素汇总

| 交互对象 | 组件 | 交互方式 | 效果 |
|---------|------|---------|------|
| Key（钥匙） | XRGrabbable + Rigidbody | 抓取 + 放入 Socket | 解锁房门 |
| KeySocket（钥匙插座） | XRSocketInteractor + KeyUnlockReceiver | 接收钥匙 | 调用 DoorController.Unlock() |
| DoorHandle（门把手） | XRSimpleInteractable | selectEntered | DoorController.Toggle()（需先解锁） |
| LightSwitch_Room1 | XRSimpleInteractable + LightSwitchController | selectEntered | 切换 Room1Light |
| LightSwitch_Room2 | XRSimpleInteractable + LightSwitchController | selectEntered | 切换 Room2Light |
| Drawer（抽屉） | XRSimpleInteractable + DrawerController | selectEntered | 沿 -Z 滑出 0.42m |
| GrabbableBox_Room1 | XRGrabbable + Rigidbody | 抓取 | 自由物理交互 |
| GrabbableBox_Room2 | XRGrabbable + Rigidbody | 抓取 | 自由物理交互 |
| MagicOrb（魔法球） | XRGrabbable + Rigidbody | 抓取 | 自由物理交互 |
| HiddenGem（隐藏宝石） | XRGrabbable + Rigidbody | 抓取 | 抽屉内隐藏物品 |

---

## 可观测状态（供 VRAgent 使用）

```csharp
// DoorController — 门锁/开关状态
bool DoorController.IsLocked     // true=锁定中，false=已解锁

// DrawerController — 通过日志观测
// Log: "[Drawer] Drawer → OPEN" / "[Drawer] Drawer → CLOSED"

// LightSwitchController — 通过日志观测
// Log: "[LightSwitch] LightSwitch_Room1 → ON/OFF"

// KeyUnlockReceiver — 通过日志观测
// Log: "[KeyUnlockReceiver] Item inserted — door unlocked!"
```

---

## 典型自动测试用例

| 测试ID | 名称 | 步骤 | 断言 |
|--------|------|------|------|
| HT01 | HappyPath：钥匙解锁开门 | 抓 Key → 插入 KeySocket → Toggle DoorHandle | 门打开（DoorController.IsLocked == false） |
| HT02 | 锁门状态下尝试开门 | 直接 Toggle DoorHandle | 门保持关闭（IsLocked == true） |
| HT03 | Room1 灯光开关 | Toggle LightSwitch_Room1 × 2 | Room1Light.enabled 先 false 后 true |
| HT04 | Room2 灯光开关 | Toggle LightSwitch_Room2 | Room2Light.enabled 变化 |
| HT05 | 抽屉发现宝石 | Toggle Drawer → 抓取 HiddenGem | Drawer 打开 + HiddenGem 可 Grab |
| HT06 | 跨房间物品搬运 | 抓 MagicOrb → 穿过门 → 放到 Room1 桌上 | MagicOrb 位置从 Room2 区域到 Room1 区域 |
| HT07 | 多物体抓取测试 | 依次抓取 Box1、Box2、MagicOrb、HiddenGem | 4 个物体均可独立 Grab/Release |
| HT08 | 导航路径测试 | Agent 从 Room1 导航到 Room2 | 需先解锁门，NavMesh 路径通畅 |

---

## Agent 配置

**当前使用的 Agent：** `VRAgent2.0-PVEO`（`activeSelf=true`，Tag=`Player`）  
**旧版 Agent：** `VRAgent`（`activeSelf=false`，已禁用）

**VRAgent2.0-PVEO 组件清单：**
- `NavMeshAgent` — 导航代理
- `CapsuleCollider` + `BoxCollider` — 碰撞体
- `AudioListener` — 音频监听
- `HenryLab.VRAgent.Online.AgentBridge` — Agent 桥接层
- `HenryLab.VRAgent.Online.VRAgentOnline` — 在线 Agent 主控制器
- `HenryLab.VRAgent.Online.StateCollector` — 场景状态采集器

**出生位置：** `(-4.48, 0.94, 1.96)` 朝向 `Y=89.86°`（Room1 中央偏北，面朝东）

---

## 场景布局说明

两个房间通过共享隔墙连接，中间有一扇需钥匙解锁的门。

| 区域 | 范围 | 关键物品 |
|------|------|---------|
| Room1（左侧） | 西墙 x≈-7, 北墙 z≈-4, 南墙 z≈4 | 桌子+钥匙、书架、可抓箱子、灯光开关、天体图腾 |
| 隔墙 + 门 | x≈0 附近 | SharedWall（门洞）、DoorPivot（锁定门）、KeySocket（钥匙插座） |
| Room2（右侧） | 东墙 x≈8, 北墙 z≈-4, 南墙 z≈4 | 桌子+魔法球、柜子(抽屉+宝石)、可抓箱子、灯光开关 |

**NavMesh：** 已烘焙（`Home_TwoRooms/NavMesh.asset`），Agent 可在两房间间导航（门打开后）。
