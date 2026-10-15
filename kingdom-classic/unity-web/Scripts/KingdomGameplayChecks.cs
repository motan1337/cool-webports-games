#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.InteropServices;
using UnityEngine;

public class KingdomGameplayChecks : MonoBehaviour
{
    [Serializable]
    public class Result
    {
        public float towerDrift;
        public float towerSpeed;
        public float workerStoppedSpeed;
        public int hammerEventsAfterStop;
        public int hammerEventsStationary;
        public bool hammerEmitterCreated;
        public string hammerClip;
        public string hammerClipState;
        public float hammerClipDuration;
        public bool hammerSourcePlaying;
        public float groundedBoulderDrift;
        public float goalArrivalDrift;
        public int scannerFirstCount;
        public int scannerSecondCount;
        public bool volumeParameterAvailable;
        public int wallsBlocking;
        public int wallsDamaged;
        public List<string> wallDetails = new List<string>();
        public bool towerPassageIntended;
        public int musicSourcesAfterCrossfade;
        public int musicSourcesAfterFade;
        public bool soundtrackPlaying;
        public int simultaneousEffects;
        public bool effectsSurvivePause;
        public int lingeringEffects;
        public bool independentAudioVolumes;
        public bool tweakStaminaVerified;
        public bool tweakRecruitVerified;
        public bool tweakDefaultsRestored;
        public KingdomStaminaChecks.Report staminaChecks;
        public KingdomMenuChecks.Result menuChecks;
        public KingdomAudioLifecycleChecks.Result audioLifecycle;
        public KingdomMenuFlowChecks.Result menuFlow;
        public bool passed;
        public List<string> errors = new List<string>();
    }

    public Result result = new Result();
    private bool running;

#if UNITY_WEBGL && DEVELOPMENT_BUILD
    [DllImport("__Internal")] private static extern void KingdomBeginGameplayChecks();
    [DllImport("__Internal")] private static extern void KingdomReportGameplayChecks(string json);

    [RuntimeInitializeOnLoadMethod]
    private static void Initialize()
    {
        var host = new GameObject("KingdomGameplayChecks");
        DontDestroyOnLoad(host);
        host.AddComponent<KingdomGameplayChecks>();
    }
#endif

    public void Run()
    {
        if (!running) StartCoroutine(Check());
    }

