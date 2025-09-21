#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace HenryLab.VRAgent
{
    /// <summary>
    /// TagInitializer 是一个 Editor 脚本，在 Unity 编辑器加载时自动执行。
    /// 它用于检查并在项目中添加所需的自定义 Tag，确保在运行时相关功能不会因为缺少 Tag 而报错。
    /// 例如，VRExplorer 中的临时目标对象会使用 <see cref="Str.Tags.TempTargetTag"/>。
    /// </summary>
    [InitializeOnLoad]
    public static class TagInitializer
    {
        static TagInitializer()
        {
            AddTagIfNotExists(Str.Tags.TempTargetTag);
        }

        private static void AddTagIfNotExists(string tag)
        {
            SerializedObject tagManager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            SerializedProperty tagsProp = tagManager.FindProperty("tags");

            bool found = false;
            for(int i = 0; i < tagsProp.arraySize; i++)
            {
                SerializedProperty t = tagsProp.GetArrayElementAtIndex(i);
                if(t.stringValue.Equals(tag)) { found = true; break; }
            }

            if(!found)
            {
                tagsProp.InsertArrayElementAtIndex(tagsProp.arraySize);
                SerializedProperty newTag = tagsProp.GetArrayElementAtIndex(tagsProp.arraySize - 1);
                newTag.stringValue = tag;
                tagManager.ApplyModifiedProperties();
                Debug.Log($"Tag '{tag}' was added to the project.");
            }
        }
    }

#endif
}