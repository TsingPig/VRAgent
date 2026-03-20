using UnityEngine;

/// <summary>
/// Static utility that generates AudioClips programmatically at runtime.
/// Supports sine-wave tones (piano, xylophone) and noise-based percussion (drums).
/// All clips are mono, 44100 Hz.
/// </summary>
public static class SynthAudioGenerator
{
    private const int SAMPLE_RATE = 44100;

    /// <summary>Drum sound categories.</summary>
    public enum DrumType { Kick, Snare, HiHat, Crash, TomHigh, TomLow }

    /// <summary>
    /// Generate a piano-style sine tone with harmonics and an ADSR envelope.
    /// </summary>
    public static AudioClip CreatePianoTone(string clipName, float frequency, float duration = 1.5f)
    {
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];

        float attack = 0.01f;
        float decay = 0.15f;
        float sustainLevel = 0.4f;
        float release = duration * 0.5f;
        float sustainEnd = duration - release;

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;

            // Harmonics for richer piano timbre
            float signal = Mathf.Sin(2f * Mathf.PI * frequency * t) * 1.0f;
            signal += Mathf.Sin(2f * Mathf.PI * frequency * 2f * t) * 0.5f;
            signal += Mathf.Sin(2f * Mathf.PI * frequency * 3f * t) * 0.2f;
            signal += Mathf.Sin(2f * Mathf.PI * frequency * 4f * t) * 0.08f;
            signal /= 1.78f; // Normalize

            // ADSR envelope
            float envelope;
            if (t < attack)
            {
                envelope = t / attack;
            }
            else if (t < attack + decay)
            {
                float decayProgress = (t - attack) / decay;
                envelope = 1f - decayProgress * (1f - sustainLevel);
            }
            else if (t < sustainEnd)
            {
                // Gradual sustain decay
                float sustainProgress = (t - attack - decay) / (sustainEnd - attack - decay + 0.001f);
                envelope = sustainLevel * (1f - sustainProgress * 0.3f);
            }
            else
            {
                float releaseProgress = (t - sustainEnd) / release;
                envelope = sustainLevel * 0.7f * (1f - releaseProgress);
            }

            samples[i] = signal * Mathf.Clamp01(envelope) * 0.7f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    /// <summary>
    /// Generate a xylophone-style tone — brighter, with faster decay and metallic harmonics.
    /// </summary>
    public static AudioClip CreateXylophoneTone(string clipName, float frequency, float duration = 1.0f)
    {
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;

            // Xylophone timbre: fundamental + inharmonic overtones
            float signal = Mathf.Sin(2f * Mathf.PI * frequency * t) * 1.0f;
            signal += Mathf.Sin(2f * Mathf.PI * frequency * 3.0f * t) * 0.35f;
            signal += Mathf.Sin(2f * Mathf.PI * frequency * 6.27f * t) * 0.15f; // Inharmonic
            signal /= 1.5f;

            // Fast exponential decay
            float envelope = Mathf.Exp(-t * 4.5f);

            samples[i] = signal * envelope * 0.75f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    /// <summary>
    /// Generate a percussion sound based on drum type.
    /// </summary>
    public static AudioClip CreateDrumSound(string clipName, DrumType drumType)
    {
        switch (drumType)
        {
            case DrumType.Kick:    return GenerateKick(clipName);
            case DrumType.Snare:   return GenerateSnare(clipName);
            case DrumType.HiHat:   return GenerateHiHat(clipName);
            case DrumType.Crash:   return GenerateCrash(clipName);
            case DrumType.TomHigh: return GenerateTom(clipName, 200f, 0.4f);
            case DrumType.TomLow:  return GenerateTom(clipName, 120f, 0.5f);
            default:               return GenerateKick(clipName);
        }
    }

    private static AudioClip GenerateKick(string clipName)
    {
        float duration = 0.5f;
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            // Pitch sweep from ~150Hz down to ~50Hz
            float freq = 50f + 100f * Mathf.Exp(-t * 15f);
            float signal = Mathf.Sin(2f * Mathf.PI * freq * t);
            float envelope = Mathf.Exp(-t * 8f);
            samples[i] = signal * envelope * 0.9f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    private static AudioClip GenerateSnare(string clipName)
    {
        float duration = 0.35f;
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];
        System.Random rng = new System.Random(42);

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            // Tone body
            float tone = Mathf.Sin(2f * Mathf.PI * 185f * t) * 0.5f;
            // White noise (snare wires)
            float noise = ((float)rng.NextDouble() * 2f - 1f) * 0.6f;
            float envelope = Mathf.Exp(-t * 12f);
            float noiseEnvelope = Mathf.Exp(-t * 18f);
            samples[i] = (tone * envelope + noise * noiseEnvelope) * 0.75f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    private static AudioClip GenerateHiHat(string clipName)
    {
        float duration = 0.15f;
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];
        System.Random rng = new System.Random(123);

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            float noise = (float)rng.NextDouble() * 2f - 1f;
            // Band-pass simulation: mix high-freq sine with noise
            float highFreq = Mathf.Sin(2f * Mathf.PI * 6000f * t) * 0.3f;
            float envelope = Mathf.Exp(-t * 35f);
            samples[i] = (noise * 0.5f + highFreq) * envelope * 0.55f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    private static AudioClip GenerateCrash(string clipName)
    {
        float duration = 1.5f;
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];
        System.Random rng = new System.Random(77);

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            float noise = (float)rng.NextDouble() * 2f - 1f;
            float shimmer = Mathf.Sin(2f * Mathf.PI * 4200f * t) * 0.15f;
            float envelope = Mathf.Exp(-t * 3f);
            samples[i] = (noise * 0.45f + shimmer) * envelope * 0.55f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    private static AudioClip GenerateTom(string clipName, float baseFreq, float duration)
    {
        int sampleCount = Mathf.CeilToInt(SAMPLE_RATE * duration);
        float[] samples = new float[sampleCount];

        for (int i = 0; i < sampleCount; i++)
        {
            float t = (float)i / SAMPLE_RATE;
            float freq = baseFreq + 60f * Mathf.Exp(-t * 10f);
            float signal = Mathf.Sin(2f * Mathf.PI * freq * t);
            float envelope = Mathf.Exp(-t * 7f);
            samples[i] = signal * envelope * 0.8f;
        }

        return CreateClipFromSamples(clipName, samples);
    }

    private static AudioClip CreateClipFromSamples(string clipName, float[] samples)
    {
        AudioClip clip = AudioClip.Create(clipName, samples.Length, 1, SAMPLE_RATE, false);
        clip.SetData(samples, 0);
        return clip;
    }
}
