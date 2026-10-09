using System;
using System.Collections.Generic;
using UnityEngine;

public static class KingdomAudio
{
    [Serializable]
    private class Entry { public string name; public float seconds; }
    [Serializable]
    private class Catalog { public Entry[] clips; }
    private static Dictionary<string, float> durations;

    public static float Duration(AudioClip clip)
    {
        if (clip == null) return 0f;
        if (durations == null)
        {
            durations = new Dictionary<string, float>();
            var asset = Resources.Load<TextAsset>("KingdomAudioDurations");
            if (asset != null)
                foreach (var item in JsonUtility.FromJson<Catalog>(asset.text).clips)
                    durations[item.name] = item.seconds;
        }
        float duration;
        if (durations.TryGetValue(clip.name, out duration)) return duration;
        if (clip.loadState == AudioDataLoadState.Loaded) return clip.length;
        throw new InvalidOperationException("Missing unloaded audio duration: " + clip.name);
    }
}
