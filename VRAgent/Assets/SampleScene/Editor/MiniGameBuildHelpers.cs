#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

namespace MiniGameBuild
{
    /// <summary>
    /// Shared helpers for all MiniGame_* SceneBuilder Editor scripts.
    /// Goal: each Build Scene menu item produces a fully decorated, lit scene
    /// with all named GameObjects ready for controller binding.
    /// </summary>
    public static class H
    {
        private const string MAT_DIR = "Assets/Materials/MiniGames";

        // ---------- GameObject helpers ----------

        public static GameObject Empty(GameObject parent, string name, Vector3 pos = default)
        {
            var t = parent.transform.Find(name);
            GameObject go;
            if (t != null) go = t.gameObject;
            else { go = new GameObject(name); go.transform.SetParent(parent.transform, false); }
            go.transform.localPosition = pos;
            return go;
        }

        public static GameObject Prim(GameObject parent, string name, PrimitiveType prim,
            Vector3 pos, Vector3 scale, Material mat = null, Vector3 rot = default)
        {
            var t = parent.transform.Find(name);
            GameObject go;
            if (t != null && t.GetComponent<MeshFilter>() != null)
            {
                go = t.gameObject;
            }
            else
            {
                if (t != null) Object.DestroyImmediate(t.gameObject);
                go = GameObject.CreatePrimitive(prim);
                go.name = name;
                go.transform.SetParent(parent.transform, false);
            }
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            go.transform.localEulerAngles = rot;
            if (mat != null)
            {
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null) mr.sharedMaterial = mat;
            }
            return go;
        }

        public static T EnsureComp<T>(GameObject go) where T : Component
        {
            var c = go.GetComponent<T>();
            return c != null ? c : go.AddComponent<T>();
        }

        public static void KinematicRb(GameObject go)
        {
            var rb = EnsureComp<Rigidbody>(go);
            rb.useGravity = false;
            rb.isKinematic = true;
        }

        public static void StripCollider(GameObject go)
        {
            var c = go.GetComponent<Collider>();
            if (c != null) Object.DestroyImmediate(c);
        }

        // ---------- Material helpers ----------

        public static Material Mat(string name, Color color, float metallic = 0f,
            float smoothness = 0.3f, Color? emission = null)
        {
            EnsureDir(MAT_DIR);
            string path = $"{MAT_DIR}/{name}.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing != null) return existing;

            var m = new Material(Shader.Find("Standard"));
            m.color = color;
            m.SetFloat("_Metallic", metallic);
            m.SetFloat("_Glossiness", smoothness);
            if (emission.HasValue)
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", emission.Value);
            }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        // ---------- Lighting ----------

        public static Light AddLight(GameObject parent, string name, LightType type,
            Vector3 pos, Color color, float intensity, float range = 10f,
            float spotAngle = 45f, Vector3 rot = default)
        {
            var go = Empty(parent, name, pos);
            go.transform.localEulerAngles = rot;
            var l = EnsureComp<Light>(go);
            l.type = type;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            if (type == LightType.Spot) l.spotAngle = spotAngle;
            l.shadows = LightShadows.Soft;
            return l;
        }

        // ---------- Environment helpers ----------

