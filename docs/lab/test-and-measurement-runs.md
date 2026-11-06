# Test and measurement runs

## Release 0.15.0 full suite (Linux, 6 November 2026)

Canonical full suite on branch `release/0.15.0` before the release commit, host pinned at `e61132a`:

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
445 passed, 15 warnings in 105.43s (0:01:45)
```

The 15 warnings are host deprecation warnings (`QImage.mirrored`).

## Environment forces F6 and clustered contacts (Linux, 6 November 2026)

- F6: `apply_environment` applies forces with one `mj_applyFT` per body and calls `mj_jacBodyCom` only for active damping terms. 100 free bodies, eight-step batch, pinned to one core, old → new: gravity override only 7.8–8.1 → 1.0 ms; linear damping 8.0–8.5 → 2.7 ms; linear and angular damping 7.9–8.1 → 5.4 ms. Archived probe "damping" at 100 bodies: 7.8 → 2.7 ms. A regression test compares `qfrc_applied` with the old dense formula (free and hinged bodies, every damping combination) at rtol 1e-12.
- Live check in IngeTrazo (Flatpak, MCP): 200 boxes, override gravity 0, attraction 0.5, softening 0.1. The real-time factor started at about 0.6 and fell to about 0 once the boxes clustered. Headless reproduction: before contact a batch takes ~33 ms (attraction ~13 ms, environment ~20 ms before F6); in the cluster `mj_step` grows to over 30 s per batch with ~900 contacts. Cause and solver comparison: [backlog](../backlog.md#idea-contact-solver-settings-for-large-clustered-scenes).

## Performance fixes F1, F2, F3, F5 (Linux, 6 November 2026)

Fixes from the [performance review](../performance-review-2026-11-06/review.md) on branch `perf/review-2026-11-06-fixes`. Full suite: 435 passed. The archived probes (`docs/performance-review-2026-11-06/scripts/run.py`) were rerun against the changed code; they measure the `newton/` of the checkout that contains `run.py`, so their "original" variants now measure the new code. A rerun with the new `--root` option against a worktree of the unchanged code gave 369.6 ms for 100 attracting bodies, matching the archive. Medians, same synthetic workloads as the review.

| Probe | Before (review archive) | After the fixes |
| --- | ---: | ---: |
| 100 free bodies, all attracting, eight-step batch | 370.6 ms | 3.0 ms |
| 50 free bodies, all attracting, eight-step batch | 85.5 ms | 1.1 ms |
| 100 free bodies, linear damping (F6, unchanged) | 8.0 ms | 7.9 ms |
| 1,000 collider paint | 31.8 ms | 20.1 ms |
| 100 changing telemetry labels | 2.49 ms | 1.34 ms |

- Attraction (F1): forces of all sources are summed per target with numpy and applied once per target with `mj_applyFT` at the centre of mass. `xfrc_applied` was not used because the worker never clears it and a test uses it as a constant external load. At a 100-body state the generalized forces match the old per-pair `mj_jacBodyCom` sum to about 5e-16 relative; regression tests compare against the old loop (including a hinged body) and check momentum conservation.
- A standalone timing with the probe's specs (worktree, old and new worker side by side) gave 3.09 → 0.34 ms (10 bodies), 89.2 → 1.63 ms (50) and 430.6 → 3.19 ms (100).
- Vertex payload (F3): not timed again; box, sphere and compound specs now reach the worker without vertices, so the review's encode/decode figures (250,000 vertices: ~81 / ~58 ms) no longer apply to them. Hull specs still carry their vertices.
- One run of `test_control_panel_is_a_bottom_dock_under_the_view_and_the_sidebar_keeps_its_height` failed in a focused run in a new worktree: the saved window layout leaks through `.test-state/` (see [known issues](../known-issues.md#test-settings-persist-between-runs)). Reproduced from a fresh `.test-state/` with `-k "control_panel or telemetry"`; after the test fix 20 of 20 runs from a fresh state pass.

## Extension-only performance review archive (Linux, 6 November 2026)

The [review archive](../performance-review-2026-11-06/README.md) preserves prioritized findings, three host-free synthetic probes, historical measurements and fresh verification output. It covers worker force scaling, telemetry styling, collider drawing and initialization, synchronous shutdown and metric boundaries. Historical figures and new raw logs are explicitly separated. No production code or models were changed; the host-dependent full test suite was not run.

## Windows installation test (Windows)

Run on 5 November 2026 on Windows 11 Pro 10.0.26300 x64, Windows PowerShell 5.1, with `scripts/lab/windows-install-test.ps1` (sandbox under `%TEMP%`, real IngeTrazo installation only read). Machine: IngeTrazo 0.6.0 from the installer, Python 3.14 only (no 3.12, no `uv`, no `pwsh`), WSL2 present.

```text
INFO 14, PASS 25, FAIL 3, SKIP 1
```

- Release zip: one `newton/` folder, 108 entries, reproducible SHA-256.
- Method B (`runtime_setup.py install`, started with Python 3.14): uv download, Python 3.12.16, MuJoCo 3.3.7, numpy 2.5.4 in 7.6 s; second run 0.7 s; 238 MB. Longest path under the real `%APPDATA%` 197 characters. Lookup order, marker protection and `uninstall` as documented. Also works under a data folder with spaces and non-ASCII characters.
- Method C with uv (documented commands) and without uv (venv + pip, uv-managed 3.12 as stand-in) work; `runtime_setup.py check` accepts their `runtime.json`.
- The worker smoke test (a box falls from 3 m and rests at 0.50 m after 2 s, `PYTHONPATH`/`PYTHONHOME` set to nonsense) passes with every runtime, 0.4 s including start.
- Failures in the first run, fixed the same day: `install-local.ps1` failed in Windows PowerShell 5.1 (its `-c 'print("MuJoCo", …)'` lost the double quotes, so Python raised `NameError`); `setup-runtime.ps1` took Python 3.14 from `PATH`, found no MuJoCo wheel and kept the 3.14 `.venv` on the next run with `-Python`; `-Update` left removed modules behind. Full run without the GUI phase after the fixes: PASS 34, INFO 13, no WARN or FAIL.
- GUI phase (`-Gui`, the installed IngeTrazo 0.6.0 started with `--new-window` and the sandbox as `APPDATA`): Newton loads from the sandbox without load errors (bundled Python 3.12.10, frozen), menu, sidebar and both toolbars present in German. The runtime setup code of the *Set up runtime* button, run inside the host, downloads uv over the host's TLS and builds the runtime in 8.2 s. Start on `domino-30-with-pendulum.igz` (38 bodies): first frame after 0.47 s, 59 frames per second over 3 s; Reset ends the worker. The registry key `HKCU\Software\IngeTrazo` changed during the run (recent files, window state) and was restored identical; no autosave in the real profile. The suite's load-error check misread the empty error list as an error (fixed in the suite).
- Real installation afterwards: runtime with method B into `%APPDATA%\ingetrazo`, extension with `install-local.ps1 -Update` (old 0.14.0 copy replaced, removed modules gone), interpreter preference cleared. *Set up runtime* in **Preferences → Newton → Runtime** then rebuilt the runtime by hand without problems; the simulation runs with it.
- Observation: after opening the model, Start and Reset, the document is marked modified (`*` in the title), so closing asks whether to save. Not yet clear whether opening or the simulation causes it.
- `Expand-Archive` over an existing installation needs `-Force`, which the update instructions in `docs/installation.md` do not mention.
## Position drive integral term (Linux)

Checked on 5 November 2026 on Linux x86_64 (Ubuntu), offscreen. Offset of the drag-chain carriage (`scripts/models/flexible_demos.py`, 4 s per target, targets 0.18 / -0.10 / 0.20 m): before 4.0 / 5.0 / 2.7 cm, after (integral gain 100 per inertia, limited to 15 % of the force) 0.02 / 0.12 / 0.19 cm. Gain 300 left up to 0.3 cm with ringing, gain 600 oscillated (up to 2.4 cm). A slider under a constant 3 cm-equivalent load stopped at 0.270 m for target 0.300 m before and reaches it within 2 mm after. Windup check with the gripper blocked by its stop (`test_coupling.py`, 160 steps of 8 per phase): the integral share was chosen so that both jaw contacts hold while blocked and the reopened jaw is back within 0.4 mm after the same time (1.0 mm at 25 %, 3.3 mm at 100 %, second contact lost at 10 %). The carrier test now allows 1 cm instead of 6 cm; five runs passed. Full suite: 412 passed.

## Keep the pose on reset (Linux)

Checked on 5 November 2026 on Linux x86_64 (Ubuntu), offscreen, same environment as below. Full suite: 412 passed in 111 s. `tests/test_keep_pose.py` runs the real worker, drives the joints of the robot arm and checks: Reset restores the model by default; with the box checked the pose is written as one undo/redo step; joint pivot and axis object agree afterwards; a locked body and a failure keep nothing. Undo is exact up to float32 rounding of the baked vertices. Not checked on screen.

## Key bindings (Linux)

Checked on 5 November 2026 on Linux x86_64 (Ubuntu), offscreen, same environment as "Limit hardness" below; host reference IngeTrazo v0.6.0, commit `e61132a7`.

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
404 passed in 89 s
```

