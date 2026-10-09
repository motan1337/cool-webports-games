using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class KingdomSpriteMigration
{
    public static void Validate()
    {
        string root = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
        var inventory = JsonUtility.FromJson<Inventory>(File.ReadAllText(Path.Combine(root, "analysis/sprite-migration.json")));
        int checkedCount = 0;
        foreach (Item item in inventory.items)
        {
            Sprite sprite = AssetDatabase.LoadAssetAtPath<Sprite>(item.path);
            var vertices = sprite.vertices;
            var uv = sprite.uv;
            var triangles = sprite.triangles;
            if (vertices.Length != item.vertices.Length || triangles.Length != item.triangles.Length)
                throw new Exception("Sprite mesh count mismatch: " + item.path);
            var pixelPivot = new Vector2(item.rect[0] + item.pivot[0] * item.rect[2], item.rect[1] + item.pivot[1] * item.rect[3]);
            for (int i = 0; i < vertices.Length; i++)
            {
                Vector2 expectedUV = new Vector2((item.vertices[i].x * item.ppu + pixelPivot.x) / sprite.texture.width,
                    (item.vertices[i].y * item.ppu + pixelPivot.y) / sprite.texture.height);
                if ((vertices[i] - item.vertices[i]).sqrMagnitude > 0.000001f || (uv[i] - expectedUV).sqrMagnitude > 0.000001f)
                    throw new Exception("Sprite vertex or UV mismatch: " + item.path + " index=" + i);
            }
            for (int i = 0; i < triangles.Length; i++)
                if (triangles[i] != item.triangles[i]) throw new Exception("Sprite triangle mismatch: " + item.path);
            checkedCount++;
        }
        File.WriteAllText(Path.Combine(root, "analysis/sprite-runtime-validation.txt"), "VALIDATED=" + checkedCount);
        Debug.Log("KINGDOM_SPRITE_RUNTIME_VALIDATED=" + checkedCount);
    }

    [Serializable] private class Item
    {
        public string path;
        public string textureGuid;
        public string name;
        public float ppu;
        public float[] rect;
        public float[] pivot;
        public float[] border;
        public Vector2[] vertices;
        public ushort[] triangles;
    }
    [Serializable] private class Inventory { public Item[] items; }

    public static void Run()
    {
        string root = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
        var inventory = JsonUtility.FromJson<Inventory>(File.ReadAllText(Path.Combine(root, "analysis/sprite-migration.json")));
        int migrated = 0;
        foreach (Item item in inventory.items)
        {
            string texturePath = AssetDatabase.GUIDToAssetPath(item.textureGuid);
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
            var existing = AssetDatabase.LoadAssetAtPath<Sprite>(item.path);
            if (texture == null || existing == null) throw new Exception("Missing sprite or texture: " + item.path);
            var rect = new Rect(item.rect[0], item.rect[1], item.rect[2], item.rect[3]);
            var pixelPivot = new Vector2(rect.x + item.pivot[0] * rect.width, rect.y + item.pivot[1] * rect.height);
            rect.xMin = Mathf.Max(0, rect.xMin);
            rect.yMin = Mathf.Max(0, rect.yMin);
            rect.xMax = Mathf.Min(texture.width, rect.xMax);
            rect.yMax = Mathf.Min(texture.height, rect.yMax);
            var pivot = new Vector2((pixelPivot.x - rect.x) / rect.width, (pixelPivot.y - rect.y) / rect.height);
            var fresh = Sprite.Create(texture, rect,
                pivot, item.ppu, 0, SpriteMeshType.FullRect,
                new Vector4(item.border[0], item.border[1], item.border[2], item.border[3]));
            fresh.name = item.name;
            fresh.OverrideGeometry(item.vertices, item.triangles);
            EditorUtility.CopySerialized(fresh, existing);
            EditorUtility.SetDirty(existing);
            UnityEngine.Object.DestroyImmediate(fresh);
            migrated++;
        }
        AssetDatabase.SaveAssets();
        File.WriteAllText(Path.Combine(root, "analysis/sprite-migration-result.txt"), "MIGRATED=" + migrated);
        Debug.Log("KINGDOM_SPRITES_MIGRATED=" + migrated);
    }
}
