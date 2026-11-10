# Example models

The models are in [`models/`](../models). They can be opened directly in IngeTrazo. The scripts under `scripts/` regenerate some of them and open them in a test window of the development environment (see [AGENTS.md](../AGENTS.md)).

| Model | Shows |
|---|---|
| `domino-30.igz`, `domino-30-with-pendulum.igz` | Surface contacts, dominoes come to rest |
| `wrecking-ball-and-brick-wall.igz` | Pendulum on a passive revolute joint, collisions, 48 stacked bricks; good for screenshots |
| `joint-chain.igz` | Twelve rigid links with passive revolute joints |
| `industrial-robot-3-axis.igz`, `industrial-robot-rotary-gripper.igz`, `industrial-robot-synchronous-gripper.igz` | Rotation servos, control panel, axis coupling |
| `collision-test.igz` | Collision exemptions and convex hull |
| `crank-drive-energy-chain.igz`, `crank-drive-drag-chain.igz` | Motor, crank drive, cable in a chain |
| `drag-chain-with-cable.igz`, `rope-and-cable.igz` | Ropes and cables |
| `sun-and-planet.igz` | Attraction and initial velocity |
| `gear-train-carousel.igz` | A man turns a crank that drives a carousel through six gear types; motor as coupling leader, closed arm linkage |
| `z0-contact-test.igz` | Movable bodies that scrape along the ground at Z = 0 (test model for the ground contact warning) |

## Gear train with crank and carousel

In **gear-train-carousel.igz** a man turns a crank, and a gear train passes the motion on to a carousel. It contains six gear types, at most two of each: spur gears (40 and 16 teeth; the 16-tooth pinion is long and also meshes inside the ring gear), worm and worm wheel (30 teeth), ring gear (48 teeth, internal), and two bevel gears (36 and 11 teeth, 90° turn, 3.27:1 so the carousel turns faster than the ring gear). Module 20 mm, about 2.9 m high.

- The crank sits on the shaft of the large spur gear (body *Worm wheel + spur gear*) and is the only drive: a motor (control *Crank*) that runs without end. It starts at −15 °/s (one turn in 24 s), which is calm to watch and keeps the simulation rate steady; its speed limit stays at 143 °/s, so the control can turn it faster.
- The gears drive each other through their teeth: spur gear 40 → pinion 16 → ring gear 48 → bevel gear 36 → carousel bevel gear 11; the carousel turns 2.73 times as fast as the crank. The original bevel pair was 20:20; the 36:11 pair gives the carousel at the calm crank speed the pace it had at −49 °/s before. Its large gear sits closer to the carousel shaft and joins the ring gear's shaft through a spacer, the small one sits higher on the carousel shaft. Pinion, ring gear and carousel are free axes with no coupling. Every tooth is its own child group with an involute profile (20° pressure angle, 1 mm backlash), the internal teeth of the ring gear in two radial pieces and its rim in segments, the bevel teeth tapered towards the cone tip; the blanks keep their lightening holes. With the collision shape *Child components* MuJoCo sees one convex shape per tooth. The model's contact solver is *PGS* (sidebar section *Model*); with the standard solver tooth contacts are thrown apart.
- The worm is the exception: it follows the crank through an axis coupling (×30, 1.25 turns per second backwards at the start speed) and does not collide with the worm wheel. Driven backwards by the wheel, a worm with an 11° lead angle locks at a friction of 0.3, as a real one would, and its segmented thread runs rough at that speed. The thread and the worm wheel, whose teeth are cut by that thread like a hob cuts them, are modelled so they visibly mesh. The electric motor beside the worm is decoration.
- Only two pairs are exempt from colliding: the man with the crank shaft (he stands where it passes) and the worm with the worm wheel. The hand's ball connection keeps the forearm and the crank apart by itself.
- The man is fixed; his upper arm (axis *Shoulder*) and forearm (axis *Elbow*) are passive rotation axes, and the hand hangs on the crank handle with a ball connection. Crank, forearm, upper arm and frame form a crank-rocker four-bar linkage (crank 0.20 m, shoulder 0.52 m from the crank axis, arm 0.34 + 0.42 m): the crank turns fully while the arm swings, and the arm never straightens.
- Direction: seen from the front the crank turns anticlockwise, so the handle moves away from the man over the top and towards him at the bottom, and the carousel turns anticlockwise seen from above, with its horses facing forwards.

