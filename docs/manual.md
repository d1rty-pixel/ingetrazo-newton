# Newton – Manual

This manual describes how to use Newton 0.14.0. Installation and overview are in the [README](../README.md), the example models in [example-models.md](example-models.md).

## Basic workflow

1. Select a group or component.
2. In the **Newton Tools** toolbar, click the **rotation axis icon** or the **linear axis icon**. No dialog opens.
3. In the model, first set the pivot or start point. A second click sets the positive axis direction. IngeTrazo's snapping applies. After the first click you can press **X**, **Y** or **Z** instead. **Esc** cancels without changes.
4. Set the behaviour and the drive in the **Newton sidebar**. Changes apply directly: numbers with Enter or when the field loses focus, drop-downs and switches immediately. Every change can be undone.
5. Press **Start**. Hold the left mouse button to grab and drag passive bodies. The **control panel** holds named actuator controls. **Reset** returns to the unchanged original model.

## Sidebar

All parameters of the selected group are in the sidebar. Like the other IngeTrazo sidebars it is divided into collapsible sections: clicking a heading opens or closes a section, and this state survives a restart. **Generic**, **Profile** and **Motion** are open at first, the other sections collapsed.

Where the sidebar refers to another body (reference body, counter body of a connection, end attachment, leader axis of a coupling, collision exemptions), it appears as its own row with a small preview image and the name. The unlink icon next to it removes the reference; both bodies are kept and the step can be undone. When the mouse pointer is over such a row, the body in the model gets a rim in the accent colour; clicking the row (not the unlink icon) selects it.

Such relations are also outlined in the model: when a body is selected, the bodies linked to it get a rim, in both directions: yellow for reference bodies, dependent bodies and couplings, magenta for counter bodies of mechanical connections and rope ends, dashed cyan for collision exemptions. When you pick a body, for example the reference body, the counter body of a connection or in the **Choose…** menu, the body under the mouse pointer gets a rim in the accent colour if it is a valid choice.

| Setting | Meaning |
|---|---|
| Movable, fixed, exclude from simulation | Participation and mobility of the body |
| Reference body | Parent element; assign or detach |
| Control name | For example "Close gripper", "Left door", "Feed" |
| Free / passive | No control; moves through gravity, contacts or dragging |
| Servo / angle | Move to a target angle in degrees and hold it |
| Position / distance | Move to a linear target in millimetres and hold it |
| Motor / speed | Rotation speed in °/s or feed in mm/s |
| Minimum / Maximum | Optional angle or distance limits |
| Start target | Stored control value when the simulation starts |
| Speed | Maximum speed of the actuator's setpoint profile |
| Acceleration | Acceleration limit of the actuator's setpoint profile |
| Deceleration | Separate limit for braking and direction changes; the chain switch synchronises it with the acceleration |
| Maximum force | Limit in Nm or N |

The model position at setup corresponds to 0° or 0 mm. A limit range in use must contain this initial position. Body values and local overrides are in the sections **Body & contact** and **Simulation overrides**; global simulation and runtime selection are in the extension preferences.

Acceleration and deceleration are coupled at first. With the chain switch on, the deceleration follows every change of the acceleration. After releasing it, it can be set separately; coupling again applies the acceleration value immediately. The limits apply in °/s² or mm/s² to the setpoint profile. On a direction change the drive first brakes to zero and then accelerates in the other direction. Both values and the coupling are stored with profiles and models; older settings automatically take over the previous symmetric acceleration.

With a multi-selection, body values and movable/fixed can be changed together. Axes and reference bodies are set up for a single selected group. Without a selected body the Newton sidebar stays empty. The overview is in the existing **Browser**: the type column shows Newton, axis kind and control name. The existing body names are kept; no additional geometry objects are created for controls.

The **Generic** section is at the top of the sidebar. The selected group or component name appears in the heading after **Newton properties**. On start the previously shown configuration stays visible and is disabled; the sections can still be opened and closed, and the sidebar can still be scrolled. Start/pause and reset are in the toolbar and the control panel. Hints for placing and editing appear for a few seconds in IngeTrazo's status bar, messages of the running simulation in the control panel. Without a selection the sidebar stays empty as before.

