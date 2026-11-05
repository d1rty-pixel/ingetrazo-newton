param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeDir = Join-Path $projectRoot '.venv'
$runtimePython = Join-Path $runtimeDir 'Scripts\python.exe'
$requirements = Join-Path $projectRoot 'newton\runtime-requirements.txt'
# MuJoCo 3.3.7 has wheels for Python 3.12. Windows PowerShell 5.1 strips double quotes from native arguments, hence none in -c.
function Get-PythonVersion([string]$Exe) {
    # 'Stop' would turn any stderr line of the probe into an exception in Windows PowerShell 5.1.
    $ErrorActionPreference = 'Continue'
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return '' }
    $probe = 'import sys, struct; print(''%d.%d-%d'' % (sys.version_info[0], sys.version_info[1], struct.calcsize(''P'') * 8))'
    return (& $Exe -c $probe 2>$null | Out-String).Trim()
}
if ((Test-Path -LiteralPath $runtimeDir) -and -not (Test-Path -LiteralPath $runtimePython)) {
    # For example a .venv created under WSL (bin/python) in a checkout shared with Linux.
    throw "$runtimeDir exists but is not a Windows Python environment. Remove it or use -Python with install-local.ps1."
}
if (Test-Path -LiteralPath $runtimePython) {
    $existing = Get-PythonVersion $runtimePython
    if ($existing -ne '3.12-64') {
        # A failed run with another Python must not block the next one.
        Write-Output "Removing $runtimeDir (Python $existing, 3.12 64-bit needed)."
        Remove-Item -LiteralPath $runtimeDir -Recurse -Force
    }
}
if (-not (Test-Path -LiteralPath $runtimePython)) {
    $found = Get-PythonVersion $Python
    if ($found -ne '3.12-64') {
        if (-not $found) { $found = 'not runnable' }
        throw "$Python is Python $found. Pass a Python 3.12 64-bit with -Python, for example -Python (py -3.12 -c 'import sys; print(sys.executable)')."
    }
    & $Python -m venv $runtimeDir
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $runtimePython -m pip install --only-binary=:all: -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'MuJoCo installation failed.' }
Write-Output "Newton runtime ready: $runtimePython"
