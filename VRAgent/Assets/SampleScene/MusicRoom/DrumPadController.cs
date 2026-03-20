using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Controls a single drum pad / cymbal. Generates its percussive AudioClip
/// on Awake based on the configured DrumType. Provides visual feedback by
/// briefly swapping material and scaling the pad on hit.
/// Wire XRSimpleInteractable.selectEntered → DrumPadController.Hit().
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class DrumPadController : MonoBehaviour
{
    [Header("Drum Settings")]
    [SerializeField] private SynthAudioGenerator.DrumType drumType = SynthAudioGenerator.DrumType.Snare;

    [Header("Visual Feedback")]
    [SerializeField] private Renderer padRenderer;
    [SerializeField] private Material materialIdle;
    [SerializeField] private Material materialHit;
    [SerializeField] private float hitScaleFactor = 0.92f;

    [Header("Events")]
    public UnityEvent onHit;

    /// <summary>The type of drum this pad represents.</summary>
    public SynthAudioGenerator.DrumType DrumType => drumType;

    /// <summary>Whether this pad is currently showing hit feedback.</summary>
    public bool IsHit { get; private set; }

    private AudioSource audioSource;
    private AudioClip generatedClip;
    private Vector3 restScale;
    private float hitTimer;

    private const float HIT_VISUAL_DURATION = 0.12f;

    private void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        audioSource.playOnAwake = false;
        audioSource.spatialBlend = 1f;

        generatedClip = SynthAudioGenerator.CreateDrumSound($"Drum_{drumType}", drumType);
        audioSource.clip = generatedClip;

        restScale = transform.localScale;
    }

    /// <summary>Strike the drum. Wire to XRSimpleInteractable.selectEntered.</summary>
    public void Hit()
    {
        if (audioSource == null || generatedClip == null) return;

        audioSource.Stop();
        audioSource.clip = generatedClip;
        audioSource.Play();

        IsHit = true;
        hitTimer = HIT_VISUAL_DURATION;
        transform.localScale = restScale * hitScaleFactor;

        if (padRenderer != null && materialHit != null)
            padRenderer.sharedMaterial = materialHit;

        onHit?.Invoke();
        Debug.Log($"[DrumPadController] {drumType} hit!");
    }

    private void Update()
    {
        if (!IsHit) return;

        hitTimer -= Time.deltaTime;
        if (hitTimer <= 0f)
        {
            IsHit = false;
            transform.localScale = restScale;
            if (padRenderer != null && materialIdle != null)
                padRenderer.sharedMaterial = materialIdle;
        }
    }
}
