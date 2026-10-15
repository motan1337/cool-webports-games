#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using UnityEngine;

public class KingdomMenuFlowChecks : MonoBehaviour
{
    [Serializable]
    public class Result
    {
        public bool tweaksBackKeepsPause;
        public bool gameFirstCancelResumesOnce;
        public bool uiFirstCancelResumesOnce;
        public bool optionsCancelKeepsPause;
        public bool passed;
    }

    public IEnumerator Check(KingdomGameplayChecks.Result result)
    {
        var game = Managers.game;
        var menu = FindObjectOfType<Menu>(true);
        var tweaks = menu.GetComponent<KingdomTweaksMenu>();
        var original = game.menuState;
        bool paused = AudioListener.pause;
        float scale = Time.timeScale;
        var report = new Result();
        try
        {
            game.ShowMenu();
            yield return null;
            tweaks.Open();
            yield return new WaitForSecondsRealtime(0.25f);
            game.HandleMenuCancel();
            menu.OnCancel();
            report.tweaksBackKeepsPause = !tweaks.IsOpen && game.menuState == Game.MenuState.Menu;
            yield return new WaitForSecondsRealtime(0.25f);
            game.HandleMenuCancel();
            menu.OnCancel();
            report.gameFirstCancelResumesOnce = game.menuState == Game.MenuState.None;
            yield return null;
            game.ShowMenu();
            yield return null;
            menu.OnCancel();
            game.HandleMenuCancel();
            report.uiFirstCancelResumesOnce = game.menuState == Game.MenuState.None;
            yield return null;
            game.ShowMenu();
            yield return null;
            menu.OnButtonOptions();
            yield return new WaitForSecondsRealtime(0.25f);
            menu.OnCancel();
            game.HandleMenuCancel();
            report.optionsCancelKeepsPause = game.menuState == Game.MenuState.Menu;
            yield return new WaitForSecondsRealtime(0.25f);
        }
        finally
        {
            if (original == Game.MenuState.Menu) game.ShowMenu();
            else game.HideMenu();
            AudioListener.pause = paused;
            Time.timeScale = scale;
        }
        report.passed = report.tweaksBackKeepsPause && report.gameFirstCancelResumesOnce &&
            report.uiFirstCancelResumesOnce && report.optionsCancelKeepsPause;
        result.menuFlow = report;
        if (!report.passed) result.errors.Add("Menu cancel flow failed: " + JsonUtility.ToJson(report));
    }
}
#endif
