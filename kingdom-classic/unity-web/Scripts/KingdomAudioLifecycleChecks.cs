#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

public class KingdomAudioLifecycleChecks : MonoBehaviour
{
    [Serializable]
    public class Result
    {
        public bool ambientParameters;
        public bool dryWeatherSilent;
        public bool rainResponds;
        public bool regionLayers;
        public bool stepTailsSurvive;
        public bool stepChangeStopsOldGait;
        public bool standingStopsAllSteps;
        public bool ambientRestartSurvivesOldFade;
        public bool passed;
        public List<string> errors = new List<string>();
    }

    private const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;

    public IEnumerator Check(Result result)
    {
        var ambient = Managers.ambient;
        bool enabled = ambient.enabled;
        ambient.enabled = false;
        string[] names = { "WindVol", "ForestWindVol", "RainVol", "MeadowVol", "ForestVol" };
        var saved = new float[names.Length];
        result.ambientParameters = true;
        for (int i = 0; i < names.Length; i++)
            result.ambientParameters &= ambient.ambientMixer.GetFloat(names[i], out saved[i]);
        try
        {
            var weather = typeof(AmbientManager).GetMethod("ApplyEnvironmentVolumes", Private);
            var region = typeof(AmbientManager).GetMethod("ApplyRegionVolumes", Private);
            weather.Invoke(ambient, new object[] { 0f, 0f });
            result.dryWeatherSilent = GainIs(ambient, "RainVol", -80f) && GainIs(ambient, "WindVol", -6.0206f);
            weather.Invoke(ambient, new object[] { 1f, 0.5f });
            result.rainResponds = GainIs(ambient, "RainVol", -6.0206f) && GainIs(ambient, "ForestWindVol", 0f);
            region.Invoke(ambient, new object[] { 0f, 0f });
            bool meadow = GainIs(ambient, "MeadowVol", 0f) && GainIs(ambient, "ForestVol", -39.928783f);
            region.Invoke(ambient, new object[] { 1f, 0f });
            bool forest = GainIs(ambient, "MeadowVol", -39.928783f) && GainIs(ambient, "ForestVol", 0f);
            region.Invoke(ambient, new object[] { 0f, 1f });
            bool castle = GainIs(ambient, "MeadowVol", -14.816608f) && GainIs(ambient, "ForestVol", -80f);
            result.regionLayers = meadow && forest && castle;
        }
        finally
        {
            for (int i = 0; i < names.Length; i++) ambient.ambientMixer.SetFloat(names[i], saved[i]);
            ambient.enabled = enabled;
        }

        var steed = (Steed)typeof(Player).GetField("_steed", Private).GetValue(Managers.kingdom.player);
        var animator = steed.GetComponent<Animator>();
        enabled = animator.enabled;
        animator.enabled = false;
        steed.OnAnimStandStart();
        steed.OnAnimGallopStart();
        var first = (AudioEmitter)typeof(Steed).GetField("_gallopSound", Private).GetValue(steed);
        yield return new WaitForSecondsRealtime(0.1f);
        steed.OnAnimGallopStart();
        var second = (AudioEmitter)typeof(Steed).GetField("_gallopSound", Private).GetValue(steed);
        result.stepTailsSurvive = first != null && second != null && first != second &&
            first.GetComponent<AudioSource>().isPlaying && second.GetComponent<AudioSource>().isPlaying;
        steed.OnAnimWalkStart();
        result.stepChangeStopsOldGait = Stopped(first) && Stopped(second);
        var walking = (AudioEmitter)typeof(Steed).GetField("_walkSound", Private).GetValue(steed);
        steed.OnAnimStandStart();
        result.standingStopsAllSteps = Stopped(walking);
        animator.enabled = enabled;

        var holder = new GameObject("Ambient fade fixture");
        var source = holder.AddComponent<AudioSource>();
        source.clip = Resources.Load<GameObject>("prefabs/characters/Worker").GetComponent<Worker>().buildingSound.clips[0];
        source.volume = 0.2f;
        source.loop = true;
        source.playOnAwake = false;
        var timed = holder.AddComponent<TimeBasedAudio>();
        timed.enabled = false;
        timed.fadeDuration = 0.15f;
        var start = typeof(TimeBasedAudio).GetMethod("StartPlaying", Private);
        var stop = typeof(TimeBasedAudio).GetMethod("StopPlaying", Private);
        start.Invoke(timed, null);
        yield return new WaitForSecondsRealtime(0.2f);
        stop.Invoke(timed, null);
        yield return new WaitForSecondsRealtime(0.05f);
        start.Invoke(timed, null);
        yield return new WaitForSecondsRealtime(0.25f);
        result.ambientRestartSurvivesOldFade = source.isPlaying && Mathf.Abs(source.volume - 0.2f) < 0.01f;
        Destroy(holder);

        if (!result.ambientParameters) result.errors.Add("Ambient mixer parameters are missing.");
        if (!result.dryWeatherSilent || !result.rainResponds) result.errors.Add("Weather audio does not match rain and wind levels.");
        if (!result.regionLayers) result.errors.Add("Ambient region layers overlap at incorrect gains.");
        if (!result.stepTailsSurvive) result.errors.Add("Repeated hoofbeat events cut off the prior clip.");
        if (!result.stepChangeStopsOldGait || !result.standingStopsAllSteps) result.errors.Add("Hoofbeats continue after changing gait or standing.");
        if (!result.ambientRestartSurvivesOldFade) result.errors.Add("A cancelled ambient fade stops resumed playback.");
        result.passed = result.errors.Count == 0;
    }

    private static bool GainIs(AmbientManager ambient, string parameter, float expected)
    {
        float gain;
        return ambient.ambientMixer.GetFloat(parameter, out gain) && Mathf.Abs(gain - expected) < 0.05f;
    }

    private static bool Stopped(AudioEmitter emitter)
    {
        return emitter == null || !emitter.GetComponent<AudioSource>().isPlaying;
    }
}
#endif