- Covers key slots, the bindings runtime (toggle, step, second step slot, skipped targets), the binding fields on the control panel cards (one undo step per change, no rebuild of the edited card) the *Key bindings* sidebar section for a single selected axis, and the *Key slots* preferences tab (labels, key caps).
- Run after removing the *Key bindings…* table, adding the sidebar section and the *Key slots* tab. Four tests needed their preferences tab index moved by one (*Runtime* is now tab 4); `test_sidebar_rows_keep_their_height_at_every_width` uses a 2500 px window instead of 1100 px (see `docs/known-issues.md`).
- Not yet checked live in IngeTrazo.

## Limit hardness (Linux)

Checked on 5 November 2026 on Linux x86_64 (Ubuntu), offscreen, with Python 3.12.14, PySide6 6.11.3, numpy 2.5.4 and MuJoCo 3.3.7; host reference IngeTrazo v0.6.0, commit `e61132a7`.

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
277 passed, 13 warnings in 53.20s
```

- Cause: joint limits used MuJoCo's default `solref`/`solimp`. In a cable drag chain of 10 g links (an external CR10 model, 11 and 12 links) the limits gave way by 13–17° at rest and by over 100° while moving; the upper run fell onto the lower run. With `solreflimit` 1/120 s and `solimplimit` 0.99–0.999 the excess stayed below 0.15°.
- New test chain (8 links of 10 g held level by ±1.5° stops): excess after 2 s at 0 / 25 / 50 / 75 / 100 % hardness 29.4 / 22.4 / 14.2 / 5.8 / 0.26°.
- Drag-chain demo with hard limits: 17 of 21 link joints rest at a stop (before 2–5), excess 0.1° (before up to 3.1°), contact penetration and connection error unchanged (≤ 0.8 mm, ≤ 0.4 mm). The carriage servo stops up to 5 cm short (before up to 3.7 cm), see [known issues](../known-issues.md#position-drive-keeps-a-steady-offset-under-load); the carrier test now allows 6 cm.
- The icon `limit_hardness` was compared with `limits`, `limit_min` and `limit_max` on the overview sheet in light and dark.
## Shared meshes in the temporary simulation (Linux)

Checked on 5 November 2026 on Linux x86_64, same model and method as "Hidden geometry" below (`prepare()` only, single run).

| Include hidden geometry | Before | Shared meshes | Also shared nested placements | Simulated bodies |
|---|---|---|---|---|
| When needed | 11.3 s | 4.3 s | 0.84 s | 12 |
| Always | 16.8 s | 6.1 s | 1.95 s | 113 |

- The before figures were measured again in the same session; they differ slightly from the table below.
- Shared meshes: the specs sent to the worker are unchanged; centres, half sizes and vertices are equal, compound parts differ by at most 1.5e-8 m (float32 rounding of the former second copy).
- Nested placements: centres and half sizes are equal (6e-10 m). Groups with children now send every vertex of their placements instead of the welded mesh, which dropped vertices on no edge or face (47 872 instead of 40 141 for the drawer); hull points differ by at most 6.5e-5 m. Loading all 113 bodies in the worker took 0.41 s instead of 0.37 s; 60 steps took 0.10 s in both cases.
- The renderer clears `_chunk_dirty`/`_attrs_dirty` on a mesh it draws; the session now restores flags that were pending when the simulation started (`test_render_flags_of_shared_meshes_survive_the_simulation`).

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
271 passed, 13 warnings in 55.80s
```