`scripts/models/gear_train_contact.py` rebuilds the gears from the coupled original (commit `d14a6de`) and measures the result; `--write` replaces the file. It finds each pair's tooth phase by turning the follower at the exact ratio and keeping the phase with the largest clearance (smallest clearance over a tooth pitch: spur 0.48 mm, ring gear 0.03 mm, bevel 0.24 mm, worm 0.08 mm), which also confirms the ratios of the original couplings up to the ring gear.

Checked headless with the worker (12 s, quality Balanced, PGS) at the start speed: the crank holds −0.262 ± 0.001 rad/s, the pinion turns at 0.655 ± 0.009, the ring gear at 0.218 ± 0.003 and the carousel at 0.714 ± 0.013 rad/s (41 °/s). Contacts occur only between meshing teeth, with at most 0.02 mm penetration, and the worker runs at about 50× real time. With the original 20:20 bevel pair and −2.5 rad/s the gears held the ratios of the couplings (crank −2.500 ± 0.006, carousel 2.084 ± 0.014 rad/s, 0.2 mm penetration, about 45× real time); the hand stays within 0.11 mm of the handle.

## Wrecking ball and brick wall

**wrecking-ball-and-brick-wall.igz** (generated by `scripts/models/wrecking_ball.py`) shows in one picture what Newton can do: a yellow gantry carries a 25 kg steel ball on a passive revolute joint (axis Y, no drive, no limits). It is modelled swung back by 58° and hits a wall of 12 × 4 bricks in running bond after about 0.6 s. The check confirms that the wall stands until the impact (< 3 mm of motion after settling) and that after 5 s 33 of 48 bricks have moved more than 30 cm. The ball is computed as a convex hull including the rod, the bricks as cuboids.

For a screenshot: open the model, start Newton, pause after about 0.8 to 1.2 s and point the camera obliquely from the front at the gantry and the wall. The default viewport of the development environment does not render under offscreen Qt, so the picture has to be taken in a real IngeTrazo session.

## Crank drive with energy chain

