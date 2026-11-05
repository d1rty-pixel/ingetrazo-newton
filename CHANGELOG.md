# Changelog

Notable changes to Newton, the physics extension for IngeTrazo. Versions follow the [GitHub releases](https://github.com/d1rty-pixel/ingetrazo-newton/releases); the version number lives in `newton/__init__.py` (`__version__`). Changes not yet released are listed under "Unreleased".

## Unreleased

### Added

- Preference *Simulation → Hidden geometry* (*When needed*, *Always*, *Never*; default *When needed*): hidden bodies are left out of the simulation unless a visible body depends on them (reference body, attachment, connection, coupling); hidden fixed bodies stay as surroundings. On the CR10 example the simulation runs about 8× faster.
- Claude Code skill `skills/ingetrazo-newton/` for modelling with Newton: objects and their effects, grouping for correct and fast simulations, performance options and limits.

### Changed

- Start is much faster on large models: the temporary simulation shares the document's meshes and nested placements instead of copying them. `prepare()` on the CR10 model (about 250 000 vertices) went from 11.3 s to 0.84 s.
- The temporary simulation refuses every edit: commands are refused before they run, groups cannot be opened, and a geometry change made anyway is reported after Reset.

### Fixed

- The "unknown collision shape" error has a translatable English text.
- Render flags of the document's meshes that were still pending at Start are restored after Reset, so the model view does not keep old paint.

### Documentation

- Performance audit results (start time, per-frame redraw cost), shared-mesh measurements and a live check in the Flatpak in `docs/test-results.md` and `docs/known-issues.md`.
- `docs/host-proposals.md` collects IngeTrazo improvements that would make Newton or other extensions simpler, safer or faster.
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
