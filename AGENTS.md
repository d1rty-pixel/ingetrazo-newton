# AGENTS.md

Guidance for coding agents and contributors working on Newton, a physics extension for the 3D modeller IngeTrazo. All documentation is English ([README](README.md), [docs/manual.md](docs/manual.md), this file); only the UI has German translations.

## Architecture

- `newton/` is the extension package that IngeTrazo loads (`setup(app)` in `newton/__init__.py`). It targets IngeTrazo 0.6.1 / Extension API 2 and must not modify IngeTrazo core files. Where API 2 lacks a hook, Newton uses a local adapter (for example `preferences.py` wraps the host preferences dialog).
- `newton/worker.py` is a standalone process: standard library, `mujoco` and `numpy` only, no Qt and no IngeTrazo imports. It speaks JSON lines prefixed with `NEWTON:` over stdin/stdout. `session.py` (simulation) and `collision_view.py` (collision preview) start it with `python -E -u worker.py` using the interpreter from `runtime.json` or the Runtime preference.
- Model data lives in `group.ext["newton"]` and is saved in the `.igz`. Settings use the `newton/` QSettings prefix. Axis overlays, axis objects and connection objects (wire groups with `ext["newton"]["axis_of"]` or `["connection_of"]`, see `axis_objects.py`) use the reserved layer `Newton Axes`. The joint and `point_attachment` data stay authoritative; a history hook syncs the objects in the same undo step. There are no aliases for older names.
- `runtime_setup.py` creates, checks and locates the runtime (Python 3.12 + MuJoCo in `<IngeTrazo data>/newton-runtime/`); it is standard library only, doubles as a command line (`python newton/runtime_setup.py --help`) and has two maintainer switches (`RUNTIME_SETUP_ENABLED`, `DOWNLOAD_UV`). `runtime_ui.py` is the preferences widget. The pinned `uv` hashes and `runtime-requirements.txt` must be updated together with `UV_VERSION`, `MUJOCO_VERSION` and `requirements-dev.txt`. See [docs/runtime-setup.md](docs/runtime-setup.md).
- Module overview: `model.py` (geometry, body specs), `panel.py` (sidebar, browser), `icons.py` (icon library), `toolbar.py` (actions, dropdown pictograms), `joints.py`/`axis_edit.py`/`axis_guides.py`/`axis_objects.py` (axes), `references.py` (reference bodies, undo adapters), `glow.py` (rims around linked bodies and pick candidates), `connections.py`, `flexible.py`, `coupling_ui.py`, `controls.py` (control panel: the dock below the 3D view, joins through the `QMainWindow` API because API 2 has only the side tray), `virtual_editor.py` (the editor in a virtual control's expanded row), `profiles*.py`, `preferences.py`, `eraser.py`, `i18n.py`.

## Development setup

The tests import IngeTrazo itself, so a checkout of the exact host version must sit next to the extension as `ingetrazo-source/` (git-ignored):

```bash
git clone https://github.com/ingelibre/ingetrazo.git ingetrazo-source
git -C ingetrazo-source checkout ffc7187bbaf8222ea5f5f19e33f6c4ed81ad4ad5
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

Canonical full suite (about 435 tests, 100–120 s on Linux):

```bash
.venv/bin/python -m pytest tests -q --basetemp=.test-state/pytest
```

- Tests run Qt offscreen (`tests/conftest.py`) and use IngeTrazo's real loader and `MainWindow`. Settings and autosave go to `.test-state/`, never to the user's profile.
- Run the tests that cover the change (`pytest tests/test_interface.py -k <name>`, or the affected test files), also before a commit. The full suite is only needed for a release, and releases are made in `../ingetrazo-extensions`, not in this repository.
- `tests/test_newton.py` runs the worker as a subprocess with `sys.executable`; keep the worker importable without IngeTrazo.
- In a git worktree (for example under `.claude/worktrees/`), symlink `ingetrazo-source` from the main checkout and use the main checkout's `.venv` interpreter; `.test-state/` is per worktree, so parallel suites do not share settings.
- Record notable test suite runs, measurements and manual checks in [docs/lab/test-and-measurement-runs.md](docs/lab/test-and-measurement-runs.md).

Useful scripts: `scripts/dev/preview.py` (open a demo in a test window), `scripts/lab/benchmark_newton.py`, `scripts/lab/audit_contacts.py`, `scripts/package.py` (builds `dist/newton-<version>.zip`: one `newton/` folder, as the IngeTrazo catalog requires, reproducible hash).

## User-visible text

- Every user-visible string goes through `tr("English source")` from `newton/i18n.py`. English is the master; missing translations fall back to English.
- Longer explanations live in `newton/help_texts.py` (English).
- `newton/i18n/en.json` is the master catalogue: every English source string mapped to itself, sorted by key. Help texts are keyed by their full English text. Many strings reach `tr()` as data (worker errors, list labels), so the master cannot be derived from `tr()` calls alone; maintain it by hand.
- Every other `newton/i18n/<language>.json` (named after the host language code, e.g. `de`, `fr`) has exactly the master's keys, no more, no fewer. To add a language, copy `en.json` and translate the values. `tests/test_i18n.py` covers every language file automatically.
- `tests/test_i18n.py` fails on a static `tr()` string or help text missing from the master, on a master key no longer used as a string literal in `newton/`, on missing or extra keys in a translation, on empty values and on mismatched `{placeholders}`. Changing an English source string changes its key: update it in `en.json` and in every translation.
- German UI terminology: Körper (simulated body), Achse (user-placed axis), Anschläge (limits), Antrieb (actuator), Steuerpult (control panel), Bezugskörper (reference body), Kollisionsform (collision shape). "Runtime" stays untranslated on purpose.

## Installing into IngeTrazo for manual testing

- Windows: `scripts/install-local.ps1` (see [docs/installation.md](docs/installation.md)).
- Linux Flatpak: `scripts/install-local.sh` copies `newton/*.py`, `i18n/` and `icons/` to `~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton/` and writes `runtime.json` with the `.venv` interpreter. `--update` replaces an existing install (backup in `.backups/`), `--destination <plugins dir>` redirects the target (use a temp dir for script tests), `--python` overrides the interpreter. The installation is a copy; rerun after changes and restart IngeTrazo.

## Icons, pictograms and layout

- Every drawing is one SVG file in `newton/icons/`, named after the icon (`movable.svg` is `"movable"`). One concept has one drawing: the toolbar action "Movable" and the dropdown value "Movable" both use `movable`. The reverse is allowed: related actions may share a drawing when the meaning stays clear in context (`unlink` detaches a reference body and removes a connection; `connect` starts a connection and selects a connection object). Do not draw a new icon only to avoid reuse. Do not draw icons inline in Python.
- File format: the common header (`icons.HEADER`, a 24 × 24 grid), then `<g id="ink">` with the shape and `<g id="accent">` with the defining detail. At runtime the ink becomes the palette's text colour, the accent the host accent (`views.theme.accent_color()`), and a separate all-grey pixmap serves the disabled state. Files without these groups (`status_error`, `status_warning`) keep their fixed signal colours.
- Drawing rules, so the set stays uniform:
  - A body is a rounded square (`rx="1"`), 10 × 10 on its own, 7 × 7 when two bodies share the picture. A point mass in a physical pictogram (gravity, bounce, attraction) is a circle.
  - Ground is a line from x 3 to x 21; anchored ground carries the hatching of `fixed`.
  - Arrowheads are 3 units long (`l3 3-3 3`); damping is two parallel bars, the second one shorter.
  - The accent marks what the action, choice or setting changes. "None" choices (`no_axis`, `rigid`) have no accent; `play`, `pause` and `reset` are drawn in the accent only.
  - Leave stroke widths to the renderer, except deliberate thick bars (`stroke-width="4"`).
  - Names are lower-case snake case; a dropdown value's drawing is prefixed with its kind (`connection_ball`, `drive_free`). A toolbar action for a dropdown value uses that value's drawing (`connect_ball` shows `connection_ball`).
- Adding an icon: write the SVG with the header and both groups, reference it by name (`icon()`, `attach()`, `CHOICES` or a physical pictogram), run `scripts/dev/icons.py --sheet` and compare it with its neighbours at 22 px in light and dark, then run `tests/test_icons.py`.
- Model overlays (axes, connection objects, rims) draw like the pictograms and share one colour language, defined in `axis_guides.COLOURS`:
  - sand (`axis`): the shape of an axis or connection; a connection object is drawn like its type's pictogram;
  - yellow (`actual`): current position, connection point and the rims of reference bodies, dependent bodies and coupling leaders linked to the selection;
  - magenta (`connected`): rims of connection targets and rope ends linked to the selection;
  - cyan, dashed (`exemption`): rims of bodies with a collision exemption to the selection;
  - violet (`target`): the servo target only; green, blue and orange: range, minimum and maximum; dotted grey: zero;
  - red: the object a click or the eraser would hit; grey: locked;
  - host accent: the body a pick would take (`newton/glow.py`).
  Do not give a colour a second meaning.
- `newton/icons.py`: `icon(name)` (QIcon), `pixmap(name, size)`, `attach(widget, name)` for buttons and labels that must follow palette changes (`repaint()`, called via `toolbar.redecorate()` from `panel.refresh_icons`).
- `newton/toolbar.py`: `CHOICES` maps fixed dropdown values to icon names and `decorate(combo, kind)` applies them; `physical_label()` puts a physical pictogram on form labels; only settings that change a physical quantity get one. `pictogram_check()` puts a pictogram on a checkbox; every checkbox in the sidebar and the profile editor has one.
- `scripts/dev/icons.py` exports icons by name as coloured SVG/PNG and writes `dist/icons/overview.png` (every icon small and enlarged, light and dark); check it after every drawing change. `tests/test_icons.py` fails on a referenced icon without a file, on a file nobody uses, and on a file that breaks the format.
- Preferences pages are built with `SettingsPage` (`newton/preferences.py`): headed categories separated by a line, each setting with its own explanation (also its tooltip). New settings need a text in `help_texts.py` and its German version.
- Sidebar sections are the host's collapsibles (`views.fold_section.FoldSection`), created with `section()`/`settings_section()` in `panel.py`; the open state is stored under `newton/open_<key>`. Add new sections to `panel.sections` so they are disabled (but still foldable) during a simulation.
- The sidebar is resizable. Keep its content narrow enough (about 240 px content, 280 px sidebar): use `toolbar.compact()` for dropdowns, `views.fold_section.narrow()` for fields side by side, `WrapLongRows` for nested forms, avoid fixed widths, and do not put word-wrapped labels inside a `QFormLayout` (they get too little height and are overlapped); place them between forms instead, as `settings_section()` does. Never cap a section's height (`QSizePolicy.Maximum`): wrapped rows need their height-for-width. `test_sidebar_rows_keep_their_height_at_every_width` checks this.

## Conventions

- Keep changes small and match the surrounding code style.
- Comments explain why, not what.
- Known bugs and unexplained observations go to [docs/known-issues.md](docs/known-issues.md); remove an entry when its fix lands.
- Do not commit `ingetrazo-source/`, `.venv/`, `.test-state/`, `newton/runtime.json` or `dist/`.

## Changelog

- [CHANGELOG.md](CHANGELOG.md) lists every notable change by release. Versions are the GitHub releases (tag `v<version>`, the version from `__version__` in `newton/__init__.py`); unreleased changes go under "Unreleased", grouped as Added, Changed, Fixed, Removed and Documentation.
- Update the changelog no later than the release: before a release is published, move "Unreleased" into a section with the release version and date. Preferably also add an entry as soon as a task is complete, in the same commit or one right after it.
- Write entries for users of the extension: what changed and why it matters, not the commit list. Measured effects (for example start time) may be named with their figure.

## Host proposals

- Develop against the pinned host only. Never wait for, anticipate or design around a host change that has not landed in the pinned version.
- Keep `ingetrazo-source/` current: at the start of a session, `git -C ingetrazo-source fetch`. If `origin/main` has moved past the pinned commit, check out the new head, update the pinned commit in "Development setup", run the full suite, and check [docs/host-proposals.md](docs/host-proposals.md) for entries that have landed. Report failures before continuing with the task.
- While working on a task that touches the host (an API, a workaround, a host bug, a slow host path), check the relevant `ingetrazo-source/` code for a fix, extension point or improvement that would make Newton, other extensions or the host safer, faster or simpler, especially one that would remove a Newton workaround. Limit this to code the task already leads to; do not survey the host speculatively.
- Record findings in [docs/host-proposals.md](docs/host-proposals.md), one entry per proposal in its format, with file references to the pinned commit. Update an existing entry instead of adding a duplicate.
- Never change `ingetrazo-source/` for this; proposals go upstream. When one lands in a pinned version, replace the Newton workaround and remove the entry.
- Upstream contributions happen only when the user asks. New public API goes upstream as an issue first (the host's plugin API is not stable yet, so its maintainers decide the shape); small, well-understood host fixes go as pull requests. Write them in English and follow the host's `CONTRIBUTING.md` (PEP 8, a regression test that fails without the fix, `python -m pytest -m "not slow"`).
- Pull requests come from the fork `d1rty-pixel/ingetrazo`, checked out separately as `../ingetrazo-fork/` (never `ingetrazo-source/`), one branch per fix from the fork's up-to-date upstream `main`. After filing, set the entry's status to **proposed** with the issue or pull request link.
