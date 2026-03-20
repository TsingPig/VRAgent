## 场景概览

**场景名称：** `MusicRoom`  
**场景路径：** `Assets/SampleScene/MusicRoom/MusicRoom.unity`  
**设计目标：** XR 音乐演奏交互场景，包含三种可发声乐器（钢琴、架子鼓、木琴）和节拍器，所有音频由 `SynthAudioGenerator` 在运行时数学合成，无需外部音频文件

---

## 新建/修改文件清单

### 脚本（`Assets/SampleScene/MusicRoom/`）

| 文件 | 职责 |
|------|------|
| `SynthAudioGenerator.cs` | 静态工具类，运行时生成 AudioClip（44100Hz 单声道）。支持正弦波+谐波 ADSR 钢琴音色、非谐泛音木琴音色、6 种打击乐音色（Kick/Snare/HiHat/Crash/TomHigh/TomLow） |
| `PianoKeyController.cs` | 单个琴键控制器。Awake 时根据 `NoteName` 枚举生成对应频率的钢琴音色 AudioClip，交互时播放音符并执行按键下沉动画 + 材质切换 |
| `DrumPadController.cs` | 单个鼓垫/镲片控制器。Awake 时根据 `DrumType` 生成打击乐 AudioClip，击打时播放声音并执行缩放反馈 + 材质闪烁 |
| `XylophoneBarController.cs` | 单个木琴琴键控制器。Awake 时生成明亮金属音色 AudioClip，敲击时播放并执行抖动旋转动画 + 材质闪烁 |
| `MetronomeController.cs` | 可开关节拍器，支持 4 档 BPM（60/90/120/150）。生成 1200Hz 短促点击音，带摆锤摆动动画和指示灯闪烁 |

### 材质（`Assets/Materials/`）

| 材质 | 用途 |
|------|------|
| `MR_Wall/Floor/Ceiling.mat` | 深色录音棚风格房间材质 |
| `Piano_Body.mat` | 钢琴琴身，高光黑色 |
| `Piano_WhiteIdle/WhitePressed.mat` | 白键空闲/按下 |
| `Piano_BlackIdle/BlackPressed.mat` | 黑键空闲/按下 |
| `Piano_Bench.mat` | 琴凳深色皮质 |
| `Drum_Shell.mat` | 鼓壳红色 |
| `Drum_HeadIdle/HeadHit.mat` | 鼓面空闲/击打（带 Emission） |
| `Drum_Cymbal/CymbalHit.mat` | 镲片金色/击打（带 Emission） |
| `Drum_Metal.mat` | 支架不锈钢 |
| `DrumStool.mat` | 鼓凳黑色 |
| `Xylo_Bar0..Bar7.mat` | 8 色彩虹琴键（红→紫，C5→C6） |
| `Xylo_Struck.mat` | 木琴敲击闪白（带 Emission） |
| `Xylo_Frame.mat` | 木琴框架木色 |
| `Metronome_Body.mat` | 节拍器胡桃木色 |
| `Metronome_DispOn/DispOff.mat` | 节拍器显示屏开/关 |
| `Amp_Body.mat` / `Speaker_Grille.mat` | 音箱装饰 |
| `MusicStand.mat` / `AcousticPanel.mat` | 谱架/吸音板 |
| `MR_Door.mat` | 房间门 |

---

## Hierarchy 结构

