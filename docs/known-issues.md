# Known issues

Bugs and observations that are known but not yet fixed. Each entry states what is confirmed and what is still unverified. Remove an entry when its fix is merged; mention the fix in the commit message and the changelog.

Status values: **open** (confirmed, not fixed), **observation** (reported, cause unknown).

## Extension-side performance bottlenecks (6 November 2026 review)

- **Status:** open (partly fixed; the fixed parts are in the changelog); trigger-dependent synthetic measurements and code-path risks, not a full-application FPS diagnosis.
- **Evidence:** [review, scripts and measurement archive](performance-review-2026-11-06/README.md). The archive separates original reported values from fresh verification logs.
- **Still open, measured:** the remaining collider drawing cost (F2: matrices, point lists and individual draw calls per paint). Contact solving in large clusters is a separate backlog item (`docs/backlog.md`).
- **Still open, code-path risks with unmeasured incidence:** preview invalidation from the global scene version and synchronous GUI preparation (F3); GUI-thread `waitForFinished(1000)` during process teardown (F4); metrics that omit serialization or actual paint phases (F7). Selection-triggered full control-panel rebuilding is an additional unmeasured hotspot, not a demonstrated per-frame rebuild.
- **Unverified:** representative-scene impact, real process shutdown latency and live input latency.

## Two tests fail on IngeTrazo 0.6.1: the host adds a scene after a refused command

- **Status:** open (host bug, [ingelibre/ingetrazo#1241](https://github.com/ingelibre/ingetrazo/pull/1241) commented 2026-11-09)
- **What:** `test_properties_actions_are_refused_during_the_simulation` and `test_direct_view_settings_during_the_simulation_stay_in_the_workspace` fail with `IndexError` in the host's `ScenesPanel._on_add` (`views/tray.py:4535`, `scene.saved_views[-1]`): Newton refuses *Add scene* during a simulation, and the host then reads the scene that was never added. They pass on 0.6.0. The tests stay unchanged on purpose, so they show when the host is fixed or changes.
- **Also failing:** `test_sidebar_rows_keep_their_height_at_every_width[260]` (8 px of horizontal scroll). It fails on 0.6.0 as well, cause not examined.

## Test settings persist between runs

- **Status:** open
- **What:** `.test-state/` QSettings are never reset, so a key left behind by one test or run reaches the next. A detach test in `tests/test_controls_dock.py` that fails between detaching and attaching leaves `newton/controls_detached=true`; four later tests then fail (`test_toolbar_action_shows_and_hides_the_control_panel`, `test_open_control_shows_the_dock_and_expands_the_row`, `test_the_float_button_moves_the_panel_into_a_window_of_its_own_and_back`, `test_a_detached_panel_stays_detached_when_it_is_reopened`).
- **Possible fix:** remove `controls.DETACHED_KEY` (or the whole `newton/` group) in the `panel` fixture before `MainWindow()`.

## Document marked modified after a simulation

- **Status:** observation
- **Reported:** 2026-11-05, Windows installation test (GUI phase), IngeTrazo 0.6.0 on Windows 11
- **Symptom:** After opening `models/domino-30-with-pendulum.igz`, Start and Reset, the title shows `*` and closing asks whether to save, although nothing was edited. The screenshot taken while the simulation ran already shows the marker.
- **Unverified:** whether opening alone sets it (for example the history hook that creates missing axis or connection objects) or the simulation workspace does.
- **Next step:** open the model in a test window, read the modified state before and after Start/Reset.

## Simulation override rows are squashed at narrow widths with the Key bindings section visible

- **Status:** observation
- **Reported:** 2026-11-05, while adding the sidebar section *Key bindings*
- **Symptom:** In `test_sidebar_rows_keep_their_height_at_every_width`, the rows of *Simulation overrides* lose their height at narrow sidebar widths once the *Key bindings* section is visible for the selected body. The test window was raised from 1100 to 2500 px, which makes it pass.
- **Checked:** Only that the taller window removes the symptom.
- **Unverified:** The cause. It may be a real height-for-width problem of the sidebar (see AGENTS.md, "Icons, pictograms and layout") or an artefact of the test window being too small for the added section; this was not distinguished. Check in the live sidebar before relying on the larger window.

## The temporary simulation's edit guard has gaps

- **Status:** open (narrowed on 6 November 2026)
- **Reported:** 2026-11-05, review of the host's edit paths before sharing meshes with the temporary simulation
- **Checked:** The simulation's clones share the document's meshes, so any change there changes the model. The workspace's `ReadOnlyHistory` (`newton/session.py`) refuses every command before it runs, `SimulationScene` (`newton/model.py`) never opens a group, and the session replaces `viewport.begin_group_edit` while it runs. Clones have their own nested group objects (`nested_clone`), which still share the meshes. After the simulation, `changed_meshes` compares each mesh's mutation serial, element counts, the first two vertices of every outer and hole loop, and a hash of all face attributes, and reports a difference.
- **Audited 2026-11-06:** every Browser (`views/outliner.py`) and Tray (`views/tray.py`) action in the pinned host: they go through `history.execute` and are refused, are stopped by another guard, or change only the workspace's own copies (layers, scenes, section display, BIM tags). Two Tray actions and Edit ▸ Copy changed the document's nested groups directly (Parts explode preview, *Place a Copy*, `copy_group`); they no longer reach the document since clones have their own nested groups. Tests cover each action family.
- **Remaining gaps:**
  - Code that changes a mesh without `history.execute` (another extension, a host script) is not stopped; changes to geometry, winding and face attributes are only reported after the simulation. Not detected: reordering a loop that keeps its first two vertices, the face `interior` flag, and changes inside attribute values that neither `marshal`, `pickle` nor `repr` reflect.
  - Simplify Mesh in the simulation, with loose faces present, raises an `IndexError` in the host after the refused command. Nothing is changed.
  - `PlaceGroupTool` becomes active in the simulation despite the tool filter (library insert, *Place a Copy*); its click is refused.
- **Cost:** the fingerprint adds about 65 ms at Start and per check at Reset (run twice) on a model with 250,000 vertices and 248,000 faces.
- Host proposals: "Read-only document or workspace", "Frozen meshes", "A mesh revision that covers every change", "Copying a group changes its source", "Parts explode preview changes the model outside history", "Placing a group bypasses the workspace tool filter", "Callers carry on after a refused command".

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

## Axis and connection objects: known gaps

- **Status:** open
- **Reported:** 2026-11-04, with the introduction of axis objects (`newton/axis_objects.py`)
- **Symptom:** While a group is open for editing, only name and visibility of axis and connection objects are synced; moves of bodies or objects inside the open group may not be mirrored until after leaving it.
- **Unverified:** whether moves inside an open group still lag; not rechecked after the hide/rename fix.
- **Checked:** unit tests cover move, rotate, undo/redo, body move, copy/paste, delete and loading documents without axis objects. Not checked in a live IngeTrazo session yet.
