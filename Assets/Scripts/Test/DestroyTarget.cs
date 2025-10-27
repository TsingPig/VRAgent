using UnityEngine;

public class DestroyTarget : MonoBehaviour
{
    public GameObject target;

    public void DestroyTargetObject()
    {
        Destroy(target);
        Debug.Log($"{target.name} has been destroyed");
    }
}
