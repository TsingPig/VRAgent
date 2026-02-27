using UnityEngine;

/// <summary>
/// Smoothly slides a drawer open or closed along its local Z axis.
/// Wire XRSimpleInteractable.selectEntered -> DrawerController.Toggle().
/// </summary>
public class DrawerController : MonoBehaviour
{
    [SerializeField] private float openDistance = 0.42f;
    [SerializeField] private float animationSpeed = 5f;

    private bool isOpen = false;
    private Vector3 closedLocalPosition;
    private Vector3 openLocalPosition;

    private void Start()
    {
        closedLocalPosition = transform.localPosition;
        openLocalPosition = closedLocalPosition + new Vector3(0f, 0f, -openDistance);
    }

    private void Update()
    {
        Vector3 target = isOpen ? openLocalPosition : closedLocalPosition;
        transform.localPosition = Vector3.Lerp(transform.localPosition, target, Time.deltaTime * animationSpeed);
    }

    /// <summary>Toggles the drawer open/closed state.</summary>
    public void Toggle()
    {
        isOpen = !isOpen;
        Debug.Log($"[Drawer] {gameObject.name} → {(isOpen ? "OPEN" : "CLOSED")}");
    }
}
