---
name: ingetrazo-newton
description: How to build, configure and speed up physics models with Newton, the MuJoCo-based physics extension for the 3D modeller IngeTrazo — bodies, axes, reference bodies, connections, couplings, ropes/cables, controls, how to group parts so the simulation is correct and fast, performance options and limits. Trigger when a user models a mechanism for Newton, asks why a Newton simulation behaves oddly or runs slowly, or inspects `group.ext["newton"]` in an `.igz`. Skip for plain IngeTrazo modelling without physics and for developing the extension itself (see AGENTS.md in the repository).
---

# Newton for IngeTrazo

Newton turns the top-level groups and components of an IngeTrazo model into rigid bodies and simulates them with MuJoCo 3.3.7 in a separate Python process. Start builds a temporary simulation that shares the model's geometry and refuses every edit; Reset discards it. The document is never changed by a simulation. Full manual: `docs/manual.md`; example models: `models/` and `docs/example-models.md`.

## Objects and what they do

| Object | Set in | Effect |
|---|---|---|
| **Body** | sidebar → Generic | Every top-level group/component. **Movable** (dynamic), **Fixed** (anchored to the world, or bolted to its reference body) or **Exclude from simulation** (shown, never collides). Unconfigured groups are **fixed colliders**; face-me figures are ignored. |
| **Collision shape** | Body & contact | **Box** and **sphere** enclose the body's world bounding box at setup. **Hull** is the convex hull of all vertices (fills openings). **Child components** builds one hull per child group (max. 256), so openings stay open. Hulls with eight cuboid corners become exact boxes. |
| **Axis** | toolbar Rotation/Linear axis | One hinge or slide joint per body, relative to its reference body or the world. Drive: **Free**, **Servo/Position** (target, holds it) or **Motor/Speed**; limits with a limit hardness (0–100 %, default 100 % = hard stop), start target, speed, acceleration, deceleration, force limit. Angles count from the axis's 0° direction (set when placing); a used limit range must contain the modelled pose. Also an object **Axis · <body>** on layer `Newton Axes`: move/rotate it with IngeTrazo's tools to move the axis. |
| **Reference body** | chain icon | Parent of a body. Without an axis the child is **rigidly attached** (no extra degree of freedom); with an axis it moves only along that axis. Directly linked bodies never collide with each other. At most one parent; loops are rejected. |
| **Connection** | Ball / Pin / Fixed connection | Extra constraint between two bodies that closes a loop (crank, four-bar) without changing the reference tree. Shown as **Connection · <body>** on `Newton Axes`. |
| **Axis coupling** | Axis coupling → Follow axis | A position axis follows a leader of the same type with ratio and direction (gripper jaws). One level only. |
| **Rope / Cable** | Flexible material | A group made of an open polyline becomes an inextensible strand (MuJoCo `elasticity.cable`); start clamped/hinged/free, end attachable to a body. |
| **Collision exemption** | Body & contact | A pair of bodies may penetrate each other. |
| **Simulation overrides** | Simulation overrides | Per-body gravity vector, damping, ground on/off, attraction field (μ = G·m), initial velocity. |
| **Profiles** | Profile / Preferences → Profiles | Reusable body and drive values; bodies remember the profile and show sync state. |
| **Controls** | control panel | One card per actuated axis (named by the control name). Passive bodies are dragged with the left mouse button during the simulation; actuated ones only through their control. |

Data model (for reading `.igz` files or scripts): everything lives in `group.ext["newton"]` — `mode` (`dynamic`/`static`/`ignore`), `shape` (`box`/`sphere`/`hull`/`compound`), `mass`, `friction`, `restitution`, `reference`, `joint` (`type` `hinge`/`slide`, `pivot`, `axis`, `drive` `free`/`velocity`/`position`, limits in radians/metres, `limit_hardness` 0–1), `point_attachment` (connection), `no_collision`, `flexible`, `simulation_override`. Axis and connection objects carry `axis_of` / `connection_of` and only mirror this data. Prefer changing models through the Newton UI: it keeps axis objects, reference tracking and undo consistent; editing `ext` directly bypasses them.

## Grouping parts for a good and fast simulation