Angle limits, position/target values and the bounded body and environment values friction, bounce and gravity have wide sliders with a compact number field. For a bounded position drive the slider range is exactly minimum and maximum, for a speed drive ±maximum speed. This also applies to linear axes in millimetres. The ranges adapt immediately when the limits change. Exact input remains possible; angles beyond a full turn are supported. A drag changes the model live and stays one undo step. Scrolling over these sliders does not change values by accident.

## Placing and editing axes

Rotation axes appear as an aligned circle with an axis line; linear axes as a direction arrow. When placing, Newton shows the future axis in the direction of the mouse pointer after the click on the start point. For rotation axes the last step is the **0° direction**: a click (or X/Y/Z) perpendicular to the axis sets where 0° lies; **Enter** keeps the previous direction. The mouse pointer works in the axis's plane of rotation, snaps to geometry and locks onto the world axes projected into that plane. From this Newton measures the **start angle**, the angle of the modelled position (direction from the axis point to the body centre) relative to 0°. Limits, targets and actual values then apply absolutely to this 0° direction; a door drawn open can thus relate limits and target to "closed = 0°". If the start angle lies outside the previous limits, Newton shifts them by the start angle when placing. The 0° direction rotates along when the body or axis object is rotated; rotating only the axis object about its own axis changes the start angle. With the selection tool an axis symbol can be clicked; the associated axis object is then selected and the sidebar shows its body. The axis object is moved, rotated and scaled with IngeTrazo's tools; there are no custom drag handles. Repositioning through the corresponding toolbar icon remains available. During the simulation and on locked axis layers, editing is disabled.

Every axis is also its own object **Axis · <body>** made of edges on the layer `Newton Axes`. IngeTrazo's Move, Rotate and Scale tools act on it like on any group: start point and direction of the axis follow the object, in the same undo step. When the body is moved, the axis object moves along. Deleting the axis object removes the axis; a copy of the axis object is discarded, a copy of the body gets its own. Documents without axis objects get them when opened. Axis objects do not take part in the simulation. When a body is selected, **Newton ▸ Select axis object** or **Select connection object** in the context menu replaces the selection with that object; the entry is only active if the body has such an object. **Lock axis object** (section **Motion**) and **Lock connection object** (section **Mechanical connection**) set IngeTrazo's object lock: the object can neither be selected in the model nor moved or rotated with tools, but still follows its body. With a locked connection object the point fields are locked too. Unlocking works through the same checkbox or the browser; both can be undone.

Axis placement uses the same snapping and axis inference as the native line tool. Snap points on existing geometry, the magnetic alignment to X/Y/Z and the Shift lock remain available; no separate snapping calculation is needed.

The native **Eraser (E)** can remove an axis symbol. Body geometry and the reference body assignment are kept. The **Remove axis** button remains available. An eraser stroke started on an axis deletes axes only; undo restores them.

All axis representations belong to the reserved, language-independent layer **`Newton Axes`**. The extension uses an existing layer of this name or creates it as soon as axes exist. The eye in the native Layers panel hides the representations together; geometry and Newton stay active. A locked axis layer prevents erasing its symbols. The bodies keep their original layers. Axis objects consist of edges only and create no model faces; the layer is not printed.

For the selected body, coloured limits and short numbers appear directly at its axis: **green** marks the range of motion, **blue/red** the limits and **yellow** the current position. The **dashed violet** mark shows the servo target, the dotted line the zero position. Rotation axes use angle arcs, linear axes a true-to-scale segment. In the simulation the displays follow the reference body and the actual joint states. Operating a control highlights the associated axis. Other axes stay subdued.

Axis labels use at least 12 pt bold type and dark, high-contrast tags. Min, max and actual are named. Placement looks for free space outside all projected axes and avoids other tags. Thin dotted leader lines assign the tags. In very crowded views the position with the least overlap is chosen. Position and range lines are 4 px thick, limits and targets 3 px. The tags too can be selected as axes or removed with the eraser.

## Reference bodies

The technical term for the assignment to a parent element is **reference body**.

