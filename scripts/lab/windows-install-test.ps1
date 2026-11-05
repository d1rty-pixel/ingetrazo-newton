<#
.SYNOPSIS
  Tests the Windows installation routes of Newton without touching the real IngeTrazo installation.

.DESCRIPTION
  Every installation and runtime test runs in a sandbox under %TEMP%: the child processes get
  APPDATA and LOCALAPPDATA pointing into it, so the host's plugin and data folder rules resolve
  to the sandbox. The real %APPDATA%\ingetrazo is only read (inventory and comparison).

  Results go to .test-state\windows-install\<timestamp>\ in the repository:
  results.json (one record per case), summary.txt, transcript.txt and logs\ with the output of
  every command. .test-state\windows-install\latest.txt names the newest run.

  Phases: inventory, package, zip, runtime (method B), manual (method C), scripts
  (setup-runtime.ps1 / install-local.ps1), worker, unicode, wsl, live, gui (only with -Gui), cleanup.

.PARAMETER Gui
  Also start the installed IngeTrazo.exe once with the sandbox as its plugins folder (--new-window),
  with a probe plugin that checks loading, runs the runtime setup inside the host and simulates a
  model. Needs IngeTrazo closed: the host keeps its settings in HKCU\Software\IngeTrazo, which the
  suite exports before and restores afterwards.

.PARAMETER GuiKeepOpen
  Leave the sandbox IngeTrazo window open after the probe for a manual look.

.PARAMETER Keep
  Keep the sandbox folder (otherwise removed at the end).

.PARAMETER Skip
  Phases to skip, for example -Skip unicode,manual.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\lab\windows-install-test.ps1 -Gui
#>
param(
    [switch]$Gui,
    [switch]$GuiKeepOpen,
    [switch]$Keep,
    [string[]]$Skip = @()
)
$ErrorActionPreference = 'Stop'
# From cmd.exe, "-Skip a,b" arrives as one string.
$Skip = @($Skip | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
# Windows PowerShell 5.1 offers TLS 1.0 by default; PyPI requires TLS 1.2.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$OutDir = Join-Path $RepoRoot ".test-state\windows-install\$Stamp"
$LogDir = Join-Path $OutDir 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Content -LiteralPath (Join-Path $RepoRoot '.test-state\windows-install\latest.txt') -Value $Stamp -Encoding ascii
# A space in the sandbox path, as in "C:\Users\Jane Doe" or "Program Files".
$Sandbox = Join-Path $env:TEMP "newton itest $Stamp"
$SbRoaming = Join-Path $Sandbox 'Roaming'
$SbLocal = Join-Path $Sandbox 'Local'
$SbPlugins = Join-Path $SbRoaming 'ingetrazo\plugins'
$SbData = Join-Path $SbRoaming 'ingetrazo'
$SbRepo = Join-Path $Sandbox 'repo copy'
New-Item -ItemType Directory -Force -Path $SbPlugins, $SbLocal, $SbRepo | Out-Null
Start-Transcript -LiteralPath (Join-Path $OutDir 'transcript.txt') | Out-Null

$Results = New-Object System.Collections.ArrayList
# An unexpected error is recorded and the suite goes on with the next statement.
trap {
    Add-Result 'ERROR' 'FAIL' 'Unexpected error in the suite' ("line $($_.InvocationInfo.ScriptLineNumber): $($_.Exception.Message)")
    continue
}
$Facts = [ordered]@{}
$script:caseCounter = 0

function Add-Result([string]$Id, [string]$Status, [string]$Name, [string]$Detail = '', [double]$Seconds = 0) {
    $record = [ordered]@{ id = $Id; status = $Status; name = $Name; detail = $Detail; seconds = [math]::Round($Seconds, 1) }
    [void]$Results.Add($record)
    $colour = @{ PASS = 'Green'; FAIL = 'Red'; WARN = 'Yellow'; SKIP = 'DarkGray'; INFO = 'Cyan' }[$Status]
    Write-Host ("[{0}] {1,-8} {2}" -f $Status, $Id, $Name) -ForegroundColor $colour
    if ($Detail) { Write-Host ("         " + ($Detail -replace "`n", "`n         ")) -ForegroundColor DarkGray }
    Save-Results
}

function Save-Results {
    $doc = [ordered]@{ stamp = $Stamp; repo = $RepoRoot; sandbox = $Sandbox; facts = $Facts; results = $Results }
    $json = $doc | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText((Join-Path $OutDir 'results.json'), $json, (New-Object System.Text.UTF8Encoding($false)))
}

function Quote-Arg([string]$a) {
    if ($a -eq '') { return '""' }
    if ($a -notmatch '[\s"]') { return $a }
    $escaped = [regex]::Replace($a, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

# Runs a program with redirected output, optional stdin, environment overrides and a timeout.
# Returns @{ Code; Out; Err; Seconds; Log }. The output also goes to logs\<name>.log.
function Invoke-Native {
    param([string]$Name, [string]$Exe, [string[]]$Arguments = @(), [string]$InputText = $null,
          [hashtable]$Env = @{}, [string]$WorkDir = $Sandbox, [int]$TimeoutSec = 900, [switch]$Sandboxed, [string]$RawArguments = $null)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = if ($null -ne $RawArguments -and $RawArguments -ne '') { $RawArguments } else { ($Arguments | ForEach-Object { Quote-Arg $_ }) -join ' ' }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $WorkDir
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $psi.StandardOutputEncoding = $utf8
    $psi.StandardErrorEncoding = $utf8
    if ($Sandboxed) {
        $psi.EnvironmentVariables['APPDATA'] = $SbRoaming
        $psi.EnvironmentVariables['LOCALAPPDATA'] = $SbLocal
    }
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    foreach ($k in $Env.Keys) {
        if ($null -eq $Env[$k]) { $psi.EnvironmentVariables.Remove($k) } else { $psi.EnvironmentVariables[$k] = [string]$Env[$k] }
    }
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    try { [void]$p.Start() } catch {
        $msg = "cannot start: $($_.Exception.Message)"
        Set-Content -LiteralPath (Join-Path $LogDir "$Name.log") -Value "> $Exe $($psi.Arguments)`n$msg" -Encoding utf8
        return @{ Code = -1; Out = ''; Err = $msg; Seconds = 0; Log = "logs\$Name.log" }
    }
    $outTask = $p.StandardOutput.ReadToEndAsync()
    $errTask = $p.StandardError.ReadToEndAsync()
    if ($null -ne $InputText) { $p.StandardInput.Write($InputText) }
    $p.StandardInput.Close()
    $code = $null
    if (-not $p.WaitForExit($TimeoutSec * 1000)) {
        try { $p.Kill() } catch {}
        $code = -999
    } else {
        $p.WaitForExit()
        $code = $p.ExitCode
    }
    $out = $outTask.Result; $err = $errTask.Result
    $watch.Stop()
    $text = "> $Exe $($psi.Arguments)`n> exit $code after $([math]::Round($watch.Elapsed.TotalSeconds,1)) s`n--- stdout`n$out`n--- stderr`n$err"
    [System.IO.File]::WriteAllText((Join-Path $LogDir "$Name.log"), $text, $utf8)
    return @{ Code = $code; Out = $out; Err = $err; Seconds = $watch.Elapsed.TotalSeconds; Log = "logs\$Name.log" }
}

function Tail([string]$s, [int]$n = 4) {
    $lines = @(($s -split "`r?`n") | Where-Object { $_.Trim() -ne '' })
    return ($lines | Select-Object -Last $n) -join "`n"
}

function Phase([string]$name) {
    if ($Skip -contains $name) { Add-Result "$name" 'SKIP' "phase '$name' skipped by -Skip"; return $false }
    Write-Host "`n=== $name ===" -ForegroundColor White
    return $true
}

function Read-JsonFile([string]$path) {
    try { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8) | ConvertFrom-Json } catch { return $null }
}

$PsExe = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $PsExe)) { $PsExe = (Get-Process -Id $PID).Path }

