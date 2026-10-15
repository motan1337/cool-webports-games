#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public static class KingdomMenuChecks
{
    [Serializable]
    public class Result
    {
        public string font;
        public int labels;
        public int verifiedGlyphs;
        public bool originalCanvas;
        public bool originalSprites;
        public bool keyboardNavigation;
        public bool pointerTargets;
        public bool passed;
        public List<string> errors = new List<string>();
    }

    public static Result Validate(Menu menu)
    {
        var result = new Result();
        KingdomTweaksMenu.Attach(menu);
        var tweaks = menu.GetComponent<KingdomTweaksMenu>();
        var template = KingdomTweaksMenu.NativeTextTemplate;
        result.font = template.font.name;
        var expectedAtlas = template.mainTexture;
#if UNITY_EDITOR
        expectedAtlas = UnityEditor.AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Texture2D/Font Texture_0.texture2D");
        if (template.font.material.mainTexture != expectedAtlas)
            result.errors.Add("Original font does not reference its recovered atlas.");
#endif
        result.originalCanvas = tweaks.Panel.GetComponentInParent<Canvas>(true) == menu.optionsPanel.GetComponentInParent<Canvas>(true)
            && tweaks.Opener.transform.parent == menu.continueButton.transform.parent
            && tweaks.Panel.GetComponentsInChildren<Canvas>(true).Length == 0;
        var originalPanel = menu.optionsPanel.transform.GetChild(0).GetComponent<Image>();
        var body = tweaks.Panel.transform.GetChild(0).GetComponent<Image>();
        result.originalSprites = originalPanel.sprite == body.sprite && originalPanel.type == body.type
            && originalPanel.color == body.color && menu.optionsPanel.GetComponent<Image>().color == tweaks.Panel.GetComponent<Image>().color;
        foreach (var text in tweaks.Panel.GetComponentsInChildren<Text>(true))
        {
            result.labels++;
            if (text.font != template.font || text.fontSize != template.fontSize || text.mainTexture != expectedAtlas)
                result.errors.Add(text.name + " does not match the original font and material.");
            if (text.text != text.text.ToUpperInvariant())
                result.errors.Add(text.name + " uses lowercase slots reserved for icons.");
            foreach (var character in text.text)
            {
                if (character == ' ') continue;
                CharacterInfo glyph;
                if (!text.font.GetCharacterInfo(character, out glyph) || glyph.glyphWidth <= 0 || glyph.glyphHeight <= 0
                    || glyph.uvTopLeft == glyph.uvBottomRight)
                    result.errors.Add(text.name + " has an absent glyph: " + character);
                else result.verifiedGlyphs++;
            }
            if (text.preferredWidth > text.rectTransform.rect.width + 1f)
                result.errors.Add(text.name + " overflows its width: " + text.preferredWidth + "/" + text.rectTransform.rect.width);
        }
        var sequence = new List<Selectable>(tweaks.Choices);
        sequence.Add(tweaks.Panel.transform.Find("Tweaks Panel/Reset Tweaks").GetComponent<Button>());
        sequence.Add(tweaks.Panel.transform.Find("Tweaks Panel/Back").GetComponent<Button>());
        result.pointerTargets = tweaks.Opener.targetGraphic.raycastTarget && tweaks.Opener.interactable;
        foreach (var item in sequence)
            result.pointerTargets &= item.targetGraphic.raycastTarget && item.interactable;
        result.keyboardNavigation = tweaks.Opener.navigation.selectOnUp != null && tweaks.Opener.navigation.selectOnDown != null;
        for (int i = 0; i < sequence.Count; i++)
        {
            var item = sequence[i];
            result.keyboardNavigation &= item.navigation.mode == Navigation.Mode.Explicit
                && item.navigation.selectOnUp == sequence[(i + sequence.Count - 1) % sequence.Count]
                && item.navigation.selectOnDown == sequence[(i + 1) % sequence.Count];
        }
        if (!result.originalCanvas) result.errors.Add("Tweaks are outside the original menu canvas.");
        if (!result.originalSprites) result.errors.Add("Tweaks do not match the original menu panel graphics.");
        if (!result.keyboardNavigation) result.errors.Add("Tweaks keyboard navigation is incomplete.");
        if (!result.pointerTargets) result.errors.Add("Tweaks buttons have no active pointer target.");
        result.passed = result.labels == KingdomTweaks.Titles.Length * 3 + 3 && result.verifiedGlyphs > 100 && result.errors.Count == 0;
        return result;
    }
}
#endif
