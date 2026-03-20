using UnityEngine;
using UnityEngine.Events;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Socket_TrophyShelf — a display socket on the bookshelf.
/// When Obj_Trophy is placed here, triggers a light-up celebration effect.
/// A small hidden "secret" — placing all 3 books on the shelf + trophy unlocks
/// the secret drawer (Drawer_Secret) in the desk.
/// </summary>
[RequireComponent(typeof(XRSocketInteractor))]
public class TrophySocketController : MonoBehaviour
{
    [Header("Trophy Visual")]
    [SerializeField] private Light trophySpotlight;

    [Header("Secret Unlock")]
    [SerializeField] private BedroomDrawerController secretDrawer;
    [SerializeField] private BookController[] requiredBooks;

    [Header("Events")]
    public UnityEvent onTrophyPlaced;
    public UnityEvent onSecretUnlocked;

    private XRSocketInteractor _socket;
    private bool _trophyPlaced   = false;
    private bool _secretUnlocked = false;

    public bool TrophyPlaced   => _trophyPlaced;
    public bool SecretUnlocked => _secretUnlocked;

    private void Awake()
    {
        _socket = GetComponent<XRSocketInteractor>();
        _socket.selectEntered.AddListener(OnTrophyInserted);
        _socket.selectExited.AddListener(OnTrophyRemoved);
    }

    private void OnTrophyInserted(SelectEnterEventArgs args)
    {
        _trophyPlaced = true;
        if (trophySpotlight != null) trophySpotlight.enabled = true;
        onTrophyPlaced?.Invoke();
        Debug.Log("[TrophySocketController] Trophy placed on shelf — checking secret condition...");
        CheckSecretCondition();
    }

    private void OnTrophyRemoved(SelectExitEventArgs args)
    {
        _trophyPlaced = false;
        if (trophySpotlight != null && !_secretUnlocked)
            trophySpotlight.enabled = false;
        Debug.Log("[TrophySocketController] Trophy removed.");
    }

    private void CheckSecretCondition()
    {
        if (_secretUnlocked) return;
        if (!_trophyPlaced) return;

        bool allBooksRead = true;
        if (requiredBooks != null)
        {
            foreach (var book in requiredBooks)
                if (book != null && !book.HasBeenRead) { allBooksRead = false; break; }
        }

        if (allBooksRead)
        {
            _secretUnlocked = true;
            secretDrawer?.ForceClose();     // ensure it starts from closed
            onSecretUnlocked?.Invoke();
            Debug.Log("[TrophySocketController] SECRET UNLOCKED — Drawer_Secret is now available!");
        }
        else
        {
            Debug.Log("[TrophySocketController] Not all books have been read yet.");
        }
    }

    private void OnDestroy()
    {
        if (_socket == null) return;
        _socket.selectEntered.RemoveListener(OnTrophyInserted);
        _socket.selectExited.RemoveListener(OnTrophyRemoved);
    }
}
