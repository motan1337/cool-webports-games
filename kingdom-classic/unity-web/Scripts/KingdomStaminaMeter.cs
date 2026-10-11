using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class KingdomStaminaMeter : MonoBehaviour
{
    private Player player;
    private Image bar;
    private GameObject display;
    private float nextLookup;

    [RuntimeInitializeOnLoadMethod]
    private static void Initialize()
    {
        var host = new GameObject("Stamina meter");
        DontDestroyOnLoad(host);
        host.AddComponent<KingdomStaminaMeter>();
    }

    private void Awake()
    {
        var canvasObject = new GameObject("Stamina canvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
        canvasObject.transform.SetParent(transform, false);
        canvasObject.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
        canvasObject.GetComponent<Canvas>().sortingOrder = 90;
        var scaler = canvasObject.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1280f, 720f);
        scaler.matchWidthOrHeight = 1f;
        var frame = new GameObject("Stamina", typeof(RectTransform), typeof(Image));
        frame.transform.SetParent(canvasObject.transform, false);
        var rect = (RectTransform)frame.transform;
        rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0f);
        rect.anchoredPosition = new Vector2(0f, 28f);
        rect.sizeDelta = new Vector2(182f, 14f);
        var background = frame.GetComponent<Image>();
        background.color = Color.black;
        background.raycastTarget = false;
        var fill = new GameObject("Fill", typeof(RectTransform), typeof(Image));
        fill.transform.SetParent(frame.transform, false);
        bar = fill.GetComponent<Image>();
        bar.color = new Color32(255, 131, 181, 255);
        bar.raycastTarget = false;
        bar.rectTransform.anchorMin = new Vector2(0f, 0.5f);
        bar.rectTransform.anchorMax = new Vector2(0f, 0.5f);
        bar.rectTransform.pivot = new Vector2(0f, 0.5f);
        bar.rectTransform.anchoredPosition = new Vector2(3f, 0f);
        display = frame;
        display.SetActive(false);
    }

    private void Update()
    {
        bool enabled = KingdomTweaks.Get(KingdomTweaks.Option.StaminaMeter) && SceneManager.GetActiveScene().name == "main";
        if (enabled && player == null && Time.unscaledTime > nextLookup)
        {
            nextLookup = Time.unscaledTime + 0.5f;
            player = FindObjectOfType<Player>();
        }
        enabled = enabled && player != null && Managers.game != null && Managers.game.menuState == Game.MenuState.None;
        display.SetActive(enabled);
        if (enabled) bar.rectTransform.sizeDelta = new Vector2(176f * Mathf.Clamp01(player.stamina), 8f);
    }
}
