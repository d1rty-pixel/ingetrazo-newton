param(
    [string]$Python = "",
    [string]$Destination = (Join-Path $env:APPDATA 'ingetrazo\plugins'),
    [switch]$Update
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $Python) {
    $Python = Join-Path $projectRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Python with MuJoCo is missing. Run scripts\setup-runtime.ps1 first or pass -Python.'
}
$Python = (Resolve-Path -LiteralPath $Python).Path
& $Python -c 'import mujoco; print("MuJoCo", mujoco.__version__)'
if ($LASTEXITCODE -ne 0) { throw 'MuJoCo is not installed in this Python.' }
$target = Join-Path $Destination 'newton'
if (Test-Path -LiteralPath $target) {
    if (-not $Update) { throw "Target already exists: $target. Use -Update to update it." }
    $entry = Join-Path $target '__init__.py'
    if (-not (Test-Path -LiteralPath $entry) -or -not ((Get-Content -LiteralPath $entry -Raw).Contains('Newton'))) {
        throw 'Not a known Newton installation. Existing folder left unchanged.'
    }
    $backup = Join-Path $projectRoot ('.backups\newton-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Get-ChildItem -LiteralPath $target -File | Copy-Item -Destination $backup
    foreach ($folder in 'i18n','icons') {
        $previous = Join-Path $target $folder
        if (Test-Path -LiteralPath $previous) {
            Copy-Item -LiteralPath $previous -Destination $backup -Recurse
        }
    }
    Write-Output "Backup: $backup"
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'newton') -Filter '*.py' |
    Copy-Item -Destination $target
Copy-Item -LiteralPath (Join-Path $projectRoot 'newton\i18n') -Destination $target -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'newton\icons') -Destination $target -Recurse -Force
$runtimeConfig = @{python=$Python} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $target 'runtime.json'), $runtimeConfig, [System.Text.UTF8Encoding]::new($false))
Write-Output "Installed: $target"
Write-Output 'Restart IngeTrazo. Open Extensions -> Newton.'