```
_Managers
_Environment
└── Directional Light                ← 方向光 intensity=0.4

Room_MusicRoom（10m × 8m × 3m 录音棚）
├── Floor / Ceiling / Walls(6面)     ← 全部 Static
├── Amp_Box / Amp_Speaker            ← 吉他音箱装饰（Static）
├── Speaker_L / Speaker_R            ← 落地监听音箱装饰（Static）
├── MusicStand_Pole / Tray           ← 谱架装饰（Static）
└── AcousticPanel_N0..N2             ← 北墙吸音板装饰（Static）

Zone_Piano（钢琴区域，北墙左侧）
├── Piano_Body / Lid / KeyTray       ← 琴体结构（Static）
├── Piano_Bench                      ← 琴凳（Static）
├── Key_C4 ~ Key_C5（8个白键）       ← PianoKeyController + AudioSource + XRSimpleInteractable
│                                       selectEntered → PlayNote()
│                                       selectExited → ReleaseKey()
└── Key_Cs4 / Ds4 / Fs4 / Gs4 / As4  ← 5个黑键，同上配置
    （共 13 个可演奏琴键）

Zone_Drums（架子鼓区域，东侧）
├── DrumKit_Frame / HiHat_Stand / Crash_Stand  ← 支架（Static）
├── DrumStool_Seat / Pole                       ← 鼓凳（Static）
├── Drum_Kick                        ← DrumPadController(Kick) + AudioSource + XRSimpleInteractable
├── Drum_Snare                       ← DrumPadController(Snare)
├── Drum_HiHat                       ← DrumPadController(HiHat)  ← 镲片
├── Drum_Crash                       ← DrumPadController(Crash)  ← 镲片
├── Drum_TomHigh                     ← DrumPadController(TomHigh)
└── Drum_TomLow                      ← DrumPadController(TomLow)
    （共 6 个可敲击鼓面，selectEntered → Hit()）

Zone_Xylophone（木琴区域，西侧）
├── Xylo_Frame_Top / 4 Legs          ← 琴架（Static）
└── XyloBar_0 ~ XyloBar_7           ← XylophoneBarController + AudioSource + XRSimpleInteractable
    （8 个彩虹琴键 C5→C6，selectEntered → Strike()）

Metronome_Unit（节拍器，放在钢琴盖上）
├── Metronome_Body / Arm / Display / TickLight
├── Button_MetronomeToggle           ← XRSimpleInteractable → MetronomeController.Toggle()
└── Button_MetronomeBPM              ← XRSimpleInteractable → MetronomeController.CycleBPM()

Zone_Switches
├── Switch_RoomLight                 ← MainLightSwitchController → Toggle()
└── DoorFrame_MusicRoom / Door

RoomLight_Ceiling                    ← Point Light intensity=2.5 range=14

Player_MusicRoom（玩家出生点，南墙入口处）
└── TrackingSpace
    ├── CameraRig
    │   └── CenterEyeAnchor         ← Camera (FOV 85)
    ├── LeftHand
    └── RightHand
```

---

## 音频合成技术细节

所有声音由 `SynthAudioGenerator` 在各控制器的 `Awake()` 中生成，保存为内存 `AudioClip`（`AudioClip.Create` + `SetData`）。

### 钢琴音色 — `CreatePianoTone()`
- **基频 + 3 个谐波**（2x, 3x, 4x），模拟真实钢琴泛音列
- **ADSR 包络**：Attack 10ms → Decay 150ms（衰减至 0.4）→ 渐衰 Sustain → Release（持续时长 50%）
- **音高范围**：C4 (261.63Hz) → C5 (523.25Hz)，完整一个八度含半音

### 架子鼓音色 — `CreateDrumSound()`
| 类型 | 合成方法 |
|------|---------|
| Kick | 150Hz→50Hz 频率扫描正弦波 + 指数衰减（模拟踩鼓音头下沉） |
| Snare | 185Hz 正弦波体 + 白噪声（响弦），双层独立衰减 |
| HiHat | 高频噪声 + 6000Hz 正弦波混合，极快衰减（35倍速） |
| Crash | 白噪声 + 4200Hz 微光泽，慢衰减 1.5s |
| TomHigh | 200Hz 基频 + 60Hz 音头扫描，中速衰减 |
| TomLow | 120Hz 基频 + 60Hz 音头扫描，慢衰减 |

### 木琴音色 — `CreateXylophoneTone()`
- **基频 + 非谐泛音**（3.0x, 6.27x），模拟金属/木质琴键的非整数泛音特征
- **快速指数衰减**（4.5 倍速），短促明亮
- **音高范围**：C5 (523.25Hz) → C6 (1046.50Hz)

---

## 交互元素汇总