        /// <summary>Build a rectangular room: floor + 4 walls + optional ceiling.</summary>
        public static void BuildRoom(GameObject root, Vector3 center, Vector3 size,
            Material floorMat, Material wallMat, Material ceilingMat = null,
            float wallThickness = 0.15f, bool addCeiling = true)
        {
            // Floor
            Prim(root, "Env_Floor", PrimitiveType.Cube,
                new Vector3(center.x, center.y - 0.05f, center.z),
                new Vector3(size.x, 0.1f, size.z), floorMat);

            // Ceiling
            if (addCeiling && ceilingMat != null)
                Prim(root, "Env_Ceiling", PrimitiveType.Cube,
                    new Vector3(center.x, center.y + size.y, center.z),
                    new Vector3(size.x, 0.1f, size.z), ceilingMat);

            float halfX = size.x * 0.5f;
            float halfZ = size.z * 0.5f;
            float wy = center.y + size.y * 0.5f;

            Prim(root, "Env_WallN", PrimitiveType.Cube,
                new Vector3(center.x, wy, center.z + halfZ),
                new Vector3(size.x, size.y, wallThickness), wallMat);
            Prim(root, "Env_WallS", PrimitiveType.Cube,
                new Vector3(center.x, wy, center.z - halfZ),
                new Vector3(size.x, size.y, wallThickness), wallMat);
            Prim(root, "Env_WallE", PrimitiveType.Cube,
                new Vector3(center.x + halfX, wy, center.z),
                new Vector3(wallThickness, size.y, size.z), wallMat);
            Prim(root, "Env_WallW", PrimitiveType.Cube,
                new Vector3(center.x - halfX, wy, center.z),
                new Vector3(wallThickness, size.y, size.z), wallMat);
        }

        /// <summary>Set the ambient + skybox simply.</summary>
        public static void Atmosphere(Color ambient, float ambientIntensity = 1f)
        {
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = ambient;
            RenderSettings.ambientIntensity = ambientIntensity;
        }

        // ---------- Player rig (keyboard+mouse test player) ----------

        /// <summary>
        /// Build (or update) a keyboard+mouse first-person player rig under root.
        /// - Adds CharacterController + PlayerRig
        /// - Camera child at eye height (1.6 m local)
        /// - Tags MainCamera so default rendering works (removes any other MainCamera in root)
        /// </summary>
        public static GameObject BuildPlayer(GameObject root, Vector3 spawnPos, float yawDeg = 0f)
        {
            // Remove any standalone "Main Camera" floating in the scene root to avoid duplicates
            var stray = GameObject.Find("Main Camera");
            if (stray != null && stray.transform.parent == null)
                Object.DestroyImmediate(stray);

            var player = Empty(root, "Player", spawnPos);
            player.transform.localEulerAngles = new Vector3(0, yawDeg, 0);

            var cc = EnsureComp<CharacterController>(player);
            cc.height = 1.8f;
            cc.radius = 0.30f;
            cc.center = new Vector3(0, 0.9f, 0);
            cc.skinWidth = 0.02f;

            // Visual capsule (first-person view typically hides body, but keeps shadow)
            var body = Prim(player, "Body", PrimitiveType.Capsule, new Vector3(0, 0.9f, 0),
                new Vector3(0.55f, 0.9f, 0.55f),
                Mat("PR_PlayerBody", new Color(0.20f, 0.45f, 0.85f), 0f, 0.4f));
            StripCollider(body);
            // Disable renderer for FPS feel
            var br = body.GetComponent<MeshRenderer>();
            if (br != null) br.enabled = false;

            // Camera (eye height 1.65m)
            var camGo = Empty(player, "Camera", new Vector3(0, 1.65f, 0));
            var cam = EnsureComp<Camera>(camGo);
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 200f;
            cam.fieldOfView = 70f;
            EnsureComp<AudioListener>(camGo);
            camGo.tag = "MainCamera";

            // Hand anchor in front of camera
            var hand = Empty(camGo, "HandAnchor", new Vector3(0.20f, -0.20f, 0.50f));

            var rig = EnsureComp<PlayerRig>(player);
            rig.cam = cam;
            rig.handAnchor = hand.transform;

            return player;
        }

        private static void EnsureDir(string assetDir)
        {
            if (AssetDatabase.IsValidFolder(assetDir)) return;
            string parent = Path.GetDirectoryName(assetDir).Replace('\\', '/');
            string leaf = Path.GetFileName(assetDir);
            if (!AssetDatabase.IsValidFolder(parent)) EnsureDir(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }
    }
}
#endif