    private IEnumerator Check()
    {
        running = true;
#if UNITY_WEBGL && DEVELOPMENT_BUILD
        KingdomBeginGameplayChecks();
#endif
        Application.logMessageReceived += OnLog;
        yield return null;
        yield return null;
        Managers.saves.autoSave = false;
        Managers.game.enabled = false;
        Managers.director.enabled = false;
        Managers.enemies.enabled = false;
        Managers.kingdom.coatOfArms = new CoatOfArms();
        Time.timeScale = 1f;
        AudioListener.pause = false;

        var slotObject = new GameObject("Regression guard slot");
        slotObject.transform.position = new Vector3(20f, 3f, 0f);
        var slot = slotObject.AddComponent<GuardSlot>();
        var archer = Instantiate(Resources.Load<GameObject>("prefabs/characters/Archer"), new Vector3(20f, 0f, 0f), Quaternion.identity).GetComponent<Archer>();
        archer.SetGuardSlot(slot);
        var body = archer.GetComponent<Rigidbody2D>();
        body.velocity = new Vector2(0.65f, 0f);
        typeof(Archer).GetMethod("EnterGuardSlot", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(archer, new object[] { slot });
        archer.GetComponent<Mover>().Pause(5f);
        float until = Time.time + 5f;
        while (Time.time < until)
        {
            result.towerDrift = Mathf.Max(result.towerDrift, Vector3.Distance(archer.transform.position, slot.transform.position));
            yield return null;
        }
        result.towerSpeed = body.velocity.magnitude;
        Destroy(archer.gameObject);
        Destroy(slotObject);

        var worker = Instantiate(Resources.Load<GameObject>("prefabs/characters/Worker"), new Vector3(0f, 0f, 0f), Quaternion.identity).GetComponent<Worker>();
        worker.enabled = false;
        var workerBody = worker.GetComponent<Rigidbody2D>();
        workerBody.gravityScale = 0f;
        var mover = worker.GetComponent<Mover>();
        var animator = worker.GetComponent<Animator>();
        var counter = worker.gameObject.AddComponent<KingdomHammerEventCounter>();
        workerBody.velocity = new Vector2(0.65f, 0f);
        mover.SetSpeed(0f);
        result.workerStoppedSpeed = Mathf.Abs(workerBody.velocity.x);
        animator.SetTrigger("Hammer");
        yield return new WaitForSeconds(0.65f);
        result.hammerEventsAfterStop = counter.hits;
        result.hammerEmitterCreated = counter.hits > 0 && FindHammerEmitter() != null;

        workerBody.velocity = Vector2.zero;
        animator.SetFloat("Speed", 0f);
        animator.Play("Hammer", 0, 0f);
        yield return new WaitForSeconds(0.6f);
        result.hammerEventsStationary = counter.hits - result.hammerEventsAfterStop;
        var sound = FindHammerEmitter();
        if (sound != null)
        {
            var source = sound.GetComponent<AudioSource>();
            result.hammerClip = source.clip.name;
            result.hammerClipState = source.clip.loadState.ToString();
            result.hammerClipDuration = KingdomAudio.Duration(source.clip);
            result.hammerSourcePlaying = source.isPlaying;
        }
        Destroy(worker.gameObject);
        yield return StartCoroutine(GetComponent<KingdomOctoberChecks>() == null
            ? gameObject.AddComponent<KingdomOctoberChecks>().Check(result)
            : GetComponent<KingdomOctoberChecks>().Check(result));
        var stamina = gameObject.AddComponent<KingdomStaminaChecks>();
        yield return StartCoroutine(stamina.Check(result));
        result.staminaChecks = stamina.report;
        result.menuChecks = KingdomMenuChecks.Validate(FindObjectOfType<Menu>(true));
        if (!result.menuChecks.passed) result.errors.Add("Native menu checks failed: " + JsonUtility.ToJson(result.menuChecks));
        yield return StartCoroutine(gameObject.AddComponent<KingdomMenuFlowChecks>().Check(result));
        result.audioLifecycle = new KingdomAudioLifecycleChecks.Result();
        yield return StartCoroutine(gameObject.AddComponent<KingdomAudioLifecycleChecks>().Check(result.audioLifecycle));
        if (!result.audioLifecycle.passed) result.errors.Add("Audio lifecycle checks failed: " + JsonUtility.ToJson(result.audioLifecycle));
        result.passed = result.groundedBoulderDrift < 0.01f && result.goalArrivalDrift < 0.01f &&
            result.scannerFirstCount == 2 && result.scannerSecondCount == 2 && result.volumeParameterAvailable &&
            result.wallsBlocking == 4 && result.wallsDamaged == 4 && result.towerPassageIntended &&
            result.musicSourcesAfterCrossfade == 1 && result.musicSourcesAfterFade == 0 && result.independentAudioVolumes &&
            result.soundtrackPlaying && result.simultaneousEffects == 10 && result.effectsSurvivePause && result.lingeringEffects == 0 &&
            result.tweakStaminaVerified && result.tweakRecruitVerified && result.tweakDefaultsRestored &&
            result.towerDrift < 0.01f && result.towerSpeed < 0.01f &&
            result.workerStoppedSpeed < 0.01f && result.hammerEventsAfterStop > 0 &&
            result.hammerEventsStationary > 0 && result.hammerEmitterCreated && result.errors.Count == 0;
        Application.logMessageReceived -= OnLog;
        string json = JsonUtility.ToJson(result, true);
        Debug.Log("KINGDOM_GAMEPLAY_CHECKS " + json);
#if UNITY_WEBGL && DEVELOPMENT_BUILD
        KingdomReportGameplayChecks(json);
#endif
#if UNITY_EDITOR
        System.IO.File.WriteAllText(System.IO.Path.GetFullPath(System.IO.Path.Combine(Application.dataPath, "../../analysis/gameplay-checks.json")), json);
        UnityEditor.EditorApplication.Exit(result.passed ? 0 : 1);
#endif
    }

    private static AudioEmitter FindHammerEmitter()
    {
        foreach (var emitter in FindObjectsOfType<AudioEmitter>())
            if (emitter.name.StartsWith("Worker Builds")) return emitter;
        return null;
    }

    private void OnLog(string message, string stack, LogType type)
    {
        if (type == LogType.Error || type == LogType.Exception) result.errors.Add(message + "\n" + stack);
    }
}

public class KingdomHammerEventCounter : MonoBehaviour
{
    public int hits;
    private void OnAnimHammerHit() { hits++; }
}
#endif
