# Known issues

Bugs and observations that are known but not yet fixed. Each entry states what is confirmed and what is still unverified. Remove an entry when its fix is merged; mention the fix in the commit message.

Status values: **open** (confirmed, not fixed), **observation** (reported, cause unknown), **fixed** (kept until the fix is released).

## Floating toolbar icons jump while a simulation runs

- **Status:** observation
- **Reported:** 2026-11-04, Linux (Ubuntu, GNOME on Wayland), IngeTrazo 0.6.0 Flatpak
- **Symptom:** With the Newton toolbar detached (floating) and a simulation running, the toolbar icons jump rapidly up and down.
- **Checked:** In an offscreen Qt run (QT_QPA_PLATFORM=offscreen), the toolbar was floated and a demo body simulated for 3 s. No Newton toolbar action emitted `changed` (no `setIcon`/`setEnabled` calls), and the toolbar requested one layout. The panel's per-refresh `setIcon` call (`newton/panel.py`, `refresh_widgets`) is therefore not confirmed as the cause.
- **Unverified:** whether it also happens on Windows, with a docked toolbar, with other (native) floating toolbars, while paused, or without other toolbar extensions (`igz_toolbars`, `organize_toolbar`) installed. The offscreen platform does not reproduce real window-manager behaviour.
- **Next step:** reproduce on a real display; compare a native IngeTrazo toolbar floated in the same way to separate a host/Qt-Wayland issue from a Newton issue.

## Narrow sidebar shows a small horizontal scrollbar

- **Status:** observation
- **Symptom:** Below roughly 280 px dock width the sidebar content (minimum about 232 px plus margins and the vertical scrollbar) is a few pixels wider than the viewport, so a horizontal scrollbar appears. Nothing is cut off.
- **Checked:** offscreen only (dock widths 260–560 px).

## Worker inherited the host's `PYTHONPATH` (Flatpak)

- **Status:** fixed (unreleased)
- **Symptom:** Start failed with "Importing the numpy C-extensions failed … `_multiarray_umath.cpython-313-x86_64-linux-gnu.so`".
- **Cause:** The Flatpak launcher exports `PYTHONPATH=/app/lib/python3.13/site-packages`. The worker process inherited it, so the external Python 3.12 loaded IngeTrazo's numpy built for Python 3.13.
- **Fix:** The worker is started with `python -E` (`newton/session.py`, `newton/collision_view.py`), which ignores all `PYTHON*` environment variables.

## Runtime fallback only knows the Windows virtual-environment layout

- **Status:** open
- **Where:** `newton/panel.py`, `default_python()`
- **Symptom:** Without `runtime.json` and without a saved preference, Newton looks only for `.venv/Scripts/python.exe` next to the extension. On Linux and macOS the interpreter is `.venv/bin/python`, so no default is found and the user must pick the runtime manually.
- **Workaround:** write `runtime.json` (see README) or choose the interpreter under Preferences → Newton → Runtime.

## Installation scripts exist only for Windows

- **Status:** open
- **Where:** `scripts/setup-runtime.ps1`, `scripts/install-local.ps1`
- **Symptom:** Linux installation is a manual sequence of commands (see README). There is no update/backup path on Linux.

## Worker protocol prefix still uses the old name

- **Status:** observation
- **Where:** `newton/worker.py` (`PREFIX = "IGPHYSICS:"`), `newton/session.py`
- **Note:** Version 0.14.0 renamed everything to Newton, but the line prefix of the worker protocol kept `IGPHYSICS:`. It is internal and harmless; unknown whether it was kept on purpose.

## Axis and connection objects: known gaps

- **Status:** open
- **Reported:** 2026-11-04, with the introduction of axis objects (`newton/axis_objects.py`)
- **Symptom:** An axis object stays visible when its body is hidden (the axis glyph hides). Its name (`Axis · <body>`) does not follow a body rename. Connection objects (`Connection · <body>`, since 2026-11-04) share these gaps. While a group is open for editing, no sync runs; it catches up with the next command after leaving the group. Grouping an axis object together with other objects (Make Group) removes it from the top level; Newton then creates a new one and keeps the axis.
- **Checked:** unit tests cover move, rotate, undo/redo, body move, copy/paste, delete and loading documents without axis objects. Not checked in a live IngeTrazo session yet.
