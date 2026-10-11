using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;

public class KingdomTweaksMenu : MonoBehaviour
{
    private static readonly Color Pink = new Color32(255, 131, 181, 255);
    private GameObject panel;
    private GameObject canvasRoot;
    private Button opener;
    private Button[] choices;
    private Font font;
    private int lastClosedFrame = -1;

    public static void Attach(Menu menu)
    {
        if (menu.GetComponent<KingdomTweaksMenu>() != null) return;
        var view = menu.gameObject.AddComponent<KingdomTweaksMenu>();
        view.font = menu.continueButton.GetComponentInChildren<Text>(true).font;
        view.Build();
    }

    public bool CloseIfOpen()
    {
        if (lastClosedFrame == Time.frameCount) return true;
        if (panel == null || !panel.activeSelf) return false;
        panel.SetActive(false);
        lastClosedFrame = Time.frameCount;
        opener.Select();
        return true;
    }

    private void OnEnable()
    {
        if (canvasRoot != null) canvasRoot.SetActive(true);
        if (panel != null) panel.SetActive(false);
    }
    private void OnDisable() { if (canvasRoot != null) canvasRoot.SetActive(false); }
    private void OnDestroy()
    {
        KingdomTweaks.Changed -= Refresh;
        if (canvasRoot != null) Destroy(canvasRoot);
    }

    private RectTransform Rect(string name, Transform parent, Vector2 anchor, Vector2 position, Vector2 size)
    {
        var item = new GameObject(name, typeof(RectTransform));
        var rect = (RectTransform)item.transform;
        rect.SetParent(parent, false);
        rect.anchorMin = rect.anchorMax = anchor;
        rect.pivot = anchor;
        rect.anchoredPosition = position;
        rect.sizeDelta = size;
        return rect;
    }

    private Text Label(string name, Transform parent, string value, Vector2 position, Vector2 size, int fontSize)
    {
        var rect = Rect(name, parent, new Vector2(0f, 1f), position, size);
        var text = rect.gameObject.AddComponent<Text>();
        text.font = font;
        text.fontSize = fontSize;
        text.color = Pink;
        text.text = value;
        text.alignment = TextAnchor.MiddleLeft;
        text.raycastTarget = false;
        return text;
    }

    private Button MakeButton(string name, Transform parent, string value, Vector2 anchor, Vector2 position, Vector2 size)
    {
        var rect = Rect(name, parent, anchor, position, size);
        var image = rect.gameObject.AddComponent<Image>();
        image.color = new Color32(42, 12, 26, 255);
        var button = rect.gameObject.AddComponent<Button>();
        var colors = button.colors;
        colors.normalColor = Color.white;
        colors.highlightedColor = new Color32(255, 169, 202, 255);
        colors.selectedColor = colors.highlightedColor;
        colors.pressedColor = new Color32(175, 66, 114, 255);
        button.colors = colors;
        var text = Label("Label", rect, value, new Vector2(12f, 0f), new Vector2(size.x - 24f, size.y), 24);
        text.alignment = TextAnchor.MiddleCenter;
        return button;
    }

    private void Build()
    {
        var root = new GameObject("Tweaks canvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        canvasRoot = root;
        var canvas = root.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 100;
        var scaler = root.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1280f, 720f);
        scaler.matchWidthOrHeight = 1f;
        opener = MakeButton("Tweaks", root.transform, "Tweaks", new Vector2(1f, 1f), new Vector2(-24f, -24f), new Vector2(170f, 46f));
        var cover = Rect("Tweaks overlay", root.transform, Vector2.zero, Vector2.zero, Vector2.zero);
        cover.anchorMax = Vector2.one;
        cover.offsetMin = cover.offsetMax = Vector2.zero;
        cover.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.98f);
        panel = cover.gameObject;
        var body = Rect("Tweaks panel", cover, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(860f, 600f));
        Label("Title", body, "Tweaks", new Vector2(20f, -8f), new Vector2(810f, 46f), 36);
        Label("Storage", body, "Saved in this browser. All tweaks are optional.", new Vector2(20f, -55f), new Vector2(810f, 30f), 20);
        choices = new Button[KingdomTweaks.Titles.Length];
        for (int i = 0; i < choices.Length; i++)
        {
            var option = (KingdomTweaks.Option)i;
            float y = -96f - i * 60f;
            Label("Title " + i, body, KingdomTweaks.Titles[i], new Vector2(20f, y), new Vector2(640f, 30f), 24);
            Label("Detail " + i, body, KingdomTweaks.Details[i], new Vector2(20f, y - 30f), new Vector2(660f, 26f), 17);
            choices[i] = MakeButton("Choice " + i, body, "Off", new Vector2(0f, 1f), new Vector2(710f, y - 4f), new Vector2(125f, 44f));
            choices[i].onClick.AddListener(() => KingdomTweaks.Set(option, !KingdomTweaks.Get(option)));
        }
        var reset = MakeButton("Reset tweaks", body, "Reset tweaks", new Vector2(0f, 1f), new Vector2(20f, -536f), new Vector2(240f, 44f));
        reset.onClick.AddListener(KingdomTweaks.Reset);
        var back = MakeButton("Back", body, "Back", new Vector2(0f, 1f), new Vector2(650f, -536f), new Vector2(185f, 44f));
        back.onClick.AddListener(() => CloseIfOpen());
        opener.onClick.AddListener(() => { panel.SetActive(true); Refresh(); choices[0].Select(); });
        KingdomTweaks.Changed += Refresh;
        Refresh();
        panel.SetActive(false);
        root.SetActive(isActiveAndEnabled);
    }

    private void Refresh()
    {
        for (int i = 0; i < choices.Length; i++)
            choices[i].GetComponentInChildren<Text>().text = KingdomTweaks.Get((KingdomTweaks.Option)i) ? "On" : "Off";
    }
}
