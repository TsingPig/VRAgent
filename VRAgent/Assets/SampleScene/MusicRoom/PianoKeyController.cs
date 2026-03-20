using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Controls a single piano key. Generates its own AudioClip at the specified
/// frequency on Awake. When interacted via XRSimpleInteractable.selectEntered,
/// plays the note and provides visual feedback (key press animation + material swap).
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class PianoKeyController : MonoBehaviour
{
    /// <summary>Standard note names for inspector labeling.</summary>
    public enum NoteName
    {
        C4, Cs4, D4, Ds4, E4, F4, Fs4, G4, Gs4, A4, As4, B4, C5
    }

    [Header("Note Settings")]
    [SerializeField] private NoteName note = NoteName.C4;
    [SerializeField] private float customFrequency = 0f;

    [Header("Visual Feedback")]
    [SerializeField] private Renderer keyRenderer;
    [SerializeField] private Material materialIdle;
    [SerializeField] private Material materialPressed;

    [Header("Key Press Animation")]
    [SerializeField] private float pressDepth = 0.015f;
    [SerializeField] private float pressSpeed = 15f;

    [Header("Events")]
    public UnityEvent onNotePlayed;

    /// <summary>Whether this key is currently pressed.</summary>
    public bool IsPressed { get; private set; }

    /// <summary>The note this key plays.</summary>
    public NoteName Note => note;

    private AudioSource audioSource;
    private AudioClip generatedClip;
    private Vector3 restLocalPosition;
    private Vector3 pressedLocalPosition;
    private bool returning;

    private static readonly float[] NOTE_FREQUENCIES =
    {
        261.63f, // C4
        277.18f, // C#4
        293.66f, // D4
        311.13f, // D#4
        329.63f, // E4
        349.23f, // F4
        369.99f, // F#4
        392.00f, // G4
        415.30f, // G#4
        440.00f, // A4
        466.16f, // A#4
        493.88f, // B4
        523.25f  // C5
    };

    private void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        audioSource.playOnAwake = false;
        audioSource.spatialBlend = 1f;

        float freq = customFrequency > 0f ? customFrequency : NOTE_FREQUENCIES[(int)note];
        generatedClip = SynthAudioGenerator.CreatePianoTone($"Piano_{note}", freq, 1.8f);
        audioSource.clip = generatedClip;

        restLocalPosition = transform.localPosition;
        pressedLocalPosition = restLocalPosition + Vector3.down * pressDepth;
    }

    /// <summary>Play the note. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void PlayNote()
    {
        if (audioSource == null || generatedClip == null) return;

        audioSource.Stop();
        audioSource.clip = generatedClip;
        audioSource.Play();

        IsPressed = true;
        returning = false;
        ApplyVisuals();

        onNotePlayed?.Invoke();
        Debug.Log($"[PianoKeyController] {note} played ({GetFrequency():F1} Hz)");
    }

    /// <summary>Release the key. Wire to XRSimpleInteractable.selectExited.</summary>
    public void ReleaseKey()
    {
        IsPressed = false;
        returning = true;
        ApplyVisuals();
    }

    private void Update()
    {
        // Animate key press/release
        Vector3 target = IsPressed ? pressedLocalPosition : restLocalPosition;
        transform.localPosition = Vector3.Lerp(transform.localPosition, target, Time.deltaTime * pressSpeed);

        if (returning && Vector3.Distance(transform.localPosition, restLocalPosition) < 0.001f)
        {
            transform.localPosition = restLocalPosition;
            returning = false;
        }
    }

    private void ApplyVisuals()
    {
        if (keyRenderer == null) return;
        keyRenderer.sharedMaterial = IsPressed ? materialPressed : materialIdle;
    }

    private float GetFrequency()
    {
        return customFrequency > 0f ? customFrequency : NOTE_FREQUENCIES[(int)note];
    }
}
