# Backlog

Planned work that is agreed but not scheduled yet. Remove an item when it is done.

## Idea: sequence editor with a timeline for controls and scripting

Status: idea, not agreed or scoped. Nothing is decided below; it records the wish so it can be refined later.

Today the controls (servo targets, motor speeds) are set by hand in the control panel while a simulation runs. A sequence editor would let the user plan and replay such movements.

- A timeline that shows every control and its value over time, in the manner of a video editor (DaVinci Resolve) or a music sequencer.
- Several sequences managed side by side, for example to test single objects or groups of objects in interaction with each other.
- Animations built from sequences: played once or looped, with parameterised control values.
- Scripting, which is a topic of its own, for example for buttons, switches or levers.
- Virtual controls built on top: one control such as "flap open/close" that drives one or more real controls to defined positions.

Open questions to settle before any work:

- Where sequences and scripts are stored (in the `.igz` next to the model data, like the other `group.ext["newton"]` data, or beside it) and how they are versioned and undone.
- Which scripting language and what it may touch (controls only, or the whole model); this is a security and data boundary and needs a decision, not a default.
- How a timeline relates to the existing control panel, the per-axis targets and the servo/motor ramps (acceleration, deceleration).
- Whether playback must be deterministic and reproducible (fixed time step) so a sequence gives the same result every run.
- How much of this the IngeTrazo host offers for UI (timeline widget, extension API) and what Newton has to build itself; see `docs/host-proposals.md`.