The revised version **models/crank-drive-energy-chain.igz** replaces the overlapping closed channel pieces with 22 open links. Each link consists of two rounded side plates with hinge collars and two short crossbars; the plates alternate their lateral mounting plane. A link is a single rigid body with four collision shapes. Only directly connected bearing partners are exempt from mutual contact; contacts between non-adjacent links stay active. This follows the basic design of side plates and crossbars: [igus energy chain wiki](https://www.igus.eu/energy-chain/wiki).

The new collision shape **Child components** computes every directly subordinate group/component as its own convex sub-body. The openings between the parts stay free; no common hull is laid over the whole frame opening. The total mass is distributed over the sub-bodies. The collision display draws all sub-shapes. Without subordinate groups the selection is rejected with an understandable message.

The connecting rod now lies in a plane offset by 105 mm in front of the wheel on a lengthened crank pin with a retainer. Between the actual wheel body including the hub and the connecting rod there is 40 mm of axial clearance. The crank/piston geometry and the 300 mm stroke are kept. The force transmission still uses real joint and connection constraints.

In the four-second contact comparison the mean contact count drops from 78 to 47.6; the former chain-against-chain contacts disappear. The connecting rod/wheel pair already had a bearing collision exemption before and produced no active solver contacts, although its display overlapped. The new geometry removes this visible overlap. The comparison run needs 5.72 instead of 7.82 seconds for four simulated seconds on this machine; the 24-second check still confirms stroke and cable routing. The earlier model version is kept for comparison under its previous file name.

The two-second Newton comparison on the crank drive gave about **0.28× real time before**, **0.54× with Balanced** and **0.91× with Quick** on this machine. These are pure worker measurements; display, machine load and other models change the speed actually reached. `scripts/lab/benchmark_newton.py --quality=balanced` repeats the test. The full 24-second test with Balanced preserves the 300 mm stroke and the cable routing.

## Crank drive with drag chain

The additional model **crank-drive-drag-chain.igz** connects a fixed-mounted electric motor through its shaft to a spoked wheel. An outer crank pin and a passive connecting rod drive the crosshead with piston rod. The 300 mm stroke moves the upper run of the drag chain, which is held at the bottom. A continuous orange power cable runs from the socket through the chain and then back to the stationary motor via a free reserve loop. It is attached to the socket and the motor; the movable chain guide acts through contacts. The control panel contains **Drive shaft · Motor speed**; the piston has no drive of its own. The speed reacts to the mechanical load.

The 24-second check confirms at least one full wheel revolution, a stroke of about −136.6 to +163.4 mm and less than 0.1 mm deviation from the geometric crank equation. The axes are hidden at first. Version 0.10.1 transfers collision exemptions of a rope/cable to all its segments, for example for idealised plugs and bearing housings. Contacts in the actual drag chain channel stay active.

## Ropes, cables and joint chains

The three new models are in `models`:

- **rope-and-cable.igz**: two strands, each 2 m long and clamped at one end, with equal end weights. Orange shows the soft rope, blue the stiffer cable; both collide with the support.
- **joint-chain.igz**: twelve rigid links with passive revolute joints. This first joint chain moves in one plane; it does not compute freely interlocking metal rings.
- **drag-chain-with-cable.igz**: 22 rigid guide links with angle limits and a carriage with the position drive **Travel**. The orange cable is separately flexible and collides with the overlapping channel faces. Sides and webs are transparent so that it stays visible. The carriage connects both ends mechanically; the cable is not bound to every link. The model limits allow −150 to +250 mm, forward/backward travel between −100 and +200 mm is verified. Small load deviations of the real carriage value remain possible. The axes are on the initially hidden layer **Newton Axes**.

Opening a test window: `.venv\Scripts\python.exe scripts/models/flexible_demos.py carrier --existing --open` (instead of `carrier` also `rope` or `chain`). The test windows use normal gravity −9.81 m/s² and the modelled support. In regular IngeTrazo, check these values under **Preferences → Newton → Simulation** if the sun model with zero gravity ran before.

## Collisions test model

**`models/collision-test.igz`** shows three cases: a blue cube lands on a plate, an orange cube falls through its exempted plate down to the support. On a part with an opening, the convex hull shows the filled opening. Open with `python scripts/models/collision_demo.py --existing --open`.

## Z0 contact test model

**`models/z0-contact-test.igz`** collects the cases of the warning at Start about movable bodies that reach below the ground plane. Red bodies should be reported, green and grey ones not; the orange cube only rests on Z = 0 and does not count.

- Row along X, 10 cm cubes: resting on Z = 0 (orange), 2 cm below, centred on Z = 0, fully below Z = 0, 5 cm above (control); a fixed cube across Z = 0 (grey) and a weightless cube across Z = 0 with ground contact switched off (green).
- Two linear servos (2 kg, 0–500 mm along +X, 200 N, 100 mm/s), bottom 0.7 mm below Z = 0 and 5 mm above.
- Two rotation servos about Z (40 cm arm, ±90°), bottom 1 mm below Z = 0 and 5 mm above.

Checked headless with the worker (6 s, targets 500 mm and 1 rad): the scraping slider reaches 3 mm and the scraping arm 0.001 rad, the controls reach their targets; the cubes below or on Z = 0 are pushed up and come to rest on the ground, the fully sunk one jumps about 20 cm. The fixed and the weightless cube stay in place.

## Sun and planet

The test model [Sun and planet](../models/sun-and-planet.igz) contains two freely movable spheres with masses of 100 and 5 kg, a distance of 4 m and a deliberately enlarged G = 0.16 m³/(kg·s²). The orbital period is about 12.26 s. Both orbit their common centre of mass; the sun is not held in place. Gravity vector, ground and damping are switched off. `scripts/models/solar_system.py --existing --open` opens the model with these global defaults in its own test window. Both bodies additionally store zero gravity and switched-off ground as overrides, so the model also works with other global defaults.

## Industrial robot with synchronous gripper

The model **`models/industrial-robot-synchronous-gripper.igz`** has four rotation servos and a shared control **Gripper opening**. It shows the distance of the jaws in millimetres: 105 mm open to 5 mm closed. Both jaws move symmetrically. Generate and open separately: `python scripts/models/robot_arm.py --gripper --open`.
