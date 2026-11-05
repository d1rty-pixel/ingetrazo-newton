# Known issues

Bugs and observations that are known but not yet fixed. Each entry states what is confirmed and what is still unverified. Remove an entry when its fix is merged; mention the fix in the commit message.

Status values: **open** (confirmed, not fixed), **observation** (reported, cause unknown), **fixed** (kept until the fix is released).

## Simulation override rows are squashed at narrow widths with the Key bindings section visible

- **Status:** observation
- **Reported:** 2026-11-05, while adding the sidebar section *Key bindings*
- **Symptom:** In `test_sidebar_rows_keep_their_height_at_every_width`, the rows of *Simulation overrides* lose their height at narrow sidebar widths once the *Key bindings* section is visible for the selected body. The test window was raised from 1100 to 2500 px, which makes it pass.
- **Checked:** Only that the taller window removes the symptom.
- **Unverified:** The cause. It may be a real height-for-width problem of the sidebar (see AGENTS.md, "Icons, pictograms and layout") or an artefact of the test window being too small for the added section; this was not distinguished. Check in the live sidebar before relying on the larger window.

## Starting a large model copies all geometry

- **Status:** fixed
- **Reported:** 2026-11-05, CR10 sliding electronics compartment model (about 250 000 vertices)
- **Symptom:** Pressing Start takes about 10 s before the simulation runs; the simulation itself is fast.
- **Checked:** `prepare()` (`newton/model.py`) copied every included group for the temporary simulation with `transformed_mesh`, which welds the whole mesh again; groups with children were welded into one mesh first. The clones now share the document's mesh and nested placements, and all points are read without a copy; on this model `prepare()` dropped from 11.3 s to 0.84 s (see `docs/lab/test-and-measurement-runs.md`).
- **Unverified:** the display cost per frame: a clone with children now draws as its nested placements (up to 141 on this model) instead of one merged mesh. Live runs in the Flatpak (see `docs/lab/test-and-measurement-runs.md`) were too noisy to decide it: 22 and 17 frames per second shared against 28 and 2 merged, with the IngeTrazo window in the background. A repeatable benchmark with the window in front is still needed.

## The temporary simulation's edit guard has gaps

- **Status:** open
- **Reported:** 2026-11-05, review of the host's edit paths before sharing meshes with the temporary simulation
- **Checked:** The simulation's clones share the document's meshes, so any change there changes the model. The workspace's `ReadOnlyHistory` (`newton/session.py`) refuses every command before it runs, `SimulationScene` (`newton/model.py`) never opens a group, and the session replaces `viewport.begin_group_edit` while it runs. The Edit menu commands and the Delete key go through `history.execute`; a test runs them in the simulation. After the simulation, `changed_meshes` compares each mesh's mutation serial and element counts with the start and reports a difference.
- **Gaps:**
  - Code that changes a mesh without `history.execute` is not stopped: another extension, a script run in the host, or code that replaces `history.execute` on the instance (Newton's own eraser does this, but the eraser is not available in the simulation).
  - Browser (`views/outliner.py`) and Tray (`views/tray.py`) actions were not checked one by one; both call `history.execute` (18 and 16 times) and a search found no direct mesh changes.
  - The check after the simulation misses changes that keep the serial and the counts: reversed faces (`FlipFacesCommand` reverses the loops in place) and face attributes (`f.attrs`, colour, material, texture).
  - Simplify Mesh in the simulation, with loose faces present, raises an `IndexError` in the host: `_on_simplify_mesh` reads `history.undo_stack[-1]` after a refused command. Nothing is changed.

## Every simulation frame rebuilds the viewport caches

- **Status:** open
- **Reported:** 2026-11-05, performance audit
- **Symptom:** On models with many moving bodies the display reaches only about 30 frames per second, although the worker is faster.
- **Checked:** `Session.apply()` raises `scene.version` on each frame so that the host redraws the moved groups. The host then rebuilds its consolidated buffers (`_sync_edges`): 31 ms per frame for the crank drive with 121 bodies, 17 ms for the CR10 model, against 0.2 ms for an unchanged frame. The host's own groups preview moves all groups by one shared offset only and is not part of Extension API 2, so a fix needs a host extension point.
- Host proposal: docs/host-proposals.md, Display transforms without changing the scene.

## Floating toolbar icons jump while a simulation runs

- **Status:** observation
- **Reported:** 2026-11-04, Linux (Ubuntu, GNOME on Wayland), IngeTrazo 0.6.0 Flatpak
- **Symptom:** With the Newton toolbar detached (floating) and a simulation running, the toolbar icons jump rapidly up and down.
- **Checked:** In an offscreen Qt run (QT_QPA_PLATFORM=offscreen), the toolbar was floated and a demo body simulated for 3 s. No Newton toolbar action emitted `changed` (no `setIcon`/`setEnabled` calls), and the toolbar requested one layout. The panel's per-refresh `setIcon` call (`newton/panel.py`, `refresh_widgets`) is therefore not confirmed as the cause.
- **Unverified:** whether it also happens on Windows, with a docked toolbar, with other (native) floating toolbars, while paused, or without other toolbar extensions (`igz_toolbars`, `organize_toolbar`) installed. The offscreen platform does not reproduce real window-manager behaviour.
- **Next step:** reproduce on a real display; compare a native IngeTrazo toolbar floated in the same way to separate a host/Qt-Wayland issue from a Newton issue.

## Worker inherited the host's `PYTHONPATH` (Flatpak)

- **Status:** fixed (unreleased)
- **Symptom:** Start failed with "Importing the numpy C-extensions failed … `_multiarray_umath.cpython-313-x86_64-linux-gnu.so`".
- **Cause:** The Flatpak launcher exports `PYTHONPATH=/app/lib/python3.13/site-packages`. The worker process inherited it, so the external Python 3.12 loaded IngeTrazo's numpy built for Python 3.13.
- **Fix:** The worker is started with `python -E` (`newton/session.py`, `newton/collision_view.py`), which ignores all `PYTHON*` environment variables.

## Axis and connection objects: known gaps

- **Status:** open
- **Reported:** 2026-11-04, with the introduction of axis objects (`newton/axis_objects.py`)
- **Symptom:** While a group is open for editing, no sync runs; axis and connection objects catch up with the next command after leaving the group (hiding or renaming a body in that time is not mirrored until then). Grouping an axis or connection object together with other objects (Make Group) removes it from the top level; Newton then creates a new one and keeps the axis.
- **Checked:** unit tests cover move, rotate, undo/redo, body move, copy/paste, delete and loading documents without axis objects. Not checked in a live IngeTrazo session yet.
