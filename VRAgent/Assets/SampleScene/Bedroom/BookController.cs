using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Book_Shelf_* — a grabbable book that can be pulled from the shelf.
/// When picked up for the first time, fires onFirstPickup.
/// Supports being placed back on a designated socket (Socket_BookReturn_*).
/// Attach to any book GameObject alongside XRGrabbable.
/// </summary>
public class BookController : MonoBehaviour
{
    [Header("Identity")]
    [SerializeField] private string bookTitle = "Unknown Title";

    [Header("Events")]
    public UnityEngine.Events.UnityEvent onFirstPickup;
    public UnityEngine.Events.UnityEvent onReturnedToShelf;

    public bool HasBeenRead   { get; private set; } = false;
    public bool IsOnShelf     { get; private set; } = true;
    public string BookTitle   => bookTitle;

    private Vector3 _shelfPosition;
    private Quaternion _shelfRotation;

    private void Start()
    {
        _shelfPosition = transform.position;
        _shelfRotation = transform.rotation;
    }

    /// <summary>Called by XRGrabbable.selectEntered event.</summary>
    public void OnPickedUp()
    {
        IsOnShelf = false;
        if (!HasBeenRead)
        {
            HasBeenRead = true;
            onFirstPickup?.Invoke();
            Debug.Log($"[BookController] \"{bookTitle}\" picked up for the first time.");
        }
        else
        {
            Debug.Log($"[BookController] \"{bookTitle}\" picked up again.");
        }
    }

    /// <summary>Called when the book is placed back in Socket_BookReturn.</summary>
    public void OnReturnedToShelf()
    {
        IsOnShelf = true;
        onReturnedToShelf?.Invoke();
        Debug.Log($"[BookController] \"{bookTitle}\" returned to shelf.");
    }

    /// <summary>Teleports the book back to its original shelf position.</summary>
    public void ResetToShelf()
    {
        transform.position = _shelfPosition;
        transform.rotation = _shelfRotation;
        IsOnShelf = true;
        Debug.Log($"[BookController] \"{bookTitle}\" reset to shelf.");
    }
}
