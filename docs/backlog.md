# Backlog

Planned work that is agreed but not scheduled yet. Remove an item when it is done.

## Virtual controls and key bindings

Agreed in [ADR 0001](adr/0001-virtual-controls.md); one step per item, in this order:

Virtual controls (switch and slider), key bindings (toggle, step), the *Key bindings* sidebar section, the *Key slots* preferences tab and the sidebar note for managed axes are done. Remaining:

1. Trigger mode *momentary* (key value while the key is held, rest value after). Deferred from the key bindings: the key slots are host shortcut actions, and a `QAction` shortcut only reports the press, never the release. Detecting the release would need an application-wide key event filter beside the host's shortcut handling; do not build it that way. Revisit when the host offers press and release for shortcut actions.

## Control panel redesign

The redesign is built: the control panel is a bottom dock with one strip per control, and the virtual control and key binding editors expand in the strips (per-state remove and the accent-coloured pressed button are part of it). What is still open:

- Key binding fields (expanded rows, *Key slots* tab): check live. Untested on screen: the captions above the fields ("Set to", "Back to", "Step", "Down key"), the key caps, and the slot names and labels staying identical in every list after a label or key change.

## Idea: sequence editor with a timeline for controls and scripting

Status: idea, not agreed or scoped. The control panel's strips sit in one column grid, so a timeline lane can later be added as a further column beside them. Virtual controls and the scripting boundary are decided in [ADR 0001](adr/0001-virtual-controls.md); the rest below records the wish so it can be refined later.

Today the controls (servo targets, motor speeds) are set by hand in the control panel while a simulation runs. A sequence editor would let the user plan and replay such movements.

- A timeline that shows every control and its value over time, in the manner of a video editor (DaVinci Resolve) or a music sequencer.
- Several sequences managed side by side, for example to test single objects or groups of objects in interaction with each other.
- Animations built from sequences: played once or looped, with parameterised control values.
- Scripting, which is a topic of its own, for example for buttons, switches or levers.
- Virtual controls built on top: one control such as "flap open/close" that drives one or more real controls to defined positions.

Open questions to settle before any work:

- Where sequences and scripts are stored; the virtual controls already use the document data (`plugin_data["newton"]`), which has room for them.
- Which scripting language; what it may touch is decided (control values only).
- How a timeline relates to the existing control panel, the per-axis targets and the servo/motor ramps (acceleration, deceleration).
- Whether playback must be deterministic and reproducible (fixed time step) so a sequence gives the same result every run.
- How much of this the IngeTrazo host offers for UI (timeline widget, extension API) and what Newton has to build itself; see `docs/host-proposals.md`.

## Idea: contact switch per body instead of exemption pairs

Status: idea, not agreed or scoped. Collision exemptions are pairs: to say "this part touches nothing but the ground" a model needs an exemption to every other body, n−1 pairs per body and n(n−1)/2 for a group of parts. The first version of `models/gear-train-carousel.igz` exempted 8 parts from each other (28 pairs) although only 6 pairs overlap; such cliques bloat the data and the sidebar list, and before the rims were limited to the exemption block they lit up the whole model on every selection.

- A body setting such as *Contacts: all bodies / ground only / none* that the worker maps to MuJoCo's `contype`/`conaffinity` bits (today every body uses `contype="2"` and `conaffinity` 2 or 3, see `worker.py`), with exemption pairs kept for single exceptions.
- Open: whether a third choice "only within its group" (contact groups by bit) is worth it, how it shows in profiles, and how it combines with the automatic exemption of a body and its reference body.
- `scripts/lab/needed_exemptions.py` already reports which exemptions of a model are needed along its motion; a sidebar action "remove exemptions that are never used" could build on it, but would need a simulation run.

## Idea: hide and unhide controls in the control panel

Status: idea, not agreed or scoped.

With many actuated axes the control panel gets long. A roller conveyor with 100+ velocity axes shows one strip per roller. The user should be able to hide controls and bring them back.

- Sidebar: a switch in the axis's motion section, for example "Show in control panel".
- Control panel: a hide button in each strip, and a toggle such as "Show hidden controls" to reach hidden strips again.
- Hiding changes the display only: drive, target, key binding and virtual control membership stay as they are, also while a simulation runs.
- The state is saved per axis in the `.igz`.

Open questions:

- Whether it also applies to virtual controls, and how it relates to an axis that a virtual control manages (those have no strip of their own).
- Whether many axes need a bulk action (hide all of a group, hide by name pattern) rather than one click each.

## Idea: contact solver settings for large clustered scenes

Status: idea, deferred on 6 November 2026; changes the friction model, so it needs a decision and regression tests first.

Measured with 200 free boxes that attract each other until they form one cluster (1,200 degrees of freedom, about 700–1,000 contacts): `mj_step` grows from 0.5 ms to over 30 s per eight-step batch, the real-time factor drops to 0. MuJoCo's Newton solver with the elliptic friction cone factorizes an almost dense 1,200 × 1,200 matrix in each of its iterations. Single `mj_step` at the same clustered state:

| Solver | ms per step | Iterations |
| --- | ---: | ---: |
| Newton, elliptic cone (current: `iterations="80"`, `cone="elliptic"`, `impratio="10"` in `worker.py`) | 146 | 20 |
| Newton, pyramidal cone | 22 | 20 |
| PGS | 12.7 | 80 (limit) |
| CG | 5.5 | 80 (limit) |

Possible directions: choose the cone or solver by model size or contact count, or expose it as a quality option. Open questions:

- How much the pyramidal cone changes sliding, rolling and grip results (impratio, gripper tests); CG and PGS hit the iteration limit, so their accuracy needs checking too.
- Which threshold (degrees of freedom, contacts) and whether the switch may happen during a run.
- Whether such clusters matter outside synthetic attraction tests (bulk material, many loose parts).

A second reason, found on 10 November 2026: gears that drive each other through tooth contacts (`models/gear-train-carousel.igz`) blow up with the Newton solver and run cleanly with PGS, at about 130× real time. Since then *Contact solver* (*Standard* or *PGS*) can be chosen in the preferences as a default and per model. Still open here: an automatic choice by model size or contact count, and whether CG or the pyramidal cone belong in the list.

## Idea: display rate setting for the simulation

Status: idea, requested on 6 November 2026; not scoped.

While a simulation runs, every worker result is applied to the view: `Session.apply()` raises `scene.version`, and the host rebuilds its consolidated buffers (17–31 ms per frame on the crank drive and CR10 models, see [known-issues.md](known-issues.md), "Every simulation frame rebuilds the viewport caches"). The display therefore settles at about 30 frames per second as a side effect, not as a deliberate limit.

- A Newton preference *Display rate* (for example 30, 60 or unlimited frames per second; suggested default 60) that limits how often poses are applied to the view. The worker keeps simulating at full rate and real-time pacing is unchanged; only the redraw is throttled.
- Halving the display rate halves the buffer rebuilds and frees GUI time for input and the control panel, already with the pinned host.
- Stays useful after the host proposal "Display transforms without changing the scene" lands, as a way to save power or GPU time.

Open questions:

- Whether the latest pose is applied when the simulation pauses or resets, so the view never shows a stale frame.
- Whether telemetry and the control panel follow the display rate or keep their own update rate.
- Where it lives: *Preferences → Simulation* next to *Quality*, or the control panel's *Options* menu.
