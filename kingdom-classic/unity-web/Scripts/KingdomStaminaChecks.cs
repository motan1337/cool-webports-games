#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

public class KingdomStaminaChecks : MonoBehaviour
{
    [Serializable]
    public class Report
    {
        public bool fedProtectsStamina;
        public bool fedBonusDeclines;
        public bool secondWindIdentified;
        public bool exhaustionIdentifiedDuringRecovery;
        public bool interruptedGrazingDoesNotRefill;
        public bool finishedGrazingRefills;
        public bool pauseFreezesStaminaAndTimers;
        public bool meterDropsStalePlayer;
        public bool meterRebindsPlayer;
        public bool meterHidesWhilePaused;
        public bool meterRestoresAfterPause;
        public bool meterTracksFedBonus;
        public bool meterTracksSecondWind;
        public bool meterTracksExhaustion;
        public bool meterTracksGrazing;
        public bool fractionsClamped;
        public bool stateRestored;
        public float fedBefore;
        public float fedAfter;
        public float reserveStamina;
        public float recoveredWhileExhausted;
    }

    private const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
    public Report report = new Report();

    public IEnumerator Check(KingdomGameplayChecks.Result result)
    {
        var player = Managers.kingdom.player;
        if (player == null)
        {
            result.errors.Add("Stamina regression: no active player.");
            yield break;
        }
        var steed = (Steed)Field(player, "_steed");
        var mover = player.GetComponent<Mover>();
        var body = player.GetComponent<Rigidbody2D>();
        var animator = player.GetComponent<Animator>();
        var steedAnimator = steed.GetComponent<Animator>();
        var playerFields = Snapshot(player);
        var moverFields = Snapshot(mover);
        var steedFields = Snapshot(steed);
        var steedSettings = new Dictionary<FieldInfo, object>();
        foreach (string name in new[] { "runStaminaRate", "walkStaminaRate", "standStaminaRate", "eatDelay", "eatDuration", "wellFedDuration", "tiredDuration", "reserveStamina", "reserveProbability" })
        {
            var field = typeof(Steed).GetField(name);
            steedSettings.Add(field, field.GetValue(steed));
        }
        var tweaks = new bool[KingdomTweaks.Titles.Length];
        for (int i = 0; i < tweaks.Length; i++) tweaks[i] = KingdomTweaks.Get((KingdomTweaks.Option)i);
        bool playerEnabled = player.enabled;
        bool gameEnabled = Managers.game.enabled;
        bool moverEnabled = mover.enabled;
        bool animatorEnabled = animator.enabled;
        bool steedAnimatorEnabled = steedAnimator.enabled;
        bool simulated = body.simulated;
        var velocity = body.velocity;
        float angularVelocity = body.angularVelocity;
        bool infinite = player.infiniteStamina;
        bool puff = steed.puffActive;
        bool sparkles = steed.footSparklesActive;
        bool torch = player.torch.activeSelf;
        bool brake = steed.brakeDust.activeSelf;
        float originalStamina = player.stamina;
        float timeScale = Time.timeScale;
        var menuState = Managers.game.menuState;
        var scale = player.transform.localScale;
        var randomState = UnityEngine.Random.state;
        var meter = FindObjectOfType<KingdomStaminaMeter>();
        try
        {
            player.enabled = false;
            Managers.game.enabled = false;
            mover.enabled = false;
            animator.enabled = false;
            steedAnimator.enabled = false;
            body.simulated = false;
            player.infiniteStamina = false;
            Time.timeScale = 1f;
            Managers.game.menuState = Game.MenuState.None;
            for (int i = 0; i < tweaks.Length; i++) KingdomTweaks.Set((KingdomTweaks.Option)i, false);
            steed.runStaminaRate = -0.5f;
            steed.walkStaminaRate = 0.1f;
            steed.standStaminaRate = 0.1f;
            steed.eatDelay = 0.1f;
            steed.eatDuration = 1f;
            steed.wellFedDuration = 5f;
            steed.tiredDuration = 5f;
            steed.reserveStamina = 0.25f;
            yield return null;

            Prepare(player, 1, 0.6f, 5f, 0f, 0f);
            report.fedBefore = player.fedFraction;
            for (int i = 0; i < 3; i++)
            {
                Tick(player, 1);
                yield return null;
            }
            report.fedAfter = player.fedFraction;
            report.fedProtectsStamina = Close(player.staminaFraction, 0.6f) && player.staminaDisplayState == Player.StaminaDisplayState.Fed;
            report.fedBonusDeclines = report.fedAfter > 0f && report.fedAfter < report.fedBefore;

            Prepare(player, 1, 0f, -1f, 0f, 0f);
            steed.reserveProbability = 1f;
            Action(player, 1);
            report.reserveStamina = player.staminaFraction;
            report.secondWindIdentified = Close(report.reserveStamina, 0.25f) && player.hasSecondWind &&
                player.staminaDisplayState == Player.StaminaDisplayState.SecondWind;

            Prepare(player, 1, 0f, -1f, 0f, 0f);
            steed.reserveProbability = 0f;
            Action(player, 1);
            float exhaustionBefore = player.exhaustionFraction;
            for (int i = 0; i < 3; i++)
            {
                Tick(player, 1);
                yield return null;
            }
            report.recoveredWhileExhausted = player.staminaFraction;
            report.exhaustionIdentifiedDuringRecovery = report.recoveredWhileExhausted > 0f && !player.hasSecondWind &&
                player.exhaustionFraction > 0f && player.exhaustionFraction < exhaustionBefore &&
                player.staminaDisplayState == Player.StaminaDisplayState.Recovering;

            Prepare(player, 3, 0.3f, -1f, 1f, 0.25f);
            bool grazingProgressVisible = Close(player.grazingFraction, 0.25f) && player.staminaDisplayState == Player.StaminaDisplayState.Eating;
            Action(player, 1);
            SetField(player, "_eatTimer", 10f);
            Action(player, 1);
            report.interruptedGrazingDoesNotRefill = grazingProgressVisible && player.staminaFraction < 0.4f &&
                player.fedFraction == 0f && player.grazingFraction == 0f && player.staminaDisplayState != Player.StaminaDisplayState.Eating;

            Prepare(player, 3, 0.3f, -1f, 1f, steed.eatDuration + 0.01f);
            Action(player, 0);
            report.finishedGrazingRefills = Close(player.staminaFraction, 1f) && Close(player.fedFraction, 1f) &&
                player.exhaustionFraction == 0f && player.grazingFraction == 0f && player.staminaDisplayState == Player.StaminaDisplayState.Fed;

            Prepare(player, 1, 0.6f, 2f, 1f, 0.4f);
            Time.timeScale = 0f;
            yield return null;
            float staminaBeforePause = player.staminaFraction;
            float fedBeforePause = player.fedFraction;
            float tiredBeforePause = player.exhaustionFraction;
            float eatingBeforePause = (float)Field(player, "_eatTimer");
            for (int i = 0; i < 3; i++)
            {
                Tick(player, 1);
                yield return null;
            }
            report.pauseFreezesStaminaAndTimers = Close(player.staminaFraction, staminaBeforePause) &&
                Close(player.fedFraction, fedBeforePause) && Close(player.exhaustionFraction, tiredBeforePause) &&
                Close((float)Field(player, "_eatTimer"), eatingBeforePause);
            Time.timeScale = 1f;
            yield return null;

            player.stamina = 2f;
            bool upperBound = Close(player.staminaFraction, 1f);
            player.stamina = -1f;
            SetField(player, "_wellFedTimer", -1f);
            SetField(player, "_tiredTimer", -1f);
            report.fractionsClamped = upperBound && player.staminaFraction == 0f && player.fedFraction == 0f && player.exhaustionFraction == 0f;

            if (meter != null)
            {
                player.enabled = true;
                KingdomTweaks.Set(KingdomTweaks.Option.StaminaMeter, true);
                Managers.game.menuState = Game.MenuState.None;
                RefreshMeter(meter);
                bool initiallyBound = meter.displayedPlayer == player;
                Managers.kingdom.player = null;
                RefreshMeter(meter);
                report.meterDropsStalePlayer = initiallyBound && meter.displayedPlayer == null && !MeterVisible(meter);
                Managers.kingdom.player = player;
                RefreshMeter(meter);
                report.meterRebindsPlayer = meter.displayedPlayer == player && MeterVisible(meter);
                Prepare(player, 1, 0.6f, 2f, 0f, 0f);
                RefreshMeter(meter);
                report.meterTracksFedBonus = meter.displayedState == Player.StaminaDisplayState.Fed &&
                    Close(meter.displayedStamina, 0.6f) && Close(meter.displayedBonus, 0.4f);
                Prepare(player, 1, 0f, -1f, 0f, 0f);
                steed.reserveProbability = 1f;
                Action(player, 1);
                RefreshMeter(meter);
                report.meterTracksSecondWind = meter.displayedState == Player.StaminaDisplayState.SecondWind &&
                    Close(meter.displayedStamina, 0.25f);
                Prepare(player, 1, 0f, -1f, 0f, 0f);
                steed.reserveProbability = 0f;
                Action(player, 1);
                RefreshMeter(meter);
                report.meterTracksExhaustion = meter.displayedState == Player.StaminaDisplayState.Recovering &&
                    Close(meter.displayedBonus, 1f);
                Prepare(player, 3, 0.3f, -1f, 1f, 0.5f);
                RefreshMeter(meter);
                report.meterTracksGrazing = meter.displayedState == Player.StaminaDisplayState.Eating &&
                    Close(meter.displayedStamina, 0.3f) && Close(meter.displayedBonus, 0.5f);
                Managers.game.menuState = Game.MenuState.Menu;
                RefreshMeter(meter);
                report.meterHidesWhilePaused = !MeterVisible(meter);
                Managers.game.menuState = Game.MenuState.None;
                RefreshMeter(meter);
                report.meterRestoresAfterPause = meter.displayedPlayer == player && MeterVisible(meter);
                player.enabled = false;
            }
        }
        finally
        {
            Managers.kingdom.player = player;
            steed.puffActive = false;
            Restore(player, playerFields);
            Restore(mover, moverFields);
            Restore(steed, steedFields);
            foreach (var setting in steedSettings) setting.Key.SetValue(steed, setting.Value);
            steed.puffActive = false;
            steed.puffActive = puff;
            steed.footSparklesActive = !sparkles;
            steed.footSparklesActive = sparkles;
            steed.brakeDust.SetActive(brake);
            player.torch.SetActive(torch);
            player.stamina = originalStamina;
            player.infiniteStamina = infinite;
            player.transform.localScale = scale;
            animator.ResetTrigger("Eat");
            animator.ResetTrigger("Rear");
            steedAnimator.ResetTrigger("Eat");
            steedAnimator.ResetTrigger("Rear");
            animator.enabled = animatorEnabled;
            steedAnimator.enabled = steedAnimatorEnabled;
            body.simulated = simulated;
            body.velocity = velocity;
            body.angularVelocity = angularVelocity;
            mover.enabled = moverEnabled;
            player.enabled = playerEnabled;
            Managers.game.enabled = gameEnabled;
            Managers.game.menuState = menuState;
            Time.timeScale = timeScale;
            UnityEngine.Random.state = randomState;
            for (int i = 0; i < tweaks.Length; i++) KingdomTweaks.Set((KingdomTweaks.Option)i, tweaks[i]);
            report.stateRestored = Close(player.stamina, originalStamina) && player.enabled == playerEnabled &&
                player.infiniteStamina == infinite && Managers.kingdom.player == player;
            if (meter != null) RefreshMeter(meter);
        }
        foreach (var field in typeof(Report).GetFields(BindingFlags.Instance | BindingFlags.Public))
            if (field.FieldType == typeof(bool) && !(bool)field.GetValue(report))
                result.errors.Add("Stamina regression: " + field.Name + " failed.");
        Debug.Log("KINGDOM_STAMINA_CHECKS " + JsonUtility.ToJson(report, true));
    }