# ---------------------------------------------------------------- inventory (read only)
$LiveData = Join-Path $env:APPDATA 'ingetrazo'
$LivePlugins = Join-Path $LiveData 'plugins'
$HostExe = $null
$AnyPython = $null
$Python312 = $null
if (Phase 'inventory') {
    $os = Get-CimInstance Win32_OperatingSystem
    $Facts.os = "$($os.Caption) $($os.Version) $($os.OSArchitecture)"
    $Facts.powershell = $PSVersionTable.PSVersion.ToString()
    $Facts.user_profile = $env:USERPROFILE
    $Facts.temp = $env:TEMP
    $Facts.execution_policy = (Get-ExecutionPolicy -List | ForEach-Object { "$($_.Scope)=$($_.ExecutionPolicy)" }) -join ', '
    try { $Facts.long_paths_enabled = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction Stop).LongPathsEnabled } catch { $Facts.long_paths_enabled = 'unset' }
    Add-Result 'INV-1' 'INFO' 'System' "$($Facts.os); PowerShell $($Facts.powershell); LongPathsEnabled=$($Facts.long_paths_enabled)"

    $uninstall = Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.PSObject.Properties['DisplayName'] -and $_.DisplayName -match 'IngeTrazo' }
    $candidates = @()
    foreach ($u in @($uninstall)) { if ($u -and $u.PSObject.Properties['InstallLocation'] -and $u.InstallLocation) { $candidates += (Join-Path $u.InstallLocation 'ingetrazo.exe') } }
    $candidates += @("$env:ProgramFiles\IngeTrazo\ingetrazo.exe", "$env:LOCALAPPDATA\Programs\IngeTrazo\ingetrazo.exe", 'C:\IngeTrazo\ingetrazo.exe')
    $HostExe = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $kind = if ($uninstall) { "installer ($(@($uninstall)[0].DisplayName), uninstaller $(@($uninstall)[0].UninstallString))" } elseif ($HostExe) { 'portable (no uninstall entry)' } else { 'not found' }
    $Facts.host_exe = $HostExe; $Facts.host_kind = $kind
    if ($HostExe) {
        $hostRoot = Split-Path $HostExe
        $Facts.host_bundled_python = (Test-Path (Join-Path $hostRoot '_internal\python312.dll'))
        $Facts.host_mcp = (Test-Path (Join-Path $hostRoot 'ingetrazo-mcp.exe'))
        Add-Result 'INV-2' 'INFO' 'IngeTrazo installation' "$HostExe`n$kind; bundled python312.dll: $($Facts.host_bundled_python)"
    } else {
        Add-Result 'INV-2' 'WARN' 'IngeTrazo installation' 'ingetrazo.exe not found; GUI phase impossible'
    }
    $running = @(Get-Process ingetrazo -ErrorAction SilentlyContinue)
    $Facts.host_running = $running.Count
    Add-Result 'INV-3' 'INFO' 'IngeTrazo running' "$($running.Count) process(es)"

    # Live plugins folder: read only.
    $livePluginsList = if (Test-Path $LivePlugins) { (Get-ChildItem -LiteralPath $LivePlugins | ForEach-Object Name) -join ', ' } else { '(missing)' }
    Add-Result 'INV-4' 'INFO' 'Live plugins folder (read only)' "$LivePlugins`n$livePluginsList"
    $liveRuntime = Join-Path $LiveData 'newton-runtime'
    $Facts.live_runtime_exists = Test-Path -LiteralPath $liveRuntime
    $pref = $null
    try { $pref = (Get-ItemProperty 'HKCU:\Software\IngeTrazo\IngeTrazo\newton' -Name python -ErrorAction Stop).python } catch {}
    $Facts.live_pref_python = $pref
    $prefState = if (-not $pref) { 'not set' } elseif (Test-Path -LiteralPath $pref) { 'exists' } else { 'MISSING (Newton falls back to runtime.json)' }
    Add-Result 'INV-5' 'INFO' 'Live Newton runtime settings (read only)' "Preference newton/python: $pref [$prefState]`n<data>\newton-runtime exists: $($Facts.live_runtime_exists)"

    # Python interpreters.
    $pyLines = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $r = Invoke-Native 'inv-py-list' $py.Source @('-0p') -WorkDir $RepoRoot
        $pyLines += $r.Out.Trim()
        $r = Invoke-Native 'inv-py3' $py.Source @('-3', '-c', 'import sys;print(sys.executable)') -WorkDir $RepoRoot
        if ($r.Code -eq 0) { $AnyPython = $r.Out.Trim() }
        $r = Invoke-Native 'inv-py312' $py.Source @('-3.12', '-c', 'import sys;print(sys.executable)') -WorkDir $RepoRoot
        if ($r.Code -eq 0) { $Python312 = $r.Out.Trim() }
    }
    if (-not $AnyPython) {
        $pc = Get-Command python -ErrorAction SilentlyContinue
        if ($pc) {
            $r = Invoke-Native 'inv-python' $pc.Source @('-c', 'import sys;print(sys.executable)') -WorkDir $RepoRoot
            if ($r.Code -eq 0) { $AnyPython = $r.Out.Trim() }
        }
    }
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    $Facts.python_any = $AnyPython; $Facts.python_312 = $Python312; $Facts.uv_on_path = if ($uvCmd) { $uvCmd.Source } else { $null }
    $Facts.pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue | ForEach-Object Source)
    Add-Result 'INV-6' 'INFO' 'Python and uv' "py launcher list:`n$($pyLines -join "`n")`nany Python 3: $AnyPython`nPython 3.12: $(if ($Python312) { $Python312 } else { 'none' })`nuv on PATH: $(if ($uvCmd) { $uvCmd.Source } else { 'no' }); pwsh: $(if ($Facts.pwsh) { $Facts.pwsh } else { 'no' })"

    $net = @()
    foreach ($url in 'https://github.com/astral-sh/uv/releases', 'https://pypi.org/pypi/mujoco/3.3.7/json') {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
            $net += "$url $($resp.StatusCode)"
        } catch { $net += "$url FAILED $($_.Exception.Message)" }
    }
    $netOk = -not ($net -match 'FAILED')
    Add-Result 'INV-7' $(if ($netOk) { 'INFO' } else { 'WARN' }) 'Internet access for the runtime download' ($net -join "`n")
    Add-Result 'INV-8' 'INFO' 'Sandbox' "$Sandbox`nresults: $OutDir"
}
if (-not $AnyPython) {
    Add-Result 'INV-9' 'FAIL' 'No Python 3 found' 'runtime_setup.py and package.py need any Python 3.9+; most phases are skipped'
}

