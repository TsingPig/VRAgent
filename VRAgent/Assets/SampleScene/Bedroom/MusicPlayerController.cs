using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// MusicPlayer_Desk — a Bluetooth speaker / music player with play/pause and track skip.
/// Interactable buttons:
///   Button_PlayPause → TogglePlayback()
///   Button_Next      → SkipTrack()
///   Button_MusicPower→ TogglePower()
///
/// AudioSource plays looping music when on.
/// Volume knob is simulated via repeated interactions.
/// </summary>
public class MusicPlayerController : MonoBehaviour
{
    [Header("Audio")]
    [SerializeField] private AudioSource audioSource;
    [SerializeField] private AudioClip[] tracks;

    [Header("Visual Indicators")]
    [SerializeField] private Renderer displayRenderer;
    [SerializeField] private Material displayOff;
    [SerializeField] private Material displayPaused;
    [SerializeField] private Material displayPlaying;
    [SerializeField] private Light    ambientGlow;

    [Header("Events")]
    public UnityEvent onPlay;
    public UnityEvent onPause;

    public bool IsPoweredOn  { get; private set; } = false;
    public bool IsPlaying    { get; private set; } = false;
    public int  CurrentTrack { get; private set; } = 0;

    private void Start() => ApplyDisplay();

    /// <summary>Toggle power. Wire to Button_MusicPower.</summary>
    public void TogglePower()
    {
        IsPoweredOn = !IsPoweredOn;
        if (!IsPoweredOn)
        {
            IsPlaying = false;
            if (audioSource != null) audioSource.Stop();
        }
        ApplyDisplay();
        Debug.Log($"[MusicPlayerController] Power → {(IsPoweredOn ? "ON" : "OFF")}");
    }

    /// <summary>Play / Pause. Wire to Button_PlayPause.</summary>
    public void TogglePlayback()
    {
        if (!IsPoweredOn) { Debug.Log("[MusicPlayerController] Power is off."); return; }

        IsPlaying = !IsPlaying;
        if (IsPlaying)
        {
            PlayCurrentTrack();
            onPlay?.Invoke();
        }
        else
        {
            if (audioSource != null) audioSource.Pause();
            onPause?.Invoke();
        }
        ApplyDisplay();
        Debug.Log($"[MusicPlayerController] Playback → {(IsPlaying ? "PLAY" : "PAUSE")}");
    }

    /// <summary>Skip to next track. Wire to Button_Next.</summary>
    public void SkipTrack()
    {
        if (!IsPoweredOn) return;
        if (tracks == null || tracks.Length == 0) return;
        CurrentTrack = (CurrentTrack + 1) % tracks.Length;
        if (IsPlaying) PlayCurrentTrack();
        Debug.Log($"[MusicPlayerController] Track → {CurrentTrack}");
    }

    private void PlayCurrentTrack()
    {
        if (audioSource == null || tracks == null || tracks.Length == 0) return;
        audioSource.clip  = tracks[CurrentTrack];
        audioSource.loop  = true;
        audioSource.Play();
    }

    private void ApplyDisplay()
    {
        if (displayRenderer != null)
        {
            displayRenderer.sharedMaterial = !IsPoweredOn ? displayOff
                                           : IsPlaying    ? displayPlaying
                                                          : displayPaused;
        }
        if (ambientGlow != null)
            ambientGlow.enabled = IsPoweredOn && IsPlaying;
    }
}
