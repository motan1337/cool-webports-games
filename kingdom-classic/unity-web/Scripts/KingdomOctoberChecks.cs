#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections;
using System.Reflection;
using UnityEngine;

public class KingdomOctoberChecks : MonoBehaviour
{
    private const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;

    public IEnumerator Check(KingdomGameplayChecks.Result result)
    {
        float volume;
        result.volumeParameterAvailable = Managers.audioManager.mainMixer.GetFloat("MasterVol", out volume);

        var observer = new GameObject("Scanner fixture");
        observer.transform.position = new Vector3(120f, 1f, 0f);
        for (int i = 0; i < 2; i++)
        {
            var item = new GameObject("Scanned item");
            item.layer = LayerMask.NameToLayer("Coins");
            item.transform.SetParent(observer.transform);
            item.transform.localPosition = new Vector3(i * 0.5f, 0f, 0f);
            item.AddComponent<BoxCollider2D>().isTrigger = true;
        }
        yield return new WaitForFixedUpdate();
        var scanner = new Scanner(observer.transform, LayerMask.GetMask("Coins"), 2f, 0.01f, 1f);
        typeof(Scanner).GetField("_lastRefresh", Private).SetValue(scanner, -10000f);
        foreach (var item in scanner.GetAll()) result.scannerFirstCount++;
        foreach (var item in scanner.GetAll()) result.scannerSecondCount++;
        Destroy(observer);

        var walker = new GameObject("Arrival fixture");
        walker.transform.position = new Vector3(130f, 5f, 0f);
        var body = walker.AddComponent<Rigidbody2D>();
        body.isKinematic = true;
        var mover = walker.AddComponent<Mover>();
        body.velocity = Vector2.right;
        mover.SetGoal(walker.transform.position.x, 1f);
        float initial = walker.transform.position.x;
        float until = Time.time + 0.7f;
        while (Time.time < until)
        {
            result.goalArrivalDrift = Mathf.Max(result.goalArrivalDrift, Mathf.Abs(walker.transform.position.x - initial));
            yield return null;
        }
        Destroy(walker);

        var prefab = Resources.Load<GameObject>("prefabs/objects/Catapult").GetComponent<WorkableCatapult>().boulderPrefab;
        var boulder = Instantiate(prefab, new Vector3(140f, 1f, 0f), Quaternion.identity).GetComponent<Boulder>();
        var stone = boulder.GetComponent<Rigidbody2D>();
        var ground = new GameObject("Impact fixture");
        var parent = new GameObject("Impact parent");
        ground.transform.SetParent(parent.transform);
        boulder.StuckProbability = 1f;
        stone.velocity = new Vector2(3f, 8f);
        typeof(Boulder).GetField("_bounces", Private).SetValue(boulder, 1);
        typeof(Boulder).GetField("_lastCollided", Private).SetValue(boulder, -10000d);
        typeof(Boulder).GetMethod("HitObject", Private).Invoke(boulder, new object[] { ground, true });
        var origin = boulder.transform.position;
        until = Time.time + 0.7f;
        while (Time.time < until)
        {
            result.groundedBoulderDrift = Mathf.Max(result.groundedBoulderDrift, Vector3.Distance(origin, boulder.transform.position));
            yield return null;
        }
        Destroy(boulder.gameObject);
        Destroy(parent);
        yield return CheckWalls(result);
        yield return CheckAudio(result);
        yield return CheckTweaks(result);
    }

