using UnityEngine;

/// <summary>
/// Three-state coffee machine: Idle → Brewing → Done.
/// Requires power (from CircuitBreaker) and cup in socket to brew.
/// Wire XRSimpleInteractable.selectEntered → TryStartBrew() on the brew button.
/// </summary>
public class CoffeeMachineController : MonoBehaviour
{
    public enum State { Idle, Brewing, Done }

    [Header("References")]
    [SerializeField] private CoffeeCupSocket cupSocket;
    [SerializeField] private Renderer bodyRenderer;

    [Header("Materials")]
    [SerializeField] private Material materialIdle;
    [SerializeField] private Material materialBrewing;
    [SerializeField] private Material materialDone;

    [Header("Settings")]
    [SerializeField] private float brewDuration = 2f;

    /// <summary>Current machine state.</summary>
    public State CurrentState { get; private set; } = State.Idle;

    private float _brewTimer;

    private void Start()
    {
        CurrentState = State.Idle;
        ApplyMaterial();
    }

    private void Update()
    {
        if (CurrentState != State.Brewing) return;

        _brewTimer += Time.deltaTime;
        if (_brewTimer >= brewDuration)
        {
            FinishBrew();
        }
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-002: Missing cupSocket.HasCup check.
    //   Coffee brews even when no cup is placed in the socket.
    //   Correct: add if (cupSocket != null && !cupSocket.HasCup) return;
    // ══════════════════════════════════════════════════════════════
    /// <summary>Start brewing coffee.</summary>
    public void TryStartBrew()
    {
        if (CurrentState != State.Idle)
        {
            Debug.LogWarning("[CoffeeMachine] Already brewing or done — reset first");
            return;
        }

        if (ApartmentStateController.Instance != null &&
            !ApartmentStateController.Instance.PowerOn)
        {
            Debug.LogWarning("[CoffeeMachine] No power — cannot brew");
            return;
        }

        // BUG-002: missing cup check
        // if (cupSocket != null && !cupSocket.HasCup)
        // {
        //     Debug.LogWarning("[CoffeeMachine] No cup in socket");
        //     return;
        // }
        ApartmentOracleRegistry.Check("BUG-002",
            cupSocket != null && !cupSocket.HasCup,
            $"Brew started without cup. HasCup={cupSocket?.HasCup}");

        CurrentState = State.Brewing;
        _brewTimer = 0f;
        ApplyMaterial();
        Debug.Log("[CoffeeMachine] Brewing started...");
    }

    // ══════════════════════════════════════════════════════════════
    // ▼ BUG-001: GetComponent<AudioSource>().Play() with no AudioSource.
    //   NullReferenceException thrown every time brew completes.
    //   Correct: var audio = GetComponent<AudioSource>();
    //            if (audio != null) audio.Play();
    // ══════════════════════════════════════════════════════════════
    private void FinishBrew()
    {
        ApartmentStateController.Instance?.SetCoffeeBrewed();

        CurrentState = State.Done;
        ApplyMaterial();
        Debug.Log("[CoffeeMachine] Coffee ready!");

        // BUG-001: NullReferenceException — no AudioSource on this GameObject
        GetComponent<AudioSource>().Play();
    }

    private void ApplyMaterial()
    {
        if (bodyRenderer == null) return;
        bodyRenderer.sharedMaterial = CurrentState switch
        {
            State.Brewing => materialBrewing,
            State.Done => materialDone,
            _ => materialIdle,
        };
    }
}
