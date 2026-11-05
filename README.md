# Newton

[![Release](https://img.shields.io/github/v/release/d1rty-pixel/ingetrazo-newton)](https://github.com/d1rty-pixel/ingetrazo-newton/releases)
[![Licence](https://img.shields.io/github/license/d1rty-pixel/ingetrazo-newton)](LICENSE)
![IngeTrazo](https://img.shields.io/badge/IngeTrazo-0.6.0-blue)
![Extension API](https://img.shields.io/badge/Extension%20API-2-blue)
![MuJoCo](https://img.shields.io/badge/MuJoCo-3.3.7-informational)
![Python](https://img.shields.io/badge/Python-3.12-informational)
[![Linux Flatpak: tested](https://img.shields.io/badge/Linux%20%28Flatpak%29-tested-success?logo=flatpak&logoColor=white)](#platform-status)
[![Windows: tested](https://img.shields.io/badge/Windows-tested-success?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0yIDMuNSAxMC41IDIuM3Y4LjlIMnpNMTEuNSAyLjIgMjIgLjd2MTAuNUgxMS41ek0yIDEyLjJoOC41djguOUwyIDE5Ljl6TTExLjUgMTIuMkgyMnYxMC41bC0xMC41LTEuNXoiLz48L3N2Zz4%3D)](#platform-status)
[![macOS: not tested](https://img.shields.io/badge/macOS-not%20tested-lightgrey?logo=apple&logoColor=white)](#platform-status)
[![Linux AppImage, tarball: not tested](https://img.shields.io/badge/Linux%20%28AppImage%2C%20tarball%29-not%20tested-lightgrey?logo=linux&logoColor=white)](#platform-status)
[![Linux Snap: not tested](https://img.shields.io/badge/Linux%20%28Snap%29-not%20tested-lightgrey?logo=snapcraft&logoColor=white)](#platform-status)

Newton is a physics extension for the 3D modeller [IngeTrazo](https://github.com/ingelibre/ingetrazo). It picks up the idea of SketchyPhysics: the groups and components of a model become bodies that fall, collide, rotate or slide on axes and are driven by motors. The simulation runs directly in the model and can be reset to the original state at any time.

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

## Quick start

1. In IngeTrazo open **Extensions → Manage extensions…**, search for **Newton**, press **Download** and restart IngeTrazo. (Not listed yet? Install it by hand: [docs/installation.md](docs/installation.md).)
2. Open **Preferences → Newton → Runtime** and press **Set up runtime**. This downloads a Python 3.12 with MuJoCo 3.3.7 once, after you confirm. Newton starts the physics in this separate Python; IngeTrazo does not ship one. Manual and command-line alternatives: [docs/runtime-setup.md](docs/runtime-setup.md).
3. Open **Extensions → Newton…** and follow *Getting started* below.

## Platform status

| Platform | Status |
|---|---|
| Linux, IngeTrazo Flatpak | tested |
| Windows (installer or portable zip) | tested on Windows 11: release zip, scripts, runtime setup (button, command line, manual), simulation |
| macOS | not tested |
| Linux AppImage, tarball | not tested |
| Linux Snap | not tested; plugin folder not verified |

## Getting started

1. Select a group or component.
2. In the **Newton Tools** toolbar, click **Rotation axis** or **Linear axis**.
3. In the model, click the pivot or start point, then click the direction or press **X**, **Y** or **Z**. **Esc** cancels.
4. In the Newton sidebar, set the behaviour and the drive. Changes apply immediately and can be undone.
5. Press **Start**. Drag passive bodies with the left mouse button and move actuators with the control panel. **Reset** restores the original model.

Ready-made examples are in [`models/`](models) and described in [docs/example-models.md](docs/example-models.md).

## AI skill

[`skills/ingetrazo-newton/`](skills/ingetrazo-newton/SKILL.md) is an Agent Skill that an AI assistant (Claude Code, Codex) loads by itself when you ask about modelling for Newton: objects, grouping for correct and fast simulations, performance and limits. Installation and checking: [docs/ai-skill.md](docs/ai-skill.md).

## Documentation

| Document | Content |
|---|---|
| [docs/installation.md](docs/installation.md) | Installing the extension: extension library, manual per platform, release zip, update, verification |
| [docs/runtime-setup.md](docs/runtime-setup.md) | The runtime (Python 3.12 + MuJoCo): button, command line, manual per platform, troubleshooting |
| [docs/manual.md](docs/manual.md) | How to use every function, technical notes and limits |
| [docs/example-models.md](docs/example-models.md) | The bundled models and their verification values |
| [docs/known-issues.md](docs/known-issues.md) | Known bugs and observations |
| [docs/host-proposals.md](docs/host-proposals.md) | Ideas for IngeTrazo itself, found while working on Newton |
| [docs/backlog.md](docs/backlog.md) | Agreed follow-up work |
| [docs/lab/test-and-measurement-runs.md](docs/lab/test-and-measurement-runs.md) | Recorded test suite runs, benchmarks and manual checks, per feature and release |
| [docs/lab/sketchyphysics-port-research.md](docs/lab/sketchyphysics-port-research.md) | Original research on SketchyPhysics and IngeTrazo |
| [docs/ai-skill.md](docs/ai-skill.md) | Using the skill with Claude Code and Codex |
| [skills/ingetrazo-newton/SKILL.md](skills/ingetrazo-newton/SKILL.md) | The skill itself: modelling for Newton, grouping, performance, limits |
| [scripts/README.md](scripts/README.md) | Helper scripts: install, package, developer tools, example model builders, measurements |
| [AGENTS.md](AGENTS.md) | Development setup, tests and conventions |

## Licence

GPL-3.0-or-later, see [LICENSE](LICENSE). MuJoCo and other dependencies are installed separately and keep their own licences. The packaged ZIP contains no Python or MuJoCo binaries.
