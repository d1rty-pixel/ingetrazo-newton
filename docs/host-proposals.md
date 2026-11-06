# Host proposals

Ideas for IngeTrazo itself, found while working on Newton: fixes, extension points and improvements that would make Newton (or other extensions, or the host) safer, faster or simpler. IngeTrazo is open source (<https://github.com/ingelibre/ingetrazo>), so these can be proposed upstream.

Newton is always developed against the pinned host version (see [AGENTS.md](../AGENTS.md)). An entry here never blocks, postpones or reshapes Newton work; the Newton-side solution is built anyway. When a proposal lands in a host version that Newton pins, replace the Newton workaround and remove the entry.

File references are to the host commit pinned in [AGENTS.md](../AGENTS.md) ("Development setup") when the entry was written or last updated (2026-11-05: `e61132a`, v0.6.0).

Status values: **idea** (noted, not proposed), **proposed** (issue or pull request upstream, link it), **accepted** (merged upstream, not yet pinned), **rejected** (upstream declined; keep the reason).

Each entry states: what was found in the host, the proposal, what Newton could remove or improve, and what else would benefit.

## Display transforms without changing the scene

- **Status:** proposed ([#1231](https://github.com/ingelibre/ingetrazo/issues/1231), 2026-11-06)
- **Found:** 2026-11-05, start-time audit and guarding the temporary simulation
- **Host today:** an extension can only move groups by changing `group.xform` and raising `scene.version`; the host then rebuilds its consolidated buffers (`_sync_edges` in `views/viewport.py`, 17–31 ms per frame). The host's groups preview moves all groups by one shared offset only.
- **Measured:** Newton's `Session.apply()` raises `scene.version` on every frame. The rebuild costs 31 ms per frame for the crank drive (121 bodies) and 17 ms for the CR10 model, against 0.2 ms for an unchanged frame; the display reaches only about 30 frames per second.
- **Proposal:** `viewport.set_display_transforms({group: matrix})` (or similar), drawn without touching the scene, `scene.version` or the buffers; cleared with `None`.
- **Newton:** could simulate on the document itself: no clone scene in `prepare()`, no shared meshes and their frame offsets (`SimulationScene.place`), and no per-frame `scene.version` bump in `Session.apply()`, which removes the buffer rebuild from every frame. Fixes "Every simulation frame rebuilds the viewport caches" in [known-issues.md](known-issues.md).
- **Others:** any animation, kinematics or exploded-view extension.

## Read-only document or workspace

- **Status:** proposed ([#1232](https://github.com/ingelibre/ingetrazo/issues/1232), 2026-11-06)
- **Found:** 2026-11-05, guarding the temporary simulation
- **Host today:** `allowed_tools` only filters tools (`views/main_window.py`, `set_tool_filter`); Edit menu commands, Delete and opening a group still work in a workspace. `History.execute` (`core/history.py`) rolls back only the active mesh.
- **Proposal:** `workspace.read_only = True` and/or `app.lock_document(reason)`: History refuses centrally, edit actions are disabled, opening a group is refused with the reason, saving is blocked.
- **Newton:** removes `ReadOnlyHistory`, `SimulationScene`, the `viewport.begin_group_edit` replacement in `session.py` and the Delete handling in `DragTool`.
- **Others:** viewer or preview workspaces (CAM, analysis).

## Command hooks in History

- **Status:** proposed ([#1233](https://github.com/ingelibre/ingetrazo/issues/1233), 2026-11-06)
- **Found:** 2026-11-05
- **Host today:** extensions that react to commands replace `history.execute` on the instance.
- **Proposal:** official before/after-command listeners on `History`.
- **Newton:** removes the replacement in `axis_objects.install` and the temporary one in `eraser.on_release`.
- **Others:** any extension that keeps derived objects in sync.

## Workspace tool substitution

- **Status:** idea
- **Found:** 2026-11-05
- **Host today:** a workspace can restrict tools but not replace one.
- **Proposal:** e.g. `workspace.tools = {"select": tool}`.
- **Newton:** removes the `viewport.set_active_tool` patch in `session.install_drag`.

## A mesh revision that covers every change

- **Status:** proposed ([#1234](https://github.com/ingelibre/ingetrazo/issues/1234), 2026-11-06)
- **Found:** 2026-11-05
- **Host today:** `Mesh._mut_serial` (`core/mesh.py`) is private and not raised by in-place winding flips (`FlipFacesCommand`) or face attribute changes.
- **Proposal:** a public revision raised by every change, or a separate attribute revision.
- **Newton:** `changed_meshes` (`session.py`) would also catch reversed faces and paint changes.
- **Others:** host caches currently combine `_mut_serial` with `_attrs_dirty`.

## Frozen meshes

- **Status:** idea
- **Found:** 2026-11-05
- **Host today:** nothing stops a script or extension from changing a mesh another document shows.
- **Proposal:** `Mesh.freeze()` / `thaw()`; every mutation primitive already raises `_mut_serial`, so one central check would do.
- **Newton:** enforcement for shared meshes, also against code outside the history.

## Renderer dirty flags per cache entry

- **Status:** idea
- **Found:** 2026-11-05
- **Host today:** the renderer clears `mesh._chunk_dirty` and `mesh._attrs_dirty` on the mesh (`views/viewport.py`, chunk validation around line 12196–12267).
- **Proposal:** keep them per cache entry, so a mesh drawn in two documents stays correct in both.
- **Newton:** could drop `pending_redraws` in `session.py`, which saves the flags of the document's meshes at Start and sets them again at Reset.

## Simplify Mesh after a refused command

- **Status:** proposed, [ingelibre/ingetrazo#1241](https://github.com/ingelibre/ingetrazo/pull/1241)
- **Found:** 2026-11-05
- **Host today:** `_on_simplify_mesh` (`views/main_window.py`) reads `history.undo_stack[-1]` after `execute`; when the command was refused (`last_rejected`) the stack can be empty and it raises `IndexError`.
- **Proposal:** check `last_rejected` and show it, as `tools/move.py` does.

## Opening a refused group reports "Editing"

- **Status:** proposed, as a comment on [ingelibre/ingetrazo#1232](https://github.com/ingelibre/ingetrazo/issues/1232#issuecomment-6689339377) (read-only workspace)
- **Found:** 2026-11-05
- **Host today:** `Viewport.begin_group_edit` (`views/viewport.py`) flashes "Editing …" even when the scene did not open the group.
- **Proposal:** flash only when `scene.edit_group` changed, or let the scene return whether it opened.
- **Newton:** removes the message-only replacement of `viewport.begin_group_edit`.

## Rigid transforms without re-welding

- **Status:** idea
- **Found:** 2026-11-05, start-time audit
- **Host today:** `transformed_mesh` (`core/group.py`) builds and welds the whole mesh again.
- **Proposal:** a fast path for rigid transforms that keeps the topology and only maps positions.
- **Newton:** faster `prepare()` where copies remain (groups with children or component transforms).
- **Others:** import, explode, paste.

## Preferences pages for extensions

- **Status:** proposed ([#1235](https://github.com/ingelibre/ingetrazo/issues/1235), 2026-11-06)
- **Found:** before 2026-11-05 (AGENTS.md, "Architecture")
- **Host today:** Extension API 2 has no hook to add a preferences page.
- **Proposal:** a registration call, e.g. `app.add_preferences_page(title, factory)`, with accept/validate callbacks.
- **Newton:** removes `install_preferences` (`newton/preferences.py`), which replaces the host's `views.preferences_dialog.PreferencesDialog` class with a subclass.
- **Others:** every extension with settings.

## Clean environment for external processes (Flatpak)

- **Status:** idea
- **Found:** 2026-11-04 ([known-issues.md](known-issues.md), "Worker inherited the host's `PYTHONPATH` (Flatpak)")
- **Host today:** the Flatpak launcher exports `PYTHONPATH=/app/lib/python3.13/site-packages` (and the bundle sets `LD_LIBRARY_PATH`); every process an extension starts inherits them.
- **Proposal:** set these only for the host's own interpreter, or offer a helper that returns a clean environment for external processes.
- **Newton:** removes `python -E` as a workaround need and `clean_env`/`worker_environment` (`newton/runtime_setup.py`, `newton/session.py`).
- **Others:** any extension that starts an external Python or tool.

## Report refused commands to the Python console and the MCP bridge

- **Status:** proposed, [ingelibre/ingetrazo#1242](https://github.com/ingelibre/ingetrazo/pull/1242)
- **Found:** 2026-11-05, testing virtual controls through the MCP bridge during a simulation
- **Host today:** `run_transactional` (`core/ai.py`, line 420) runs the code inside one `SnapshotImport` through `history.execute` and reads only `history.last_error`. When a history refuses the command before it runs (`last_rejected`), the code never runs, stdout stays empty and the result says `changed: True`; `scripts/ingetrazo_mcp.py` then prints only "(changed: True)".
- **Proposal:** check `history.last_rejected` after `execute`; return it as an error (or a separate `rejected` field) with `changed: False`, and let the MCP bridge print it.
- **Newton:** the simulation's `ReadOnlyHistory` (`newton/session.py`) refuses every command on purpose, so a script or AI tool cannot change the model during a simulation. With this, the caller learns why nothing happened instead of seeing a silent success.
- **Others:** any workspace or extension that refuses commands, and every user of the Python console.

## Press and release for shortcut actions

- **Status:** idea
- **Found:** 2026-11-05, designing key bindings for Newton's controls
- **Host today:** keyboard shortcuts are `QAction` shortcuts, managed by the shortcut page (`views/shortcuts.py`: stored per action under `shortcuts/<key>`, clashes resolved by `assign`, reapplied after `load_extensions` in `views/main_window.py`, line 2986). A `QAction` reports only `triggered` on the press (repeated while the key is held); nothing reports the release. Tools get raw key events only through the viewport (`views/viewport.py`, around line 18126).
- **Proposal:** let an action opt in to hold semantics, for example a host signal `pressed(action)` / `released(action)` for actions with a flag such as `action.setProperty("ingetrazo_hold", True)`, fired once per press (no auto-repeat) and once on release, also when the window loses focus while the key is held.
- **Newton:** enables the trigger mode *momentary* (a control holds its key value while the key is down) without an application-wide key event filter beside the host's shortcut handling ([backlog.md](backlog.md), "Virtual controls and key bindings", item *momentary*).
- **Others:** any extension or tool with hold-to-act keys (temporary views, push-to-talk style modifiers, jog controls).

## Shortcut page that follows added and removed actions

- **Status:** proposed, [ingelibre/ingetrazo#1244](https://github.com/ingelibre/ingetrazo/pull/1244)
- **Found:** 2026-11-05, Newton key slots
- **Host today:** `ShortcutsPanel` (`views/shortcuts.py`, line 387) collects the window's actions once, when the preferences dialog is built, and `assign` checks clashes only against that list. An action an extension adds or removes while the dialog is open is missing from the list and from the clash check, so two actions can end up on one key (Qt then fires neither).
- **Proposal:** a public `ShortcutsPanel.reload()`, or let the page re-collect the actions whenever it is shown and before every `assign`.
- **Newton:** removes `refresh_shortcut_page` (`newton/preferences.py`), which writes `PreferencesDialog._shortcuts._actions` and calls `_fill()`.
- **Others:** any extension whose commands change at runtime.

## A bottom panel area for extensions

- **Status:** idea
- **Found:** 2026-11-06, Newton's control panel as a dock below the 3D view
- **Host today:** `ExtensionApp.add_panel` (`views/extension_api.py`, line 167) puts a widget only into the side tray, as a tab beside Properties. An extension that needs a wide, short panel (a strip per control) has no API for it. The window layout (`restore_late_toolbars`, `views/main_window.py`, line 2994) restores the saved state by object name when an extension asks for it, and that `restoreState` also restores the corner ownership saved with the layout, so a layout saved before the panel existed brings the default corners back.
- **Proposal:** `add_panel(..., area="bottom")` (or `add_bottom_panel`) that creates the `QDockWidget` in `Qt.BottomDockWidgetArea` with a stable object name, lists it in *Window ▸ Panels*, keeps the side tray at full window height (`setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)`, re-applied after every `restoreState`) and restores it with the window layout.
- **Newton:** removes the dock created in `Controls.make_dock` through the `QMainWindow` API, the `setCorner` call there and its repetition in `Controls.refresh` and after `restore_toolbar_layout` in `newton/toolbar.py`, and the own show/hide toggle for the dock.
- **Others:** any extension with a timeline, console, log or table that needs width more than height.

## Copying a group changes its source

- **Status:** idea
- **Found:** 2026-11-06, audit of Browser and Tray actions during a simulation
- **Host today:** `copy_group` (`core/group.py:677–683`) gives the source's plain nested groups an identity matrix and sets `component = False` on them, outside any command. *Place a Copy* in the Components panel (`views/tray.py:1490` → `kept_components.make_template`) reaches it, and so probably does Edit ▸ Copy.
- **Proposal:** leave the source untouched and convert only the copy, or do the conversion inside an undoable command.
- **Newton:** in a simulation the clones' nested groups were the document's own groups, so *Place a Copy* changed the document without undo; Newton now gives clones their own child groups.
- **Others:** any caller of `copy_group` that expects its input unchanged.

## Parts explode preview changes the model outside history

- **Status:** idea
- **Found:** 2026-11-06, audit of Browser and Tray actions during a simulation
- **Host today:** dragging the Parts explode slider (`views/tray.py:1964–1992` → `core/explode.py:87–97`, `apply_explode`) sets `xform` and `explode_offset` on the parts directly; release restores them (`explode.restore`) and only the final step goes through `history.execute`.
- **Proposal:** draw the preview as a display-only offset (see "Display transforms without changing the scene"), or skip the preview when the history refuses commands.
- **Newton:** with its own child groups per clone the preview no longer reaches the document; a read-only workspace would make that independent of how Newton clones.

## Placing a group bypasses the workspace tool filter

- **Status:** proposed, [ingelibre/ingetrazo#1243](https://github.com/ingelibre/ingetrazo/pull/1243)
- **Found:** 2026-11-06, audit of Browser and Tray actions during a simulation
- **Host today:** `MainWindow._start_place` (`views/main_window.py:7388`) activates `PlaceGroupTool` without the workspace's `_tool_filter`, which `_activate_tool` (`:3586`) enforces. Library insert and *Place a Copy* use it; in Newton's simulation the click's `InsertGroupCommand` is then refused.
- **Proposal:** route `_start_place` through the same filter.
- **Others:** every workspace that restricts tools.

## Callers carry on after a refused command

- **Status:** proposed, [ingelibre/ingetrazo#1241](https://github.com/ingelibre/ingetrazo/pull/1241)
- **Found:** 2026-11-06, audit of Browser and Tray actions during a simulation
- **Host today:** `History.execute` (`core/history.py:239`) returns `None`, so callers cannot tell a refusal from success. `MaterialsPanel._restamp` (`views/tray.py:2648–2670`) updates the paint tool and reports "Material … updated" after a refusal; `_place_view` with `open_sheet` (`views/outliner.py:3720`) would raise `ValueError`. "Simplify Mesh after a refused command" above has the same cause.
- **Proposal:** let `execute` return whether the command ran, or have these callers check `history.last_rejected`.
- **Others:** any workspace or extension that refuses commands.
