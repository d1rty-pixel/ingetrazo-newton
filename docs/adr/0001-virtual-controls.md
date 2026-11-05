# ADR 0001: Virtual controls

- **Status:** accepted
- **Date:** 2026-11-05
- **Scope:** first step of the "sequence editor, scripting and virtual controls" idea in [backlog.md](../backlog.md)

## Context

The control panel shows one card per actuated joint (servo, position drive, motor). Each card sets that joint's target; the session sends all targets with every step (`Session.targets`, `newton/session.py`), and the worker ramps towards them (`World.step`, `newton/worker.py`). Couplings tie follower axes to a leader in the solver with a fixed ratio.

Users want controls that mean something in the model ("flap open/closed", "gripper"), drive several joints to defined positions at once, and can be operated from the keyboard. Later, a sequence editor and scripts should be able to operate the same controls.

## Decision

### Virtual controls

A virtual control has a name, a kind, a list of joints and a list of **states**. Each state holds one target value per joint. There are two kinds:

- **Switch:** the value is a state index. Setting it moves every joint to that state's values. Two states (on/off, open/closed) are the normal case; more states make a multi-position switch.
- **Slider:** the value is a position from 0 to 1 (shown as 0–100 %) along the states, interpolated linearly between neighbouring states placed at equal steps. Two states give "from – to"; more states give a piecewise-linear path.

One data model covers both kinds; the kind only decides whether the value is discrete or continuous. A virtual slider adds value over the joint's own slider because it moves several joints with their own values and ranges under one name, which a coupling (fixed ratio, leader drives the force) does not cover.

Each control stores an **initial value** (state index or position). At Start it overrides the start targets of its joints.

### Rules

- A joint can belong to at most one virtual control. The editor offers only free joints; a document that breaks the rule anyway fails at Start with a message, like an invalid coupling.
- Only joints with a control of their own qualify: no free (passive) joints and no coupling followers. A coupling leader qualifies; its followers move with it.
- Joints that a virtual control manages get no card of their own in the control panel.
- A joint that no longer exists (body deleted, copy with a new ID) is ignored at Start and shown as missing in the editor.
- Values are stored in SI units (radians, metres, per second for motors) like every other Newton value; the editor shows them in the joint's display unit.

### Storage

The controls are document data, not body data: they span several bodies. They live in the host's extension document data (`ExtensionApp.document_data()` / `set_document_data()`, stored as `scene.plugin_data["newton"]` in the `.igz`). Each change is one undo step through the host's `SetPluginDataCommand`.

```json
{"controls": [
  {"id": "3f9c…", "name": "Flap", "kind": "switch",
   "joints": ["<group uid>", "<group uid>"],
   "states": [{"name": "Closed", "values": [0.0, 0.0]},
              {"name": "Open", "values": [1.5708, 0.02]}],
   "initial": 0}
]}
```

`controls` is one key in a dictionary so that later data (sequences, key assignments) can sit beside it.

### Resolution

The main process turns control values into joint targets (`Session.set_target` for each joint). The worker and its protocol do not change: it still receives one target per joint and ramps towards it.

### Editing

Controls are created and changed in an editor dialog opened from the control panel. It is a separate window for now, so it does not depend on the planned control panel redesign. Like the sidebar, it is disabled during a simulation (the simulation's history refuses every command).

### Boundaries for later steps

These are decided now so that the first step does not block them:

- **Scripting:** a script may only read and set control values (virtual and real). It may not change the model, the document or files.
- **Sequences:** a sequence sets control values over time; it does not address joints directly.
- **Key bindings:** a list of key slots in the preferences (five by default, more can be added, no fixed upper limit; a sanity limit of 999 applies when reading the settings). The keys are a user setting (QSettings); which slot operates which control is stored in the document. Every control, virtual or real, gets a trigger mode: **toggle** (switch between its rest value and its key value), **momentary** (key value while the key is held, rest value after) or **step** (each press changes the value by a step, a second slot for the opposite direction).
- **Sidebar:** a joint managed by a virtual control says so in the sidebar, with a button that opens the editor on that control.
- **Keep pose on stop:** a control panel option that writes the simulated poses back into the document instead of restoring them. It changes the model and therefore needs its own design (one undo step, start angles, the simulation's edit guard).

## Alternatives considered

- **Resolve virtual controls in the worker.** Rejected: the worker would need the mapping and a new protocol message, and the main process already owns the targets.
- **Store the control on one of its bodies (`group.ext["newton"]`).** Rejected: a control spans several bodies and would be lost or duplicated when that body is deleted or copied.
- **A slider as a linear map per joint (`target = a·v + b`).** Rejected in favour of states: the user enters the positions they want ("open", "closed") instead of factors, and a slider and a switch share one editor.
- **Waiting for a host timeline or control API.** Rejected: Newton is developed against the pinned host only.

## Consequences

- **Behaviour:** documents without virtual controls behave as before. A document with virtual controls shows them in the control panel above the joint cards; the managed joints' own cards disappear.
- **Risks:** a joint's start target in the sidebar is overridden by its virtual control's initial value; the sidebar note (later step) makes that visible. Copying a body gives it a new ID, so the copy is not part of the original's control.
- **Rollout:** in the next release; no migration, the data is new.
- **Rollback:** remove the feature; documents keep an unused `plugin_data["newton"]` entry that the host ignores.
- **Tests:** validation and resolution as pure functions; session targets at Start and on change; the control panel cards; editor round trip with undo; `.igz` save and load.

## Addendum 2026-11-05: switches that move their axes one after another

A switch can set `"sequential": true` (editor: *Move the axes one after another*). The session then sets the first axis's target and each next one when the previous axis's ramp has reached its target (the worker's `command` equals its `target`), in the order of `joints`. The ramp, not the measured position, decides, so no settling tolerance is needed. Switching again drops the rest of the old order; the initial state at Start applies at once. The worker protocol stays unchanged. Sliders ignore the option. Arriving together (stretching the faster axes' ramps) was discussed as a third mode and is not built; it would need a per-axis ramp factor in the worker protocol.
