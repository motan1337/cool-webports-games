using System.IO;
using UnityEditor;
using UnityEngine;

public static class KingdomEmptyFrames
{
    public static void Run()
    {
        const string texturePath = "Assets/Texture2D/KingdomEmptyFrame.png";
        var pixel = new Texture2D(1, 1, TextureFormat.RGBA32, false);
        pixel.SetPixel(0, 0, Color.clear);
        pixel.Apply();
        File.WriteAllBytes(texturePath, pixel.EncodeToPNG());
        Object.DestroyImmediate(pixel);
        AssetDatabase.ImportAsset(texturePath, ImportAssetOptions.ForceUpdate);
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        foreach (string name in new[] { "horse_puff_7", "boss_death_27", "trollcave_surface_destroy_18" })
        {
            string path = "Assets/Sprite/" + name + ".asset";
            var previous = AssetDatabase.LoadAssetAtPath<Sprite>(path);
            var fresh = Sprite.Create(texture, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0.5f), previous.pixelsPerUnit, 0, SpriteMeshType.FullRect);
            fresh.name = name;
            EditorUtility.CopySerialized(fresh, previous);
            EditorUtility.SetDirty(previous);
            Object.DestroyImmediate(fresh);
        }
        AssetDatabase.SaveAssets();
        Debug.Log("KINGDOM_EMPTY_FRAMES_MIGRATED=3");
    }
}
