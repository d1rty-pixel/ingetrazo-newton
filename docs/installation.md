# Installing Newton

Newton has two parts, installed separately:

1. **The extension**, the `newton/` folder inside IngeTrazo's plugins folder (this page).
2. **The runtime**, a Python 3.12 environment with MuJoCo in which the physics runs: [runtime-setup.md](runtime-setup.md).

Newton targets IngeTrazo 0.6.0 (Extension API 2). Its code is Python and contains no binaries.

## Status per platform

| Platform | Status |
|---|---|
| Linux, IngeTrazo Flatpak | tested |
| Windows (installer or portable zip) | scripts exist (`install-local.ps1`, `setup-runtime.ps1`), run not re-verified |
| macOS (IngeTrazo `.dmg`, Apple Silicon) | not tested |
| Linux AppImage or tarball | not tested; same plugin folder logic as the host code below |
| Linux Snap | not tested; plugin folder not verified |

## A. From the IngeTrazo extension library

This describes the intended route once Newton is listed in the IngeTrazo community catalog. Until then, use [section B](#b-manual-installation). The dialog names below come from the IngeTrazo 0.6.0 source; the catalog entry itself is not verified.

1. In IngeTrazo open **Extensions → Manage extensions…**. The window is titled "Manage extensions".
2. On the **Browse** tab, type `Newton` in the search field and select the entry. It shows the version, licence and a link to the repository.
3. Press **Download** (the button reads **Update** when a newer version exists). Community entries that are not on the maintainers' reviewed list are labelled as unreviewed and ask for confirmation first. Extensions are Python code: install only what you trust.
4. Restart IngeTrazo. The host says "Restart required to apply changes"; extensions register their tools at startup.
5. After the restart Newton appears as **Extensions → Newton…**. The **Installed** tab lists it with **Update**, **Disable** and **Uninstall**.
6. Set up the runtime: **Preferences → Newton → Runtime → Set up runtime** ([runtime-setup.md](runtime-setup.md)). The simulation does not run before that.

For maintainers: the catalog expects a ZIP with exactly one top-level folder, `newton/`. The host checks the download against the SHA-256 in the catalog. `scripts/package.py` builds `dist/newton-<version>.zip` in that form with a reproducible hash.

## B. Manual installation

IngeTrazo loads every package folder `plugins/<name>/__init__.py` from its per-user plugins folder at startup. Newton must end up as `<plugins>/newton/__init__.py`. **Extensions → Open extensions folder** opens `<plugins>` (and creates it if needed).

### Plugin folder per installation

| IngeTrazo installation | `<plugins>` |
|---|---|
| Windows installer or portable zip | `%APPDATA%\ingetrazo\plugins` |
| Linux Flatpak | `~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins` |
| Linux AppImage, tarball | `${XDG_DATA_HOME:-~/.local/share}/ingetrazo/plugins` |
| macOS app | `~/.local/share/ingetrazo/plugins` (the host uses the XDG rule on every non-Windows system) |
| Linux Snap | not verified |

The Flatpak path is the XDG rule applied inside the sandbox, whose data folder is `~/.var/app/<id>/data`; the helper script uses it (tested).

### What to copy

Into `<plugins>/newton/`:

- `newton/*.py` (including `runtime_setup.py`) and `newton/runtime-requirements.txt`, which the runtime installer reads,
- the folders `newton/i18n/` and `newton/icons/`,
- `LICENSE` (optional),
- `runtime.json` is optional: it only points to a Python interpreter, see [runtime-setup.md](runtime-setup.md#picking-the-interpreter).

Do not copy `tests/`, `scripts/`, `models/` or `docs/`. The release zip described below has exactly this content.

### From the release zip

Download `newton-<version>.zip` from the [GitHub releases](https://github.com/d1rty-pixel/ingetrazo-newton/releases), or build it from a checkout (`python scripts/package.py` writes `dist/newton-<version>.zip`). The zip contains one `newton/` folder, so unpack it **into** `<plugins>`.

```bash
# Linux Flatpak
unzip newton-<version>.zip -d ~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins
# Linux AppImage or tarball
unzip newton-<version>.zip -d "${XDG_DATA_HOME:-$HOME/.local/share}/ingetrazo/plugins"
# macOS
unzip newton-<version>.zip -d ~/.local/share/ingetrazo/plugins
```

```powershell
# Windows
Expand-Archive newton-<version>.zip -DestinationPath "$env:APPDATA\ingetrazo\plugins"
```

Restart IngeTrazo, then set up the runtime.

### From a checkout with the helper scripts

Both scripts copy `newton/*.py`, `newton/i18n/` and `newton/icons/` and write `runtime.json` pointing to the project's `.venv`. They need that `.venv` with MuJoCo first (see [AGENTS.md](../AGENTS.md#development-setup)). They refuse to overwrite an existing installation unless told to update.

**Linux Flatpak** (tested), from the repository root:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mujoco==3.3.7
scripts/install-local.sh
```

| Option | Meaning |
|---|---|
| `--update` | replace an existing installation; the previous copy goes to `.backups/` in the repository |
| `--python PATH` | interpreter for `runtime.json` instead of `.venv/bin/python` |
| `--destination DIR` | plugins folder instead of the Flatpak one, for example `~/.local/share/ingetrazo/plugins` for an AppImage |

**Windows** (scripts exist, run not re-verified), PowerShell from the repository root:

```powershell
.\scripts\setup-runtime.ps1 -Python 'C:\Path\to\Python312\python.exe'
.\scripts\install-local.ps1
```

`setup-runtime.ps1` creates `.venv` and installs `mujoco==3.3.7` into it. `install-local.ps1` installs into `%APPDATA%\ingetrazo\plugins\newton`. Options: `-Update` (backup in `.backups`), `-Python` (another interpreter, for example an existing environment's `Scripts\python.exe`), `-Destination` (another plugins folder).

### Update and uninstall

- Update: repeat the copy or unzip over the existing folder (delete `<plugins>/newton/i18n` and `icons` first so removed files do not linger), or use `--update` / `-Update`. The runtime lives outside the plugin folder and survives.
- Uninstall: close IngeTrazo, delete `<plugins>/newton/`. To also remove the runtime, first use **Remove runtime** in the preferences (or `runtime_setup.py uninstall`), see [runtime-setup.md](runtime-setup.md).
- An extension put into the plugins folder by hand is shown on the **Installed** tab as "Installed by hand, outside the extension manager"; the manager can replace it with a catalog version once one exists.

## C. Verify

1. Restart IngeTrazo completely.
2. **Extensions → Newton…** exists, and the Newton sidebar and the toolbars **Newton Tools** and **Newton Simulation** can be shown.
3. **Preferences → Newton → Runtime** shows `Interpreter: <path>`. "No runtime found." means the runtime is still missing. **Check runtime** tests it.
4. Open one of the [example models](example-models.md) and press **Start**.

If the extension fails to load, the host lists it with a load error (Extensions → Manage extensions…, **Installed** tab, **View load error**) and still starts.
