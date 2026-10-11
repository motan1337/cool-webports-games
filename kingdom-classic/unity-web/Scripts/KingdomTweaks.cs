using System;
using UnityEngine;

public static class KingdomTweaks
{
    public enum Option { LongerSprint, FasterRecovery, RecruitsRunHome, BuildersHurry, QuickerGrazing, NoCameraShake, StaminaMeter }
    public static readonly string[] Titles = {
        "Double sprint time", "Double stamina recovery", "Recruits run home",
        "Builders hurry to jobs", "Quicker grazing", "No camera shake", "Show stamina"
    };
    public static readonly string[] Details = {
        "Use half as much stamina while running.", "Recover stamina and clear exhaustion twice as fast.",
        "Recruits outside your walls run back towards the campfire.", "Builders travel to jobs 50% faster. Hammer speed stays the same.",
        "Start grazing and finish a meal in half the time.", "Stop the camera shaking on impacts.",
        "Show your mount's remaining stamina above the bottom edge."
    };
    private static bool[] values;
    public static event Action Changed;
    private static string Key(Option option) { return "kingdom.tweaks.v1." + option; }
    private static void Load()
    {
        if (values != null) return;
        values = new bool[Titles.Length];
        for (int i = 0; i < values.Length; i++) values[i] = PlayerPrefs.GetInt(Key((Option)i), 0) == 1;
    }
    public static bool Get(Option option)
    {
        Load();
        return values[(int)option];
    }
    public static void Set(Option option, bool enabled)
    {
        Load();
        values[(int)option] = enabled;
        PlayerPrefs.SetInt(Key(option), enabled ? 1 : 0);
        PlayerPrefs.Save();
        if (Changed != null) Changed();
    }
    public static void Reset()
    {
        Load();
        for (int i = 0; i < values.Length; i++)
        {
            values[i] = false;
            PlayerPrefs.DeleteKey(Key((Option)i));
        }
        PlayerPrefs.Save();
        if (Changed != null) Changed();
    }
    public static float StaminaRate(float rate)
    {
        return rate < 0f ? rate * (Get(Option.LongerSprint) ? 0.5f : 1f)
            : rate * (Get(Option.FasterRecovery) ? 2f : 1f);
    }
    public static float WorkTravelSpeed(float speed) { return speed * (Get(Option.BuildersHurry) ? 1.5f : 1f); }
    public static float GrazingTime(float seconds) { return seconds * (Get(Option.QuickerGrazing) ? 0.5f : 1f); }
}
