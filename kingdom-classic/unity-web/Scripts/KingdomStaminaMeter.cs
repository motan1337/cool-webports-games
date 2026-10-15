using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class KingdomStaminaMeter : MonoBehaviour
{
    private Player player;
    private Image bar;
    private Image auxiliary;
    private GameObject display;
    private Text status;
    public Player displayedPlayer { get { return player; } }
    public float displayedStamina { get; private set; }
    public float displayedBonus { get; private set; }
    public Player.StaminaDisplayState displayedState { get; private set; }

    [RuntimeInitializeOnLoadMethod]
    private static void Initialize()
    {
        if (FindObjectOfType<KingdomStaminaMeter>() != null) return;
        var host = new GameObject("Stamina meter");
        DontDestroyOnLoad(host);
        host.AddComponent<KingdomStaminaMeter>();
    }

    private RectTransform Rect(string name, Transform parent, Vector2 position, Vector2 size)
    {
        var rect = new GameObject(name, typeof(RectTransform)).GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0f);
        rect.pivot = new Vector2(0.5f, 0f);
        rect.anchoredPosition = position;
        rect.sizeDelta = size;
        return rect;
    }

    private Image Fill(string name, Transform parent, float y, Color color)
    {
        var track = Rect(name + " track", parent, new Vector2(0f, y), new Vector2(112f, 5f));
        var background = track.gameObject.AddComponent<Image>();
        background.color = new Color32(34, 30, 27, 255);
        background.raycastTarget = false;
        var fill = Rect(name, track, Vector2.one, new Vector2(110f, 3f));
        fill.anchorMin = fill.anchorMax = fill.pivot = Vector2.zero;
        var image = fill.gameObject.AddComponent<Image>();
        image.color = color;
        image.raycastTarget = false;
        return image;
    }

    private void Awake()
    {
        var root = new GameObject("Stamina canvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
        root.transform.SetParent(transform, false);
        root.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
        root.GetComponent<Canvas>().sortingOrder = 90;
        root.GetComponent<Canvas>().pixelPerfect = true;
        var scaler = root.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(480f, 270f);
        scaler.matchWidthOrHeight = 1f;
        display = Rect("Stamina", root.transform, new Vector2(0f, 8f), new Vector2(180f, 26f)).gameObject;
        bar = Fill("Stamina", display.transform, 5f, new Color32(218, 207, 184, 255));
        auxiliary = Fill("Bonus or rest", display.transform, 0f, new Color32(154, 137, 101, 255));
        display.SetActive(false);
    }

    private void BindFont()
    {
        if (status != null) return;
        var template = KingdomTweaksMenu.NativeTextTemplate;
        if (template == null)
        {
            var menu = FindObjectOfType<Menu>(true);
            if (menu != null && menu.continueButton != null)
                template = menu.continueButton.GetComponentInChildren<Text>(true);
        }
        if (template == null) return;
        status = KingdomTweaksMenu.CreateText(template, display.transform, "Stamina state", "STAMINA");
        status.color = bar.color;
        status.alignment = TextAnchor.MiddleCenter;
        status.horizontalOverflow = HorizontalWrapMode.Overflow;
        status.verticalOverflow = VerticalWrapMode.Overflow;
        status.rectTransform.anchorMin = status.rectTransform.anchorMax = new Vector2(0.5f, 0f);
        status.rectTransform.pivot = new Vector2(0.5f, 0f);
        status.rectTransform.anchoredPosition = new Vector2(0f, 12f);
        status.rectTransform.sizeDelta = new Vector2(180f, 12f);
    }

    private void LateUpdate()
    {
        player = SceneManager.GetActiveScene().name == "main" && Managers.kingdom != null ? Managers.kingdom.player : null;
        bool visible = KingdomTweaks.Get(KingdomTweaks.Option.StaminaMeter) && player != null &&
            player.isActiveAndEnabled && Managers.game != null && Managers.game.menuState == Game.MenuState.None &&
            (Managers.game.gameState == Game.GameState.Game || Managers.game.gameState == Game.GameState.Intro);
        display.SetActive(visible);
        if (!visible) return;
        BindFont();
        displayedStamina = player.staminaFraction;
        displayedState = player.staminaDisplayState;
        displayedBonus = displayedState == Player.StaminaDisplayState.Recovering ? player.exhaustionFraction
            : displayedState == Player.StaminaDisplayState.Eating ? player.grazingFraction : player.fedFraction;
        bar.rectTransform.sizeDelta = new Vector2(Mathf.Round(110f * displayedStamina), 3f);
        auxiliary.rectTransform.sizeDelta = new Vector2(Mathf.Round(110f * displayedBonus), 3f);
        auxiliary.transform.parent.gameObject.SetActive(displayedBonus > 0f);
        if (status != null)
            status.text = displayedState == Player.StaminaDisplayState.Fed ? "FED BONUS"
                : displayedState == Player.StaminaDisplayState.Recovering ? "RECOVERING"
                : displayedState == Player.StaminaDisplayState.Eating ? "GRAZING"
                : displayedState == Player.StaminaDisplayState.SecondWind ? "SECOND WIND" : "STAMINA";
    }
}
