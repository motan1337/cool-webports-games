using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

[InitializeOnLoad]
public static class KingdomGameplayRegression
{
    private const string Key = "KingdomGameplayRegression";

    static KingdomGameplayRegression()
    {
        EditorApplication.playModeStateChanged += state =>
        {
            if (state != PlayModeStateChange.EnteredPlayMode || !SessionState.GetBool(Key, false)) return;
            SessionState.SetBool(Key, false);
            var host = new GameObject("KingdomGameplayChecks");
            host.AddComponent<KingdomGameplayChecks>().Run();
        };
    }

    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/main.unity");
        Object.FindObjectOfType<Game>().skipIntro = true;
        foreach (var camera in Object.FindObjectsOfType<Camera>()) camera.cullingMask = 0;
        SessionState.SetBool(Key, true);
        EditorApplication.EnterPlaymode();
    }
}
