# Backlog

Planned work that is agreed but not scheduled yet. Remove an item when it is done.

## Warn about movable bodies that touch the z=0 plane

A movable body that lies on, partly below or across z=0 scrapes along the ground plane, which distorts the simulation result. This is easy to cause by accident.

- At simulation start, show a warning in the control panel listing the affected bodies.
- Possibly also mark the affected bodies in the sidebar.
- Possibly offer an explicit check the user can run before starting.
- Make the warning switchable in the preferences.
- Decided (2026-11-05): a body that only rests on z=0 (lowest point at z=0, no overlap) does not count; only bodies that reach below z=0 do. Fixed bodies and bodies whose ground contact is switched off (preference or simulation override) do not count either.
- Decided (2026-11-05): the warning only informs; it never blocks the start.
- Test model: [`models/z0-contact-test.igz`](../models/z0-contact-test.igz), see [example models](example-models.md#z0-contact-test-model).
