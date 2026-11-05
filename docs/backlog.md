# Backlog

Planned work that is agreed but not scheduled yet. Remove an item when it is done.

## Virtual controls and key bindings

Agreed in [ADR 0001](adr/0001-virtual-controls.md); one step per item, in this order:

Virtual controls (switch and slider), key bindings (toggle, step), the *Key bindings* sidebar section and the *Key slots* preferences tab are done. Remaining:

1. Sidebar note "managed by virtual control …" with a button that opens the editor.
2. Trigger mode *momentary* (key value while the key is held, rest value after). Deferred from the key bindings: the key slots are host shortcut actions, and a `QAction` shortcut only reports the press, never the release. Detecting the release would need an application-wide key event filter beside the host's shortcut handling; do not build it that way. Revisit when the host offers press and release for shortcut actions.

## Control panel redesign

Agreed, not designed yet. The control panel looks too technical; redesign it as a whole, including where the virtual control editor lives. Start with a draft before any code.

Points collected so far:

- Virtual control editor: *Remove state* removes the last state (or the column of a selected cell, which the value boxes rarely make current); the user expects to delete a chosen state. Give each state its own remove action.
- The pressed button of a virtual switch hardly stands out from the others (a slightly darker grey in the Qt style).
- Key binding fields (sidebar section, control cards, *Key slots* tab): check live after the redesign. Untested on screen: the captions above the fields ("Set to", "Back to", "Step", "Down key") in the narrow sidebar, the key caps, and the slot names and labels staying identical in every list after a label or key change.

## Idea: sequence editor with a timeline for controls and scripting

Status: idea, not agreed or scoped. Virtual controls and the scripting boundary are decided in [ADR 0001](adr/0001-virtual-controls.md); the rest below records the wish so it can be refined later.

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
