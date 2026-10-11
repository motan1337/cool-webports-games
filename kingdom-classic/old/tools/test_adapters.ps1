$ErrorActionPreference = 'Stop'
$kingdomRoot = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $kingdomRoot 'analysis') | Out-Null
$testOutput = Join-Path $kingdomRoot 'analysis\input-tests.exe'
$state = Join-Path $kingdomRoot 'unity-web\Assets\Scripts\Assembly-CSharp\KingdomInputState.cs'
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /target:exe "/out:$testOutput" $state (Join-Path $PSScriptRoot 'test_input.cs')
if ($LASTEXITCODE -ne 0) { throw 'Input test compilation failed.' }
& $testOutput
if ($LASTEXITCODE -ne 0) { throw 'Input checks failed.' }
node (Join-Path $PSScriptRoot 'test_save.cjs')
if ($LASTEXITCODE -ne 0) { throw 'Save checks failed.' }