    private IEnumerator CheckWalls(KingdomGameplayChecks.Result result)
    {
        var floor = new GameObject("Enemy test floor");
        floor.tag = "Ground";
        floor.transform.position = new Vector3(230f, 0f, 0f);
        floor.AddComponent<BoxCollider2D>().size = new Vector2(100f, 1.5f);
        var tower = Resources.Load<GameObject>("prefabs/buildings/Tower4");
        result.towerPassageIntended = tower.GetComponent<Wall>() == null;
        foreach (var collider in tower.GetComponentsInChildren<Collider2D>(true))
            if (collider.gameObject.layer == LayerMask.NameToLayer("Obstacles") && !collider.isTrigger)
                result.towerPassageIntended = false;
        for (int level = 1; level <= 4; level++)
        {
            float x = 200f + level * 10f;
            var wall = Instantiate(Resources.Load<GameObject>("prefabs/buildings/Wall" + level), new Vector3(x, 0f, 0f), Quaternion.identity);
            wall.GetComponent<WorkableBuilding>().CompleteConstruction();
            var damageable = wall.GetComponent<Damageable>();
            int before = damageable.hitPoints;
            var troll = Instantiate(Resources.Load<GameObject>("prefabs/enemies/Troll"), new Vector3(x + 2.5f, 1f, 0f), Quaternion.identity).GetComponent<Troll>();
            float minimum = troll.transform.position.x;
            float until = Time.time + 5f;
            while (Time.time < until && damageable != null && damageable.hitPoints == before)
            {
                minimum = Mathf.Min(minimum, troll.transform.position.x);
                yield return null;
            }
            if (minimum > x + 0.1f) result.wallsBlocking++;
            if (damageable != null && damageable.hitPoints < before) result.wallsDamaged++;
            result.wallDetails.Add("Wall" + level + " minX=" + minimum + " wallX=" + x + " enemy=" + troll.transform.position +
                " hp=" + (damageable == null ? -1 : damageable.hitPoints) + "/" + before +
                " ignored=" + Physics2D.GetIgnoreLayerCollision(20, 21) +
                " state=" + ((StateMachine<Troll.State>)typeof(Troll).GetField("_fsm", Private).GetValue(troll)).current +
                " charging=" + typeof(Troll).GetField("_isCharging", Private).GetValue(troll) +
                " landed=" + typeof(Troll).GetField("_touchedGround", Private).GetValue(troll) +
                " target=" + typeof(Troll).GetField("_attackTarget", Private).GetValue(troll));
            foreach (var collider in wall.GetComponentsInChildren<Collider2D>())
                result.wallDetails.Add(collider.name + " layer=" + collider.gameObject.layer + " bounds=" + collider.bounds +
                    " paths=" + (collider is PolygonCollider2D ? ((PolygonCollider2D)collider).pathCount.ToString() : "box"));
            Destroy(troll.gameObject);
            Destroy(wall);
            yield return null;
        }
        Destroy(floor);
    }

    private IEnumerator CheckAudio(KingdomGameplayChecks.Result result)
    {
        var manager = Managers.audioManager;
        float sound = manager.soundVolume;
        float music = manager.musicVolume;
        manager.MuteNone();
        yield return new WaitForSecondsRealtime(0.6f);
        manager.soundVolume = 0f;
        manager.musicVolume = 0.5f;
        float effectGain, musicGain;
        bool effectParameter = manager.mainMixer.GetFloat("EffectsVol", out effectGain);
        bool musicParameter = manager.mainMixer.GetFloat("MusicVol", out musicGain);
        result.independentAudioVolumes = effectParameter && musicParameter && effectGain <= -80f && Mathf.Abs(musicGain + 6.0206f) < 0.05f;
        var clip = Resources.Load<GameObject>("prefabs/characters/Worker").GetComponent<Worker>().buildingSound.clips[0];
        manager.PlayTrack(clip, true);
        yield return new WaitForSecondsRealtime(0.15f);
        manager.PlayTrack(clip, true);
        yield return new WaitForSecondsRealtime(0.6f);
        foreach (var source in manager.GetComponents<AudioSource>()) if (source.isPlaying) result.musicSourcesAfterCrossfade++;
        manager.FadeCurrentTrack();
        yield return new WaitForSecondsRealtime(0.6f);
        foreach (var source in manager.GetComponents<AudioSource>()) if (source.isPlaying) result.musicSourcesAfterFade++;
        manager.soundVolume = sound;
        manager.musicVolume = music;
        manager.PlayTrack(Managers.holder.soundTrack[0], true);
        float until = Time.unscaledTime + 15f;
        while (Time.unscaledTime < until && !result.soundtrackPlaying)
        {
            foreach (var source in manager.GetComponents<AudioSource>())
                if (source.isPlaying && source.clip == Managers.holder.soundTrack[0]) result.soundtrackPlaying = true;
            yield return null;
        }
        manager.StopTracks();
        var emitter = Resources.Load<GameObject>("prefabs/characters/Worker").GetComponent<Worker>().buildingSound;
        var sources = new AudioSource[10];
        for (int i = 0; i < sources.Length; i++) sources[i] = emitter.Play().GetComponent<AudioSource>();
        yield return new WaitForSecondsRealtime(0.15f);
        foreach (var source in sources) if (source != null && source.isPlaying) result.simultaneousEffects++;
        manager.Pause();
        yield return new WaitForSecondsRealtime(1.4f);
        result.effectsSurvivePause = true;
        foreach (var source in sources) if (source == null) result.effectsSurvivePause = false;
        manager.Resume();
        yield return new WaitForSecondsRealtime(1.5f);
        foreach (var source in sources) if (source != null && source.gameObject.activeInHierarchy) result.lingeringEffects++;
    }