1. **One top-level group per rigid part that moves as a unit.** Screws, nuts, labels and small details belong *inside* the part's group, not next to it. Every top-level group is a body; nested geometry merges into its collider.
2. **Decoration and reference geometry out of the simulation.** Set it to **Exclude from simulation**, or put it on a layer and hide that layer (see hidden geometry below). Unconfigured top-level groups silently become fixed colliders — an imported assembly with hundreds of loose parts creates hundreds of colliders.
3. **Pick the cheapest shape that is still correct.** Box/sphere for blocks and balls; hull for convex parts; **Child components** only where an opening or concavity matters (frames, U-channels, drawers, trays) — and then with few, roughly convex children. A long part rotated at setup gets a fat box (world bounding box), so use hull for slanted parts.
4. **Rigidly mounted parts as reference children without axis**, not as separate bodies with fixed connections: they add no degrees of freedom and are exempt from colliding with their parent. Use connections only to close real loops.
5. **Keep the reference tree shallow and acyclic**; close each mechanical loop with one connection — extra ones over-constrain it.
6. **Model at real scale in metres** with realistic masses in kg; very light parts carrying very heavy ones make the solver converge slowly.
7. **Static environment as few, simple bodies** (floor plate, frame as one compound), or use the built-in ground at Z = 0.
8. **Separate touching parts that should not interact** with a collision exemption instead of relying on tiny gaps.

## Performance

Where time goes (measured, see `docs/lab/test-and-measurement-runs.md` and `docs/known-issues.md`):
- **Start:** `prepare()` (`newton/model.py`) shares each included group's mesh and nested placements, but reads every vertex for the bounds and collision shapes; cost grows with vertex count. A model with ~250 000 vertices needs under 1 s.
- **Simulation:** almost entirely MuJoCo's constraint solver. It grows with contacts, closed loops (connections), couplings and cable segments. Python overhead in the worker is about 1 %.
- **Display:** every frame redraws all moving bodies; the host rebuilds its buffers (15–30 ms per frame with 100+ bodies).

What helps, most effective first:
- **Hide what you do not need to see.** With *Preferences → Newton → Simulation → Hidden geometry → Include: When needed* (default), hidden bodies are left out unless a visible body depends on them (reference body, attachment, connection, coupling); hidden fixed bodies stay as surroundings. Skipped bodies are not even copied. *Always* simulates everything hidden, *Never* drops all of it.
- **Fewer bodies, fewer contacts:** merge parts (rule 1), exclude decoration, add exemptions between parts that touch permanently.
- **Lower-poly collision geometry:** hulls of dense meshes start slower; a box or a coarse child component is enough for most parts.
- **Quality** (*Preferences → Newton → Simulation*): *Quick* for setting up big mechanisms, *Balanced* for daily work, *Precise* for demanding contacts. Large cable/chain models use the CG solver at Quick/Balanced.
- **Cables:** stiffer and finer cables force internal sub-steps; reduce stiffness or segment count first.
- The control panel shows the achieved **× real time**; its tooltip lists contacts, solver iterations, sub-steps and display time — check it before guessing.
- `scripts/benchmark_newton.py` measures the worker for a model without GUI (`--profile`, `--quality=`).

## Limits

- Bodies are top-level groups/components only; nested parts form one collider (except *Child components*).
- One incoming reference/axis per body; no closed reference chains, no ball or universal joint as an axis, coupling chains not supported.
- Box/sphere are enclosing approximations; hulls close openings; no automatic concave decomposition; compound mass is split evenly between children.
- Bounce is approximated by contact damping; the optional ground is an infinite plane at Z = 0.
- Ropes/cables are inextensible; no rubber stretching, breaking or soft bodies.
- No replay, magnetism, buoyancy or SketchyPhysics scripts; the simulated end pose cannot be taken over into the model.
- One simulation per window; no guaranteed frame rate for large models.
- Requires IngeTrazo 0.6.0 (Extension API 2) and a separate Python 3.12 with `mujoco==3.3.7` (set up under *Preferences → Newton → Runtime*).

## Troubleshooting

- **Nothing moves:** no body is movable, or the movable bodies are fixed to their reference body; a servo holds its target.
- **Mechanism locks:** a hull fills a gap (switch to Child components), a connection over-constrains the loop, or the start pose lies outside the limits.
- **A chain bends through its limits or its upper run sags:** the limit hardness of its axes is below 100 %; soft limits give way under the load of many light links.
- **Parts explode or jitter:** interpenetrating colliders at start, extreme mass ratios, or too stiff cables — check *Show collision shapes* (*Preferences → Newton → Appearance* or the Extensions menu command).
- **"The reference body is missing, hidden or excluded":** the parent is excluded or hidden while *Hidden geometry* is *Never*.
- **Slow start or low × real time:** see Performance; hide unrelated assemblies first.
