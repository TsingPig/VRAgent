using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

/// <summary>
/// Curtain_Window — a grabbable curtain rod ring that slides open/closed.
/// Toggle by pulling the drawstring (XRSimpleInteractable on Drawstring_Curtain)
/// or by directly grabbing the curtain panel.
///
/// Open  → curtain scrunches to the side (localScale.z shrinks, position shifts).
/// Closed → curtain is fully extended.
/// </summary>
public class CurtainController : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Transform curtainPanel;     // the curtain mesh

    [Header("Open State")]
    [SerializeField] private Vector3 openLocalPos   = new Vector3(-0.8f, 0f, 0f);
    [SerializeField] private Vector3 openLocalScale = new Vector3(0.15f, 1f, 1f);

    [Header("Closed State")]
    [SerializeField] private Vector3 closedLocalPos   = new Vector3(0f, 0f, 0f);
    [SerializeField] private Vector3 closedLocalScale = new Vector3(1f, 1f, 1f);

    [Header("Animation")]
    [SerializeField] private float speed = 3f;

    public bool IsOpen { get; private set; } = false;

    private void Update()
    {
        if (curtainPanel == null) return;
        Vector3 targetPos   = IsOpen ? openLocalPos   : closedLocalPos;
        Vector3 targetScale = IsOpen ? openLocalScale : closedLocalScale;
        curtainPanel.localPosition = Vector3.Lerp(curtainPanel.localPosition, targetPos,   Time.deltaTime * speed);
        curtainPanel.localScale    = Vector3.Lerp(curtainPanel.localScale,    targetScale, Time.deltaTime * speed);
    }

    /// <summary>Toggle curtain open/closed. Wire to Drawstring_Curtain XRSimpleInteractable.selectEntered.</summary>
    public void Toggle()
    {
        IsOpen = !IsOpen;
        Debug.Log($"[CurtainController] {gameObject.name} → {(IsOpen ? "OPEN" : "CLOSED")}");
    }
}
