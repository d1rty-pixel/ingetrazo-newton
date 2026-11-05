# Backlog

Planned work that is agreed but not scheduled yet. Remove an item when it is done.

## Warn about movable bodies that touch the z=0 plane

A movable body that lies on, partly below or across z=0 scrapes along the ground plane, which distorts the simulation result. This is easy to cause by accident.

- At simulation start, show a warning in the control panel listing the affected bodies.
- Possibly also mark the affected bodies in the sidebar.
- Possibly offer an explicit check the user can run before starting.
- Make the warning switchable in the preferences.
- Open: whether bodies that only rest on z=0 (no overlap) count, and whether the warning blocks the start.
