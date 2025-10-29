using UnityEngine;

public class ExitRoom : MonoBehaviour
{
    private void OnCollisionEnter(Collision collision)
    {
        if(collision.gameObject.CompareTag("Player"))
        {
            Debug.Log("Exit!");
            Application.Quit();
        }
    }
}
