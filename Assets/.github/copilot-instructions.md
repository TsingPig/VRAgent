# VRAgent Unity Package Development Guide

## Architecture Overview

VRAgent is a Unity package for automated VR testing that transforms JSON test plans into executable VR interactions. The system uses:

- **FileID-based object resolution** for stable scene references across Unity sessions
- **Dynamic component attachment** (XRGrabbable, XRTriggerable, XRTransformable) at runtime
- **LLM-generated test plans** imported as JSON and executed sequentially

### Core Components

- `VRAgent.cs` - Main test executor, inherits from `BaseExplorer` (VRExplorer framework)
- `FileIdManager.cs` - Runtime mapping between FileIDs and GameObjects/MonoBehaviours
- `FileIdResolver.cs` - Static utilities for FileID/GUID resolution and UnityEvent creation
- `JSON/` - Action/Task definitions with Newtonsoft.Json polymorphic deserialization

## Key Patterns

### FileID Resolution System
```csharp
// Always use FileIdManager for runtime lookups, not direct resolution
var manager = Object.FindAnyObjectByType<FileIdManager>();
GameObject obj = manager.GetObject(fileId);
MonoBehaviour component = manager.GetComponent(scriptFileId);
```

FileIDs are extracted from Unity's `GlobalObjectId` with different parsing for prefab instances vs scene objects.

### Test Plan Structure
JSON test plans contain `taskUnits` → `actionUnits` with three action types:
- **Grab**: Move objects to positions or other objects (`GrabActionUnit`)
- **Trigger**: Execute UnityEvents with timing (`TriggerActionUnit`) 
- **Transform**: Apply position/rotation/scale deltas (`TransformActionUnit`)

### Dynamic Component Management
Components are added at test execution time, not design time:
```csharp
// Pattern: Add component → Configure → Generate BaseAction tasks
XRGrabbable grabbable = objA.AddComponent<XRGrabbable>();
grabbable.destination = targetTransform;
task.AddRange(GrabTask(grabbable)); // Returns BaseAction sequence
```

### UnityEvent Serialization for Methods with Return Values
The system automatically wraps non-void methods using `SerializableMethodWrapper` components to maintain Inspector serialization. When `CreateUnityEvent()` encounters methods with return values, it:
1. Adds a `SerializableMethodWrapper` to the target GameObject
2. Configures the wrapper with target component and method name
3. Binds the wrapper's `InvokeWrappedMethod()` to the UnityEvent

## Development Workflows

### Test Plan Import/Export
1. **Tools → VR Explorer → Import Test Plan** - Main entry point
2. **FileID Discovery**: Use `TestPlanImporterWindow` to select objects and copy FileIDs to clipboard
3. **Validation**: Check that `FileIdManager` exists in scene and all referenced objects resolve correctly

### Editor-Only Features
All core resolution logic is wrapped in `#if UNITY_EDITOR` - this system only works in editor mode for test authoring.

### Component Lifecycle
- **Import**: Dynamically attach XR components based on test plan
- **Execute**: Run sequential tasks with async/await pattern  
- **Cleanup**: `RemoveTestPlan()` strips all added components and temp objects

## Critical Dependencies

- **Unity XR Interaction Toolkit 2.0.4+** for XRGrabbable/XRTriggerable base classes
- **Newtonsoft.Json** for polymorphic ActionUnit deserialization
- **HenryLab.VRExplorer** base framework (external dependency)

## Anti-Patterns to Avoid

- Never use `FindComponentByFileID()` directly - always go through `FileIdManager`
- Don't manually add XR components at design time - they're managed by the test execution system
- Avoid hardcoded object references - use FileID strings for cross-session stability
- Don't call Unity's `Object.FindObjectOfType()` in performance-critical paths - cache in FileIdManager

## Debugging Tools

- **Rich Text Logging**: Use `new RichText().Add(text, color, bold)` for structured debug output  
- **Test Metrics**: `TestPlanCounter` tracks object resolution success rates
- **Inspector Validation**: FileIdManager shows live object/component mappings in Inspector