using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Controls a single xylophone bar. Generates a bright, metallic-sounding
/// AudioClip on Awake at the configured frequency. Provides hit feedback
/// with a brief material flash and wobble animation.
/// Wire XRSimpleInteractable.selectEntered → XylophoneBarController.Strike().
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class XylophoneBarController : MonoBehaviour
{
    [Header("Note Settings")]
    [SerializeField] private int barIndex = 0;
    [SerializeField] private float customFrequency = 0f;

    [Header("Visual Feedback")]
    [SerializeField] private Renderer barRenderer;
    [SerializeField] private Material materialIdle;
    [SerializeField] private Material materialStruck;

    [Header("Animation")]
    [SerializeField] private float wobbleAmplitude = 2f;
    [SerializeField] private float wobbleDecay = 8f;

    [Header("Events")]
    public UnityEvent onStrike;

    /// <summary>Whether this bar is currently vibrating.</summary>
    public bool IsVibrating { get; private set; }

    /// <summary>Index of this bar on the xylophone (0-7).</summary>
    public int BarIndex => barIndex;

    private AudioSource audioSource;
    private AudioClip generatedClip;
    private Quaternion restRotation;
    private float vibrateTimer;
    private float vibrateFreq;

    /// <summary>C5 scale frequencies for 8 bars.</summary>
    private static readonly float[] BAR_FREQUENCIES =
    {
        523.25f,  // C5
        587.33f,  // D5
        659.25f,  // E5
        698.46f,  // F5
        783.99f,  // G5
        880.00f,  // A5
        987.77f,  // B5
        1046.50f  // C6
    };

    private void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        audioSource.playOnAwake = false;
        audioSource.spatialBlend = 1f;

        float freq = customFrequency > 0f ? customFrequency : GetBarFrequency();
        generatedClip = SynthAudioGenerator.CreateXylophoneTone($"Xylo_Bar{barIndex}", freq, 1.2f);
        audioSource.clip = generatedClip;

        restRotation = transform.localRotation;
        vibrateFreq = freq * 0.05f; // Visible wobble frequency
    }

    /// <summary>Strike the bar. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Strike()
    {
        if (audioSource == null || generatedClip == null) return;

        audioSource.Stop();
        audioSource.clip = generatedClip;
        audioSource.Play();

        IsVibrating = true;
        vibrateTimer = 0f;

        if (barRenderer != null && materialStruck != null)
            barRenderer.sharedMaterial = materialStruck;

        onStrike?.Invoke();
        Debug.Log($"[XylophoneBarController] Bar {barIndex} struck ({GetBarFrequency():F1} Hz)");
    }

    private void Update()
    {
        if (!IsVibrating) return;

        vibrateTimer += Time.deltaTime;
        float decay = Mathf.Exp(-vibrateTimer * wobbleDecay);

        if (decay < 0.01f)
        {
            IsVibrating = false;
            transform.localRotation = restRotation;
            if (barRenderer != null && materialIdle != null)
                barRenderer.sharedMaterial = materialIdle;
            return;
        }

        // Wobble around local Z axis
        float angle = Mathf.Sin(vibrateTimer * vibrateFreq * 2f * Mathf.PI) * wobbleAmplitude * decay;
        transform.localRotation = restRotation * Quaternion.Euler(0f, 0f, angle);
    }

    private float GetBarFrequency()
    {
        int idx = Mathf.Clamp(barIndex, 0, BAR_FREQUENCIES.Length - 1);
        return customFrequency > 0f ? customFrequency : BAR_FREQUENCIES[idx];
    }
}
