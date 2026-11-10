# Changelog

Notable changes to Newton, the physics extension for IngeTrazo. Versions follow the [GitHub releases](https://github.com/d1rty-pixel/ingetrazo-newton/releases); the version number lives in `newton/__init__.py` (`__version__`). Changes not yet released are listed under "Unreleased".

## Unreleased

### Fixed

- Opening a model saved before axis and connection objects existed (including most example models) no longer marks it as changed. Newton rebuilds those objects from the saved axes, which counted as an edit, so after Start and Reset the title showed `*` and closing asked to save although nothing was edited.

### Documentation

- New [FAQ](docs/faq.md), starting with why bodies on a layer shown during the simulation stay invisible (hidden bodies left out at Start) and how to include them.

## 0.15.0 — 2026-11-06

### Added

- Control panel, *Key* column: a control without a key binding shows the key dropdown right in its strip; a bound one shows the key as before with a *Modify* button that swaps in the dropdown. The expand handle of an axis is disabled while it has no binding (nothing to show), and the strip icons and the handle follow the toolbar icon size of IngeTrazo's preferences.
- Button in the control panel's header to detach the panel into a window of its own and to attach it again; the window can be moved and resized, remembers its size and stays detached when the panel is opened again. A floating dock could not be moved on Wayland, so the detached panel is a separate window.
- Option *Keep the pose on reset* in the control panel's *Options* menu (off by default, remembered). Reset then writes the simulated pose of the bodies into the model as one undo step instead of restoring the original; axes and attachments move with the bodies and joint start angles stay as they are. Flexible or locked bodies, bodies that contain groups and a changed geometry keep nothing and say why; a reset after an error never keeps the pose.
- **Virtual controls**: a switch or slider in the control panel that moves several axes to defined states at once, for example *Flap: closed / open*. Created with *New virtual control* in the control panel and edited in the expanded row of the control, with a remove button for every state, every axis and the control; saved in the `.igz`, one undo step per change. A switch can move its axes one after another instead of together. See the manual, *Virtual controls*.
- **Key bindings**: keys move axes and virtual controls while a simulation runs. Key slots (*Newton: Key 1* …, five by default) get their keys in IngeTrazo's shortcut settings, on their own *Key slots* preferences tab; no key is assigned by default. Each slot can carry a label (for example *Gripper*) that shows in the shortcut settings and in the binding choices. An axis or virtual control is bound to a slot in its expanded row of the control panel, as *Toggle* (between two values) or *Step* (up, and down with an optional second slot). Bindings are saved in the `.igz`. See the manual, *Key bindings*.
- Option *Keep warnings and errors on reset* in the control panel's *Options* menu (off by default, remembered). While a simulation runs, the bodies in a warning such as the Z = 0 warning cannot be selected; with the box checked, Reset keeps the warning and its body table instead of replacing it with the reset notice, and the rows then select the bodies in the restored model. Start always clears every message and checks again.
- Sidebar: the *Motion* section of an axis that a virtual control manages says so ("Managed by virtual control …") and has a button that opens that control's row in the control panel dock for editing.
- The Start warning lists the affected bodies as a table below a short sentence, with a thumbnail, the name and how far the body reaches below Z = 0. Hovering a row outlines the body in the view, a click selects it; long lists show the first six and a count. The table disappears with the message.
- Icon `ground_below` for the preference *Warn about bodies below Z = 0*, so it no longer looks like *Ground at Z = 0*.
- Warning at Start: the control panel lists movable bodies that reach below Z = 0 while their ground contact is on, because they scrape along the ground and distort the result. Bodies that only rest on Z = 0, fixed bodies and bodies without ground contact are not listed; the warning never blocks the start and can be switched off under *Simulation → Gravity and ground*. Example model `models/z0-contact-test.igz`.
- Preference *Simulation → Hidden geometry* (*When needed*, *Always*, *Never*; default *When needed*): hidden bodies are left out of the simulation unless a visible body depends on them (reference body, attachment, connection, coupling); hidden fixed bodies stay as surroundings. On the CR10 example the simulation runs about 8× faster.
- Claude Code skill `skills/ingetrazo-newton/` for modelling with Newton: objects and their effects, grouping for correct and fast simulations, performance options and limits.
- *Limit hardness* (0–100 %) per axis, as a slider below the limits and in profiles: how firmly the limits hold. 0 % is MuJoCo's default softness, 100 % a hard stop.
- Pictograms for *Quality* and *Include* (hidden geometry) in *Preferences → Simulation*, so every setting on that page has one.
- `scripts/install-local.sh`: Linux counterpart of `install-local.ps1` (Flatpak target by default, `--update` with backup in `.backups`, `--destination` and `--python` overrides).

### Changed

- The control panel is now a dock below the 3D view instead of a floating window; the sidebar keeps the full height beside it. The header holds Start/Pause, Reset, the time, the speed, the latest note, *New virtual control* and *Options*. Every control is one strip with its icon, name, actual value, target and key cap, in one column grid; a strip expands in place for its key binding and, for a virtual control, its states. Errors and warnings appear as a banner above the strips. The pressed button of a switch is drawn in the accent colour. The dock is hidden until Start or the *Controls* toolbar button, which now shows and hides it; its state is remembered with the window layout. Hiding it does not end a running simulation.
- Sidebar: **Axis coupling**, **Mechanical connection**, **Material** and **Simulation overrides** fold themselves when the selected body has nothing set there and open when it has; the state follows the selection and any change, and a manual click holds until then (no longer remembered across restarts for these four).
- The sidebar section *Flexible material* is now called *Material*.
- Profile editor: *Body & contact* is split into *Body* and *Collisions* like the sidebar, and *Simulation overrides* work as in the sidebar (no *Use own simulation settings* box; every value shown, defaults greyed, a reset button per row, only differing values stored). Existing profiles load and apply unchanged.
- Sidebar: the collision settings (shape, *Show collision shape*, exemptions) moved out of *Body & contact* into their own section *Collisions*; *Body & contact* is now *Body* (mass, friction, bounce). The sections follow a new order: Generic, Profile, Material, Body, Collisions, Motion, Mechanical connection, Axis coupling, Simulation overrides.
- Sidebar texts: shorter section paragraphs and a hover text on every key row (labels and inputs) of Generic, Motion, Axis coupling, Mechanical connection, Material, Body, Collisions and Simulation overrides. The Motion section tooltip is replaced by the Actuator tooltip.
- Length values follow the unit set under *Window → Units* (slide axis limits, target, speed and acceleration, connection points, rope and cable radius, softening radius, initial velocity), in the sidebar, the control panel and the profile editor; the fields update when the unit changes. Documents in metres now see these values in metres instead of millimetres. Gravity, attraction, pressures, damping, forces and mass stay in SI units, rotations in degrees.
- *Simulation overrides* no longer has a switch: every setting is shown and editable, values equal to the global default are greyed (and inherited), a changed value is drawn normally, and a button beside each value resets it to the default.
- *Preferences → Runtime*: *Check runtime* sits with the Python environment it checks and shows its result there, also in builds without automatic setup. *Remove runtime* is offered only for a runtime Newton created itself, refuses a symbolic link, and its confirmation names Newton's own folder and says when your current interpreter lies outside it.
- The axis plates in the 3D view are lighter: the name stays bold, while minimum, maximum and actual position are drawn in a smaller regular weight.
- Messages in the control panel are complete sentences that say what happened and what to do, for example when the Newton process stops or does not answer, and when saving, editing or deleting is refused during a simulation. German texts follow.
- Sidebar: the drawing of a setting or checkbox now sits left of its label (as in the toolbar and the preferences) instead of at the right end; long labels wrap beside the drawing.
- Selecting many axes no longer freezes the view: every axis gets one plate (name, minimum, maximum and actual position in their guide colours) instead of up to four labels, and the free-space search is bounded. Select-all of 20 jointed bodies went from 10 s to 29 ms per paint. The plates are hidden while the view or an object is being dragged and while zooming, and a plate next to the axis is chosen before one at the viewport edge.
- Start is much faster on large models: the temporary simulation shares the document's meshes and nested placements instead of copying them. `prepare()` on the CR10 model (about 250 000 vertices) went from 11.3 s to 0.84 s.
- Limits are hard by default (limit hardness 100 %), also in existing models. Before, they gave way under load: in a cable drag chain of 10 g links by 13–17° at rest and by over 100° while moving; now by less than 0.3°. Mechanisms that rested on soft limits can behave slightly stiffer.
- The temporary simulation refuses every edit: commands are refused before they run, groups cannot be opened, and a geometry change made anyway is reported after Reset.
- The worker's protocol lines use the prefix `NEWTON:` instead of `IGPHYSICS:` (internal, no effect for users).
- Attraction between bodies is computed once per body instead of once per pair: 100 mutually attracting bodies need about 3 ms instead of about 370 ms per 33 ms of simulated time, so such scenes run in real time. The forces are unchanged.
- Shown collision shapes paint faster in large models (1,000 shapes: about 20 ms instead of 31 ms per frame), and the joint values in the control panel only restyle when a joint reaches or leaves its limit (100 changing values: about 1.3 ms instead of 2.5 ms per update).
- Per-body simulation overrides (own gravity, damping) are cheaper: a body that only overrides gravity no longer needs a Jacobian per step, and damping computes only the parts that are set (100 bodies with own gravity: about 8 ms → 1 ms per 33 ms of simulated time; with linear damping about 8 → 2.7 ms).
- Start and the collision preview no longer send the vertices of box, sphere and compound shapes to the Newton process, which never used them; a detailed mesh with a box collision shape no longer slows down the start (250,000 vertices: about 80 ms of encoding saved).

### Fixed

- The simulation can no longer change the document's nested groups through the Parts explode slider, *Place a Copy* or Edit ▸ Copy, and the check after a simulation now also reports reversed faces and changed face colours, materials or textures.
- Windows: `install-local.ps1` works in Windows PowerShell 5.1; it reported "MuJoCo is not installed" for every interpreter because PowerShell dropped the quotes of its MuJoCo check.
- Windows: `setup-runtime.ps1` accepts only a Python 3.12 64-bit and says so, replaces a `.venv` left by another Python instead of failing again, leaves a Linux `.venv` from WSL alone and installs the pinned `runtime-requirements.txt` (with numpy).
- `install-local.ps1 -Update` and `install-local.sh --update` remove modules that a newer version no longer has.
- The control cards no longer show "No key" for every key binding while a simulation runs.
- A position-driven axis (servo) now reaches its target under a steady load instead of stopping short. The drive gained an integral term limited to 15 % of the axis force. In the drag-chain demo the carriage was 2.7–5.0 cm off target and is now within 0.2 cm.
- Axis and connection objects now follow hiding and renaming of their body while a group is open for editing, instead of catching up after leaving the group. Grouping an axis or connection object together with other objects (Make Group) no longer captures it: it stays a top-level object in the same undo step, and no duplicate is created.
- The installation scripts copy `runtime-requirements.txt` and `LICENSE`; without the requirements file *Set up runtime* failed after a script installation.
- *Preferences → Runtime*: the status line is no longer cut off and the descriptions on every preferences page use the normal text colour instead of a pale grey. The page now links to the manual installation guide on GitHub instead of naming a repository file.
- The default runtime lookup finds `.venv/bin/python` on Linux and macOS, not only `.venv/Scripts/python.exe` on Windows; one helper in `runtime_setup.py` serves both lookups.
- Axis and connection objects follow their body when it is hidden or unhidden and when it is renamed (a renamed object is overwritten); both steps undo together with the body's change.
- The "unknown collision shape" error has a translatable English text.
- No horizontal scrollbar in the sidebar at a dock width of 260 px; the side margins are narrower to make room.
- Render flags of the document's meshes that were still pending at Start are restored after Reset, so the model view does not keep old paint.

### Documentation

- Archived the extension-only performance review, reproducible synthetic probes and measurement records under `docs/performance-review-2026-11-06/`; the fixes are listed under Changed.
- Windows is tested: release zip, installation scripts, runtime setup (button, command line, manual) and simulation on Windows 11 with IngeTrazo 0.6.0. The README shows the status of every platform as a badge. `scripts/lab/windows-install-test.ps1` repeats the test in a sandbox.
- New `docs/installation.md` (extension library, manual install per platform, release zip, verification) and `docs/ai-skill.md` (using the skill with Claude Code and Codex); `docs/runtime-setup.md` now starts with the automatic setup and has manual steps per platform; shorter README with a platform status table.
- Test model `models/z0-contact-test.igz` and the decisions for the planned warning about bodies below the ground at Z = 0 (resting on Z = 0 does not count; the warning does not block the start).
- New `SECURITY.md`: supported versions, private reporting through GitHub (first response within 7 days) and the scope of the policy.
- Performance audit results (start time, per-frame redraw cost), shared-mesh measurements and a live check in the Flatpak in `docs/lab/test-and-measurement-runs.md` and `docs/known-issues.md`.
- `docs/host-proposals.md` collects IngeTrazo improvements that would make Newton or other extensions simpler, safer or faster.
- `scripts/lab/benchmark_overlays.py` times the overlay paint and the selection refresh for N jointed bodies.
- Known issue: cable tests fail when `tests/test_newton.py` runs before `tests/test_flexible.py` in one process.

## 0.14.0 — 2026-11-04

First release in this repository, for IngeTrazo 0.6.0 (Extension API 2). The extension was imported from earlier development as version 0.14.0; the changes below were made before the release.

### Added

- Runtime setup: creates, checks and removes a Python 3.12 + MuJoCo runtime from *Preferences → Newton → Runtime*, also usable from the command line (`newton/runtime_setup.py`).
- Control panel with run controls, messages, error and warning marks, opening at the view's corner and sized to its cards.
- Axis objects and connection objects on the layer `Newton Axes`: they can be moved with IngeTrazo's Move, Rotate and Scale tools, selected from the context menu and locked from the sidebar; hinges get an axis preview and a 0° direction.
- Ball, pin and fixed connections can be placed from the toolbar; connections are drawn like their pictograms, results are reported, and the body is made movable when needed.
- Rims around linked bodies (reference bodies, connection targets, collision exemptions) and around the body a pick would take, each kind in its own colour.
- Referenced bodies appear as sidebar rows with picture and remove button; a row outlines and selects its body.
- Collision shape display per body from the sidebar; collision exemptions in the body and contact section.
- Context menu grouped, with connection types.
- Every icon is an SVG in a library with uniform drawing rules; every sidebar checkbox and physical setting has a pictogram; labels scale with the toolbar icon size.
- Every setting on the preferences pages has its own explanation.
- Example model: wrecking ball and brick wall.

### Changed

- Run controls moved from the sidebar into the control panel.
- The toolbar is split into *Newton Tools* and *Newton Simulation*.
- Sidebar sections fold like the host's side panels; settings that a fixed or excluded body ignores are disabled.
- Newton's own drag handles for axes and connections were removed in favour of the host's tools.
- The reserved layer is called `Newton Axes`.
- Documentation, example models, scripts, demo data and tests are in English; the UI keeps its German translation, with corrected terminology. Translation catalogues are maintained by hand and checked by tests.

### Fixed

- The worker starts with `python -E`, so the host's `PYTHONPATH` (for example in the Flatpak) does not reach it.
- Hidden bodies are simulated instead of left out.
- The mouse wheel no longer changes dropdowns and number fields while scrolling.
- Toolbar actions keep working when PySide drops their wrapper.
- Connection markers are easier to hit, highlighted on hover, readable on small bodies; pin connections match their pictogram; saved connection wires are rebuilt when their drawing changes.
- Sidebar rows keep their full height and the sidebar does not scroll sideways; folded sections stack with more space.
- The control panel grows when the speed line appears and fits its cards after they are replaced.
- Edit hints stay visible; run messages show in the control panel.
- The release zip contains a single `newton` folder and has a reproducible hash.
