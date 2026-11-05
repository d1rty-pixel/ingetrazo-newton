# Known issues

Bugs and observations that are known but not yet fixed. Each entry states what is confirmed and what is still unverified. Remove an entry when its fix is merged; mention the fix in the commit message.

Status values: **open** (confirmed, not fixed), **observation** (reported, cause unknown), **fixed** (kept until the fix is released).

## Starting a large model copies all geometry

- **Status:** open
- **Reported:** 2026-11-05, CR10 sliding electronics compartment model (about 250 000 vertices)
- **Symptom:** Pressing Start takes about 10 s before the simulation runs; the simulation itself is fast.
- **Checked:** `prepare()` (`newton/model.py`) copied every included group for the temporary simulation with `transformed_mesh`, which welds the whole mesh again. The clones now share the document's mesh (plain groups and component instances), and compound parts read their points without a copy; on this model `prepare()` dropped from 11.3 s to 4.3 s (see `docs/test-results.md`).
- **Remaining:** A group with children still needs one welded world-space mesh (`world_mesh` → `_merged_placements`), most of the remaining time. Sharing the children instead would need clones with nested placements; not investigated.

## The temporary simulation's edit guard has gaps

- **Status:** open
- **Reported:** 2026-11-05, review of the host's edit paths before sharing meshes with the temporary simulation
- **Checked:** The simulation's clones share the document's meshes, so any change there changes the model. The workspace's `ReadOnlyHistory` (`newton/session.py`) refuses every command before it runs, `SimulationScene` (`newton/model.py`) never opens a group, and the session replaces `viewport.begin_group_edit` while it runs. The Edit menu commands and the Delete key go through `history.execute`; a test runs them in the simulation. After the simulation, `changed_meshes` compares each mesh's mutation serial and element counts with the start and reports a difference.
- **Gaps:**
  - Code that changes a mesh without `history.execute` is not stopped: another extension, a script run in the host, or code that replaces `history.execute` on the instance (Newton's own eraser does this, but the eraser is not available in the simulation).
  - Browser (`views/outliner.py`) and Tray (`views/tray.py`) actions were not checked one by one; both call `history.execute` (18 and 16 times) and a search found no direct mesh changes.
  - The check after the simulation misses changes that keep the serial and the counts: reversed faces (`FlipFacesCommand` reverses the loops in place) and face attributes (`f.attrs`, colour, material, texture).
  - Simplify Mesh in the simulation, with loose faces present, raises an `IndexError` in the host: `_on_simplify_mesh` reads `history.undo_stack[-1]` after a refused command. Nothing is changed.

## Cable tests fail after `test_newton.py` in the same process

- **Status:** open
- **Reported:** 2026-11-05, focused test run
- **Symptom:** `pytest tests/test_newton.py tests/test_flexible.py` fails 7 tests in `test_flexible.py` (every test that loads a rope or cable) with `mj_initPlugin: plugin->init failed for plugin id 0` / `Invalid parameter specification in cable plugin`. Each test passes alone and the canonical full suite passes, where `test_flexible.py` runs first.
- **Checked:** Also happens without the shared-mesh change (same 7 failures on the previous commit). Likely state left by a `test_newton.py` test in the process (MuJoCo plugin registry or worker module state).
- **Unverified:** which `test_newton.py` test causes it, and whether the same can happen in a long IngeTrazo session that simulates a cable after other models.

## Every simulation frame rebuilds the viewport caches

- **Status:** open
- **Reported:** 2026-11-05, performance audit
- **Symptom:** On models with many moving bodies the display reaches only about 30 frames per second, although the worker is faster.
- **Checked:** `Session.apply()` raises `scene.version` on each frame so that the host redraws the moved groups. The host then rebuilds its consolidated buffers (`_sync_edges`): 31 ms per frame for the crank drive with 121 bodies, 17 ms for the CR10 model, against 0.2 ms for an unchanged frame. The host's own groups preview moves all groups by one shared offset only and is not part of Extension API 2, so a fix needs a host extension point.

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
