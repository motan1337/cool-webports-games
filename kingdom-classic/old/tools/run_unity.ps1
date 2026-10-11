param(
    [ValidateSet('Import', 'Build', 'Release', 'Probe', 'Sprites', 'EmptyFrames', 'GameplayChecks')][string]$Mode = 'Import',
    [string]$Editor = 'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
$kingdomRoot = Split-Path $PSScriptRoot -Parent
$projectPath = Join-Path $kingdomRoot 'unity-web'
$logPath = Join-Path $kingdomRoot ('analysis/unity-' + $Mode.ToLowerInvariant() + '.log')
if (-not (Test-Path -LiteralPath $Editor)) { throw "Editor not found: $Editor" }
$arguments = @('-batchmode', '-nographics', '-quit', '-projectPath', ('"' + $projectPath + '"'), '-buildTarget', 'WebGL', '-logFile', ('"' + $logPath + '"'))
if ($Mode -eq 'GameplayChecks') { $arguments = $arguments | Where-Object { $_ -ne '-quit' }; $arguments += @('-executeMethod', 'KingdomGameplayRegression.Run') }
if ($Mode -eq 'Build') { $arguments += @('-executeMethod', 'KingdomWebBuild.Build') }
if ($Mode -eq 'Release') { $arguments += @('-executeMethod', 'KingdomWebBuild.Release') }
if ($Mode -eq 'Probe') { $arguments += @('-executeMethod', 'KingdomWebBuild.Probe') }
if ($Mode -eq 'Sprites') { $arguments += @('-executeMethod', 'KingdomSpriteMigration.Run') }
if ($Mode -eq 'EmptyFrames') { $arguments += @('-executeMethod', 'KingdomEmptyFrames.Run') }
$process = Start-Process -FilePath $Editor -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
Write-Output "Unity $Mode exit code: $($process.ExitCode)"
Write-Output "Log: $logPath"
exit $process.ExitCode
