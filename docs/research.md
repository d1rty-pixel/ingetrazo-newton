# Newton — Research on SketchyPhysics and IngeTrazo

As of 3 November 2026. Research and source code analysis, no runtime test yet and no implemented physics extension.

Addendum on the subsequent implementation: Newton has since been implemented; see the [manual](manual.md). MuJoCo 3.3.7 is used as the backend, after installing PyBullet failed for lack of official Windows binary packages and C++ build tools. The following sections record the original state of the research.

## Result

A functional re-implementation is technically plausible. A physics engine of our own is not required for it. IngeTrazo provides model geometry, components, a Python/Qt user interface and extension points. An additional engine computes motion and contacts. The real development work lies in the adapter, in the operation and in a reliable simulation inside the modelling program.

The examined public IngeTrazo source state is `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`, which is also release v0.6.0 of 1 November 2026. A local reference copy is in `ingetrazo-source/`. The architecture proposed here is a conclusion from the source code, not an already proven product feature. [Release](https://github.com/ingelibre/ingetrazo/releases/tag/v0.6.0)

## What defines SketchyPhysics

SketchyPhysics combines grouped 3D objects with interactive rigid-body physics. Central are start/pause/reset, an inspector, connected joints and direct dragging during the simulation. Bodies can be static, frozen, ignored or without collision. Controls include sliders, inputs and formulas. Added to that are thrusters, magnets, emitters and a buoyancy plane. The documented joints comprise hinge, servo, motor, slider, piston, gyro, fixed, corkscrew, spring, ball and universal. [Historical project FAQ](https://community.sketchucation.com/topic/111111/sketchyphysics3-faq)

Later versions added or improved compound collision bodies, convex hulls, static meshes, centre-of-mass/mass functions, continuous collision detection, contact events and recording including the camera. The authors also document problems with scaling and mirrored bodies: these cases explicitly belong in our adapter test. [Developer post on 3.5.6](https://community.sketchucation.com/topic/147275/sketchyphysics-3-5-6-26-january-2015)

The project page names 3.7.4 of 26 November 2017 as the latest state and restricts it to 32-bit SketchUp. Raycasts, impulses, script functions and sound are documented there as well. MSPhysics is an independent successor with a different scope; its 14 joint types must not be taken wholesale as original SketchyPhysics functions. [SketchyPhysics project page](https://sketchy-physics.github.io/page/index.html), [MSPhysics by its developer](https://github.com/AntonSynytsia/MSPhysics)

## What IngeTrazo provides

The documented extension API is version 2 and subject to change during 0.x. The entry point is `setup(app)`. Relevant functions are:

| Need | Existing access |
|---|---|
| Inspector and control panel | `add_panel`, own Qt widgets and dialogs |
| Commands and context menus | `add_menu`, `add_menu_action`, `add_context_menu` |
| Parameters in the project | `document_data`, `set_document_data` |
| Parameters on the body | `group.ext[app.key]` |
| Joint markers | `add_overlay`, `world_to_pixels`, `add_pickable` |
| Placement | `add_snap_provider`, tool base class |
| Document switching | `on_document_changed`, `on_document_closed` |
| Separate simulation scene | `enter_workspace`, `leave_workspace` |

Model changes should go through the history. Background computation must not change the document directly; results must be passed back to the GUI thread. Menu tools are activated as one-shot actions: an interactive joint tool additionally needs a suitable activation in the viewport. [Plugin guide](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/docs/plugins.md), [ExtensionApp](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/views/extension_api.py), [Tool base](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/tools/base.py)

The examined core and the runtime dependencies contain no rigid-body engine. Components, however, have transformation matrices (`xform`); groups have persistent `uid` identifiers. Both are suitable for the mapping between model and engine. Classic groups and instances treat their geometry differently. The adapter must therefore unify local coordinates, nested transformations and body centres of mass. [Group implementation](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/core/group.py), [Dependencies](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/requirements.txt)

### The decisive rendering boundary

`add_overlay` is a QPainter overlay on top of the image. It is not a general 3D renderer with depth testing. It is suitable for labelled joints; on its own it is not suitable for many shaded physics bodies.

The viewport internally has `begin_groups_preview` and `set_groups_preview_matrix`. They combine the selected bodies and draw them with a shared preview matrix. That solves a shared translation or rotation, but not independent poses of many bodies. I did not find a publicly documented batch interface for temporary individual transformations in the examined state. [Viewport, from line 6694](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/views/viewport.py#L6694)

Proposal: on start, create a simulation scene of its own and show it in the workspace. Update only its component matrices; the original model stays parked. On reset the workspace is left. An action "Take over pose" writes the chosen end position into the original as one undoable step. The workspace protocol supports this separation in principle. Cache refresh, picking and speed of the moving scene must be verified in practice. The workspace alone is not yet a fast animation interface.

## Feasibility matrix

The ratings mean: technically representable with an additional engine or custom extension code. They are no promise that IngeTrazo already contains these functions.

| Function family | Assessment | Required implementation |
|---|---|---|
| Falling bodies, contacts, gravity | Good | Engine, body adapter, position transfer |
| Mass, friction, bounce, damping | Good | Physics parameters and inspector |
| Static, ignored, no collision | Good | Body mode and collision filter |
| Frozen/sleeping and waking | Good, agree semantics | Engine activation and triggers |
| Box, sphere, cylinder, capsule | Good | Primitive collision shapes |
| Convex and compound bodies | Good, extra effort | Hulls or decomposition; own collision preview |
| Arbitrary moving concave meshes | Laborious | Engine-appropriate decomposition; do not close holes with a single hull |
| Static environment | Good | Triangle mesh or simplified colliders |
| Hinge, motor, servo | Good, check backend | Revolute joint plus speed/position control |
| Slider, piston, spring | Good, check backend | Linear joint, drive, spring and damping |
| Ball, universal, corkscrew, gyro | Feasible, more laborious | Suitable constraints or their combination |
| Fixed and breakable connection | Feasible | Connection plus load threshold and release |
| Thrust and magnet effects | Good | Custom force models on the engine |
| Emitter | Feasible | Body lifecycle, copies, limits and display |
| Buoyancy | Feasible, additional logic | Displacement approximation and forces; own fluid simulation unnecessary for a simple plane |
| Mouse dragging | Feasible | Picking, target point and temporary spring/pull constraint |
| Keyboard, sliders, gamepad | Feasible | Input routing; connect gamepad separately |
| Scripts and contact events | Feasible | Own Python event interface |
| Replay and animation export | Feasible | Record poses; integrate image/video export separately |
| Existing SketchyPhysics models | Not automatically compatible | Separate metadata import and translation; Ruby/SketchUp code needs porting |

In particular: opening geometry from a `.skp` does not mean that joints, physics attributes or Ruby scripts then work. No existing SketchyPhysics importer was found for this.

## Ready-made physics engines

### Bullet / PyBullet as the first prototype candidate

Bullet is a ready-made physics engine; PyBullet provides Python access. This removes the need to develop a contact solver, collision detection and basic dynamics. The official example also demonstrates changeable constraints. [Bullet project](https://github.com/bulletphysics/bullet3), [constraint example](https://github.com/bulletphysics/bullet3/blob/master/examples/pybullet/examples/constraint.py)

My recommendation is to try PyBullet first as an exchangeable backend. Important: "Bullet supports joints" does not guarantee that the Python interface offers every connection created freely in the model directly. Freely connected individual bodies, closed mechanisms, motors and spring behaviour must be checked as concrete cases. If the bindings restrict this, another backend or a native bridge may make more sense.

### MuJoCo as an alternative for mechanisms

MuJoCo has joints, actuators and additional bindings. Its model is fundamentally organised as a body tree; several primitive joints can form compound mobilities. Freely assembled mechanisms and loops need a deliberate translation. [Official modelling documentation](https://mujoco.readthedocs.io/en/stable/modeling.html)

This makes MuJoCo a serious comparison candidate if motorised mechanics become more important than freely addable play objects. The final choice should follow small functional tests, not the feature lists alone.

### What we have to "teach" the engines

1. Which model group is which body and whether it is movable.
2. Which simplified collision shape is used. Visible geometry and collision geometry may differ.
3. Mass, centre of mass, inertia, material parameters and initial velocity.
4. Which two bodies a joint connects; local anchors, axes, limits and drive values.
5. Conversion of the engine pose back into the model transformation. Centre of mass and model origin are often different.
6. Behaviour of start/pause/reset, inputs, stored parameters and replay.

Proposal: use SI units, fixed physics steps with a time accumulator and a frame update separate from it. Store new body data and joints, but keep running engine handles and every time step in memory only. Copied bodies need their own identities and correctly reassigned joint references.

## Installing and testing locally

### With an installed Windows version

1. In IngeTrazo open `Extensions → Open plugins folder`.
2. Place a single `.py` or a package directory there.
3. For a package, `__init__.py` must lie directly in the package folder, for example:

```text
%APPDATA%\ingetrazo\plugins\
  newton\
    __init__.py
    panel.py
    adapter.py
    backends\
      __init__.py
      bullet.py
```

4. Restart IngeTrazo completely. For local development a ZIP is unpacked beforehand; an additional outer ZIP folder prevents detection.
5. Load errors appear in the Extensions menu; full errors are in the log. A `.disabled` marker in a package prevents its loading.

Detection happens at start. There is no documented general hot reload. Packages should use relative imports: the loader uses private module names and does not add the plugin folder to `sys.path` globally. No catalogue entry is needed for private tests. [Loader source code](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/core/extensions.py)

### Development environment from the source code

For a native Python backend, an own Python environment is the most convenient at first. The Windows build uses Python 3.12. Example after installing Python 3.12, in the folder `ingetrazo-source`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Only for the PyBullet prototype:
.\.venv\Scripts\python.exe -m pip install pybullet
.\.venv\Scripts\python.exe main.py
```

These commands were not run here. Dependencies and matching wheels must be checked before the first run. Your own plugin code can be placed under `<app>/plugins/` for this development instance; avoid identical plugin names in the user folder, because the bundled one is found first. The Python console in IngeTrazo (`Ctrl+Shift+P`) is suitable for small geometry and API experiments. [Start from source](https://github.com/ingelibre/ingetrazo/tree/v0.6.0), [Windows build](https://github.com/ingelibre/ingetrazo/blob/v0.6.0/.github/workflows/build-windows.yml)

A `pip install` in this environment installs nothing into the Python runtime of an already packaged IngeTrazo EXE. For later delivery you need either matching bundled native modules including libraries or a separately started physics process. The latter can reduce the Python/ABI dependency on the host, but requires a process interface. The plugin system currently documents no ready-made general dependency installer.

## A sensible first implementation

Before a large re-implementation, three technical probes should be completed:

1. **Display:** 50 independently moving components in a simulation scene; reset, project switching and return to the original work. Measure the frame rate, do not promise one in advance.
2. **Mechanics:** connect two freely selected bodies with a hinge; add motor and servo. Additionally check a closed four-bar mechanism. This decides the engine bindings.
3. **Installation:** the same prototype runs both from source and with the installed Windows version including the physics dependency.

Then, as the first usable version: static ground, dynamic groups, box/sphere/convex hull, mass/friction/bounce, start/pause/reset, an inspector and hinge/motor. A tower of falling cubes, a pendulum and a driven wheel form concrete acceptance scenes. Piston, spring, mouse dragging and replay follow afterwards. Magnetism, emitters, buoyancy and script compatibility should be added only after a stable foundation.

The biggest open point is thus the robust integration into IngeTrazo: display, inputs, document lifecycle and delivery. The basic physics can be taken over by ready-made libraries.
