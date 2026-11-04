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
    throw 'Python mit MuJoCo fehlt. Zuerst scripts\setup-runtime.ps1 ausführen oder -Python angeben.'
}
$Python = (Resolve-Path -LiteralPath $Python).Path
& $Python -c 'import mujoco; print("MuJoCo", mujoco.__version__)'
if ($LASTEXITCODE -ne 0) { throw 'MuJoCo ist in diesem Python nicht installiert.' }
$target = Join-Path $Destination 'newton'
if (Test-Path -LiteralPath $target) {
    if (-not $Update) { throw "Ziel existiert bereits: $target. Für ein Update -Update verwenden." }
    $entry = Join-Path $target '__init__.py'
    if (-not (Test-Path -LiteralPath $entry) -or -not ((Get-Content -LiteralPath $entry -Raw).Contains('Newton'))) {
        throw 'Keine bekannte Installation von Newton. Vorhandenen Ordner nicht verändert.'
    }
    $backup = Join-Path $projectRoot ('.backups\newton-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Get-ChildItem -LiteralPath $target -File | Copy-Item -Destination $backup
    $previousTranslations = Join-Path $target 'i18n'
    if (Test-Path -LiteralPath $previousTranslations) {
        Copy-Item -LiteralPath $previousTranslations -Destination $backup -Recurse
    }
    Write-Output "Sicherung: $backup"
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'newton') -Filter '*.py' |
    Copy-Item -Destination $target
Copy-Item -LiteralPath (Join-Path $projectRoot 'newton\i18n') -Destination $target -Recurse -Force
$runtimeConfig = @{python=$Python} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $target 'runtime.json'), $runtimeConfig, [System.Text.UTF8Encoding]::new($false))
Write-Output "Installiert: $target"
Write-Output 'IngeTrazo neu starten. Extensions -> Newton öffnen.'
