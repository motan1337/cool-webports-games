using System.Runtime.InteropServices;
using UnityEngine;

public class KingdomBrowserAudio : MonoBehaviour
{
#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")] private static extern void KingdomInstallAudioUnlock();
    [DllImport("__Internal")] private static extern void KingdomSetAudioPaused(int paused);

    [RuntimeInitializeOnLoadMethod]
    private static void Initialize()
    {
        var host = new GameObject("Browser audio activation");
        DontDestroyOnLoad(host);
        host.AddComponent<KingdomBrowserAudio>();
        KingdomInstallAudioUnlock();
    }

    private void LateUpdate() { KingdomSetAudioPaused(AudioListener.pause ? 1 : 0); }
#endif
}