- Select the child → **chain icon "Assign reference body"** → click the reference body in the model. The commands are also available in the context menu and the sidebar.
- When the reference body is moved normally, its dependent parts follow, including further levels below. They are also part of the motion preview. The change stays **one shared undo step**.
- If only the child is moved, the reference body stays in place. The assignment is kept; levels below the child follow the child.
- Rotation and scaling through the native group transformations are passed on as well; axis position and direction are carried along.
- **Detach reference body** removes the dependency without moving parts. An existing axis is kept and then refers to the world.
- A movable body with a reference body but no axis of its own is rigidly connected to its reference body in the simulation. A placed axis releases the corresponding relative motion.
- **Fixed** with a reference body means: bolted to it. The body follows its motion but cannot be dragged itself. Without a reference body, fixed means: anchored to the world.
- Settings without effect are disabled. With **Fixed** this affects motion, axis coupling and flexible material; mass and own simulation settings stay active only with a reference body, because the body then carries its motion. A mechanical connection remains possible, because a fixed body can anchor a movable one. With **Exclude from simulation** only behaviour and profile can be operated.
- Without a reference body a placed axis is attached to the world. A movable body without an axis and without a reference body moves freely.

Directly connected bodies do not collide with each other, so that bearings do not block themselves. Other body pairs still collide. Closed reference body/joint loops are rejected with a message.

## Connections between bodies

The three toolbar icons **Ball joint**, **Pin joint** and **Fixed connection** create an additional connection between two bodies; they show the same pictures as the type selection. Select a body, click the icon of the desired type, set the shared connection point and finally click the counter body; the body under the mouse pointer is outlined if it qualifies. A **ball joint** leaves spatial rotations free. For a **pin joint**, click the direction after the point or press X/Y/Z, then the counter body. A **fixed connection** holds the relative position. **Connect bodies…** in the context menu and in the sidebar works the same way and uses the type chosen in the section **Mechanical connection**. This allows building closed mechanisms without rebuilding the reference body hierarchy. If the selected body were fixed to a fixed counter body or without Newton, it automatically becomes movable, otherwise nothing could move; a fixed body to which a movable counter body is attached stays fixed. The status bar reports the result.

Every connection is also its own object **Connection · <body>** made of edges on the layer `Newton Axes`. Its shape shows the type like its pictogram in the selection list: a ball joint a sphere, a pin joint a dashed pin through a ring, a fixed connection a cube with a bolted plate at the connection point. The extension draws it in the colours of the axes, with a yellow connection point, red on hover, grey when locked. Violet stays reserved for the servo target. When the body is selected, a tag names "→ counter body". For small bodies the representation stays at least 18 px large. As with the axis object, IngeTrazo's Move, Rotate and Scale act on it: connection point and pin axis follow the object, in the same undo step; when the body is moved, the connection object moves along. Since the connection point usually lies inside the body, a click with the selection tool near it selects the connection object instead of the body; it lights up. Deleting or erasing the connection object removes the connection and keeps both bodies. Alternatively the sidebar and context menu are available. In the sidebar the counter body appears as a row with a preview image; **Set connected body…** only exchanges the counter body, point, type and pin axis stay. The unlink icon of the row removes the connection. Point coordinates are directly editable in millimetres; pins have an editable axis. During the simulation a yellow marker shows the moving connection point. Connection objects do not take part in the simulation. Ropes/cables still use their own end attachments. Connection type, attachment point and pin axis are stored in the `.igz`.

## Axes moving together

In the section **Axis coupling → Follow axis → Choose…** an axis can follow a position drive of the same type; the menu shows only matching axes. The chosen leader axis appears as a row, its unlink icon makes the axis independent again. **Same direction/Opposite direction** refers to the spatial direction of the two axes. A ratio of 1 means the same distance or angle. By default every axis is independent.

The coupling is enforced in the MuJoCo solver. The control panel shows only the leading control; the following axis cannot be dragged. The permitted distances, speeds and accelerations are limited to the common range. The leading drive provides the shared force or torque; the force limit of the following axis is not used as a second drive. A leading drive can have several direct follower axes. Coupling chains, loops and mixed rotation/linear couplings are not yet included.