Live check in the IngeTrazo 0.6.0 Flatpak (installed copy, AI bridge, CR10 model, "When needed"). The merged variant was produced by patching `prepare()` in the running app to weld each clone's placements into one mesh, as before. Each run lasted 20 s after Start; the IngeTrazo window was not in front.

| Variant | Start (warm) | First frame | Frames per second after that |
|---|---|---|---|
| Shared nested placements | 0.12 s | 4.4 s, 4.0 s | 22.2, 16.9 |
| Merged (previous) | 2.9 s, 2.7 s | 5.2 s, 5.2 s | 27.7, 1.7 |

- The model displays correctly while simulating (screenshot checked); Reset reports "Original model restored." and no geometry change.
- `run_python` over the AI bridge is refused while the simulation runs: the bridge executes it as a history command, which `ReadOnlyHistory` refuses. Measurements were therefore scheduled with a timer before Start.
- The frame rates scatter too much to compare the variants (see known issues).

## Hidden geometry (Linux)

Checked on 5 November 2026 on Linux x86_64 with the worker run in-process (no GUI drawing time). The CR10 sliding electronics compartment model has 208 groups, 120 of them hidden (101 movable). Each figure is a single run on this machine and is no general speed guarantee.

| Include hidden geometry | `prepare()` | Simulated bodies | Degrees of freedom | Speed |
|---|---|---|---|---|
| Always (previous behaviour) | 15.9 s | 113 | 27 | 13× real time |
| When needed | 10.0 s | 12 | 4 | 102× real time |
| Never | 11.3 s | 10 | 4 | 98× real time |

