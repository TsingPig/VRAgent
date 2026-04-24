using UnityEngine;

/// <summary>
/// Visual muzzle-flash quad. Hosts BUG-008 (visual indicator not reset).
/// </summary>
public class MuzzleFlashController : MonoBehaviour
{
    public static MuzzleFlashController Instance { get; private set; }

    public GameObject flashQuad;
    public float visibleDuration = 0.06f;

    private float _timer = 0f;
    private bool _showing = false;

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
    }

    public void Flash()
    {
        if (flashQuad != null) flashQuad.SetActive(true);
        _showing = true;
        _timer = 0f;
    }

    public void ForceHide()
    {
        if (flashQuad != null) flashQuad.SetActive(false);
        _showing = false;
    }

    private void Update()
    {
        if (!_showing) return;
        _timer += Time.deltaTime;
        if (_timer >= visibleDuration)
        {
            // BUG-008: timer expires but flashQuad is NOT deactivated.
            // CORRECT: if (flashQuad != null) flashQuad.SetActive(false);
            _showing = false;
            ShootingRangeOracleRegistry.Check("BUG-008",
                flashQuad != null && flashQuad.activeSelf,
                "Muzzle flash quad still active after window expired");
        }
    }
}