When a leading axis is removed or its body is fixed, its follower axes become independent again. This operation can be undone as one step. Couplings are stored in the model; custom profiles do not copy references to other model bodies.

## Own simulation settings and force fields

The further object settings are organised in **Axis coupling**, **Body & contact** (with the collision exemptions) and **Simulation overrides**. Each section explains related parameters in one context paragraph. Axis coupling appears only for a single selected axis; direction and ratio appear only for a following axis.

Under **Simulation overrides** a body can replace the global gravity with its own world vector X/Y/Z, set linear and rotational damping and switch the automatic ground at Z = 0 on or off independently. Modelled supports keep their normal contacts. Switching off the main switch restores inheritance. The overrides are stored with the model and in custom profiles.

**Attraction** creates a Newtonian force field directed at the body's centre of mass with strength μ = G × mass (m³/s²). Zero creates no field. If all bodies use the same G, the forces act mutually and conserve the total momentum. A softening radius defuses the singularity at the centre. **Initial velocity X/Y/Z** applies to freely movable bodies in world coordinates and is restored on every simulation start. The values are independent of joint drives.

## Ropes, cables and joint chains

The section **Flexible material** adds **Rigid**, **Rope** and **Cable**. For your own rope/cable, draw an open line or a connected open polyline, group it and choose the material. A single straight line is automatically divided into 20 segments. Branches, closed loops and surface groups are rejected with an understandable message. Edits to the original polyline are read in at the next simulation start; group movements and undo are preserved.

MuJoCo's bundled plugin `mujoco.elasticity.cable` computes bending and torsion of an inextensible sequence of spatial ball joints. The rope starts with a small bending/torsion modulus, the cable with higher values; both remain adjustable. Radius and total mass additionally determine the behaviour. The start can be clamped, hinged or free. A rigid reference body moves the start attachment along; the end can be attached to another rigid body via **End attachment → Choose…**; the unlink icon of the row frees it again. Freely movable sections can be grabbed during the simulation. Reset restores the original model. The flexibility is stored in the `.igz`.

For stiffer and finer cables the worker automatically uses smaller internal time steps. The simulation time reported outwards and the drive ramps stay the same. Configurations that are too stiff are rejected with a hint to reduce the stiffness or the number of segments. A numerically unstable simulation reports an error.

These are flexible strands of constant length and joint mechanisms. Elastic stretching as with rubber, breaking, general deformable solids and an automatic conversion of arbitrary solid parts are not yet included. The general body profiles so far cover the previous body/drive values, not the centre line or flexible material data.

## Checking and disabling collisions

Collision shapes are hidden by default. **Window → Preferences → Newton → Appearance → Show collision shapes in new windows** sets the default for new windows and, on OK, also applies the display to the current window. The view uses the actual collision shapes of the Newton process as coloured outlines with transparent faces. The additional command in the Extensions menu toggles the display temporarily, also without a selection and during the simulation. A temporary toggle does not change the start default. In the section **Body & contact**, **Show collision shape** shows or hides only the shape of the selected body, independent of the global display and without changing it. This exception applies only to the open document until restart, is not stored and creates no undo step. Older stored runtime displays are not taken over as a new start default.

The **Configure collision display shortcut…** button in the Newton preferences opens IngeTrazo's native shortcut page directly at the matching command. There you can assign a shortcut and check conflicts; none is assigned at first. Selected bodies are highlighted in the collision view. The display does not change any contacts. In edit mode the shape is recalculated after geometry or parameter changes; scene and undo history stay unchanged.

In the section **Body & contact** under **Collision exemptions**: select a body, press **Exempt body…** and click the second body in the model. This pair may then penetrate each other. Every stored exemption appears as a row with a preview image; its unlink icon re-enables normal contact behaviour. Both commands can be undone and are stored in the `.igz`. Direct reference body connections remain automatically exempt from mutual collision as well.

## Simulation and control panel

