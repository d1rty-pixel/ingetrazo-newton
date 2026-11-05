# Newton

Newton is a physics extension for the 3D modeller [IngeTrazo](https://github.com/ingelibre/ingetrazo). It picks up the idea of SketchyPhysics: the groups and components of a model become bodies that fall, collide, rotate or slide on axes and are driven by motors. The simulation runs directly in the model and can be reset to the original state at any time.

Version 0.14.0 · for IngeTrazo 0.6.0 (Extension API 2) · physics by [MuJoCo](https://mujoco.org) 3.3.7 · licence GPL-3.0-or-later

## What Newton can do

- **Bodies:** movable, fixed or excluded; mass, friction, bounce and collision shape (box, sphere, convex hull, child components).
- **Axes:** place rotation and linear axes directly in the model, with limits, servo or motor drive and a force limit.
- **Reference bodies:** parts hang on other parts and follow them while editing and in the simulation.
- **Connections:** ball, pin and fixed connections close mechanisms such as a crank drive.
- **Axis coupling:** several axes follow one shared control, for example two gripper jaws.
- **Ropes and cables:** open polylines become flexible strands of constant length.
- **Controls:** named controls for all actuators; passive bodies can be dragged with the mouse.
- **Profiles:** reusable parameter sets for bodies and actuators.

Not yet included: ball and universal joints as axes, replay, magnetism, buoyancy and the scripts of SketchyPhysics, among others. All limits are listed in the [manual](docs/manual.md#limits).

## Requirements

- IngeTrazo 0.6.0 (Windows installation or Flatpak on Linux)
- a separate **Python 3.12 (64-bit)** with `mujoco==3.3.7`. Newton starts the physics in this Python as its own process; IngeTrazo itself does not ship a suitable Python.

## Installation

The runtime (Python 3.12 with MuJoCo) can be set up with one click in the preferences under *Newton ▸ Runtime*, or created by hand or by script for every IngeTrazo package (Windows, AppImage, Flatpak, macOS): [docs/runtime-setup.md](docs/runtime-setup.md). The following sections describe installing from the repository.

### Windows

```powershell
.\scripts\setup-runtime.ps1 -Python 'C:\Path\to\Python312\python.exe'
.\scripts\install-local.ps1
```

`setup-runtime.ps1` creates the `.venv` environment in the project folder. `install-local.ps1` copies the extension to `%APPDATA%\ingetrazo\plugins\newton` and writes the Python path to `runtime.json`. `install-local.ps1 -Update` updates an existing installation; the previous version goes to `.backups`. An existing environment with MuJoCo can be passed with `-Python 'C:\Path\to\environment\Scripts\python.exe'`.

### Linux (Flatpak)

There is no install script yet. By hand:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mujoco==3.3.7
target=~/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins/newton
mkdir -p "$target"
cp newton/*.py "$target"/ && cp -r newton/i18n newton/icons "$target"/
printf '{"python": "%s"}\n' "$PWD/.venv/bin/python" > "$target/runtime.json"
```

The Flatpak may access the home directory and can therefore start the `.venv` directly.

### After installing

Restart IngeTrazo completely and open **Extensions → Newton…**. The toolbars **Newton Tools** (modelling) and **Newton Simulation** can be shown through the normal toolbar management. The `.venv` must stay in place as long as Newton uses it. After moving it, choose the Python path again under **Preferences → Newton → Runtime**.

## Getting started

1. Select a group or component.
2. In the **Newton Tools** toolbar, click **Rotation axis** or **Linear axis**.
3. In the model, click the pivot or start point, then click the direction or press **X**, **Y** or **Z**. **Esc** cancels.
4. In the Newton sidebar, set the behaviour and the drive. Changes apply immediately and can be undone.
5. Press **Start**. Drag passive bodies with the left mouse button and move actuators with the control panel. **Reset** restores the original model.

Ready-made examples are in [`models/`](models) and described in [docs/example-models.md](docs/example-models.md).

## Claude Code skill

[`skills/ingetrazo-newton/SKILL.md`](skills/ingetrazo-newton/SKILL.md) gives [Claude Code](https://claude.com/claude-code) a compact guide to Newton: the objects and their effects, how to group parts so the simulation is correct and fast, performance options and limits. Install it for all your projects, or only for one project, by linking or copying the folder:

```bash
# for all projects
mkdir -p ~/.claude/skills && ln -s "$PWD/skills/ingetrazo-newton" ~/.claude/skills/ingetrazo-newton
# or only for one project
mkdir -p /path/to/project/.claude/skills && cp -r skills/ingetrazo-newton /path/to/project/.claude/skills/
```

On Windows, copy the folder to `%USERPROFILE%\.claude\skills\`. Claude Code picks the skill up in new sessions. It is used automatically when you ask about Newton models, or explicitly with `/ingetrazo-newton`, for example `/ingetrazo-newton why does my drawer simulation start so slowly?`.

## Documentation

| Document | Content |
|---|---|
| [docs/manual.md](docs/manual.md) | How to use every function, technical notes and limits |
| [docs/example-models.md](docs/example-models.md) | The bundled models and their verification values |
| [docs/known-issues.md](docs/known-issues.md) | Known bugs and observations |
| [docs/host-proposals.md](docs/host-proposals.md) | Ideas for IngeTrazo itself, found while working on Newton |
| [docs/backlog.md](docs/backlog.md) | Agreed follow-up work |
| [docs/test-results.md](docs/test-results.md) | Verification log per version |
| [docs/research.md](docs/research.md) | Original research on SketchyPhysics and IngeTrazo |
| [skills/ingetrazo-newton/SKILL.md](skills/ingetrazo-newton/SKILL.md) | Claude Code skill: modelling for Newton, grouping, performance, limits |
| [AGENTS.md](AGENTS.md) | Development setup, tests and conventions |

## Licence

GPL-3.0-or-later, see [LICENSE](LICENSE). MuJoCo and other dependencies are installed separately and keep their own licences. The packaged ZIP contains no Python or MuJoCo binaries.
