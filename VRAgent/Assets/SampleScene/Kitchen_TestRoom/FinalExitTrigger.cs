using UnityEngine;

/// <summary>
/// Placed as a trigger collider in Room D (the exit area).
/// When the player enters, checks if the final door is properly unlocked
/// and the dish has been delivered. Logs the result clearly.
/// Does NOT quit the application — it signals test completion instead.
/// </summary>
public class FinalExitTrigger : MonoBehaviour
{
    private const string PlayerTag = "Player";

    [SerializeField] private RecipeController recipeController;

    private bool _hasTriggered = false;

    /// <summary>Whether the player successfully completed the task before exiting.</summary>
    public bool CompletedSuccessfully { get; private set; } = false;

    private void OnTriggerEnter(Collider other)
    {
        if (_hasTriggered) return;
        if (!other.CompareTag(PlayerTag)) return;

        _hasTriggered = true;

        RecipeController rc = recipeController != null ? recipeController : RecipeController.Instance;
        if (rc == null)
        {
            Debug.LogError("[FinalExitTrigger] RecipeController not found.");
            return;
        }

        if (rc.FinalDoorUnlocked)
        {
            CompletedSuccessfully = true;
            Debug.Log("[FinalExitTrigger] SUCCESS — Player exited Room D with completed dish. Task finished!");
            rc.PrintStateSnapshot();
        }
        else
        {
            Debug.LogWarning("[FinalExitTrigger] FAIL — Player reached exit but task is incomplete. Deliver plated dish to Counter_Serving first.");
            rc.PrintStateSnapshot();
            // Reset so the player can try again.
            _hasTriggered = false;
        }
    }
}