    private IEnumerator CheckTweaks(KingdomGameplayChecks.Result result)
    {
        var saved = new bool[KingdomTweaks.Titles.Length];
        for (int i = 0; i < saved.Length; i++) saved[i] = KingdomTweaks.Get((KingdomTweaks.Option)i);
        var player = Managers.kingdom.player;
        player.enabled = false;
        var state = typeof(Player).GetField("_actionState", Private);
        var direction = typeof(Player).GetField("_previousKeyDirection", Private);
        var fed = typeof(Player).GetField("_wellFedTimer", Private);
        var ground = typeof(Player).GetField("_groundType", Private);
        var oldState = state.GetValue(player);
        var oldDirection = direction.GetValue(player);
        var oldFed = fed.GetValue(player);
        var oldGround = ground.GetValue(player);
        float oldStamina = player.stamina;
        try
        {
            var action = typeof(Player).GetMethod("UpdateActionState", Private);
            direction.SetValue(player, 1);
            fed.SetValue(player, -1f);
            ground.SetValue(player, Player.GroundType.Normal);
            state.SetValue(player, System.Enum.ToObject(state.FieldType, 1));
            KingdomTweaks.Set(KingdomTweaks.Option.LongerSprint, false);
            player.stamina = 0.8f;
            action.Invoke(player, new object[] { 1, false, false });
            float ordinaryDrain = 0.8f - player.stamina;
            KingdomTweaks.Set(KingdomTweaks.Option.LongerSprint, true);
            player.stamina = 0.8f;
            action.Invoke(player, new object[] { 1, false, false });
            float tunedDrain = 0.8f - player.stamina;
            state.SetValue(player, System.Enum.ToObject(state.FieldType, 2));
            KingdomTweaks.Set(KingdomTweaks.Option.FasterRecovery, false);
            player.stamina = 0.5f;
            action.Invoke(player, new object[] { 0, false, false });
            float ordinaryRecovery = player.stamina - 0.5f;
            KingdomTweaks.Set(KingdomTweaks.Option.FasterRecovery, true);
            player.stamina = 0.5f;
            action.Invoke(player, new object[] { 0, false, false });
            float tunedRecovery = player.stamina - 0.5f;
            result.tweakStaminaVerified = ordinaryDrain > 0f && ordinaryRecovery > 0f &&
                Mathf.Abs(ordinaryDrain - tunedDrain * 2f) < 0.000001f && Mathf.Abs(tunedRecovery - ordinaryRecovery * 2f) < 0.000001f;

            KingdomTweaks.Set(KingdomTweaks.Option.RecruitsRunHome, true);
            var recruit = Instantiate(Resources.Load<GameObject>("prefabs/characters/Peasant"), new Vector3(Managers.kingdom.border.right + 10f, 1f, 0f), Quaternion.identity).GetComponent<Peasant>();
            recruit.enabled = false;
            var idle = recruit.Idle();
            idle.MoveNext();
            var mover = recruit.GetComponent<Mover>();
            float goal = (float)typeof(Mover).GetField("_goalPosition", Private).GetValue(mover);
            float speed = (float)typeof(Mover).GetField("_goalSpeed", Private).GetValue(mover);
            result.tweakRecruitVerified = goal == Managers.kingdom.campfirePosition && speed == recruit.runSpeed;
            Destroy(recruit.gameObject);
        }
        finally
        {
            state.SetValue(player, oldState);
            direction.SetValue(player, oldDirection);
            fed.SetValue(player, oldFed);
            ground.SetValue(player, oldGround);
            player.stamina = oldStamina;
            player.enabled = true;
            for (int i = 0; i < saved.Length; i++) KingdomTweaks.Set((KingdomTweaks.Option)i, saved[i]);
        }
        result.tweakDefaultsRestored = true;
        for (int i = 0; i < saved.Length; i++)
            if (KingdomTweaks.Get((KingdomTweaks.Option)i) != saved[i]) result.tweakDefaultsRestored = false;
        yield return null;
    }
}
#endif