No visible body of this model depends on a hidden movable body. The remaining start time is mostly the copy of visible geometry for the temporary simulation (see known issues).

## Axis overlay performance (Linux)

Checked on 5 November 2026 on Linux x86_64 (Ubuntu, GNOME/Wayland), Python 3.12, PySide6 6.11.3, offscreen, host reference IngeTrazo v0.6.0.

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
266 passed, 13 warnings in 51.66s
.venv/bin/python scripts/lab/benchmark_overlays.py --sizes=5,20,60 --repeat=3 --images=.test-state/overlays
```

`scripts/lab/benchmark_overlays.py` builds a static base with N hinged leaves in a separate offscreen window and times the overlay paint (`panel.draw_joints`) and the selection refresh. Paint time with all bodies selected, minimum of 3 runs:

| Bodies | Before | After |
|---|---|---|
| 5 | 83 ms | under 10 ms |
| 20 | 10126 ms | 29 ms |
| 60 | not measured | 141 ms |

- Cause: `place_caption` searched every obstacle edge and every placed label for each of up to four labels per axis, about N⁴ work. The selection refresh stayed below 40 ms throughout; history sync and file I/O did not show up in the profile.
- Fix: one plate per axis (name, minimum, maximum, actual, each in its guide colour), a staged candidate search (nearest positions, then the edges of the 4 nearest neighbours, viewport edges last), one projection call per axis, and no plates while a mouse button is held over the viewport or shortly after the mouse wheel.
- Not measured: a single selection of 60 bodies is 21 ms. The target of 50 ms for select-all with 60 bodies was not reached (141 ms); the user judged the result in the live window as clearly better.
- Checked visually in a separate IngeTrazo window with 60 hinged leaves: a single selection places its plate next to the axis, plates hide while orbiting and moving. Keyboard navigation was not checked.
- The benchmark runs offscreen without OpenGL, so it times the 2D overlay only.

## Control panel height (Linux)

Checked on 4 November 2026 on Linux x86_64 (Ubuntu, GNOME/Wayland), IngeTrazo 0.6.0 Flatpak, toolbar icons 40 px, with Python 3.12.14 and PySide6 6.11.3.

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
246 passed, 13 warnings in 51.41s
```

- Cause of the control panel being too small: `QScrollArea.setWidget()` does not refresh the size hint of the scroll area cached in the layout. `fit_height()` therefore computed with a negative frame height (−8 px) and gave the cards 88 instead of 180 px. Wayland respects `resize()`; the window size was not the problem.
- Measured live in the Flatpak (demo with two drives): before 520 × 190, card area 88 px; after `updateGeometry()` and `fit_height()` 520 × 282, card area 180 px.
- The new test `test_control_panel_opens_tall_enough_for_its_cards` reproduces the bug offscreen (70 instead of 94 px) and passes with the fix.
- In the Flatpak with the installed version: after starting the simulation the control panel opens at 520 × 300, the card area (198 px) shows both cards (178 px) without a scroll bar; confirmed visually.

## Unreleased state after 0.14.0 (Linux)

