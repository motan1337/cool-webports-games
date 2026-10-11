using UnityEngine;

public sealed class KingdomWebInput
{
    private readonly KingdomInputState state = new KingdomInputState();
    private int polledFrame = -1;

    private void Poll()
    {
        if (polledFrame == Time.frameCount) return;
        polledFrame = Time.frameCount;
        bool left = Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow);
        bool right = Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow);
        bool pay = Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow);
        int horizontal = (right ? 1 : 0) - (left ? 1 : 0);
        int vertical = (Input.GetKey(KeyCode.UpArrow) ? 1 : 0) - (Input.GetKey(KeyCode.DownArrow) ? 1 : 0);
        state.Advance(Time.unscaledTime, horizontal, vertical, pay, Input.GetKey(KeyCode.LeftShift),
                      Input.GetKey(KeyCode.Return), Input.GetKey(KeyCode.Escape),
                      Input.GetKey(KeyCode.Tab), KingdomBrowserLifetime.focused);
    }

    public float GetAxisRaw(int id) { Poll(); return state.GetAxisRaw(id); }
    public float GetAxis(int id) { Poll(); return state.GetAxis(id); }
    public bool GetButton(int id) { Poll(); return state.GetButton(id); }
    public bool GetButtonDown(int id) { Poll(); return state.GetButtonDown(id); }
    public bool GetButtonUp(int id) { Poll(); return state.GetButtonUp(id); }
    public bool GetNegativeButtonDown(int id) { Poll(); return state.GetNegativeButtonDown(id); }
    public bool GetButtonDoublePressDown(int id) { Poll(); return state.GetButtonDoublePressDown(id); }
    public bool GetNegativeButtonDoublePressDown(int id) { Poll(); return state.GetNegativeButtonDoublePressDown(id); }
    public float GetButtonTimePressed(int id) { Poll(); return state.GetButtonTimePressed(id); }
    public float GetAxisRawTimeActive(int id) { Poll(); return state.GetAxisRawTimeActive(id); }
}

public sealed class KingdomBrowserLifetime : MonoBehaviour
{
    public static bool focused = true;

    [RuntimeInitializeOnLoadMethod]
    private static void Initialize()
    {
        GameObject host = new GameObject("Kingdom browser lifecycle");
        DontDestroyOnLoad(host);
        host.AddComponent<KingdomBrowserLifetime>();
    }

    private void OnApplicationFocus(bool value) { focused = value; }
    private void OnApplicationPause(bool value) { focused = !value; }
}

public static class KingdomInput
{
    private static readonly KingdomWebInput player = new KingdomWebInput();
    public static KingdomWebInput GetPlayer() { return player; }
}
