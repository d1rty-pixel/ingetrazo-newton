# AGENTS.md

Guidance for coding agents and contributors working on Newton, a physics extension for the 3D modeller IngeTrazo. User documentation is German ([README](README.md), [docs/handbuch.md](docs/handbuch.md)); this file and [docs/known-issues.md](docs/known-issues.md) are English.

## Architecture

- `newton/` is the extension package that IngeTrazo loads (`setup(app)` in `newton/__init__.py`). It targets IngeTrazo 0.6.0 / Extension API 2 and must not modify IngeTrazo core files. Where API 2 lacks a hook, Newton uses a local adapter (for example `preferences.py` wraps the host preferences dialog).
- `newton/worker.py` is a standalone process: standard library, `mujoco` and `numpy` only, no Qt and no IngeTrazo imports. It speaks JSON lines prefixed with `IGPHYSICS:` over stdin/stdout. `session.py` (simulation) and `collision_view.py` (collision preview) start it with `python -E -u worker.py` using the interpreter from `runtime.json` or the Runtime preference.
- Model data lives in `group.ext["newton"]` and is saved in the `.igz`. Settings use the `newton/` QSettings prefix. Axis overlays, axis objects and connection objects (wire groups with `ext["newton"]["axis_of"]` or `["connection_of"]`, see `axis_objects.py`) use the reserved layer `Newton Axes`. The joint and `point_attachment` data stay authoritative; a history hook syncs the objects in the same undo step. There are no aliases for older names.
- Module overview: `model.py` (geometry, body specs), `panel.py` (sidebar, browser), `toolbar.py` (icons, actions), `joints.py`/`axis_edit.py`/`axis_guides.py`/`axis_objects.py` (axes), `references.py` (reference bodies, undo adapters), `connections.py`, `flexible.py`, `coupling_ui.py`, `controls.py` (control panel), `profiles*.py`, `preferences.py`, `eraser.py`, `i18n.py`.

## Development setup

The tests import IngeTrazo itself, so a checkout of the exact host version must sit next to the extension as `ingetrazo-source/` (git-ignored):

```bash
git clone https://github.com/ingelibre/ingetrazo.git ingetrazo-source
git -C ingetrazo-source checkout e61132a7f8a098ca77fb6b0e7cac488c1bd410cb
```

Python 3.12 (64-bit) environment in `.venv` (git-ignored):

```bash
# Linux
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Tests

Canonical full suite (about 45 s, 160 tests):

```bash
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
```

- Tests run Qt offscreen (`tests/conftest.py`) and use IngeTrazo's real loader and `MainWindow`. Settings and autosave go to `.test-state/`, never to the user's profile.
- Run focused tests during development (`pytest tests/test_interface.py -k <name>`), the full suite once before a commit.
- `tests/test_newton.py` runs the worker as a subprocess with `sys.executable`; keep the worker importable without IngeTrazo.
- Record notable verification runs in [docs/testergebnisse.md](docs/testergebnisse.md).

Useful scripts: `scripts/preview.py` (open a demo in a test window), `scripts/benchmark_newton.py`, `scripts/audit_contacts.py`, `scripts/package.py` (builds `dist/newton-<version>.zip`).

## User-visible text

- Every user-visible string goes through `tr("English source")` from `newton/i18n.py`. English is the master; missing translations fall back to English.
- Longer explanations live in `newton/help_texts.py` (English).
- `newton/i18n/en.json` is the master catalogue: every English source string mapped to itself, sorted by key. Help texts are keyed by their full English text. Many strings reach `tr()` as data (worker errors, list labels), so the master cannot be derived from `tr()` calls alone; maintain it by hand.
- Every other `newton/i18n/<language>.json` (named after the host language code, e.g. `de`, `fr`) has exactly the master's keys, no more, no fewer. To add a language, copy `en.json` and translate the values. `tests/test_i18n.py` covers every language file automatically.
- `tests/test_i18n.py` fails on a static `tr()` string or help text missing from the master, on a master key no longer used as a string literal in `newton/`, on missing or extra keys in a translation, on empty values and on mismatched `{placeholders}`. Changing an English source string changes its key: update it in `en.json` and in every translation.
- German UI terminology: Körper (simulated body), Achse (user-placed axis), Anschläge (limits), Antrieb (actuator), Steuerpult (control panel), Bezugskörper (reference body), Kollisionsform (collision shape). "Runtime" stays untranslated on purpose.

## Installing into IngeTrazo for manual testing

- Windows: `scripts/install-local.ps1` (see README).
- Linux Flatpak: copy `newton/*.py` and `newton/i18n/` to `~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton/` and write `runtime.json` with the `.venv` interpreter. The installation is a copy; recopy after changes and restart IngeTrazo.

## Icons, pictograms and layout

- All drawings are inline SVG in `newton/toolbar.py`, in IngeTrazo's style: the shape in the palette's text colour, the defining detail in the host accent colour (`views.theme.accent_color()`), and a separate all-grey pixmap for the disabled state.
  - `PATHS`: toolbar and button icons, `icon(name)`.
  - `CHOICES`: one pictogram per fixed dropdown value, attached with `decorate(combo, kind)`; they show how the bodies involved interact.
  - `PICTOGRAMS`: physical quantities, used by `pictogram()` (preferences), `physical_label()` (form labels) and `physical_check()` (checkboxes). Only settings that change a physical quantity get one.
  - `redecorate()` repaints everything after a palette change (called from `panel.refresh_icons`).
- Preferences pages are built with `SettingsPage` (`newton/preferences.py`): headed categories separated by a line, each setting with its own explanation (also its tooltip). New settings need a text in `help_texts.py` and its German version.
- Sidebar sections are the host's collapsibles (`views.fold_section.FoldSection`), created with `section()`/`settings_section()` in `panel.py`; the open state is stored under `newton/open_<key>`. Add new sections to `panel.sections` so they are disabled (but still foldable) during a simulation.
- The sidebar is resizable. Keep its content narrow enough (about 240 px content, 280 px sidebar): use `toolbar.compact()` for dropdowns, `views.fold_section.narrow()` for fields side by side, `WrapLongRows` for nested forms, avoid fixed widths, and do not put word-wrapped labels inside a `QFormLayout` (they get too little height and are overlapped); place them between forms instead, as `settings_section()` does. Never cap a section's height (`QSizePolicy.Maximum`): wrapped rows need their height-for-width. `test_sidebar_rows_keep_their_height_at_every_width` checks this.

## Conventions

- Keep changes small and match the surrounding code style.
- Comments explain why, not what.
- Known bugs and unexplained observations go to [docs/known-issues.md](docs/known-issues.md); remove an entry when its fix lands.
- Do not commit `ingetrazo-source/`, `.venv/`, `.test-state/`, `newton/runtime.json` or `dist/`.