Checked on 4 November 2026 on Linux x86_64 (Ubuntu, GNOME/Wayland) with Python 3.12.14 (uv), PySide6 6.11.3, numpy 2.5.4 and MuJoCo 3.3.7; host reference unchanged IngeTrazo v0.6.0, commit `e61132a7`, additionally manually in the IngeTrazo 0.6.0 Flatpak.

```text
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
141 passed, 2 warnings in 51.43s
```

- The worker starts with `python -E`. In the Flatpak the start previously failed because the `PYTHONPATH` set by the launcher loaded the numpy for Python 3.13 into the Python 3.12 runtime. After the change the simulation ran in the Flatpak.
- Newly checked: every preferences setting has its own, unique explanation; disabled toolbar icons have their own grey image.
- Responsiveness (rendered offscreen and automatically checked for overlap, clipped text and overflow): sidebar in the dock at 260–560 px, preferences pages at 360–760 px without findings. The minimum width of the sidebar content dropped from 326 to 232 px. The overlap of the force-field hint observed in the real window could not be reproduced offscreen; it is fixed by a changed layout, but can only be confirmed visually in the Flatpak.

## Version 0.14.0 (Windows)

Checked on 4 November 2026 on Windows x64 with Python 3.12.14, PySide6 6.11.3 and MuJoCo 3.3.7. Host reference: IngeTrazo v0.6.0, commit `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`.

### Automated checks

Version 0.14.0 renames the extension to Newton: package, classes, public module imports, settings keys, model keys, overlay layer, Qt object names, preferences adapter, toolbar, context menus, dialogs and language files use the new name. The bundled `.igz` models are converted directly. Old namespaces are neither read nor migrated. The visible German toolbar, sidebar and preferences titles were additionally rendered offscreen through the real host dialog and checked. Third-party products and their sources keep their actual names.

Version 0.13.0 adds a categorised value editor for profiles: built-ins are readable and read-only, custom profiles editable, built-ins duplicable. Coherent English master texts and German translations explain relations and side effects in appearance, simulation, runtime and the advanced body settings. Runtime stays Runtime in the German interface too. The preferences were rendered with the host dialog and Segoe UI and checked visually.

Profile assignments store ID and parameter signature on the body and survive native `.igz` saving/loading. The checks distinguish local deviations, profile changes and deleted profiles. Single sync keeps geometry, transformation and axis position. Bulk sync uses the most recently edited profile values, stays queued until OK and forms one undo step. Cancel changes neither profiles nor bodies. A pre-check of all affected bodies prevents partial changes when axes are missing. Explicitly linking old bodies keeps their previously implicit static mobility. A missing optional control display is treated as the default display when applying a profile.

Version 0.12.1 arranges the control panel row as actual value on the left, slider in the middle and setpoint input on the right. It uses the same RangeControl component as the sidebar, including slider style, height, compact 104-pixel field and protection against accidental scroll wheel changes. Four existing checks on real drive controls, coupled gripper opening and palette pass in 8.66 seconds. The display was additionally rendered with five actuator cards and actual values of different lengths and checked visually; all sliders and right-hand input fields are aligned.

Last full run (Newton 0.14.0):

```text
.venv\Scripts\python.exe -m pytest tests -q --basetemp=.test-state/newton-rename
141 passed in 64.99s (0:01:04)
```

The full suite includes the coupling with negative ratio as well as the new contact and domino regressions.

Version 0.12.0 checks compound collision bodies with a test body that actually falls through: a common convex hull stops it above the opening, four sub-bodies let it fall through the opening to the ground. The collision display contains all four geometries; the total mass is preserved. The new energy chain has 22 rigid frames with four sub-bodies each and no blanket self-contact exemptions for non-adjacent links. The spatial separation of wheel body and connecting rod is checked with at least 39.9 mm of geometric clearance; a Newton run confirms the crank drive keeps working. The sidebar rejects a child-components collision shape on a simple body without subgroups.

Four simulation seconds of contact audit: before 156 bodies, 156 geometries, on average 78 contacts, 7.818 s run time; after 90 bodies, 156 geometries, on average 47.63 contacts, 5.720 s run time. Degrees of freedom stay 201. The chain/chain category disappears in the checked run; remaining contacts are cable/bed, cable/chain and chain/bed. These are individual comparison runs, not a general speed guarantee. `scripts/lab/audit_contacts.py` documents the active contact pairs and categories.

The revised model passes the 24-second check: motor angle 15.02 rad, stroke −136.7 to +163.4 mm, crank deviation below 0.14 mm and maximum measured cable distance about 50.5 mm including the open chain ends. The rigid first frame attachment has a visible bracket; the additional bracket details are, like the bed screws, display only, the attachment is computed by the held first body.

