# Setting up the Newton runtime

Newton runs its physics in a separate Python process. IngeTrazo does not ship a suitable Python, so Newton needs a **runtime**: a Python 3.12 (64-bit) environment with `mujoco==3.3.7`. It is created once per user and survives Newton updates.

Supported by design: Windows x64, Linux x86_64 (AppImage, tarball, Flatpak) and macOS arm64. Windows and Linux are tested; macOS and Snap are not, bug reports are welcome.

There are three ways to create the runtime. All of them end in the same layout and the same `runtime.json`, so they can be mixed.

| Method | Needs | Use it when |
|---|---|---|
| A. **Set up runtime** button | internet access | normal desktop use |
| B. `runtime_setup.py` on the command line | any Python 3.9+ | scripted or headless setups, Flatpak from a terminal |
| C. Manual commands | `uv` or Python 3.12 | you want full control |

## Where the runtime lives

The runtime sits next to IngeTrazo's `plugins` folder, **outside** the Newton plugin folder, so updating or reinstalling Newton does not delete it. `<data>` is the folder that contains `plugins`:

| IngeTrazo installation | `<data>` |
|---|---|
| Windows installer or portable zip | `%APPDATA%\ingetrazo` |
| Linux AppImage or tarball | `${XDG_DATA_HOME:-~/.local/share}/ingetrazo` |
| Linux Flatpak | `~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo` |
| macOS app | `~/.local/share/ingetrazo` (IngeTrazo uses this on macOS too) |
| Linux Snap (untested) | `~/snap/ingetrazo/current/.local/share/ingetrazo` |

The folder `<data>/newton-runtime/` holds `python/` (the interpreter), `venv/`, `cache/`, `tools/uv`, `runtime.json` and a marker file `.newton-runtime`. Removing the runtime deletes only a folder that carries this marker.

Newton picks the interpreter in this order: the path in *Preferences ▸ Newton ▸ Runtime*, then `<data>/newton-runtime/runtime.json`, then a `runtime.json` inside the plugin folder (older versions), then `newton-runtime/venv`.

## Method A: button

1. Open *Preferences ▸ Newton ▸ Runtime* and press **Set up runtime**.
2. Newton names what it will do (download `uv`, a Python 3.12 and `mujoco==3.3.7` into the folder above) and asks for confirmation. Nothing is downloaded before you confirm.
3. Wait for "Runtime ready". No restart of IngeTrazo is needed. **Check runtime** tests it again, **Remove runtime** deletes the folder.

Builds can disable this feature with `RUNTIME_SETUP_ENABLED = False` in `newton/runtime_setup.py`; the button is then replaced by a pointer to this page. With `DOWNLOAD_UV = False` Newton never downloads a binary and uses a `uv` that is already in your `PATH`.

## Method B: command line

`runtime_setup.py` is part of the Newton package and uses only the Python standard library.

```bash
python3 runtime_setup.py install      # create or repair
python3 runtime_setup.py check        # exit 0 when the runtime works
python3 runtime_setup.py path         # print the interpreter path
python3 runtime_setup.py uninstall
```

Options:

- `--data-dir DIR` targets another IngeTrazo data folder.
- `--flatpak` is a shortcut for the Flatpak data folder.
- `--yes` skips the confirmation.
- `--json` prints one JSON object (`step`, `message`) per progress line.
- `--uv PATH` uses this `uv` instead of `PATH` or a download.
- `--find-links DIR` installs MuJoCo from a folder or URL of wheels (offline setups).

Exit codes: 0 ok, 1 failure, 2 bad arguments, 3 unsupported platform.

Without options the runtime goes next to the plugin the script belongs to, in a source checkout into `.newton-runtime/`.

```powershell
# Windows
py -3 "$env:APPDATA\ingetrazo\plugins\newton\runtime_setup.py" install --yes
```

```bash
# Flatpak, on the host
python3 ~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton/runtime_setup.py install --flatpak --yes
```

## Method C: manual

Use the folder from the table as `<data>`. With [uv](https://docs.astral.sh/uv/), the same commands work on every platform and IngeTrazo package, and uv downloads Python 3.12 when none is installed:

```bash
export UV_PYTHON_INSTALL_DIR=<data>/newton-runtime/python UV_PYTHON_PREFERENCE=only-managed
uv venv --python 3.12 <data>/newton-runtime/venv
uv pip install --python <data>/newton-runtime/venv/bin/python --only-binary :all: mujoco==3.3.7 numpy==2.5.4
printf '{"python": "%s"}\n' "<data>/newton-runtime/venv/bin/python" > <data>/newton-runtime/runtime.json
```

On Windows use `venv\Scripts\python.exe` and `set` instead of `export`, and write `runtime.json` with forward slashes or doubled backslashes.

Without uv, using a Python 3.12 you already have:

```bash
python3.12 -m venv <data>/newton-runtime/venv
<data>/newton-runtime/venv/bin/python -m pip install --only-binary :all: mujoco==3.3.7 numpy==2.5.4
```

**Flatpak:** a venv built on the host's system Python does **not** work, because the sandbox cannot see the host's `/usr`. Use the uv commands above: the interpreter then lives under your home folder, which the Flatpak can read.

Check the result:

```bash
<data>/newton-runtime/venv/bin/python -c "import mujoco; print(mujoco.__version__)"   # 3.3.7
```

## Troubleshooting

- **"MuJoCo is not usable" or wrong version:** run `runtime_setup.py check`; it names the failing part. `install` repairs an existing runtime.
- **Corporate proxy:** set `HTTPS_PROXY`. Without internet, download the wheels elsewhere and use `--find-links`.
- **SmartScreen or antivirus blocks `uv.exe`:** use method C with a Python 3.12 you already have, or pass `--uv` pointing to a trusted copy.
- **Newton still says "No runtime found":** the path in *Preferences ▸ Newton ▸ Runtime* wins over the files; clear it or point it to `runtime.json`'s interpreter.
- **Snap:** hidden folders in your home are not visible to the confined app; use the Snap data folder listed above.

## Security notes

Downloaded `uv` binaries are verified against a SHA-256 pinned in `runtime_setup.py` before they are executed. Python comes from uv's standalone builds and MuJoCo from PyPI as binary wheels only (`--only-binary`). Packages are pinned by version, not by hash.