- **Start / Pause / Resume / Reset** are available in the **Newton Simulation** toolbar and in the control panel. Start and pause share one state-dependent button. The control panel also works without an object selection.
- In the simulation the left mouse button grabs passive, non-fixed bodies. The motion is a damped pull force at the grab point, without teleporting; joints and contacts keep acting. Releasing ends the pull force.
- The mouse moves the pull target in the plane parallel to the screen through the grab point. Camera navigation with the middle mouse button remains available.
- **Servo and motor bodies with a control cannot be dragged manually**, not even when the force limit is small. They are controlled exclusively through the control panel. This rule is checked both in the user interface and in the Newton process.
- On start the separate **control panel** opens automatically if it is not already open. It also shows the simulation time. Every actuator card is titled **group/component name actuator name**. The actual value is at the far left, the wide slider in the middle and the small setpoint input field on the right. Slider style, height, spacing and the 104-pixel input field match the min/max sliders of the sidebar. A shared actual-value column width keeps all controls aligned, even with different units or long numbers. It opens at the top right corner of the 3D view, next to the sidebar, with equal distance to the top and right; under Wayland the compositor decides the position. It is only as tall as its controls and scrolls as soon as they are taller than the 3D view. The toolbar command reopens the control panel at any time. Error messages carry a red, warnings a yellow exclamation mark; plain notes appear without a sign.
- While paused, a new control target is approached only on resume. Reset discards the runtime targets. Permanent start values are set in the sidebar.
- Speed and acceleration limit the setpoint profile; the actual body follows it according to force limit, loads and contacts. The simulation stays physical, so this is no guarantee of an exactly limited real acceleration.
- Saving in the simulation workspace points to reset and then saving the original. Taking over the simulated end position is not yet included.

The control panel shows the simulation speed actually reached as **× real time**. While paused, no waiting time is counted in the measurement. A tooltip names Newton time, display processing, response time of the process, contact count, solver iterations and internal sub-steps. The display processing measures applying the poses and UI signals, not the pure GPU drawing time.

Under **Preferences → Newton → Simulation → Quality** there are **Quick**, **Balanced** and **Precise**. The choice applies at the next start. Long cable mechanisms use a CG solver with elliptic friction at Quick/Balanced; Precise uses Newton with a tighter tolerance. Collision geometry, cable resolution and the time steps required for stability are not simplified. After a compute batch only the position-dependent data is refreshed, instead of solving the full system of equations again for the output.

Speed motors use PI control with acceleration feed-forward and protection against integrator wind-up at the force limit. The motor thereby compensates loads without exceeding its set force/torque limit. In the control panel **Limit** marks a limit that has been reached; the actual-value tooltip contains setpoint, current ramp value and utilisation. Blocked or too weak motors stay physically limited.

## Profiles

The insertable example models were removed from the interface. Instead there are eight predefined profiles: free rotation axis, rotation motor, rotation servo, free linear axis, linear motor, linear positioning, and free and fixed body.

A profile overrides mass, friction, bounce, collision shape and mobility as well as drive, limits, start target, speed, acceleration and force limit. With an existing axis, placement, control name and reference body are kept. If a required axis is missing, placement in the model begins; Esc cancels without changing data. A body profile without an axis removes an existing axis but keeps the reference body.

**Window → Preferences → Newton → Profiles** shows the values of every profile by body/contact, motion and simulation overrides. Custom profiles are directly editable, built-ins read-only and duplicable. **Save as…** takes over the current object settings. Changes in the preferences are saved with **OK**; **Cancel** discards them.

When applying, the body remembers the profile ID and the parameter state taken over. The sidebar shows **In sync**, **Local changes**, **Profile changed** or **Missing profile**. **Sync** takes over the current profile parameters and overwrites local deviations; axis position, names, geometry and reference body are kept. **Unlink** keeps the object values. The assignment is stored in the `.igz`; custom profiles live in the local IngeTrazo user settings.

Under **Preferences → Newton → Profiles → Synchronise linked bodies (N)** the shared sync in the current model can be queued for **OK**; clicking again withdraws it. Profile values edited after queueing are used as well. The operation is fully checked beforehand and can be undone with one undo. Existing bodies without an assignment can be linked with **Link selection without changing values** without changing their parameters immediately. New axes still need placement in the sidebar.

