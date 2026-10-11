param(
    [ValidateSet('Import', 'Build', 'Release', 'Probe', 'Sprites', 'EmptyFrames', 'GameplayChecks')][string]$Mode = 'Import',
    [string]$Editor = 'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe',
    [string]$ProjectPath = ''
)
$ErrorActionPreference = 'Stop'
$kingdomRoot = Split-Path $PSScriptRoot -Parent
if (-not $ProjectPath) { $ProjectPath = Join-Path $kingdomRoot 'unity-web' }
if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath 'Assets')) -or -not (Test-Path -LiteralPath (Join-Path $ProjectPath 'ProjectSettings'))) {
    throw 'This reference export contains authored source only. Supply -ProjectPath for your recovered Unity project.'
}
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$kingdomRoot = Split-Path $ProjectPath -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $kingdomRoot 'analysis') | Out-Null
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
