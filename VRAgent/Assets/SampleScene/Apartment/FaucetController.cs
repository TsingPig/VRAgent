using UnityEngine;

/// <summary>
/// Controls a faucet: toggle water stream on/off.
/// Shows/hides a water stream child GameObject and plays optional audio.
/// Wire XRSimpleInteractable.selectEntered → Toggle().
/// </summary>
public class FaucetController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private GameObject waterStream;
    [SerializeField] private AudioSource waterAudio;

    /// <summary>Whether the faucet is currently running.</summary>
    public bool IsRunning { get; private set; }

    private void Start()
    {
        IsRunning = false;
        if (waterStream != null) waterStream.SetActive(false);
    }

    /// <summary>Toggle water on/off.</summary>
    public void Toggle()
    {
        IsRunning = !IsRunning;

        if (waterStream != null)
        {
            waterStream.SetActive(IsRunning);
        }

        if (waterAudio != null)
        {
            if (IsRunning) waterAudio.Play();
            else waterAudio.Stop();
        }

        Debug.Log($"[FaucetController] {gameObject.name} → {(IsRunning ? "ON" : "OFF")}");
    }
}