# ---------------------------------------------------------------- package (release zip)
# Work on a copy of the repository parts the scripts need, so .venv, .backups and dist stay untouched.
foreach ($item in 'newton', 'scripts', 'LICENSE') {
    Copy-Item -LiteralPath (Join-Path $RepoRoot $item) -Destination $SbRepo -Recurse -Force
}
Get-ChildItem -LiteralPath $SbRepo -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
Remove-Item -LiteralPath (Join-Path $SbRepo 'newton\runtime.json') -ErrorAction SilentlyContinue
$Version = ([regex]::Match((Get-Content -LiteralPath (Join-Path $RepoRoot 'newton\__init__.py') -Raw), '__version__ = "([^"]+)"')).Groups[1].Value
$Facts.newton_version = $Version
$Expected = @()
$Expected += Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'newton') -File | Where-Object { $_.Extension -in '.py', '.txt' } | ForEach-Object { "newton/$($_.Name)" }
$Expected += Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'newton\i18n') -Filter '*.json' | ForEach-Object { "newton/i18n/$($_.Name)" }
$Expected += Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'newton\icons') -Filter '*.svg' | ForEach-Object { "newton/icons/$($_.Name)" }
$Expected += 'newton/LICENSE'
$Expected = @($Expected | Sort-Object)
$Zip = $null
if ((Phase 'package') -and $AnyPython) {
    $r = Invoke-Native 'pkg-build-1' $AnyPython @((Join-Path $SbRepo 'scripts\package.py')) -WorkDir $SbRepo
    $Zip = Join-Path $SbRepo "dist\newton-$Version.zip"
    if ($r.Code -eq 0 -and (Test-Path -LiteralPath $Zip)) {
        $hash1 = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash
        Add-Result 'PKG-1' 'PASS' "package.py builds newton-$Version.zip" "SHA-256 $hash1" $r.Seconds
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [System.IO.Compression.ZipFile]::OpenRead($Zip)
        $names = @($archive.Entries | ForEach-Object FullName | Sort-Object)
        $archive.Dispose()
        $tops = @($names | ForEach-Object { ($_ -split '/')[0] } | Sort-Object -Unique)
        $missing = @($Expected | Where-Object { $names -notcontains $_ })
        $extra = @($names | Where-Object { $Expected -notcontains $_ })
        $ok = ($tops.Count -eq 1 -and $tops[0] -eq 'newton' -and $missing.Count -eq 0 -and $extra.Count -eq 0)
        Add-Result 'PKG-2' $(if ($ok) { 'PASS' } else { 'FAIL' }) 'Zip has exactly one newton/ folder with the expected files' "top: $($tops -join ', '); entries: $($names.Count); missing: $($missing -join ', '); extra: $($extra -join ', ')"
        Start-Sleep -Seconds 2
        $r2 = Invoke-Native 'pkg-build-2' $AnyPython @((Join-Path $SbRepo 'scripts\package.py')) -WorkDir $SbRepo
        $hash2 = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash
        Add-Result 'PKG-3' $(if ($hash1 -eq $hash2) { 'PASS' } else { 'FAIL' }) 'Zip is reproducible (same SHA-256 on rebuild)' "$hash1`n$hash2"
        $Facts.zip_sha256 = $hash1
    } else {
        Add-Result 'PKG-1' 'FAIL' 'package.py builds the zip' "exit $($r.Code); $(Tail $r.Err)`nlog: $($r.Log)" $r.Seconds
        $Zip = $null
    }
}

# ---------------------------------------------------------------- zip installation (docs/installation.md B, "From the release zip")
$SbNewton = Join-Path $SbPlugins 'newton'
if ((Phase 'zip') -and $Zip) {
    # The documented command, with APPDATA pointing into the sandbox.
    $saved = $env:APPDATA
    try {
        $env:APPDATA = $SbRoaming
        Expand-Archive $Zip -DestinationPath "$env:APPDATA\ingetrazo\plugins"
    } finally { $env:APPDATA = $saved }
    $init = Join-Path $SbNewton '__init__.py'
    $ok = (Test-Path -LiteralPath $init) -and (Test-Path -LiteralPath (Join-Path $SbNewton 'runtime-requirements.txt')) -and (Test-Path -LiteralPath (Join-Path $SbNewton 'icons'))
    Add-Result 'ZIP-1' $(if ($ok) { 'PASS' } else { 'FAIL' }) 'Expand-Archive puts the extension at <plugins>\newton\__init__.py' $SbNewton
    # Updating with the same command over an existing folder.
    try {
        Expand-Archive $Zip -DestinationPath $SbPlugins -ErrorAction Stop
        Add-Result 'ZIP-2' 'WARN' 'Expand-Archive over an existing installation' 'succeeded without -Force (unexpected)'
    } catch {
        Add-Result 'ZIP-2' 'INFO' 'Expand-Archive over an existing installation needs -Force' ("Without -Force: " + $_.Exception.Message.Split("`n")[0] + "`nThe update instructions in installation.md do not mention -Force.")
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $SbNewton '__init__.py'))) {
    # Later phases need an installed copy.
    Copy-Item -LiteralPath (Join-Path $SbRepo 'newton') -Destination $SbPlugins -Recurse -Force
}

