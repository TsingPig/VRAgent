using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public abstract class TestBase : MonoBehaviour {
    public abstract void UpdateVertexData(TMP_VertexDataUpdateFlags flags);
}

public class Test : TestBase
{
    public GameObject go;
    // Start is called before the first frame update
    void Start()
    {

    }

    // Update is called once per frame
    void Update()
    {

    }

    public void TestFunc()
    {
        Debug.Log(go.name);
    }
    public string TestFuncStr()
    {
        return go.name;
    }
    public override void UpdateVertexData(TMP_VertexDataUpdateFlags flags)
    {

    }
}
