# Setting up the Newton runtime

Newton runs its physics in a separate Python process. IngeTrazo does not ship a suitable Python, so Newton needs a **runtime**: a Python 3.12 (64-bit) environment with `mujoco==3.3.7` (and `numpy==2.5.4`, see `newton/runtime-requirements.txt`). It is created once per user and survives Newton updates. Install the extension first: [installation.md](installation.md).

| Platform | Status |
|---|---|
| Linux x86_64, IngeTrazo Flatpak | tested |
| Windows x64 | tested on Windows 11 with IngeTrazo 0.6.0: the button, methods B and C (`scripts/lab/windows-install-test.ps1`) |
| macOS | not tested; the automatic setup has a `uv` download for Apple silicon (arm64) only |
| Linux AppImage or tarball | not tested |
| Linux Snap | not tested |

There are three methods. All end in the same layout and the same `runtime.json`, so they can be mixed.

| Method | Needs | Use it when |
|---|---|---|
| A. **Set up runtime** button | internet access | normal desktop use (start here) |
| B. `runtime_setup.py` on the command line | any Python 3.9+ | scripted or headless setups, or when the button fails |
| C. Manual commands | `uv` or Python 3.12 | you want full control, or no download of `uv` is allowed |

## Where the runtime lives

The runtime sits next to IngeTrazo's `plugins` folder, **outside** the Newton plugin folder, so updating or reinstalling Newton does not delete it. `<data>` is the folder that contains `plugins`:

| IngeTrazo installation | `<data>` |
|---|---|
| Windows installer or portable zip | `%APPDATA%\ingetrazo` |
| Linux AppImage or tarball | `${XDG_DATA_HOME:-~/.local/share}/ingetrazo` |
| Linux Flatpak | `~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo` |
| macOS app | `~/.local/share/ingetrazo` (IngeTrazo uses this on macOS too) |
| Linux Snap (not verified) | `~/snap/ingetrazo/current/.local/share/ingetrazo` |

`<data>/newton-runtime/` holds `python/` (the interpreter), `venv/`, `cache/`, `tools/uv`, `runtime.json` and a marker file `.newton-runtime`. Removing the runtime deletes only a folder that carries this marker, so a runtime you built by hand (method C, no marker) is never deleted by Newton.

## Method A: the button

1. Open **Preferences → Newton → Runtime** and press **Set up runtime**.
2. Newton names what it will do: download `uv` 0.13.7 (checked against a pinned SHA-256), a Python 3.12 and `mujoco==3.3.7` into the folder above, and test it. Nothing is downloaded before you confirm.
3. Wait for "Runtime ready". No restart of IngeTrazo is needed; the page then shows `Interpreter: <path>`.

The other buttons: **Check runtime** starts the interpreter and tests that MuJoCo imports with the right version. **Remove runtime** deletes `<data>/newton-runtime/` after confirmation, only when it carries the marker, that is, only a runtime Newton installed itself. An interpreter you chose elsewhere is never touched.

Offline: the button needs internet. Without it use method B with `--find-links` or method C.

Maintainer switches in `newton/runtime_setup.py`: `RUNTIME_SETUP_ENABLED = False` replaces the button with a link to the manual section below; `DOWNLOAD_UV = False` never downloads a binary and uses a `uv` already in `PATH`.

## Method B: command line

`runtime_setup.py` is part of the Newton package and uses only the Python standard library, so any Python 3.9+ runs it. Run the installed copy and it targets the right `<data>` by itself:

```bash
python3 <plugins>/newton/runtime_setup.py install      # create or repair
python3 <plugins>/newton/runtime_setup.py check        # exit 0 when the runtime works
python3 <plugins>/newton/runtime_setup.py path         # print the interpreter path
python3 <plugins>/newton/runtime_setup.py uninstall
```