# ---------------------------------------------------------------- runtime method B (runtime_setup.py)
$RtB = Join-Path $SbData 'newton-runtime'
$RtBPython = Join-Path $RtB 'venv\Scripts\python.exe'
$Setup = Join-Path $SbNewton 'runtime_setup.py'
$UvExe = $null
if ((Phase 'runtime') -and $AnyPython) {
    $r = Invoke-Native 'rt-check-empty' $AnyPython @($Setup, 'check') -Sandboxed
    Add-Result 'RT-1' $(if ($r.Code -eq 1) { 'PASS' } else { 'FAIL' }) 'check without a runtime exits 1' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
    $r = Invoke-Native 'rt-usage' $AnyPython @($Setup, 'install', '--flatpak', '--data-dir', $Sandbox) -Sandboxed
    Add-Result 'RT-2' $(if ($r.Code -eq 2) { 'PASS' } else { 'FAIL' }) '--data-dir with --flatpak exits 2' "exit $($r.Code)"

    $r = Invoke-Native 'rt-install' $AnyPython @($Setup, 'install', '--yes', '--json') -Sandboxed -TimeoutSec 1200
    $events = @($r.Out -split "`r?`n" | Where-Object { $_.StartsWith('{') } | ForEach-Object { try { $_ | ConvertFrom-Json } catch {} })
    $steps = ($events | ForEach-Object step | Select-Object -Unique) -join ' > '
    $cfg = Read-JsonFile (Join-Path $RtB 'runtime.json')
    $ok = $r.Code -eq 0 -and (Test-Path -LiteralPath $RtBPython) -and (Test-Path -LiteralPath (Join-Path $RtB '.newton-runtime')) -and $cfg -and ($cfg.python -eq $RtBPython)
    Add-Result 'RT-3' $(if ($ok) { 'PASS' } else { 'FAIL' }) "runtime_setup.py install (Python $(Split-Path -Leaf (Split-Path $AnyPython)) runs it; default <data> from the plugin location)" "exit $($r.Code); steps: $steps`nruntime.json python: $(if ($cfg) { $cfg.python } else { '(none)' })`n$(Tail $r.Err 3)`nlog: $($r.Log)" $r.Seconds
    $Facts.rt_install_seconds = [math]::Round($r.Seconds, 1)
    $UvExe = Join-Path $RtB 'tools\uv.exe'
    if (-not (Test-Path -LiteralPath $UvExe)) { $UvExe = $Facts.uv_on_path }
    if (Test-Path -LiteralPath $RtB) {
        $size = (Get-ChildItem -LiteralPath $RtB -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $longest = Get-ChildItem -LiteralPath $RtB -Recurse -File -Force -ErrorAction SilentlyContinue | Sort-Object { $_.FullName.Length } -Descending | Select-Object -First 1
        $rel = $longest.FullName.Substring($RtB.Length)
        # The same file under the real data folder of this user.
        $realLen = (Join-Path $LiveData 'newton-runtime').Length + $rel.Length
        $Facts.rt_size_mb = [math]::Round($size / 1MB)
        Add-Result 'RT-4' $(if ($realLen -lt 250) { 'INFO' } else { 'WARN' }) 'Runtime size and longest path' "$($Facts.rt_size_mb) MB; longest file: ...$rel`nits length under the real %APPDATA%: $realLen characters (MAX_PATH 260)"
    }
    $r = Invoke-Native 'rt-check' $AnyPython @($Setup, 'check') -Sandboxed
    Add-Result 'RT-5' $(if ($r.Code -eq 0 -and $r.Out -match 'MuJoCo 3\.3\.7') { 'PASS' } else { 'FAIL' }) 'runtime_setup.py check' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 2)"
    $r = Invoke-Native 'rt-path' $AnyPython @($Setup, 'path') -Sandboxed
    Add-Result 'RT-6' $(if ($r.Code -eq 0 -and $r.Out.Trim() -eq $RtBPython) { 'PASS' } else { 'FAIL' }) 'runtime_setup.py path prints the venv interpreter' $r.Out.Trim()
    if (Test-Path -LiteralPath $RtBPython) {
        $r = Invoke-Native 'rt-versions' $RtBPython @('-E', '-c', 'import sys,platform,mujoco,numpy;print(sys.version.split()[0],platform.architecture()[0],mujoco.__version__,numpy.__version__)')
        Add-Result 'RT-7' $(if ($r.Out -match '^3\.12\.\d+ 64bit 3\.3\.7 2\.5\.4') { 'PASS' } else { 'FAIL' }) 'Runtime versions (Python 3.12 64-bit, MuJoCo 3.3.7, numpy 2.5.4)' $r.Out.Trim()
    }
    $r = Invoke-Native 'rt-reinstall' $AnyPython @($Setup, 'install', '--yes') -Sandboxed -TimeoutSec 900
    Add-Result 'RT-8' $(if ($r.Code -eq 0) { 'PASS' } else { 'FAIL' }) 'install again repairs/keeps the runtime (idempotent)' "exit $($r.Code); $(Tail ($r.Out + $r.Err) 1)" $r.Seconds

    # Lookup order: <data>\newton-runtime\runtime.json wins over a runtime.json in the plugin folder.
    $pluginCfg = Join-Path $SbNewton 'runtime.json'
    [System.IO.File]::WriteAllText($pluginCfg, '{"python": "C:/does/not/exist/python.exe"}')
    $r = Invoke-Native 'rt-order-1' $AnyPython @($Setup, 'path') -Sandboxed
    $ok1 = $r.Out.Trim() -eq $RtBPython
    $fallback = Join-Path $Sandbox 'fallback.json'
    Copy-Item -LiteralPath (Join-Path $RtB 'runtime.json') -Destination $fallback
    Remove-Item -LiteralPath (Join-Path $RtB 'runtime.json')
    $pluginTarget = $RtBPython -replace '\\', '/'
    [System.IO.File]::WriteAllText($pluginCfg, "{`"python`": `"$pluginTarget`"}")
    $r2 = Invoke-Native 'rt-order-2' $AnyPython @($Setup, 'path') -Sandboxed
    $ok2 = ($r2.Out.Trim() -replace '\\', '/') -eq $pluginTarget
    Move-Item -LiteralPath $fallback -Destination (Join-Path $RtB 'runtime.json')
    Remove-Item -LiteralPath $pluginCfg
    Add-Result 'RT-9' $(if ($ok1 -and $ok2) { 'PASS' } else { 'FAIL' }) 'Interpreter lookup order (data runtime.json, then plugin runtime.json with forward slashes)' "data wins: $ok1 ($($r.Out.Trim())); plugin file used when alone: $ok2 ($($r2.Out.Trim()))"

    # Never touches a folder without its marker.
    $foreign = Join-Path $Sandbox 'foreign data'
    New-Item -ItemType Directory -Force -Path (Join-Path $foreign 'newton-runtime') | Out-Null
    Set-Content -LiteralPath (Join-Path $foreign 'newton-runtime\keep.txt') -Value 'user data'
    $r = Invoke-Native 'rt-foreign-install' $AnyPython @($Setup, 'install', '--yes', '--data-dir', $foreign) -Sandboxed
    $r2 = Invoke-Native 'rt-foreign-uninstall' $AnyPython @($Setup, 'uninstall', '--yes', '--data-dir', $foreign) -Sandboxed
    $kept = Test-Path -LiteralPath (Join-Path $foreign 'newton-runtime\keep.txt')
    Add-Result 'RT-10' $(if ($r.Code -eq 1 -and $r2.Code -eq 1 -and $kept) { 'PASS' } else { 'FAIL' }) 'install/uninstall refuse a folder without the marker' "install exit $($r.Code): $(Tail $r.Err 1)`nuninstall exit $($r2.Code): $(Tail $r2.Err 1)`nfile kept: $kept"
}

# ---------------------------------------------------------------- method C (manual commands from runtime-setup.md)
$RtC = $null; $RtC2 = $null
if ((Phase 'manual') -and $UvExe -and (Test-Path -LiteralPath $UvExe)) {
    # The documented commands verbatim; only "uv" is the uv from method B and APPDATA is the sandbox.
    $doc = @'
$rt = "$env:APPDATA\ingetrazo\newton-runtime"
$env:UV_PYTHON_INSTALL_DIR = "$rt\python"; $env:UV_PYTHON_PREFERENCE = 'only-managed'
uv venv --python 3.12 "$rt\venv"
if ($LASTEXITCODE) { exit 10 }
uv pip install --python "$rt\venv\Scripts\python.exe" --only-binary :all: mujoco==3.3.7 numpy==2.5.4
if ($LASTEXITCODE) { exit 11 }
@{python = "$rt\venv\Scripts\python.exe"} | ConvertTo-Json | Set-Content -Encoding ascii "$rt\runtime.json"
& "$rt\venv\Scripts\python.exe" -c "import mujoco; print(mujoco.__version__)"   # 3.3.7
'@
    $cRoaming = Join-Path $Sandbox 'method C\Roaming'
    New-Item -ItemType Directory -Force -Path $cRoaming | Out-Null
    $scriptFile = Join-Path $Sandbox 'method-c-uv.ps1'
    Set-Content -LiteralPath $scriptFile -Value ("function uv { & '$UvExe' @args }`n" + $doc) -Encoding utf8
    $r = Invoke-Native 'manual-c-uv' $PsExe @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptFile) -Env @{ APPDATA = $cRoaming; LOCALAPPDATA = (Join-Path $Sandbox 'method C\Local') } -TimeoutSec 1200
    $RtC = Join-Path $cRoaming 'ingetrazo\newton-runtime'
    $cfg = Read-JsonFile (Join-Path $RtC 'runtime.json')
    $ok = $r.Code -eq 0 -and $r.Out.Trim().EndsWith('3.3.7') -and $cfg
    Add-Result 'MAN-1' $(if ($ok) { 'PASS' } else { 'FAIL' }) 'Method C with uv (documented PowerShell commands)' "exit $($r.Code); $(Tail ($r.Out + $r.Err) 2)`nruntime.json: $(if ($cfg) { $cfg.python } else { 'unreadable' })`nlog: $($r.Log)" $r.Seconds
    if ($cfg) {
        $r = Invoke-Native 'manual-c-uv-check' $AnyPython @($Setup, 'check', '--data-dir', (Join-Path $cRoaming 'ingetrazo')) -Sandboxed
        Add-Result 'MAN-2' $(if ($r.Code -eq 0) { 'PASS' } else { 'FAIL' }) 'runtime_setup.py accepts the runtime.json written by method C (UTF-8/ASCII, backslashes)' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
    }

    # Without uv: needs "a Python 3.12 x64 you already have".
    $base312 = $Python312
    $note = 'py -3.12'
    if (-not $base312) {
        $base312 = Get-ChildItem -LiteralPath (Join-Path $RtB 'python') -Recurse -Filter python.exe -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
        $note = 'no Python 3.12 installed; using the uv-managed 3.12 from method B as stand-in'
    }
    if ($base312) {
        $c2Roaming = Join-Path $Sandbox 'method C2\Roaming'
        $RtC2 = Join-Path $c2Roaming 'ingetrazo\newton-runtime'
        $venv = Join-Path $RtC2 'venv'
        $r = Invoke-Native 'manual-c-venv' $base312 @('-m', 'venv', $venv)
        $c2Python = Join-Path $venv 'Scripts\python.exe'
        $r2 = Invoke-Native 'manual-c-pip' $c2Python @('-m', 'pip', 'install', '--only-binary', ':all:', 'mujoco==3.3.7', 'numpy==2.5.4') -TimeoutSec 900
        $r3 = Invoke-Native 'manual-c-pip-check' $c2Python @('-E', '-c', 'import mujoco;print(mujoco.__version__)')
        $ok = $r.Code -eq 0 -and $r2.Code -eq 0 -and $r3.Out.Trim() -eq '3.3.7'
        Add-Result 'MAN-3' $(if ($ok) { 'PASS' } else { 'FAIL' }) 'Method C without uv (venv + pip)' "$note`nvenv exit $($r.Code), pip exit $($r2.Code), mujoco $($r3.Out.Trim())`n$(Tail $r2.Err 2)" ($r.Seconds + $r2.Seconds)
    } else {
        Add-Result 'MAN-3' 'SKIP' 'Method C without uv' 'no Python 3.12 available'
    }
} elseif ($Skip -notcontains 'manual') {
    Add-Result 'MAN-1' 'SKIP' 'Method C' 'no uv available (method B failed?)'
}

