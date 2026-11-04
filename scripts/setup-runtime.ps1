param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeDir = Join-Path $projectRoot '.venv'
$runtimePython = Join-Path $runtimeDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtimePython)) {
    & $Python -m venv $runtimeDir
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Use Python 3.12 x64.' }
}
& $runtimePython -m pip install --only-binary=:all: 'mujoco==3.3.7'
if ($LASTEXITCODE -ne 0) { throw 'MuJoCo installation failed.' }
Write-Output "Newton runtime ready: $runtimePython"
