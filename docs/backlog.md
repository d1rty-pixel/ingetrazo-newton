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
