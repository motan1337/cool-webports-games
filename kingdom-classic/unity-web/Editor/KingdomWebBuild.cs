using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class KingdomWebBuild
{
    public static void Probe()
    {
        int missing = 0;
        using (StreamWriter writer = new StreamWriter(Path.GetFullPath(Path.Combine(Application.dataPath, "../../analysis/scene-probe.txt"))))
        {
            foreach (string path in new[] { "Assets/loader.unity", "Assets/blocks.unity", "Assets/main.unity" })
            {
                var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
                foreach (GameObject root in scene.GetRootGameObjects())
                foreach (Transform item in root.GetComponentsInChildren<Transform>(true))
                {
                    int count = GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(item.gameObject);
                    if (count == 0) continue;
                    missing += count;
                    writer.WriteLine(path + " | " + item.name + " | missing=" + count);
                }
            }
            writer.WriteLine("TOTAL_MISSING_SCRIPTS=" + missing);
            foreach (string guid in AssetDatabase.FindAssets("t:Shader", new[] { "Assets/Shader" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
                writer.WriteLine(path + " | shaderErrors=" + ShaderUtil.ShaderHasError(shader));
                foreach (var message in ShaderUtil.GetShaderMessages(shader))
                    writer.WriteLine(message.severity + " " + message.message);
            }
        }
        Debug.Log("KINGDOM_SCENE_PROBE missing=" + missing);
    }

    public static void Build()
    {
        BuildPlayer(true);
    }

    public static void Release()
    {
        BuildPlayer(false);
    }

    private static void BuildPlayer(bool development)
    {
        KingdomSpriteMigration.Validate();
        string output = Path.GetFullPath(Path.Combine(Application.dataPath, development ? "../../build/webgl" : "../../build/webgl-release"));
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.WebGL, ScriptingImplementation.IL2CPP);
        PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.WebGL, ManagedStrippingLevel.Low);
        PlayerSettings.WebGL.compressionFormat = development ? WebGLCompressionFormat.Disabled : WebGLCompressionFormat.Gzip;
        PlayerSettings.WebGL.decompressionFallback = !development;
        PlayerSettings.WebGL.dataCaching = false;
        PlayerSettings.WebGL.exceptionSupport = development ? WebGLExceptionSupport.FullWithStacktrace : WebGLExceptionSupport.FullWithoutStacktrace;
        PlayerSettings.WebGL.template = "PROJECT:Kingdom";
        PlayerSettings.runInBackground = true;
        PlayerSettings.companyName = "Kingdom";
        PlayerSettings.productName = "Kingdom Classic";
        PlayerSettings.SetScriptingDefineSymbolsForGroup(BuildTargetGroup.WebGL, "KINGDOM_BROWSER");
        BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { "Assets/loader.unity", "Assets/blocks.unity", "Assets/main.unity" },
            locationPathName = output,
            target = BuildTarget.WebGL,
            options = development ? BuildOptions.Development : BuildOptions.None
        });
        if (report.summary.result != BuildResult.Succeeded)
            throw new Exception("WebGL build failed: " + report.summary.result);
        Debug.Log("KINGDOM_WEB_BUILD_OK " + output + " " + report.summary.totalSize);
    }
}