`<plugins>` is the plugins folder from [installation.md](installation.md#plugin-folder-per-installation).

```powershell
# Windows
py -3 "$env:APPDATA\ingetrazo\plugins\newton\runtime_setup.py" install --yes
```

```bash
# Linux Flatpak, run on the host (outside the sandbox)
python3 ~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton/runtime_setup.py install --flatpak --yes
# Linux AppImage or tarball, macOS
python3 "${XDG_DATA_HOME:-$HOME/.local/share}/ingetrazo/plugins/newton/runtime_setup.py" install --yes
```

Options:

- `--data-dir DIR` targets another IngeTrazo data folder (`<data>` above); needed when you run the script from a source checkout, because it would otherwise create `.newton-runtime/` inside the checkout.
- `--flatpak` is a shortcut for the Flatpak `<data>`. Use either `--data-dir` or `--flatpak`.
- `--yes` skips the confirmation (also for `uninstall`).
- `--json` prints one JSON object (`step`, `message`) per progress line.
- `--uv PATH` uses this `uv` instead of the one in `PATH` or a download.
- `--find-links DIR` installs MuJoCo from a folder or URL of wheels (offline setups).

Exit codes: 0 ok, 1 failure, 2 bad arguments, 3 unsupported platform.

The built-in `uv` download exists for Windows x64, Linux x86_64 and macOS arm64. On any other machine (for example an Intel Mac) install `uv` yourself and pass `--uv` or put it in `PATH`; it is then used on every platform.

## Method C: manual

Use the folder from the table above as `<data>`. The result must be a Python 3.12 (64-bit) with `mujoco==3.3.7` and `numpy==2.5.4`, installed from binary wheels. MuJoCo 3.3.7 publishes cp312 wheels for Windows x86_64, Linux x86_64 and aarch64, and macOS arm64 and x86_64 (checked on PyPI).

### Windows

With [uv](https://docs.astral.sh/uv/) (install it as the uv documentation describes, for example `winget install astral-sh.uv`; this command is not verified here). uv downloads Python 3.12 when none is installed. PowerShell:

```powershell
$rt = "$env:APPDATA\ingetrazo\newton-runtime"
$env:UV_PYTHON_INSTALL_DIR = "$rt\python"; $env:UV_PYTHON_PREFERENCE = 'only-managed'
uv venv --python 3.12 "$rt\venv"
uv pip install --python "$rt\venv\Scripts\python.exe" --only-binary :all: mujoco==3.3.7 numpy==2.5.4
@{python = "$rt\venv\Scripts\python.exe"} | ConvertTo-Json | Set-Content -Encoding ascii "$rt\runtime.json"
& "$rt\venv\Scripts\python.exe" -c "import mujoco; print(mujoco.__version__)"   # 3.3.7
```

Without uv, with a Python 3.12 x64 you already have:

```powershell
$rt = "$env:APPDATA\ingetrazo\newton-runtime"
py -3.12 -m venv "$rt\venv"
& "$rt\venv\Scripts\python.exe" -m pip install --only-binary :all: mujoco==3.3.7 numpy==2.5.4
@{python = "$rt\venv\Scripts\python.exe"} | ConvertTo-Json | Set-Content -Encoding ascii "$rt\runtime.json"
```

The repository also has `scripts\setup-runtime.ps1`, which creates a `.venv` in the checkout instead (see [installation.md](installation.md#from-a-checkout-with-the-helper-scripts)).

### Linux

With uv (see the uv documentation for installing it). Replace `DATA` with the `<data>` folder for your installation:

```bash
DATA=~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo     # Flatpak; AppImage: ${XDG_DATA_HOME:-~/.local/share}/ingetrazo
export UV_PYTHON_INSTALL_DIR=$DATA/newton-runtime/python UV_PYTHON_PREFERENCE=only-managed
uv venv --python 3.12 $DATA/newton-runtime/venv
uv pip install --python $DATA/newton-runtime/venv/bin/python --only-binary :all: mujoco==3.3.7 numpy==2.5.4
printf '{"python": "%s"}\n' "$DATA/newton-runtime/venv/bin/python" > $DATA/newton-runtime/runtime.json
$DATA/newton-runtime/venv/bin/python -c "import mujoco; print(mujoco.__version__)"   # 3.3.7
```

Without uv, with a Python 3.12 you already have (not for the Flatpak, see below):

```bash
python3.12 -m venv $DATA/newton-runtime/venv
$DATA/newton-runtime/venv/bin/python -m pip install --only-binary :all: mujoco==3.3.7 numpy==2.5.4
printf '{"python": "%s"}\n' "$DATA/newton-runtime/venv/bin/python" > $DATA/newton-runtime/runtime.json
```

**Flatpak specifics:**

- A venv built on the host's system Python does **not** work: the sandbox cannot see the host's `/usr`. Use the uv commands, whose interpreter lives under your home folder, which the Flatpak can read.
- The Flatpak sets a `PYTHONPATH` for its own Python. Newton starts the worker with `python -E`, so that variable does not leak into the runtime; nothing to configure.

### macOS (not tested)

Same commands as Linux with `DATA=~/.local/share/ingetrazo`. Install uv as its documentation describes. IngeTrazo's `.dmg` is built for Apple silicon (see the IngeTrazo README); MuJoCo 3.3.7 also has Intel wheels, but the automatic setup has no `uv` download for Intel, so install `uv` yourself there.

### Picking the interpreter

Newton picks the interpreter in this order:

1. the path in **Preferences → Newton → Runtime** (wins over everything else; clear it to fall back),
2. `<data>/newton-runtime/runtime.json`,
3. a `runtime.json` inside the plugin folder (older versions and the helper scripts write it there),
4. `<data>/newton-runtime/venv`.

`runtime.json` is `{"python": "/absolute/path/to/python"}`; on Windows use forward slashes or doubled backslashes. A runtime in any other place (for example the `.venv` of a checkout) works the same way: set its interpreter in the preferences or in `runtime.json`.

## Troubleshooting

- **"MuJoCo is not usable" or wrong version:** run `runtime_setup.py check`; it names the failing part. `install` repairs an existing runtime.
- **Corporate proxy:** set `HTTPS_PROXY`. Without internet, download the wheels elsewhere and use `--find-links`.
- **SmartScreen or antivirus blocks `uv.exe`:** use method C with a Python 3.12 you already have, or pass `--uv` pointing to a trusted copy.
- **Newton still says "No runtime found":** the path in *Preferences → Newton → Runtime* wins over the files; clear it or point it to `runtime.json`'s interpreter.
- **Button missing or "Runtime setup is disabled":** the build has `RUNTIME_SETUP_ENABLED = False`; use the manual section.
- **Snap (not verified):** hidden folders in your home are not visible to the confined app; use the Snap data folder listed above.

## Security notes

Downloaded `uv` binaries are verified against a SHA-256 pinned in `runtime_setup.py` before they are executed. Python comes from uv's standalone builds and MuJoCo from PyPI as binary wheels only (`--only-binary`). Packages are pinned by version, not by hash.