| 交互对象 | 交互方式 | 触发方法 | 反馈 |
|---------|---------|---------|------|
| 钢琴白键 × 8 | XRSimpleInteractable | `PlayNote()` / `ReleaseKey()` | 音频 + 按键下沉 15mm + 材质变灰 |
| 钢琴黑键 × 5 | XRSimpleInteractable | `PlayNote()` / `ReleaseKey()` | 音频 + 按键下沉 15mm + 材质变亮 |
| 鼓面 × 4 | XRSimpleInteractable | `Hit()` | 音频 + 缩放至 92% + 材质 Emission 闪烁 (120ms) |
| 镲片 × 2 | XRSimpleInteractable | `Hit()` | 音频 + 缩放至 92% + 材质 Emission 闪烁 (120ms) |
| 木琴琴键 × 8 | XRSimpleInteractable | `Strike()` | 音频 + Z轴抖动旋转 + 材质闪白 |
| 节拍器开关 | XRSimpleInteractable | `Toggle()` | 节拍音 + 摆锤摆动 + 指示灯闪烁 |
| 节拍器 BPM | XRSimpleInteractable | `CycleBPM()` | 循环切换 60/90/120/150 BPM |
| 灯光开关 | XRSimpleInteractable | `Toggle()` | 开关房间主灯 + 材质切换 |

**XRTriggerable 配置：** 所有交互对象均挂载 `HenryLab.XRTriggerable`（`triggeringTime=0.1`，灯光开关为 `0.2`），供 EAT 框架自动触发。

---

## 可观测状态（供 VRAgent 使用）

各控制器均提供可读属性，Agent 可通过场景状态采集获取：

```csharp
// PianoKeyController — 检测琴键是否按下
bool PianoKeyController.IsPressed

// DrumPadController — 检测鼓垫是否处于击打反馈中
bool DrumPadController.IsHit

// XylophoneBarController — 检测琴键是否振动中
bool XylophoneBarController.IsVibrating

// MetronomeController — 检测节拍器状态
bool MetronomeController.IsRunning
int  MetronomeController.CurrentBPM
```

---

## 典型自动测试用例

| 测试ID | 名称 | 步骤 | 断言 |
|--------|------|------|------|
| MR01 | 弹奏钢琴 C 大调音阶 | 依次 selectEntered Key_C4→D4→E4→F4→G4→A4→B4→C5 | 每次 `IsPressed == true` + AudioSource.isPlaying |
| MR02 | 弹奏含半音的旋律 | 交替触发白键和黑键 | 所有 13 键均可独立发声 |
| MR03 | 鼓组全覆盖 | 依次 Hit 全部 6 个鼓面 | 每次 `IsHit == true` + 不同音色 |
| MR04 | 木琴音阶 | 依次 Strike XyloBar_0→7 | 音高递增 (C5→C6)，每次 `IsVibrating == true` |
| MR05 | 节拍器开关 | Toggle → 等 3s → Toggle | `IsRunning` 先 true 后 false |
| MR06 | 节拍器 BPM 切换 | CycleBPM × 4 | `CurrentBPM` 依次为 90→120→150→60 |
| MR07 | 灯光开关 | Toggle Switch_RoomLight | 房间灯从亮变暗（RoomLight_Ceiling.enabled 变化） |
| MR08 | 多乐器并行 | 同时触发钢琴+鼓+木琴 | 三个 AudioSource 同时播放无冲突 |

---

## Player（测试用）

**场景内 GameObject：** `Player_MusicRoom`（南墙入口处，位置 `(0, 0, 2.5)` 朝向房间内部）

**组件清单：**
- `CharacterController` — 胶囊体碰撞（高 1.8m，半径 0.25）
- `EditorPlayerController` — 编辑器键鼠控制器

**子节点结构：**
```
Player_MusicRoom        ← CharacterController / EditorPlayerController
└── TrackingSpace
    ├── CameraRig        ← 旋转节点
    │   └── CenterEyeAnchor  ← Camera（FOV 85）
    ├── LeftHand
    └── RightHand
```

---

## 场景布局说明

房间尺寸 10m × 8m × 3m，录音棚风格（深色墙壁、木地板、吸音板）。

| 区域 | 位置 | 内容 |
|------|------|------|
| 钢琴区（北墙左侧） | (-1.5, 0, -3.5) | 立式钢琴 + 琴凳 + 节拍器 |
| 架子鼓区（东侧） | (3, 0, -2.5) | 5鼓1镲(+1镲)套鼓 + 鼓凳 |
| 木琴区（西侧） | (-3.5, 0, 0.5) | 8键彩虹木琴 + 琴架 |
| 音箱/装饰 | 各墙壁 | 吉他音箱、落地音箱、谱架、3块吸音板 |
| 入口 | 南墙 (0.6, 1, 3.9) | 门框 + 门 + 灯光开关 |
