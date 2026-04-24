# Bezi Scene Generation Prompts — VRAgent MiniGames Benchmark

> **Target tool**: [Bezi](https://www.bezi.com/) (AI-native 3D design for Unity)
> **Goal**: Generate the visual / spatial / lighting content of 7 VR mini-game test scenes.
> **Note**: All gameplay logic, controllers, oracle bugs, and FileID hookups are already implemented as MonoBehaviours in `<Scene>Controllers.cs`. Bezi only needs to create the **visual GameObjects + transforms + materials + lighting**. After Bezi finishes, run `Tools/MiniGame <Name>/Build Scene` in Unity to attach controllers to the matching named GameObjects.
>
> **CRITICAL — Naming Contract**: Every GameObject name listed under `Hierarchy (must-match names)` is a hard requirement. The Editor SceneBuilder script looks up objects **by exact name** under a single root (`<Scene>_Root`) and attaches the corresponding controller component. If a name does not match, the auto-builder will create a duplicate empty GameObject and components will not bind to your visuals.

---

## 0. Global Conventions (apply to all 7 scenes)

- **Scale**: 1 Unity unit = 1 meter. Player standing position ≈ origin (0, 1.7, 0).
- **Root**: each scene has exactly one root empty GameObject named `<Scene>_Root` at world origin.
- **Camera + Light**: every `.unity` already has `Main Camera` and `Directional Light`. Do NOT duplicate them.
- **VR Player Rig**: place a placeholder `PlayerHand` empty GameObject (used as grab destination) at (0, 1.2, 0.3). No actual XR rig needed for benchmarking.
- **Materials**: PBR materials. Prefer flat untextured single-color materials with Smoothness 0.3, Metallic 0 unless noted.
- **Colliders**: every interactable visual should have a matching primitive collider (Box / Sphere / Capsule).
- **Rigidbodies**: any object the player will grab needs `Rigidbody { useGravity=false, isKinematic=true }`.
- **Audio**: do NOT add `AudioSource` to any object whose name appears in the bug list as "no AudioSource" (these are intentional NRE bugs — see per-scene "Forbidden components").
- **Tags / Layers**: leave as Default unless specified.

---

## 1. MiniGame_ShootingRange

**Theme**: indoor FPS gun range with paper targets and a control panel.
**Mood**: bright, neutral concrete walls, fluorescent ceiling lights.
**Footprint**: ~12 m × 8 m room.

### Hierarchy (must-match names)
```
ShootingRange_Root
├── PlayerHand                  (empty, placeholder)
├── StateController             (empty cube anchor at origin)
├── ScoreManager                (empty)
├── WaveSpawner                 (empty, in front of targets row)
├── Weapon_Pistol               (small pistol model, BoxCollider, Rigidbody iskinematic)
├── Weapon_Rifle                (rifle model, same)
├── AmmoMagazine_00 .. _02      (3 magazine cuboids on a side table, BoxCollider, Rigidbody)
├── Target_00 .. _04            (5 paper-target quads on stands at z=+6, x = -4 .. +4)
├── MuzzleFlash                 (empty + small quad child "FlashQuad" disabled)
└── ControlPanel                (wall panel with emissive screen)
```

### Visual layout
- Floor: 12×8 dark grey concrete.
- Back wall (z=+8): white drywall with 5 numbered lanes painted in red.
- Side table at (-3, 0.9, -1) holding 3 magazines.
- Targets are 1.2 m tall flat boards, z=+6, evenly spaced.
- ControlPanel on left wall (-6, 1.5, 0), facing +X. A child quad "Screen" with emissive cyan material.

### Forbidden components (preserve bugs)
- `Weapon_Pistol` and `Weapon_Rifle`: **no AudioSource** (BUG-001).
- `MuzzleFlash`: child `FlashQuad` must start **disabled** (BUG-008).

---

## 2. MiniGame_RhythmBeat

**Theme**: Beat-Saber-style stage. Dark room with neon block lanes.
**Mood**: dark/black floor, vibrant cyan + magenta neon, volumetric haze.
**Footprint**: ~6 m × 8 m.

### Hierarchy (must-match names)
```
RhythmBeat_Root
├── PlayerHand
├── StateController
├── SongController
├── DifficultySelector          (panel with 3 buttons child quads: Easy / Normal / Hard)
├── ScoreBoard                  (wall panel emissive)
├── ComboCounter                (floating TMP-style quad above ScoreBoard)
├── BeatSaberWeapon_L           (cyan saber, Rigidbody iskinematic, BoxCollider long)
├── BeatSaberWeapon_R           (magenta saber, same)
├── BeatBlock_00 .. _09         (10 cubes on a 2-lane track moving toward player; layout z = 3..12)
└── StageLights                 (empty parent of 4 spot Light children, colored cyan/magenta)
```

### Visual layout
- Floor: black with two glowing lanes (cyan strip x=-0.5 width 0.6, magenta strip x=+0.5 width 0.6) running z=0..12.
- BeatBlocks are 0.4 m cubes; alternate cyan/magenta materials matching the lane.
- DifficultySelector at (-1.5, 1.4, 1.5) tilted toward player.
- ScoreBoard at (0, 2.4, -1) on back wall.

### Forbidden components
- `BeatSaberWeapon_L/R`: **no AudioSource** (BUG-001).

---

## 3. MiniGame_EscapeRoom

**Theme**: dim Victorian study. Wood + brass + warm low-key lighting.
**Footprint**: ~5 m × 5 m square room with one exit door.

### Hierarchy (must-match names)
```
EscapeRoom_Root
├── PlayerHand
├── StateController
├── CombinationLock             (wall-mounted dial panel, 3 numbered rings as child quads)
├── KeySafe                     (small wall safe, hinged door child "SafeDoor")
├── Key                         (brass key prop, BoxCollider, Rigidbody iskinematic)
├── ExitDoor                    (large wood door at +Z wall, hinged child "DoorPanel")
├── HintLight                   (Point Light child "Bulb" disabled)
├── PuzzlePanel                 (book on desk with glyph child quads)
└── Furniture                   (parent: Desk, Bookshelf, Armchair, Rug — pure decoration)
```

### Visual layout
- Walls: dark wood paneling. Floor: parquet. Single ceiling chandelier (warm 2700K).
- Desk at (1.2, 0, 1) facing -Z. PuzzlePanel sits on desk surface.
- Bookshelf on -X wall. KeySafe embedded on +X wall at 1.4 m height.
- ExitDoor at +Z wall, 2.1 m tall.
- HintLight sphere bulb prop hangs above desk, child "Bulb" Point Light starts disabled.

### Forbidden components
- `CombinationLock`: **no AudioSource** (BUG-001).

---

## 4. MiniGame_BowlingSports

**Theme**: classic bowling alley lane.
**Footprint**: ~3 m × 12 m lane plus 4 m approach area.

### Hierarchy (must-match names)
```
Bowling_Root
├── PlayerHand
├── StateController
├── Scoreboard                  (LED wall panel at end of lane behind pins)
├── Lane                        (long flat rectangle, lacquered wood material)
├── BowlingBall                 (sphere, Rigidbody iskinematic, SphereCollider, glossy black)
├── Pin_00 .. _09               (10 white pins arranged in classic triangle at z=+5..+8)
└── PinResetLight               (overhead lamp; child "Bulb" emissive material disabled)
```

### Visual layout
- Lane: 1 m wide, 10 m long, glossy varnished wood. Gutters on both sides (slightly recessed).
- BowlingBall at (0, 0.5, -3) — approach area side.
- Pins arranged classic 1-2-3-4 triangle at z = +5..+8, x spacing 0.4 m.
- Scoreboard at (0, 3, +9), large flat panel with emissive numeric area.
- PinResetLight hangs at (0, 3.5, +6.5).

### Forbidden components
- `BowlingBall`: **no AudioSource** (BUG-001).
- `PinResetLight` child `Bulb`: starts disabled (BUG-008).

---

## 5. MiniGame_HorrorSurvival

**Theme**: abandoned hospital corridor. Dark, fog, flickering lights.
**Mood**: very low ambient, single flashlight cone is primary light source. Sickly green tint.
**Footprint**: ~8 m × 12 m L-shaped corridor.

### Hierarchy (must-match names)
```
Horror_Root
├── PlayerHand
├── StateController
├── Flashlight                  (handheld torch prop, BoxCollider, Rigidbody iskinematic)
│   └── LightCone               (Spot Light child, disabled)
├── Battery                     (small AA battery prop, BoxCollider, Rigidbody iskinematic)
├── ExitDoor                    (rusted metal door with chain/lock prop)
├── EnemyAI                     (humanoid silhouette at end of corridor, BoxCollider)
├── HealthSystem                (empty anchor for HUD)
│   └── RedOverlay              (full-screen red quad child, disabled)
└── Key_00 .. _02               (3 keys on tables/floors at different positions)
```

### Visual layout
- Walls: peeling paint texture, off-white. Floor: cracked tiles.
- Hospital props: gurneys, IV stands, tipped wheelchair (decoration only — name them `Decor_*`).
- Lighting: 1 ceiling fluorescent flickering at end of corridor; everywhere else dark.
- Battery placed on a gurney at (-2, 0.9, 2). Keys distributed across the corridor at z=2, 5, 9.
- ExitDoor at far end (z=+11).
- EnemyAI placeholder: tall thin black capsule at (0, 1, +9), facing player.

### Forbidden components
- `Flashlight`: **no AudioSource** (BUG-001).
- `Flashlight/LightCone`: starts disabled (BUG-008-equivalent visual).
- `HealthSystem/RedOverlay`: starts disabled.

---

## 6. MiniGame_SandboxBuilder

**Theme**: Minecraft-style creative voxel build space. Grass plain with grid floor.
**Footprint**: ~16 m × 16 m open area.

### Hierarchy (must-match names)
```
Sandbox_Root
├── PlayerHand
├── StateController
├── BlockPlacer                 (handheld tool prop, BoxCollider, Rigidbody iskinematic)
├── Block_00 .. _05             (6 voxel cubes 1×1×1, varied colors: stone/wood/glass/grass/brick/sand)
├── Toolbox                     (wall hotbar with 6 slot child quads)
├── SaveLoad                    (terminal panel with emissive screen child "Screen")
└── HighlightOutline            (yellow wireframe cube)
    └── OutlineMesh             (child mesh, disabled)
```

### Visual layout
- Floor: 16×16 grass-textured plane WITH a faint white grid line every 1 m (use a tiled grid material).
- Skybox: bright sunny day.
- Blocks lined up on a workbench at (0, 0.5, 0) with 1.1 m spacing.
- Toolbox panel mounted on a small kiosk at (-3, 1.2, 0).
- SaveLoad terminal at (+3, 1.2, 0).
- HighlightOutline placed slightly above one block to preview placement.

### Forbidden components
- `BlockPlacer`: **no AudioSource** (BUG-001).
- `HighlightOutline/OutlineMesh`: starts disabled (BUG-008).

---

## 7. MiniGame_TowerDefense

**Theme**: top-down style tower defense map (player stands on a balcony overlooking).
**Footprint**: ~12 m × 12 m grid map + balcony at -Z.

### Hierarchy (must-match names)
```
TowerDefense_Root
├── PlayerHand
├── StateController
├── ResourceManager             (gold counter UI panel on balcony rail)
├── TowerPlacer                 (handheld tool, BoxCollider, Rigidbody iskinematic)
├── Tower_00 .. _03             (4 tower cylinders+cone tops on grid slots, BoxCollider)
├── WaveSpawner                 (gate prop at far end of map, +Z)
└── Enemy_00 .. _02             (3 small humanoid/goblin capsules walking path)
    └── (each) RedHP            (small red bar child quad, disabled)
```

### Visual layout
- Map: 12×12 grass+stone path winding from gate (+Z) to player base (-Z).
- Visible grid of 1×1 tower slots beside the path.
- Towers are 0.6 m radius cylinder bases with cone tops (~1.5 m tall total). Mix gray-stone and brown-wood.
- WaveSpawner: stone gateway prop at (0, 0, +6).
- Enemies: 0.6 m capsules with green tint at the start of the path (z = +5).
- Balcony rail: low wall at z = -5 with ResourceManager panel mounted on it.

### Forbidden components
- `TowerPlacer`: **no AudioSource** (BUG-001).
- All `Enemy_*/RedHP` children: start disabled (BUG-008).

---

## Workflow After Bezi Generates

For each scene:

1. **Open `MiniGame_<Name>.unity` in Unity**.
2. Verify Bezi created a single root `<Scene>_Root` with the exact named children listed above. Rename any drift.
3. Run the menu item:
   - `Tools/MiniGame ShootingRange/Build Scene`
   - `Tools/MiniGame RhythmBeat/Build Scene`
   - `Tools/MiniGame EscapeRoom/Build Scene`
   - `Tools/MiniGame BowlingSports/Build Scene`
   - `Tools/MiniGame HorrorSurvival/Build Scene`
   - `Tools/MiniGame SandboxBuilder/Build Scene`
   - `Tools/MiniGame TowerDefense/Build Scene`

   The script is **idempotent**: it walks the existing hierarchy, attaches the correct controller MonoBehaviour to each named GameObject, and only creates an empty if a required name is missing.
4. `File → Save`.
5. Validate by running the gold-standard test plan:
   - `Tools/VR Explorer/Import Test Plan` → select `MiniGame_<Name>/gold_standard_test_plan.json`.
   - Replace `FILEID_*` and `SCRIPT_*` placeholders via the importer's selector, then Run.
6. Console search `[ORACLE:BUG-` should show all 10 bugs triggered per scene.

---

## Single-Sentence Summary Prompt for Bezi

> "Generate 7 small Unity VR test scenes (Shooting Range, Beat Saber rhythm stage, Victorian escape room, classic bowling alley, abandoned-hospital horror corridor, Minecraft-style voxel sandbox, tower defense balcony view). Each scene has exactly one root GameObject `<Scene>_Root` at the world origin and uses the precise child object names listed in the per-scene tables. Add primitive colliders and kinematic rigidbodies to interactable props. Do NOT add AudioSources to any prop named in the 'Forbidden components' list — these omissions are intentional and required by the test oracle. Materials should be PBR with simple flat colors. No XR Rig, no audio clips, no scripts — those are auto-attached by an Editor menu item after generation."