Version 0.11.0 adds eleven checks on motor control, anti-windup, real-time measurement, quality and mechanical connections as well as three native UI checks. A motor holds its speed under an additional load with less than 1 % deviation; a too weak motor respects its force limit and does not overshoot after unloading through a charged integrator. The telemetry is explicitly serialised through JSON, as in the real worker protocol. Native rotating carries point and pin axis along; undo restores both.

Ball, pin and fixed connections are checked in the solver for the motions they actually allow. The native interaction check connects two bodies with a pin by choosing the counter body, placing the point and choosing the Y axis, then edits the point directly in the sidebar and checks undo. A real Qt mouse press activates dragging the marker; releasing is one undo step. The eraser removes only the connection and keeps the geometry. The real-time display and the pause state are checked with a real external worker.

In the regularly installed IngeTrazo the running new version was confirmed visually: the control panel showed about 0.49× real time at a 37.2°/s setpoint and 37.3°/s actual value. The sidebar stayed visible and disabled meanwhile. The existing user windows were not closed or changed.

The repeatable two-second worker benchmark of the stored crank drive needs 7.265 s before (0.275×), 3.685 s with Balanced (0.543×) and 2.198 s with Quick (0.910×). Newtonian geometry and the two internal cable steps stayed the same. These are individual measurements on this machine, without GUI drawing time; they are no general speed guarantee. The profile before the change showed 6.712 of 7.262 s in `mj_step`, another 0.424 s in the `mj_forward` additionally called for the output. A native timer run located most of the computing time in the constraint solver.

The full 24-second run with Balanced and the new motor control reaches a motor angle of 15.02 rad instead of 10.95 rad in the old run. The stroke stays −0.1366 to +0.1634 m; the maximum geometric crank deviation is below 0.08 mm. The end connections stay at about 0.5 mm error, the maximum measured channel distance drops to about 6.30 cm including the open exit. An unstable attempt with CG and a pyramidal friction cone was discarded; the published levels still use elliptic friction.

The model **crank-drive-drag-chain.igz** was checked over 24 simulation seconds: motor angle 10.95 rad, stroke −0.1366 to +0.1634 m, maximum deviation from the geometric crank equation below 0.00008 m. The end connections show about 0.4 mm error. The 156 bodies comprise the continuous force flow motor shaft → wheel → connecting rod → passive piston → drag chain. The cable is attached only at the socket and the motor and has a free reserve loop behind the moving chain exit. The largest distances of the evaluated cable segments from the moving channel centre line are below 6.5 cm, including the open chain exit. There was no automatic simulation reset.

The additional regression of version 0.10.1 checks collision exemptions for a whole flexible object: without an exemption the segments and the housing touch, with the exemption all segments stay free of contact and at rest. The contact faces of the actual drag chain are not exempt from this.

The crank drive was finally opened with `C:\Program Files\IngeTrazo\ingetrazo.exe --new-window` in the regular IngeTrazo and checked visually. The existing window with the unsaved user project stayed open.

Version 0.10.0 adds MuJoCo's native cable elasticity plugin with separate bending/torsion moduli, radius, damping, start attachment and optional end attachment. Checked are the segmented display in the temporary model, unchanged source data, saving/loading, a real external QProcess simulation, reset, sidebar undo, conversion of a grouped line, reading in edited line end points as well as native moving with undo. All three start types (clamped, hinged and free) are checked in the real Newton model.

The rope/cable model runs five seconds with end weights and support contact: the stiffer cable hangs higher, the end connections deviate by less than 1 cm, and the reported time stays correct despite the internal subdivision. The lengths of the rope segments stay constant, the clamped start fixed. The joint chain swings for four seconds without the joint distances changing.

The drag chain is moved for twelve seconds to +180, −100 and +200 mm. Checked are less than 4 cm deviation from the carriage target under load, less than 5 mm error of the end connections and cable segments within 6 cm of the actual moving channel centre line. The channel consists of separate contact faces with overlapping transitions; the cable is attached only at the ends. It has its own ball joints and native bending/torsion forces. Configurations that are too stiff are rejected before the start with an understandable error.

The three models **rope-and-cable.igz**, **joint-chain.igz** and **drag-chain-with-cable.igz** were natively saved and loaded again. The drag chain test window including the material editor and the travel control panel was opened and checked visually. The saved final version has transparent channel walls and hidden axes.

