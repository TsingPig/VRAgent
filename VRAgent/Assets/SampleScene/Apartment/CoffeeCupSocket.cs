using UnityEngine;

/// <summary>
/// Detects whether a coffee cup is placed in the machine's socket slot.
/// Attach to the same GameObject as the XRSocketInteractor.
/// Wire selectEntered → OnCupPlaced(), selectExited → OnCupRemoved().
/// </summary>
public class CoffeeCupSocket : MonoBehaviour
{
    /// <summary>Whether a cup is currently in the socket.</summary>
    public bool HasCup { get; private set; }

    public void OnCupPlaced()
    {
        HasCup = true;
        ApartmentStateController.Instance?.SetCupPlaced();
        Debug.Log("[CoffeeCupSocket] Cup placed");
    }

    public void OnCupRemoved()
    {
        HasCup = false;
        Debug.Log("[CoffeeCupSocket] Cup removed");
    }
}