# ---------------------------------------------------------------- repository scripts (setup-runtime.ps1, install-local.ps1)
if (Phase 'scripts') {
    $setupPs = Join-Path $SbRepo 'scripts\setup-runtime.ps1'
    $installPs = Join-Path $SbRepo 'scripts\install-local.ps1'
    $dest = Join-Path $Sandbox 'scripts plugins'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $psArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File')

    $r = Invoke-Native 'scr-install-novenv' $PsExe ($psArgs + @($installPs, '-Destination', $dest)) -WorkDir $SbRepo
    $okNoVenv = $r.Code -ne 0 -and (($r.Out + $r.Err) -match 'setup-runtime\.ps1 first')
    Add-Result 'SCR-1' $(if ($okNoVenv) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 without .venv stops with a hint' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"

    if ($AnyPython) {
        $r = Invoke-Native 'scr-install-nomujoco' $PsExe ($psArgs + @($installPs, '-Python', $AnyPython, '-Destination', $dest)) -WorkDir $SbRepo
        Add-Result 'SCR-2' $(if ($r.Code -ne 0 -and -not (Test-Path (Join-Path $dest 'newton'))) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 with a Python without MuJoCo stops and copies nothing' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 2)"
    }

    # setup-runtime.ps1 with its default "python" (whatever PATH gives).
    $r = Invoke-Native 'scr-setup-default' $PsExe ($psArgs + @($setupPs)) -WorkDir $SbRepo -TimeoutSec 900
    $venvPy = Join-Path $SbRepo '.venv\Scripts\python.exe'
    $v = Invoke-Native 'scr-default-python' 'python' @('-c', 'import sys;print(sys.version.split()[0])')
    $default312 = $v.Out.Trim() -like '3.12.*'
    if ($default312) {
        Add-Result 'SCR-3' $(if ($r.Code -eq 0) { 'PASS' } else { 'FAIL' }) 'setup-runtime.ps1 with default -Python python (a 3.12)' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)" $r.Seconds
    } else {
        $clear = $r.Code -ne 0 -and (($r.Out + $r.Err) -match '3\.12') -and -not (Test-Path -LiteralPath (Join-Path $SbRepo '.venv'))
        Add-Result 'SCR-3' $(if ($clear) { 'PASS' } else { 'FAIL' }) "setup-runtime.ps1 with default python ($($v.Out.Trim())) refuses it, names 3.12 and creates no .venv" "exit $($r.Code): $(Tail ($r.Out + $r.Err) 2)" $r.Seconds
    }
    Remove-Item -LiteralPath (Join-Path $SbRepo '.venv') -Recurse -Force -ErrorAction SilentlyContinue
    $base312 = $Python312
    if (-not $base312 -and (Test-Path (Join-Path $RtB 'python'))) {
        $base312 = Get-ChildItem -LiteralPath (Join-Path $RtB 'python') -Recurse -Filter python.exe -Depth 2 | Select-Object -First 1 -ExpandProperty FullName
    }
    if ($base312 -and $AnyPython -and -not $default312) {
        # A .venv left from an older script version or by hand with another Python is replaced.
        Invoke-Native 'scr-wrong-venv' $AnyPython @('-m', 'venv', '--without-pip', (Join-Path $SbRepo '.venv')) | Out-Null
        $r = Invoke-Native 'scr-setup-retry' $PsExe ($psArgs + @($setupPs, '-Python', $base312)) -WorkDir $SbRepo -TimeoutSec 900
        $v = Invoke-Native 'scr-setup-retry-ver' $venvPy @('-E', '-c', 'import sys;print(sys.version.split()[0])')
        $is312 = $v.Out.Trim() -like '3.12.*'
        Add-Result 'SCR-3b' $(if ($r.Code -eq 0 -and $is312) { 'PASS' } else { 'FAIL' }) 'setup-runtime.ps1 replaces a .venv made with another Python' "exit $($r.Code); .venv Python afterwards: $($v.Out.Trim())`n$(Tail ($r.Out + $r.Err) 2)" $r.Seconds
        Remove-Item -LiteralPath (Join-Path $SbRepo '.venv') -Recurse -Force -ErrorAction SilentlyContinue
    }
    # A Linux .venv from WSL in a shared checkout must be left alone.
    New-Item -ItemType Directory -Force -Path (Join-Path $SbRepo '.venv\bin') | Out-Null
    Set-Content -LiteralPath (Join-Path $SbRepo '.venv\bin\python') -Value 'linux'
    $r = Invoke-Native 'scr-setup-wsl-venv' $PsExe ($psArgs + @($setupPs, '-Python', $(if ($base312) { $base312 } else { 'python' }))) -WorkDir $SbRepo
    $kept = Test-Path -LiteralPath (Join-Path $SbRepo '.venv\bin\python')
    Add-Result 'SCR-3c' $(if ($r.Code -ne 0 -and $kept -and -not (Test-Path -LiteralPath $venvPy)) { 'PASS' } else { 'FAIL' }) 'setup-runtime.ps1 leaves a Linux (WSL) .venv alone' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
    Remove-Item -LiteralPath (Join-Path $SbRepo '.venv') -Recurse -Force -ErrorAction SilentlyContinue

    if ($base312) {
        $r = Invoke-Native 'scr-setup-312' $PsExe ($psArgs + @($setupPs, '-Python', $base312)) -WorkDir $SbRepo -TimeoutSec 900
        $v = Invoke-Native 'scr-setup-312-ver' $venvPy @('-E', '-c', 'import sys;import mujoco,numpy;print(sys.version.split()[0],mujoco.__version__,numpy.__version__)')
        $pinned = $v.Out.Trim() -match '^3\.12\.\d+ 3\.3\.7 2\.5\.4$'
        $status = if ($r.Code -ne 0) { 'FAIL' } elseif ($pinned) { 'PASS' } else { 'WARN' }
        Add-Result 'SCR-4' $status 'setup-runtime.ps1 -Python <3.12> creates .venv with the pinned runtime' "exit $($r.Code); python mujoco numpy: $($v.Out.Trim())$(if (-not $pinned) { "`nnumpy is not pinned by setup-runtime.ps1 (runtime-requirements.txt pins 2.5.4)" })" $r.Seconds

        $r = Invoke-Native 'scr-install' $PsExe ($psArgs + @($installPs, '-Destination', $dest)) -WorkDir $SbRepo
        $target = Join-Path $dest 'newton'
        $cfg = Read-JsonFile (Join-Path $target 'runtime.json')
        $installed = @()
        if (Test-Path -LiteralPath $target) {
            $installed = @(Get-ChildItem -LiteralPath $target -Recurse -File | ForEach-Object { 'newton/' + $_.FullName.Substring($target.Length + 1).Replace('\', '/') } | Sort-Object)
        }
        $missing = @($Expected | Where-Object { $installed -notcontains $_ })
        $extra = @($installed | Where-Object { $Expected -notcontains $_ -and $_ -ne 'newton/runtime.json' })
        $ok = $r.Code -eq 0 -and $cfg -and $cfg.python -eq $venvPy -and $missing.Count -eq 0 -and $extra.Count -eq 0
        $missingText = if ($missing.Count -gt 5) { "$($missing.Count) files" } else { $missing -join ', ' }
        Add-Result 'SCR-5' $(if ($ok) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 installs the same files as the zip plus runtime.json' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 3)`nruntime.json: $(if ($cfg) { $cfg.python })`nmissing: $missingText; extra: $($extra -join ', ')"
      if (-not (Test-Path -LiteralPath (Join-Path $target '__init__.py'))) {
        Add-Result 'SCR-6' 'SKIP' 'install-local.ps1 -Update cases' 'need the installation from SCR-5'
      } else {
        $r = Invoke-Native 'scr-install-again' $PsExe ($psArgs + @($installPs, '-Destination', $dest)) -WorkDir $SbRepo
        Add-Result 'SCR-6' $(if ($r.Code -ne 0 -and (($r.Out + $r.Err) -match '-Update')) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 refuses an existing installation without -Update' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
        Set-Content -LiteralPath (Join-Path $target 'stale.py') -Value '# removed in a newer version'
        $r = Invoke-Native 'scr-update' $PsExe ($psArgs + @($installPs, '-Destination', $dest, '-Update')) -WorkDir $SbRepo
        $backups = @(Get-ChildItem -LiteralPath (Join-Path $SbRepo '.backups') -Directory -ErrorAction SilentlyContinue)
        $stale = Test-Path -LiteralPath (Join-Path $target 'stale.py')
        Add-Result 'SCR-7' $(if ($r.Code -eq 0 -and $backups.Count -eq 1) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 -Update makes a backup in .backups' "exit $($r.Code); backups: $($backups.Count)"
        Add-Result 'SCR-8' $(if ($stale) { 'WARN' } else { 'PASS' }) 'Files removed from Newton disappear on -Update' "stale.py still present after -Update: $stale"
        $foreign = Join-Path $Sandbox 'foreign plugins'
        New-Item -ItemType Directory -Force -Path (Join-Path $foreign 'newton') | Out-Null
        Set-Content -LiteralPath (Join-Path $foreign 'newton\__init__.py') -Value '# another extension'
        $r = Invoke-Native 'scr-update-foreign' $PsExe ($psArgs + @($installPs, '-Destination', $foreign, '-Update')) -WorkDir $SbRepo
        $untouched = (Get-ChildItem -LiteralPath (Join-Path $foreign 'newton')).Count -eq 1
        Add-Result 'SCR-9' $(if ($r.Code -ne 0 -and $untouched) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 -Update refuses a foreign newton folder' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
        if ($Facts.pwsh) {
            $r = Invoke-Native 'scr-install-pwsh' $Facts.pwsh @('-NoProfile', '-File', $installPs, '-Destination', (Join-Path $Sandbox 'pwsh plugins')) -WorkDir $SbRepo
            Add-Result 'SCR-10' $(if ($r.Code -eq 0) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 under PowerShell 7' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 1)"
        }
      }
    } else {
        Add-Result 'SCR-4' 'SKIP' 'setup-runtime.ps1 with Python 3.12' 'no Python 3.12 available'
    }
    # cmd.exe users: the documented call needs PowerShell; check that the scripts run when started from cmd.
    # cmd /c keeps the outer quotes only with /s and the whole command line quoted once more.
    $r = Invoke-Native 'scr-from-cmd' "$env:SystemRoot\System32\cmd.exe" -RawArguments ("/d /s /c `"powershell -NoProfile -ExecutionPolicy Bypass -File `"$installPs`" -Destination `"$(Join-Path $Sandbox 'cmd plugins')`"`"") -WorkDir $SbRepo
    Add-Result 'SCR-11' $(if ($r.Code -eq 0) { 'PASS' } else { 'FAIL' }) 'install-local.ps1 started from cmd.exe' "exit $($r.Code): $(Tail ($r.Out + $r.Err) 2)"
}

# ---------------------------------------------------------------- worker smoke test with every interpreter
function Get-WorkerPayload {
    $h = 0.5
    $verts = @()
    foreach ($x in -$h, $h) { foreach ($y in -$h, $h) { foreach ($z in -$h, $h) { $verts += , @($x, $y, $z) } } }
    $body = [ordered]@{ uid = 'probe-box'; center = @(0, 0, 3); half = @($h, $h, $h); vertices = $verts; mass = 1.0; shape = 'box'
        friction = 0.5; restitution = 0.0; joint = $null; reference = $null; inertia_mass = 1.0; no_collision = @(); simulation_override = $null }
    $lines = @((@{ op = 'init'; bodies = @($body); floor = $true } | ConvertTo-Json -Depth 6 -Compress))
    for ($i = 0; $i -lt 20; $i++) { $lines += '{"op": "step", "count": 24}' }
    $lines += '{"op": "quit"}'
    return ($lines -join "`n") + "`n"
}
if (Phase 'worker') {
    $payload = Get-WorkerPayload
    $worker = Join-Path $SbNewton 'worker.py'
    $interpreters = [ordered]@{ 'method B' = $RtBPython }
    if ($RtC) { $interpreters['method C uv'] = Join-Path $RtC 'venv\Scripts\python.exe' }
    if ($RtC2) { $interpreters['method C venv'] = Join-Path $RtC2 'venv\Scripts\python.exe' }
    $n = 0
    foreach ($label in $interpreters.Keys) {
        $exe = $interpreters[$label]; $n++
        if (-not (Test-Path -LiteralPath $exe)) { Add-Result "WRK-$n" 'SKIP' "Worker with $label" 'interpreter missing'; continue }
        # PYTHONPATH and PYTHONHOME of a foreign Python must not reach the worker (-E).
        $r = Invoke-Native "wrk-$n" $exe @('-E', '-u', $worker) -InputText $payload -WorkDir $SbNewton -Env @{ PYTHONPATH = 'C:\nonexistent\site-packages'; PYTHONHOME = 'C:\nonexistent' } -TimeoutSec 120
        $replies = @($r.Out -split "`r?`n" | Where-Object { $_.StartsWith('NEWTON:') } | ForEach-Object { $_.Substring(7) | ConvertFrom-Json })
        $z = $null
        if ($replies.Count -gt 0 -and $replies[-1].ok) { $z = $replies[-1].poses.'probe-box'[0][2] }
        $ok = $r.Code -eq 0 -and $replies.Count -eq 21 -and @($replies | Where-Object { -not $_.ok }).Count -eq 0 -and $null -ne $z -and $z -gt 0.45 -and $z -lt 0.56
        Add-Result "WRK-$n" $(if ($ok) { 'PASS' } else { 'FAIL' }) "Worker protocol and physics with $label (box falls from 3 m and rests at 0.5 m)" "exit $($r.Code); replies $($replies.Count)/21; z after 2 s: $z; $([math]::Round($r.Seconds,2)) s incl. start`n$(Tail $r.Err 2)" $r.Seconds
    }
}

# ---------------------------------------------------------------- non-ASCII user folder
if ((Phase 'unicode') -and $AnyPython -and $UvExe -and (Test-Path -LiteralPath $UvExe)) {
    $uData = Join-Path $Sandbox 'Jürgen Ølsen 测试\ingetrazo'
    New-Item -ItemType Directory -Force -Path $uData | Out-Null
    $r = Invoke-Native 'uni-install' $AnyPython @($Setup, 'install', '--yes', '--uv', $UvExe, '--data-dir', $uData) -Sandboxed -TimeoutSec 1200
    $r2 = Invoke-Native 'uni-check' $AnyPython @($Setup, 'check', '--data-dir', $uData) -Sandboxed
    $uPython = Join-Path $uData 'newton-runtime\venv\Scripts\python.exe'
    $r3 = $null; $wok = $false
    if (Test-Path -LiteralPath $uPython) {
        $r3 = Invoke-Native 'uni-worker' $uPython @('-E', '-u', (Join-Path $SbNewton 'worker.py')) -InputText (Get-WorkerPayload) -WorkDir $SbNewton -TimeoutSec 120
        $wok = $r3.Code -eq 0 -and @($r3.Out -split "`n" | Where-Object { $_ -like 'NEWTON:{"ok": true*' }).Count -eq 21
    }
    Add-Result 'UNI-1' $(if ($r.Code -eq 0 -and $r2.Code -eq 0 -and $wok) { 'PASS' } else { 'FAIL' }) 'Runtime in a folder with spaces and non-ASCII characters (--uv, --data-dir)' "install exit $($r.Code), check exit $($r2.Code): $(Tail ($r2.Out + $r2.Err) 1), worker ok: $wok`n$(Tail $r.Err 2)" $r.Seconds
    Invoke-Native 'uni-uninstall' $AnyPython @($Setup, 'uninstall', '--yes', '--data-dir', $uData) -Sandboxed | Out-Null
}

# ---------------------------------------------------------------- WSL
if (Phase 'wsl') {
    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if ($wsl) {
        $r = Invoke-Native 'wsl-info' $wsl.Source @('-e', 'sh', '-c', 'uname -sr; command -v python3; python3 --version; command -v uv || echo "uv: none"') -TimeoutSec 60
        Add-Result 'WSL-1' 'INFO' 'WSL present' ((($r.Out + $r.Err) -replace "`0", '').Trim())
        if (Test-Path -LiteralPath $RtB) {
            # A Windows runtime is not usable from Linux: the CLI under WSL must not report it as working.
            $wslSetup = '/mnt/' + $Setup.Substring(0, 1).ToLower() + ($Setup.Substring(2) -replace '\\', '/')
            $wslData = '/mnt/' + $SbData.Substring(0, 1).ToLower() + ($SbData.Substring(2) -replace '\\', '/')
            $r = Invoke-Native 'wsl-check' $wsl.Source @('-e', 'python3', $wslSetup, 'check', '--data-dir', $wslData) -TimeoutSec 60
            Add-Result 'WSL-2' $(if ($r.Code -ne 0) { 'PASS' } else { 'WARN' }) 'runtime_setup.py check under WSL does not accept the Windows runtime' "exit $($r.Code): $(Tail (($r.Out + $r.Err) -replace "`0", '') 1)"
        }
    } else {
        Add-Result 'WSL-1' 'INFO' 'WSL' 'wsl.exe not found'
    }
}

# ---------------------------------------------------------------- live installation (read only)
if (Phase 'live') {
    $liveNewton = Join-Path $LivePlugins 'newton'
    if (Test-Path -LiteralPath (Join-Path $liveNewton '__init__.py')) {
        $liveVersion = ([regex]::Match((Get-Content -LiteralPath (Join-Path $liveNewton '__init__.py') -Raw), '__version__ = "([^"]+)"')).Groups[1].Value
        $diff = @()
        foreach ($rel in $Expected) {
            $src = if ($rel -eq 'newton/LICENSE') { Join-Path $RepoRoot 'LICENSE' } else { Join-Path $RepoRoot ($rel -replace '/', '\') }
            $dst = Join-Path $LivePlugins ($rel -replace '/', '\')
            if (-not (Test-Path -LiteralPath $dst)) { $diff += "missing $rel" }
            elseif ((Get-FileHash -LiteralPath $src).Hash -ne (Get-FileHash -LiteralPath $dst).Hash) { $diff += "differs $rel" }
        }
        $liveFiles = Get-ChildItem -LiteralPath $liveNewton -Recurse -File | ForEach-Object { 'newton/' + $_.FullName.Substring($liveNewton.Length + 1).Replace('\', '/') }
        $old = @($liveFiles | Where-Object { $Expected -notcontains $_ -and $_ -ne 'newton/runtime.json' -and $_ -notmatch '__pycache__' })
        $cfg = Read-JsonFile (Join-Path $liveNewton 'runtime.json')
        $missingCount = @($diff | Where-Object { $_ -like 'missing*' }).Count
        $differsCount = @($diff | Where-Object { $_ -like 'differs*' }).Count
        Add-Result 'LIVE-1' $(if ($diff.Count) { 'INFO' } else { 'PASS' }) "Live Newton $liveVersion against this checkout ($Version)" "missing: $missingCount, differing: $differsCount, files not in this version: $($old -join ', ')`nplugin runtime.json: $(if ($cfg) { $cfg.python } else { '(none)' })"
        if ($cfg -and $cfg.python -and -not (Test-Path -LiteralPath $cfg.python)) {
            Add-Result 'LIVE-2' 'WARN' 'Live plugin runtime.json points to a missing interpreter' $cfg.python
        }
    } else {
        Add-Result 'LIVE-1' 'INFO' 'Live Newton' 'not installed'
    }
}

# ---------------------------------------------------------------- GUI: the real host with the sandbox as plugins folder
$RegKey = 'HKCU\Software\IngeTrazo'
if ($Gui -and (Phase 'gui')) {
    if (-not $HostExe) {
        Add-Result 'GUI-0' 'SKIP' 'GUI phase' 'ingetrazo.exe not found'
    } elseif (@(Get-Process ingetrazo -ErrorAction SilentlyContinue).Count) {
        Add-Result 'GUI-0' 'SKIP' 'GUI phase' 'IngeTrazo is running. Close it and rerun with -Gui -Skip package,zip,... (its settings are restored after the sandbox run, which needs it closed)'
    } else {
        $regBefore = Join-Path $OutDir 'registry-before.reg'
        $regAfter = Join-Path $OutDir 'registry-after.reg'
        & reg.exe export $RegKey $regBefore /y | Out-Null
        $autosave = Join-Path $LiveData 'IngeTrazo\autosave'
        $autosaveBefore = @(Get-ChildItem -LiteralPath $autosave -File -ErrorAction SilentlyContinue | ForEach-Object Name)
        Copy-Item -LiteralPath (Join-Path $RepoRoot 'scripts\lab\windows_install_probe.py') -Destination (Join-Path $SbPlugins 'zz_newton_probe.py')
        $model = Join-Path $Sandbox 'domino-30-with-pendulum.igz'
        Copy-Item -LiteralPath (Join-Path $RepoRoot 'models\domino-30-with-pendulum.igz') -Destination $model
        $probeOut = Join-Path $OutDir 'gui-probe.json'
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $HostExe
        $psi.Arguments = '--new-window ' + (Quote-Arg $model)
        $psi.UseShellExecute = $false
        $psi.WorkingDirectory = Split-Path $HostExe
        $psi.EnvironmentVariables['APPDATA'] = $SbRoaming
        $psi.EnvironmentVariables['LOCALAPPDATA'] = $SbLocal
        $psi.EnvironmentVariables['NEWTON_PROBE_OUT'] = $probeOut
        $psi.EnvironmentVariables['NEWTON_PROBE_SETUP_ROOT'] = (Join-Path $Sandbox 'host button\newton-runtime')
        $psi.EnvironmentVariables['NEWTON_PROBE_KEEP_OPEN'] = $(if ($GuiKeepOpen) { '1' } else { '0' })
        Write-Host 'Starting IngeTrazo with the sandbox plugins folder. Do not use the window until it closes by itself.' -ForegroundColor Yellow
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $hostProc = [System.Diagnostics.Process]::Start($psi)
        $limit = if ($GuiKeepOpen) { 3600 } else { 600 }
        if (-not $hostProc.WaitForExit($limit * 1000)) {
            Add-Result 'GUI-0' 'WARN' 'Sandbox IngeTrazo did not close by itself' "killed after $limit s (a dialog may have been open)"
            try { $hostProc.Kill() } catch {}
            Start-Sleep -Seconds 2
        }
        $watch.Stop()
        $probe = Read-JsonFile $probeOut
        if (-not $probe) {
            Add-Result 'GUI-1' 'FAIL' 'Probe plugin wrote no report' "Host exit $($hostProc.ExitCode). Logs: $SbLocal\IngeTrazo"
        } else {
            $errs = 'none'
            if ($probe.PSObject.Properties['load_errors'] -and $probe.load_errors -and @($probe.load_errors.PSObject.Properties).Count) {
                $errs = $probe.load_errors | ConvertTo-Json -Compress
            }
            $sandboxed = $probe.PSObject.Properties['newton_file'] -and $probe.newton_file -and $probe.newton_file.StartsWith($SbPlugins)
            Add-Result 'GUI-1' $(if ($probe.newton_loaded -and $sandboxed -and $errs -eq 'none') { 'PASS' } else { 'FAIL' }) 'Host loads Newton from the sandbox plugins folder' "file: $($probe.newton_file)`nversion: $($probe.newton_version); load errors: $errs; frozen: $($probe.frozen)"
            if ($probe.PSObject.Properties['menu_actions']) {
                $okUi = $probe.dock -and @($probe.menu_actions).Count -gt 0 -and @($probe.toolbars).Count -ge 2
                Add-Result 'GUI-2' $(if ($okUi) { 'PASS' } else { 'FAIL' }) 'Menu entry, sidebar and toolbars exist' "menu: $($probe.menu_actions -join ', '); toolbars: $($probe.toolbars -join ', '); dock: $($probe.dock)"
                Add-Result 'GUI-3' 'INFO' 'Runtime as the host sees it' "runtime_dir: $($probe.runtime_dir)`nresolve(): $($probe.resolve)`ncheck: $($probe.check_resolved | ConvertTo-Json -Compress)`npreference newton/python: $($probe.settings_newton_python)`nsidebar interpreter at start: $($probe.panel_python_initial)`nQt AppDataLocation: $($probe.qt_appdata)"
            }
            if ($probe.PSObject.Properties['install_in_host']) {
                $ih = $probe.install_in_host
                Add-Result 'GUI-4' $(if ($ih.ok) { 'PASS' } else { 'FAIL' }) "'Set up runtime' code path inside the frozen host (uv download over the host's TLS)" "$(if ($ih.ok) { "$($ih.python); $($ih.check -join ' ')" } else { $ih.error })" $ih.seconds
            }
            if ($probe.PSObject.Properties['simulation']) {
                $s = $probe.simulation
                Add-Result 'GUI-5' $(if ($s.ok) { 'PASS' } else { 'FAIL' }) "Start in the host simulates the opened model ($($probe.model_bodies) Newton bodies)" ("python: $($probe.simulation_python)`n" + ($s | ConvertTo-Json -Compress))
                Add-Result 'GUI-6' $(if ($probe.reset_restored) { 'PASS' } else { 'FAIL' }) 'Reset stops the worker' "process gone: $($probe.reset_restored)"
            } elseif ($probe.PSObject.Properties['model_bodies']) {
                Add-Result 'GUI-5' 'FAIL' 'Start in the host' "model bodies: $($probe.model_bodies)"
            }
            $lastStep = @($probe.steps)[-1]
            if ($lastStep -and $lastStep.name -eq 'probe exception') { Add-Result 'GUI-7' 'FAIL' 'Probe exception' $lastStep.error }
        }
        foreach ($log in Get-ChildItem -LiteralPath (Join-Path $SbLocal 'IngeTrazo') -Filter '*.log' -ErrorAction SilentlyContinue) {
            Copy-Item -LiteralPath $log.FullName -Destination (Join-Path $OutDir ("host-" + $log.Name))
            $tail = Tail (Get-Content -LiteralPath $log.FullName -Raw) 6
            if ($tail) { Add-Result 'GUI-8' 'INFO' "Host log $($log.Name)" $tail }
        }
        # Restore the host settings the sandbox run may have written (window state, newton/python).
        & reg.exe export $RegKey $regAfter /y | Out-Null
        $changed = (Get-Content -LiteralPath $regBefore -Raw) -ne (Get-Content -LiteralPath $regAfter -Raw)
        if ($changed) {
            & reg.exe delete $RegKey /f | Out-Null
            & reg.exe import $regBefore | Out-Null
            $regCheck = Join-Path $OutDir 'registry-restored.reg'
            & reg.exe export $RegKey $regCheck /y | Out-Null
            $same = (Get-Content -LiteralPath $regBefore -Raw) -eq (Get-Content -LiteralPath $regCheck -Raw)
            Add-Result 'GUI-9' $(if ($same) { 'PASS' } else { 'FAIL' }) 'Host settings (HKCU\Software\IngeTrazo) restored after the sandbox run' "changed by the run: yes; restored identical: $same; backup: registry-before.reg"
        } else {
            Add-Result 'GUI-9' 'PASS' 'Host settings unchanged by the sandbox run' ''
        }
        $autosaveAfter = @(Get-ChildItem -LiteralPath $autosave -File -ErrorAction SilentlyContinue | ForEach-Object Name)
        $newAutosave = @($autosaveAfter | Where-Object { $autosaveBefore -notcontains $_ })
        Add-Result 'GUI-10' $(if ($newAutosave.Count) { 'WARN' } else { 'PASS' }) 'No autosave left in the real profile' "new files: $($newAutosave -join ', ')"
    }
}

# ---------------------------------------------------------------- cleanup
if (Phase 'cleanup') {
    if ($AnyPython -and (Test-Path -LiteralPath $RtB)) {
        $r = Invoke-Native 'rt-uninstall' $AnyPython @($Setup, 'uninstall', '--yes') -Sandboxed
        Add-Result 'RT-11' $(if ($r.Code -eq 0 -and -not (Test-Path -LiteralPath $RtB)) { 'PASS' } else { 'FAIL' }) 'runtime_setup.py uninstall removes the runtime' "exit $($r.Code): $(Tail $r.Err 1)"
    }
    if (-not $Keep) {
        try { Remove-Item -LiteralPath $Sandbox -Recurse -Force -ErrorAction Stop; Add-Result 'END' 'INFO' 'Sandbox removed' $Sandbox }
        catch { Add-Result 'END' 'WARN' 'Sandbox not fully removed' "$Sandbox`n$($_.Exception.Message)" }
    }
}

$counts = $Results | Group-Object { $_.status } | ForEach-Object { "$($_.Name) $($_.Count)" }
$summary = "Newton Windows installation test $Stamp`n$($counts -join ', ')`n`n" + (($Results | ForEach-Object { "[{0}] {1,-8} {2}" -f $_.status, $_.id, $_.name }) -join "`n")
Set-Content -LiteralPath (Join-Path $OutDir 'summary.txt') -Value $summary -Encoding utf8
Save-Results
Stop-Transcript | Out-Null
Write-Host "`n$($counts -join ', ')"
Write-Host "Results: $OutDir"