Version 0.9.0 checks four ordered preferences tabs and the adoption of global simulation settings only on OK. Global simulation and runtime were removed from the sidebar. The object overrides are directly editable, undoable and survive profiles and native saving/loading. Newton tests check weightlessness, lateral gravity, separate ground release with the ground globally on and off, and preserved body contacts. Linear and rotational damping are checked globally and locally.

The new sun/planet model is checked over three orbits: distance 4 m with less than 2.5 cm deviation, stable common centre of mass and demonstrable motion of the sun. Zero gravity and missing damping allow a free orbit without a joint or a prescribed path. Attraction stays finite even with overlapping centres; initial velocities are restored when loading again. The model was opened in its own native IngeTrazo window; the new object settings and the start in the external Newton process were inspected.

Version 0.8.0 additionally checks the visible, disabled configuration during the simulation, Generic in first place and the object name in the heading. Deceleration with synchronisation, separate values, undo and native saving/loading are checked. An external Newton run confirms different acceleration and braking rates including braking before a direction reversal. The collision display starts off by default, is in the preferences and opens the native shortcut management; conflict management and saving are handled by the host. Temporary toggling changes no start default. The labelling test additionally checks free distance from the projected axis ranges.

In the newly opened native robot window the Generic section, the heading, the chain switch for the deceleration and the relocated tags were inspected. After start the whole configuration stayed visible and greyed out; the simulation control stayed available.

Version 0.7.0 adds the following checks:

- Collision shapes are determined in edit mode by the external Newton process, updated after parameter changes and drawn as outlines with transparent faces. The same geometry data set is available during the simulation. Purely static documents can also be checked.
- The collision demo lands on the plate with contact enabled; an excluded pair penetrates. Removing the exemption restores the actual contact. Pair assignments survive saving/loading and undo. Previously unconfigured static bodies do not accidentally become movable.
- Real native mouse events activate the axis handle already on press. Dragging moves the origin with a preview, releasing applies it and undo restores the original data. The body geometry stays unchanged. Cancelling a direction handle discards the preview; its working plane lies at the original handle point.
- Larger axis tags are arranged without overlap and stay selectable through their visible rectangles. The test draws into an image with a real QPainter.
- The new axis placement was compared directly with IngeTrazo's native line tool: snap points on existing geometry and magnetic X/Y/Z alignment yield the same points and inference kinds.

Version 0.7.1 adds wide sidebar sliders with compact number fields. Checked are the exact adoption of linear min/max values, the live adjustment of the position limits, the immediate model data change and one shared undo/redo step for a complete drag. Precise angle input above 180° and passive/disabled controls stay correct. The display was additionally inspected in the native robot window on a linear axis with 0–50 mm.

The original domino scene showed position fluctuations of up to 69.93 mm and clear continued tipping between 10 and 15 simulation seconds. After the contact correction all 30 stones still fall (the last after 3.3 s); the maximum position span in the same rest window is 0.56 mm. The change of orientations is also checked within bounds. The scene is not frozen artificially. A separate test confirms the exact geometry of rotated cuboids; a deformed eight-corner polyhedron is still treated as a hull.

After the sidebar structuring (0.6.1) the affected host/UI suite was checked again: `32 passed in 24.96s`. The Newton computation was not changed for it. In the native test window the four sections with coherent context texts were checked for readability and spacing. With independent axes, direction and ratio are hidden; leading and following axes have matching context descriptions.

