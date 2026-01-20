# Changelog


## [1.8.12] - 2025-12-11
### Updated
- NavMeshPointChecker editor tool
- Refactor FileIdManager to FileIDContainer and add ParameterResolver

## [1.8.6] - 2025-10-22

### Updated 

- **Restructured VRAgent** design to remove dependency on static Mono layer script bindings
- Optimize codes and files structure

### Feature

- MoveAction Path Checking
- VRAgent fileID debug logs
- ***[Star]*** **support binding methods with return values to UnityEvent**
- ***[Star]*** **support cross-assembly method invocation failures in third-party components**

### Fixed

- Grab target ObjectB catching bugs

- Task Action Execution Broken bug

-  VRAgent GameObject FileID missing Log & Runtime component got method; 

    

### Updated

-  rename VRAgent to XRAgent; Colorful Task Debug



## [1.7.4] - 2025-09-12

### Added

- JSON scripts (ActionUnitConverter, ActionDef, TaskDef for optimize structure of JSON format in test plan)
- TagInitializer for tag the object that instantiated for temporary usage
- TriggerActionUnit for Test Plan
- `sampleScene3` for testing

### Updated

- Optimized **Test Plan documentation** for clearer usage and structure
- Optimize XRTriggerable by inheriting from XRTransformable
- Adding Check if-else in XRGrabbable OnGrabbed(); 
- Replace EditorPrefabs with PlayPrefabs for stroing TestPlanPath

### Feature

- supported `target_position ` for GrabActionUnit, `triggerring_time` for TriggerActionUnit
- **Trigger Action/ Transform Action** supported initailly in Test Plan Json;  (supporting Event List)
- GetObjectFileID supporting Object parameter 

### Fixed 

- prefab can't be identified when it is on the top-level of the scene
- XRTriggerable: Triggered Events Execution problem
- Test Plan path selection issue;
- Remove add XRGrabinteractable in XRBase Start();

## [1.6.6] - 2025-08-22

### Added
- **VREscaper** prefab.
- Interaction Counter for tracking different types of interactions in dataset projects.
- **VREscaper** feature set:
  - Support for importing JSON (.json) format Test Plans and automated test execution.  
  - FileID-based GameObject Finding System (`FileIdResolver.cs` & `TestPlanImporterWindow.cs`).

### Changed
- Added configurable `autonomousEventInterval` parameter (with Inspector slider) to control autonomous event execution delay; Adding `ResetExploration()` in `BaseExplorer` allows repeatable task executaion

### Fixed
- FileID consistency for prefab instance GameObjects across scenes.
- Correct VREscaper prefab path.
- Removed random movement behavior from `BaseTask`.



## [1.5.6] - 2025-06-18

### Fixed

- GameObjectConfigManager prefab import & export logic

### Added
- Support for exporting GameObjects with scripts under the `VRExplorer` namespace only.
- Stable identifier logic using `GlobalObjectId` (scene objects) & AssetDatabase GUID(prefabs).

- `RemoveVRExplorerScripts()` for remove all the added VRExplorer Mono predefined scripts.