    private static bool Close(float first, float second) { return Mathf.Abs(first - second) < 0.00001f; }
    private static object Field(object owner, string name) { return owner.GetType().GetField(name, Private).GetValue(owner); }
    private static void SetField(object owner, string name, object value) { owner.GetType().GetField(name, Private).SetValue(owner, value); }
    private static Dictionary<FieldInfo, object> Snapshot(object owner)
    {
        var fields = new Dictionary<FieldInfo, object>();
        foreach (var field in owner.GetType().GetFields(Private)) fields.Add(field, field.GetValue(owner));
        return fields;
    }
    private static void Restore(object owner, Dictionary<FieldInfo, object> fields)
    {
        foreach (var field in fields) field.Key.SetValue(owner, field.Value);
    }
    private static void Prepare(Player player, int state, float stamina, float fed, float tired, float eating)
    {
        var field = typeof(Player).GetField("_actionState", Private);
        field.SetValue(player, Enum.ToObject(field.FieldType, state));
        SetField(player, "_previousKeyDirection", 1);
        SetField(player, "_groundType", Player.GroundType.Normal);
        SetField(player, "_wellFedTimer", fed);
        SetField(player, "_tiredTimer", tired);
        SetField(player, "_eatTimer", eating);
        SetField(player, "_usingReserve", false);
        player.stamina = stamina;
    }
    private static void Action(Player player, int direction)
    {
        typeof(Player).GetMethod("UpdateActionState", Private).Invoke(player, new object[] { direction, false, false });
    }
    private static void Tick(Player player, int direction)
    {
        typeof(Player).GetMethod("Update", Private).Invoke(player, null);
        Action(player, direction);
    }
    private static void RefreshMeter(KingdomStaminaMeter meter)
    {
        typeof(KingdomStaminaMeter).GetMethod("LateUpdate", Private).Invoke(meter, null);
    }
    private static bool MeterVisible(KingdomStaminaMeter meter)
    {
        return ((GameObject)Field(meter, "display")).activeSelf;
    }
}
#endif
