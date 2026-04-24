#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.AI;
using UnityEngine;
using UnityEngine.AI;

/// <summary>
/// Editor utility to configure NavMesh settings for the Apartment scene:
/// 1. Verify walls/floors/ceiling are Navigation Static (flag 8)
/// 2. Add NavMeshObstacle + Carve to door panels
/// 3. Bake the NavMesh
/// Run via menu: Tools → Apartment → Setup NavMesh
/// </summary>
public static class ApartmentNavMeshSetup
{
    // Objects that should be Navigation Static (walls, floors, ceilings, counters, large furniture)
    private static readonly string[] StaticPatterns = new[]
    {
        "Wall_", "IW_", "Floor_", "Ceiling",
        "Counter_", "CounterTop_",
        "DF_", "WF_",           // door frames, window frames
        "Sofa_", "TVStand",
        "Fridge_Body",
        "SBookshelf_", "MWardrobe_Body",
        "ShoeCabinet", "ShoeRack",
        "DiningTable_", "CoffeeTable_",
        "MDesk_", "SDesk_",
        "Bathtub_", "Toilet_", "Vanity_Cabinet", "Vanity_Top",
        "RangeHood", "UpperCab_",
        "Railing_",
        "Bal_Rack_", "Bal_Table_", "Bal_Pot",
    };

    // Door panel objects that should get NavMeshObstacle with Carve
    private static readonly string[] DoorPanelNames = new[]
    {
        "Door_Entrance_Panel",
        "Door_Bath_Panel",
        "Door_MBR_Panel",
        "Door_SBR_Panel",
    };

    [MenuItem("Tools/Apartment/Setup NavMesh (Static + Obstacles + Bake)")]
    public static void SetupAndBake()
    {
        int staticCount = SetNavigationStatic();
        int obstacleCount = AddDoorObstacles();

        Debug.Log($"[ApartmentNavMesh] Set {staticCount} objects as Navigation Static");
        Debug.Log($"[ApartmentNavMesh] Added NavMeshObstacle to {obstacleCount} door panels");

        // Bake
        UnityEditor.AI.NavMeshBuilder.BuildNavMesh();
        Debug.Log("[ApartmentNavMesh] NavMesh baked successfully!");

        EditorUtility.DisplayDialog("Apartment NavMesh Setup",
            $"Done!\n\n" +
            $"• {staticCount} objects → Navigation Static\n" +
            $"• {obstacleCount} doors → NavMeshObstacle (Carve)\n" +
            $"• NavMesh baked",
            "OK");
    }

    [MenuItem("Tools/Apartment/1. Set Navigation Static")]
    public static int SetNavigationStatic()
    {
        var allObjects = Object.FindObjectsOfType<GameObject>(true);
        int count = 0;

        foreach (var go in allObjects)
        {
            if (ShouldBeStatic(go.name))
            {
                var flags = GameObjectUtility.GetStaticEditorFlags(go);
                if ((flags & StaticEditorFlags.NavigationStatic) == 0)
                {
                    flags |= StaticEditorFlags.NavigationStatic;
                    GameObjectUtility.SetStaticEditorFlags(go, flags);
                    Undo.RecordObject(go, "Set Navigation Static");
                    count++;
                }
            }
        }

        if (count > 0)
        {
            EditorUtility.SetDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects()[0]);
            Debug.Log($"[ApartmentNavMesh] Marked {count} additional objects as Navigation Static");
        }
        else
        {
            Debug.Log("[ApartmentNavMesh] All matching objects already Navigation Static");
        }

        return count;
    }

    [MenuItem("Tools/Apartment/2. Add Door NavMeshObstacles")]
    public static int AddDoorObstacles()
    {
        int count = 0;

        foreach (string panelName in DoorPanelNames)
        {
            var go = GameObject.Find(panelName);
            if (go == null)
            {
                // Try searching inactive objects
                foreach (var obj in Resources.FindObjectsOfTypeAll<GameObject>())
                {
                    if (obj.name == panelName && obj.scene.isLoaded)
                    {
                        go = obj;
                        break;
                    }
                }
            }

            if (go == null)
            {
                Debug.LogWarning($"[ApartmentNavMesh] Door panel not found: {panelName}");
                continue;
            }

            var obstacle = go.GetComponent<NavMeshObstacle>();
            if (obstacle == null)
            {
                obstacle = Undo.AddComponent<NavMeshObstacle>(go);
                count++;
            }

            // Configure: box shape with carve enabled
            obstacle.shape = NavMeshObstacleShape.Box;
            obstacle.carving = true;
            obstacle.carvingMoveThreshold = 0.1f;
            obstacle.carvingTimeToStationary = 0.5f;
            obstacle.carveOnlyStationary = false;

            // Size from existing collider or renderer bounds
            var col = go.GetComponent<Collider>();
            if (col != null)
            {
                obstacle.center = col.bounds.center - go.transform.position;
                obstacle.size = col.bounds.size;
            }
            else
            {
                var rend = go.GetComponent<Renderer>();
                if (rend != null)
                {
                    obstacle.center = rend.bounds.center - go.transform.position;
                    obstacle.size = rend.bounds.size;
                }
                else
                {
                    // Reasonable default for a door
                    obstacle.center = Vector3.zero;
                    obstacle.size = new Vector3(0.9f, 2.1f, 0.05f);
                }
            }

            // Door panels should NOT be Navigation Static (they move)
            var flags = GameObjectUtility.GetStaticEditorFlags(go);
            if ((flags & StaticEditorFlags.NavigationStatic) != 0)
            {
                flags &= ~StaticEditorFlags.NavigationStatic;
                GameObjectUtility.SetStaticEditorFlags(go, flags);
            }

            EditorUtility.SetDirty(go);
            Debug.Log($"[ApartmentNavMesh] NavMeshObstacle (Carve) → {panelName}");
        }

        return count;
    }

    [MenuItem("Tools/Apartment/3. Bake NavMesh")]
    public static void BakeNavMesh()
    {
        UnityEditor.AI.NavMeshBuilder.BuildNavMesh();
        Debug.Log("[ApartmentNavMesh] NavMesh baked!");
    }

    private static bool ShouldBeStatic(string name)
    {
        foreach (var pattern in StaticPatterns)
        {
            if (name.StartsWith(pattern) || name == pattern.TrimEnd('_'))
                return true;
        }
        return false;
    }
}
#endif
