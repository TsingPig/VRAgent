using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// A toggleable metronome that produces a steady tick at the configured BPM.
/// Generates its own click AudioClip. Visual feedback via a pendulum-style
/// oscillating arm and indicator light.
/// Wire XRSimpleInteractable.selectEntered → MetronomeController.Toggle().
/// Tap BPM button → MetronomeController.CycleBPM().
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class MetronomeController : MonoBehaviour
{
    [Header("Settings")]
    [SerializeField] private int[] bpmOptions = { 60, 90, 120, 150 };
    [SerializeField] private int defaultBpmIndex = 1;

    [Header("References")]
    [SerializeField] private Transform pendulumArm;
    [SerializeField] private Light tickLight;
    [SerializeField] private Renderer bpmDisplayRenderer;

    [Header("Materials — BPM Display")]
    [SerializeField] private Material displayOff;
    [SerializeField] private Material displayOn;

    [Header("Pendulum")]
    [SerializeField] private float swingAngle = 25f;

    [Header("Events")]
    public UnityEvent onTick;

    /// <summary>Whether the metronome is running.</summary>
    public bool IsRunning { get; private set; }

    /// <summary>Current BPM value.</summary>
    public int CurrentBPM => bpmOptions[currentBpmIndex];

    private AudioSource audioSource;
    private AudioClip tickClip;
    private int currentBpmIndex;
    private float tickInterval;
    private float tickTimer;
    private float lightTimer;

    private const float TICK_DURATION = 0.04f;
    private const float LIGHT_FLASH_DURATION = 0.08f;
    private const int SAMPLE_RATE = 44100;

    private void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        audioSource.playOnAwake = false;
        audioSource.spatialBlend = 1f;

        tickClip = GenerateTickClip();
        audioSource.clip = tickClip;

        currentBpmIndex = Mathf.Clamp(defaultBpmIndex, 0, bpmOptions.Length - 1);
        RecalculateInterval();

        if (tickLight != null) tickLight.enabled = false;
        ApplyDisplay();
    }

    /// <summary>Start or stop the metronome.</summary>
    public void Toggle()
    {
        IsRunning = !IsRunning;
        tickTimer = 0f;

        if (!IsRunning)
        {
            if (tickLight != null) tickLight.enabled = false;
            if (pendulumArm != null) pendulumArm.localRotation = Quaternion.identity;
        }

        ApplyDisplay();
        Debug.Log($"[MetronomeController] {(IsRunning ? "STARTED" : "STOPPED")} at {CurrentBPM} BPM");
    }

    /// <summary>Cycle to the next BPM preset.</summary>
    public void CycleBPM()
    {
        currentBpmIndex = (currentBpmIndex + 1) % bpmOptions.Length;
        RecalculateInterval();
        Debug.Log($"[MetronomeController] BPM → {CurrentBPM}");
    }

    private void Update()
    {
        if (!IsRunning) return;

        tickTimer += Time.deltaTime;

        // Tick
        if (tickTimer >= tickInterval)
        {
            tickTimer -= tickInterval;
            audioSource.Stop();
            audioSource.Play();
            lightTimer = LIGHT_FLASH_DURATION;
            if (tickLight != null) tickLight.enabled = true;
            onTick?.Invoke();
        }

        // Light flash decay
        if (lightTimer > 0f)
        {
            lightTimer -= Time.deltaTime;
            if (lightTimer <= 0f && tickLight != null)
                tickLight.enabled = false;
        }

        // Pendulum swing
        if (pendulumArm != null)
        {
            float phase = (tickTimer / tickInterval) * 2f * Mathf.PI;
            float angle = Mathf.Sin(phase) * swingAngle;
            pendulumArm.localRotation = Quaternion.Euler(0f, 0f, angle);
        }
    }

    private void RecalculateInterval()
    {
        tickInterval = 60f / CurrentBPM;
    }

    private void ApplyDisplay()
    {
        if (bpmDisplayRenderer == null) return;
        bpmDisplayRenderer.sharedMaterial = IsRunning ? displayOn : displayOff;
    }

    private AudioClip GenerateTickClip()
    {
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * TICK_DURATION);
        float[] samples = new float[sampleCount];

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            float signal = Mathf.Sin(2f * Mathf.PI * 1200f * t);
            float envelope = 1f - (t / TICK_DURATION);
            samples[i] = signal * envelope * 0.8f;
        }

        AudioClip clip = AudioClip.Create("MetronomeTick", sampleCount, 1, SAMPLE_RATE, false);
        clip.SetData(samples, 0);
        return clip;
    }
}