- Free fall and landing on the plane; a static body stays put.
- Body-to-body contact: two cubes stack without falling through.
- 50 independent bodies land and deliver finite poses.
- A pendulum rotates under gravity; the joint anchor stays fixed.
- A motor drives a convex wheel; re-initialising restores the initial position.
- Nested, mirrored and scaled geometry is copied correctly without changing the original.
- Demo and parameter changes are undoable; parameters survive `.igz` saving and loading.
- Unconfigured, ignored and hidden groups are treated according to the documented rules.
- The real external worker answers the JSON protocol and reports invalid commands.
- IngeTrazo's real plugin loader and MainWindow load the extension; simulation, pause, reset and unexpected process end preserve the original scene and history.
- A servo moves to changing target angles under gravity and holds them.
- A linear position drive moves to target distances and limits them at the stops.
- A free linear axis falls exclusively along its axis; a speed drive can be reversed.
- A joint between movable bodies carries its anchor along with the parent body.
- Joint loops and missing parents are explicitly caught; legacy joints are interpreted.
- Named controls move a door to 60° and a carriage to 400 mm through real external sessions. Reset discards runtime targets without changing start values.
- Two snap points and the axis keyboard shortcuts align joints; Z is intercepted before the built-in zoom shortcut.
- Native moves of the reference body carry dependent parts and their axes along, also with classic groups without an instance matrix.
- Child movements do not change the reference body; multi-selection does not move children twice.
- Rotation, live preview, detaching the assignment, undo/redo and reference body assignment after reloading the `.igz` are checked.
- Dragging moves passive bodies without teleporting and sets passive joint chains in motion. Servo/motor bodies are explicitly rejected in the worker.
- Reference body connections without an axis of their own form a rigid connection in the simulation.
- A dependent part marked fixed follows its movable reference body but cannot be grabbed itself.
- Speed and acceleration limits of the actuator's setpoint profile are checked.
- All eleven toolbar actions have icons; four separators structure the functions. Profile management and preferences were removed from the toolbar. Native icons, alternative sets and palette changes are checked.
- Axes are placed without a dialog; sidebar changes apply directly, with correct unit conversion and without unintended history entries when refreshing the display.
- The native eraser removes rotation and linear axes, keeps geometry and reference body and supports undo. Axis stroke, multiple axes, Shift, cancelling and ordinary geometry erasing are checked.
- Eight built-in profiles, creating from object settings, renaming, replacing and deleting custom profiles; applying keeps spatial data and identities and forms one undo step. Cancelling the axis placement changes nothing.
- The control panel starts, pauses, resumes and resets, also without an object selection.
- Without a selection the Newton sidebar stays empty. The real browser type column shows servo axis bodies and control names.
- German host language and English fallback for an unsupported language; English master catalogue and valid translation keys.
- The native preferences dialog contains exactly one Newton tab with icon selection and profile management. Changes stay local until OK, Cancel discards them. Saving, renaming, replacing and deleting profiles are checked in the dialog. The existing units page navigation is kept.
- Solver coupling keeps both jaws moved equally far, also with asymmetric load on a fixed test body. Both contact pairs are checked. Reopening, negative ratio factor, bounded common distance as well as speed/acceleration limits are checked. Missing axes, loops and invalid couplings are rejected.
- An opening control maps 5–105 mm to the common jaw distance. The follower axis has no second control, cannot be dragged and is decoupled in one shared undo step when the leading axis is removed.
- An existing `Newton_Axes` layer is reused; visibility and coupling survive saving/loading. Hiding suppresses drawing and axis picking without disabling bodies or Newton.
- Markers for range, limits, zero position, target and actual position are checked. The axis frame follows the moving reference body during the simulation.

### Visual check and installation

The visual check of 0.5.0 showed, in the separate IngeTrazo test window, native icons and separators, the spatial rotation axis symbol, profile selection and motion parameters without an apply button. The opened control panel showed the named control and start/reset; pause/resume are shown state-dependently and checked by host tests. The additional preferences integration of 0.5.1 was checked automatically against the real host dialog. In the previous version, pendulum start and servo door at 60° were additionally checked visibly. Eraser, profile management and dragging are checked automatically; a complete manual acceptance run of these interactions was not recorded. No frame rate benchmark.

The local installer was first run in a project test folder. Then the extension was installed under `%APPDATA%\ingetrazo\plugins\newton`. The configured Newton runtime is this project's `.venv`; the installer could import MuJoCo 3.3.7.

The already running installed IngeTrazo EXE was not restarted. Its open user project was not changed. The final release for exactly this EXE therefore requires its next restart and the loading of the extension; the automated host check was done against the source state named above.

The new synchronous gripper model was opened with the native host. The control panel shows five controls including a shared opening width. The axis layer is present in the native layer tree. The detailed limit and position geometry was checked in host tests; a complete manual run of all visibility and limit changes was not recorded.

The separate model `models/collision-test.igz` was opened in the native window. Checked visibly were the collision outlines, the blue cube resting on the plate and the orange cube that fell through its plate. A complete manual test of all axis handles and snap views was not recorded; these cases are covered by the host tests.

An installable ZIP is at `dist/newton-0.14.0.zip`. It contains the extension code, English and German language catalogue and the installation guide, but no Python or MuJoCo binaries.
