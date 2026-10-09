using System.Runtime.InteropServices;

public static class KingdomBrowserSave
{
#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern void KingdomSyncSave();
    [DllImport("__Internal")]
    private static extern void KingdomExitGame();
#endif
    public static void Flush()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        KingdomSyncSave();
#endif
    }

    public static void Exit()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        KingdomExitGame();
#elif !UNITY_WEBGL
        UnityEngine.Application.Quit();
#endif
    }
}