## Preferences, toolbar and language

**Window → Preferences → Newton** contains four tabs: **Appearance**, **Simulation**, **Profiles** and **Runtime**. They hold the collision display, global gravity/ground/damping, profile management and the Python path. Changes are applied only with OK, global simulation values are used at the next start. The sidebar no longer contains global simulation or runtime configuration.

Every page is divided into headed categories separated by a line. Every setting has its own explanation, which also appears as a tooltip. Settings that change a physical quantity (gravity, ground, damping) additionally show a pictogram of that quantity. **Show collision shapes in new windows** sets whether the collision display is switched on when a window opens.

Newton ships two toolbars. **Newton Tools** contains, each group separated by a little space, axes, connections, reference bodies, movable/fixed, the sidebar and, at the far right, the control panel. **Newton Simulation** contains start/pause, reset and drag body. Profile management and preferences were removed from the toolbar. The toolbar uses IngeTrazo's toolbar size. The icons follow IngeTrazo's style: the shape is drawn in the text colour, the defining detail (pivot, direction, connection) in the accent colour. Disabled icons appear fully grey. The icons react to the light and dark palette.

In the sidebar and the profile editor, drop-downs with fixed values (behaviour, collision shape, drive, connection, material, attachment, coupling direction, axis) show a pictogram for every value that depicts the interaction of the bodies involved. Number fields for physical quantities (for example mass, friction, bounce, limits, speed, force, gravity, damping, attraction, cable radius and stiffness) carry a small pictogram after their name. The sidebar can be narrowed to about 280 px without content being cut off or rows being squashed.

The extension supplements the native preferences dialog through a local adapter: Extension API 2 has no official registration point for this. IngeTrazo files stay unchanged; existing pages and their navigation are kept. This adapter is checked against the host version named below.

The interface follows IngeTrazo's language setting. English and German are included. English is the source language; **`newton/i18n/en.json`** is the master file, every further language sits next to it as its own file (for example `de.json`) with exactly the same entries. A missing language falls back to English. Object, control and profile names you assign yourself are not translated. After a change of the host language, its usual restart procedure applies.

## Technical notes

Surface contacts use several contact points and an elliptic friction calculation. A convex collider with eight corners is computed as an exact, spatially oriented cuboid only if all corners mathematically confirm the cuboid. Other hulls stay hulls. This lets toppled dominoes come to rest without freezing them artificially. Background: [MuJoCo 3.3.7, contact options](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#option-flag-multiccd).

Newton uses the Python package `newton`, the model key `group.ext["newton"]`, the settings prefix `newton/` and the reserved layer `Newton Axes`. There are no compatibility aliases and no automatic import of earlier data or settings. The bundled models have been converted to this scheme.

### Limits

- A body has at most one incoming reference body/joint connection. Branched chains work; closed reference body chains and several joints on the same body do not yet. Axis couplings link the motion coordinates of already existing joints.
- Newton bodies are currently groups/components at the top model level. Nested geometry inside such a body forms one shared collider.
- Native group transformations and their undo/redo steps are supplemented by local extension adapters. Direct geometry changes by other extensions without these commands can bypass the reference body tracking. Deforming geometry inside a body is not moving the body.
- Unconfigured normal groups are static. Unconfigured face-me scale figures are visual only. Hidden groups and groups on hidden layers take part in the simulation invisibly, as if they were visible; loose geometry is displayed but does not collide.
- Box and sphere are simplified enclosing colliders. Convex hulls close concave holes. No automatic concave decomposition; degenerate hulls can be rejected.
- Bounce is an approximation through MuJoCo's contact damping. The optional ground is an infinite plane at Z=0.
- No ball/universal joints, replay, magnetism, buoyancy or SketchyPhysics script compatibility yet.
- One simulation per window; the workspace blocks switching projects. No guaranteed frame rate for large models.
- IngeTrazo's 0.x API is subject to change. Checked was v0.6.0, commit `e61132a7f8a098ca77fb6b0e7cac488c1bd410cb`.
