using System.Collections.Generic;
using UnityEngine;

// =============================================================================
// MiniGame_SandboxBuilder — All controllers (10 injected bugs)
// 8-step flow: PowerOn → ToolSelected → BlockGrabbed → BlockPlaced →
//   BlockRotated → StructureValidated → SavedLocally → Published → GameComplete
// =============================================================================

public class SandboxStateController : MonoBehaviour
{
    public static SandboxStateController Instance;
    public bool PowerOn, ToolSelected, BlockGrabbed, BlockPlaced, BlockRotated, StructureValidated, SavedLocally, Published, GameComplete;
    public int  BlocksPlaced;
    public int  MinBlocksToPublish = 5;

    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SetPowerOn(bool v)         { PowerOn = v;       SandboxOracleRegistry.StateAssert("Power", $"PowerOn={v}"); }
    public void SetToolSelected(bool v)    { ToolSelected = v; }
    public void SetBlockGrabbed(bool v)    { BlockGrabbed = v; }
    public void RegisterBlockPlaced()      { BlocksPlaced++; BlockPlaced = true; SandboxOracleRegistry.StateAssert("Build", $"Blocks={BlocksPlaced}"); }
    public void SetBlockRotated(bool v)    { BlockRotated = v; }
    public void SetStructureValidated(bool v){ StructureValidated = v; }
    public void SetSavedLocally(bool v)    { SavedLocally = v; }

    public void TryPublish()
    {
        // BUG-006: skips MinBlocksToPublish check.
        SandboxOracleRegistry.Check("BUG-006",
            BlocksPlaced < MinBlocksToPublish,
            $"Published with only {BlocksPlaced}/{MinBlocksToPublish} blocks");
        Published = true;
        GameComplete = true;
    }

    public void ResetAllState()
    {
        PowerOn = ToolSelected = BlockGrabbed = BlockPlaced = BlockRotated = StructureValidated = SavedLocally = Published = GameComplete = false;
        BlocksPlaced = 0;
        // BUG-010: doesn't clear placed BuildingBlock instances or SaveLoad data.
        SandboxOracleRegistry.Check("BUG-010",
            SaveLoadController.Instance != null && !string.IsNullOrEmpty(SaveLoadController.Instance.LastSavedLevelName),
            "ResetAllState left SaveLoad data");
    }
}

/// <summary>Block placer (the player's tool). Hosts BUG-001 (NRE) and BUG-009 (place before grid validation).</summary>
public class BlockPlacer : MonoBehaviour
{
    public BuildingBlock pendingBlock;
    public bool gridValidationPassed = false;

    public void PlaceBlock()
    {
        // BUG-009: registers block placement BEFORE checking gridValidationPassed.
        SandboxStateController.Instance?.RegisterBlockPlaced();
        if (!gridValidationPassed)
        {
            SandboxOracleRegistry.Trigger("BUG-009",
                "Block placed before validating grid alignment");
        }

        // BUG-001: NRE — no AudioSource on placer.
        GetComponent<AudioSource>().Play();
    }
}

/// <summary>BuildingBlock. Hosts BUG-002 (stack accepted with no support) and BUG-005 (rotate wrong axis).</summary>
public class BuildingBlock : MonoBehaviour
{
    public BuildingBlock blockBelow;
    public bool IsPlaced { get; private set; }

    public void StackOn(BuildingBlock below)
    {
        // BUG-002: skips below != null check.
        SandboxOracleRegistry.Check("BUG-002",
            below == null,
            "BuildingBlock stacked with no support below");
        blockBelow = below;
        IsPlaced = true;
    }

    public void StackWithoutSupport() => StackOn(null);

    public void Rotate90()
    {
        SandboxStateController.Instance?.SetBlockRotated(true);
        // BUG-005: rotates around X (lays block sideways) instead of Y.
        // CORRECT: transform.Rotate(0, 90, 0);
        transform.Rotate(90, 0, 0);
        SandboxOracleRegistry.Check("BUG-005", true, "Block rotated around X axis (lays sideways)");
    }
}

/// <summary>Toolbox / hotbar. Hosts BUG-003 (deselect no reset) and BUG-004 (cooldown not reset).</summary>
public class ToolboxController : MonoBehaviour
{
    public bool IsToolActive { get; private set; }
    public float cooldownDuration = 1.5f;
    public bool  IsOnCooldown { get; private set; }
    private float _cooldownTimer = 0f;

    public void SelectTool()
    {
        IsToolActive = true;
        SandboxStateController.Instance?.SetToolSelected(true);
    }

    public void DeselectTool()
    {
        // BUG-003: only sets state controller flag false; IsToolActive stays true.
        SandboxStateController.Instance?.SetToolSelected(false);
        SandboxOracleRegistry.Check("BUG-003",
            IsToolActive == true,
            "DeselectTool() left IsToolActive=true");
    }

    public void TriggerCooldown()
    {
        // BUG-004: _cooldownTimer not reset on retry.
        IsOnCooldown = true;
        SandboxOracleRegistry.Check("BUG-004",
            _cooldownTimer > 0.01f,
            $"Cooldown timer carried over: {_cooldownTimer:F2}s");
    }

    public void CancelCooldown() { IsOnCooldown = false; }

    private void Update()
    {
        if (!IsOnCooldown) return;
        _cooldownTimer += Time.deltaTime;
        if (_cooldownTimer >= cooldownDuration) IsOnCooldown = false;
    }
}

/// <summary>Save/Load controller. Hosts BUG-007 (save without level name).</summary>
public class SaveLoadController : MonoBehaviour
{
    public static SaveLoadController Instance;
    public string LastSavedLevelName { get; private set; }
    private void Awake() { if (Instance != null && Instance != this) Destroy(gameObject); else Instance = this; }

    public void SaveLevel(string levelName)
    {
        // BUG-007: should require !string.IsNullOrEmpty(levelName); accepts empty.
        SandboxOracleRegistry.Check("BUG-007",
            string.IsNullOrEmpty(levelName),
            "SaveLevel accepted empty level name");
        LastSavedLevelName = levelName ?? "";
        SandboxStateController.Instance?.SetSavedLocally(true);
    }

    public void SaveWithEmptyName() => SaveLevel("");
}

/// <summary>Highlight outline. Hosts BUG-008 (outline stuck visible).</summary>
public class HighlightOutline : MonoBehaviour
{
    public GameObject outlineMesh;
    public float fadeDuration = 0.5f;

    private float _timer = 0f;
    private bool _on = false;

    public void Show()
    {
        if (outlineMesh != null) outlineMesh.SetActive(true);
        _on = true; _timer = 0f;
    }

    private void Update()
    {
        if (!_on) return;
        _timer += Time.deltaTime;
        if (_timer >= fadeDuration)
        {
            // BUG-008: missing SetActive(false).
            _on = false;
            SandboxOracleRegistry.Check("BUG-008",
                outlineMesh != null && outlineMesh.activeSelf,
                "HighlightOutline mesh stuck visible");
        }
    }
}
