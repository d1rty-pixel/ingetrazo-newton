param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeDir = Join-Path $projectRoot '.venv'
$runtimePython = Join-Path $runtimeDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtimePython)) {
    & $Python -m venv $runtimeDir
    if ($LASTEXITCODE -ne 0) { throw 'Python-Umgebung konnte nicht angelegt werden. Python 3.12 x64 verwenden.' }
}
& $runtimePython -m pip install --only-binary=:all: 'mujoco==3.3.7'
if ($LASTEXITCODE -ne 0) { throw 'MuJoCo-Installation fehlgeschlagen.' }
Write-Output "Newton-Laufzeit bereit: $runtimePython"
