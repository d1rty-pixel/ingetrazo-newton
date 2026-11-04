"""Model conversion and undoable settings. All geometry lives in metres."""
from __future__ import annotations

import copy
import math
from PySide6.QtGui import QMatrix4x4, QVector3D
from core.group import Group, world_mesh, transformed_mesh
from core.history import Command,CompoundCommand
from core.scene import Scene
from .worker import joint_settings,resolve_couplings

KEY = "newton"
DEFAULTS = dict(mode="dynamic", shape="box", mass=1.0, friction=.5, restitution=.1,simulation_override=None)
AXES_LAYER = "Newton Axes"


def ensure_axis_layer(scene):
    layer = next((l for l in scene.layers if l.name==AXES_LAYER),None)
    if layer is None:
        from core.layers import Layer
        layer = Layer(AXES_LAYER,color=(.9,.55,.15),printable=False)
        scene.layers.append(layer)
        scene.version += 1
    return layer


def axes_visible(scene,picking=False):
    layer = next((l for l in scene.layers if l.name==AXES_LAYER),None)
    return layer is None or (layer.visible and not (picking and layer.locked))


def settings(group):
    return {**DEFAULTS, **(group.ext or {}).get(KEY, {})}


def reference_id(group):
    cfg = settings(group)
    return cfg.get("reference", (cfg.get("joint") or {}).get("parent"))


class Configure(Command):
    keeps_paint = True

    def __init__(self, groups, values, partial=False):
        self.groups = list(groups)
        self.values = copy.deepcopy(values)
        self.before = [copy.deepcopy(g.ext) for g in self.groups]
        self.partial = partial

    def do(self, scene):
        for g in self.groups:
            g.ext = copy.deepcopy(g.ext or {})
            g.ext[KEY] = {**(settings(g) if self.partial else {}), **copy.deepcopy(self.values)}
        if any(settings(g).get("joint") or settings(g).get("point_attachment") for g in self.groups):
            ensure_axis_layer(scene)
        scene.version += 1

    def undo(self, scene):
        for g, old in zip(self.groups, self.before):
            g.ext = copy.deepcopy(old)
        scene.version += 1


def unlink_followers(scene,uids):
    return [Configure([g],dict(joint=dict(settings(g)["joint"],coupling=None)),partial=True)
            for g in scene.groups if g.uid not in uids and
            ((settings(g).get("joint") or {}).get("coupling") or {}).get("master") in uids]


def remove_axes_command(groups,scene=None):
    groups = list(groups)
    commands = [Configure([g],dict(joint=None,reference=reference_id(g)),partial=True)
                for g in groups if settings(g).get("joint")]
    if scene is not None:
        commands.extend(unlink_followers(scene,{g.uid for g in groups}))
    return commands[0] if len(commands)==1 else CompoundCommand(commands) if commands else None


class AddDemo(Command):
    keeps_groups = True

    def __init__(self, groups):
        self.groups = groups

    def do(self, scene):
        scene.groups.extend(self.groups)
        scene.version += 1

    def undo(self, scene):
        for g in self.groups:
            scene.groups.remove(g)
            scene.selection.discard(g)
        scene.version += 1


def prepare(source,require_movable=True):
    """Independent world-space copies, recentered at each body's initial frame.

    Unconfigured groups remain static. Loose mesh is displayed, but omitted from
    newton; the UI calls this out. Nested children form one top-level body.
    """
    scene = Scene()
    scene.materials = copy.deepcopy(source.materials)
    scene.layers = copy.deepcopy(source.layers)
    scene.display_style = copy.deepcopy(source.display_style)
    scene.mesh = transformed_mesh(source.loose_mesh, QMatrix4x4())
    specs, movers = [], {}
    for group in source.groups:
        cfg = (group.ext or {}).get(KEY,{})
        if cfg.get("axis_of") or cfg.get("connection_of"):
            continue  # Axis and connection objects only mirror body data.
        mesh = world_mesh(group)
        if not mesh.vertices:
            continue
        if group.hidden or any(l.name == group.layer and not l.visible for l in source.layers):
            continue
        xyz = [[v.position.x(), v.position.y(), v.position.z()] for v in mesh.vertices]
        lo = [min(v[i] for v in xyz) for i in range(3)]
        hi = [max(v[i] for v in xyz) for i in range(3)]
        if not all(math.isfinite(x) for x in lo + hi):
            raise ValueError(f"Ungültige Geometrie: {group.name}")
        cfg = settings(group)
        if KEY not in (group.ext or {}):
            # Face-me scale figures are visual references, not physical walls.
            cfg["mode"] = "ignore" if group.billboard else "static"
        if cfg.get("flexible") and cfg["mode"]=="dynamic":
            if cfg.get("joint"):raise ValueError("Flexible bodies cannot also have a motion axis.")
            from .flexible import expand
            expand(group,cfg,scene,specs,movers)
            continue
        center = [(a+b)/2 for a, b in zip(lo, hi)]
        half = [max((b-a)/2, .001) for a, b in zip(lo, hi)]
        joint = joint_settings(cfg["joint"]) if cfg.get("joint") and cfg["mode"] == "dynamic" else None
        if joint:
            joint["parent"] = reference_id(group)
        origin = joint["pivot"] if joint else center
        t = QMatrix4x4()
        t.translate(*[-v for v in origin])
        clone = Group(transformed_mesh(mesh, t), group.name)
        clone.uid = group.uid
        clone.ext = copy.deepcopy(group.ext)
        clone.material = copy.deepcopy(group.material)
        clone.billboard = group.billboard
        clone.layer = group.layer
        clone.xform = QMatrix4x4()
        clone.xform.translate(*origin)
        scene.groups.append(clone)
        if cfg["mode"] == "ignore":
            continue
        specs.append(dict(uid=group.uid, center=center, half=half,
            vertices=[[p[i]-center[i] for i in range(3)] for p in xyz],
            mass=cfg["mass"] if cfg["mode"] == "dynamic" else 0,
            shape=cfg["shape"], friction=cfg["friction"],
            restitution=cfg["restitution"], joint=joint))
        specs[-1]["reference"] = reference_id(group)
        specs[-1]["inertia_mass"] = cfg["mass"]
        specs[-1]["no_collision"] = list(cfg.get("no_collision",[]))
        specs[-1]["simulation_override"] = copy.deepcopy(cfg.get("simulation_override"))
        if cfg["shape"]=="compound":
            if not group.children:raise ValueError("Compound collision needs child groups or components.")
            matrix = group.xform or QMatrix4x4()
            parts = []
            for child in group.children:
                if child.hidden:continue
                part = transformed_mesh(world_mesh(child),matrix)
                vertices = [[p-center[k] for k,p in enumerate(v.position.toTuple())] for v in part.vertices]
                if vertices:parts.append(vertices)
            if not parts:raise ValueError("Compound collision needs child groups or components.")
            specs[-1]["parts"] = parts
        if cfg.get("point_attachment"):specs[-1]["point_attachment"] = copy.deepcopy(cfg["point_attachment"])
        movers[group.uid] = clone
    resolve_couplings({s["uid"]:s.get("joint") for s in specs})
    if require_movable and not any(s["mass"] > 0 for s in specs):
        raise ValueError("No movable bodies. Select a body and make it movable.")
    return scene, specs, movers


def joint_rows(scene,include_fixed=False):
    """Stable body IDs identify controls; names are user-facing only."""
    rows = []
    for g in scene.groups:
        cfg = settings(g)
        if (cfg["mode"] == "dynamic" or include_fixed) and cfg.get("joint"):
            rows.append(dict(uid=g.uid, body=g.name, **dict(joint_settings(cfg["joint"]),parent=reference_id(g))))
    if not include_fixed:
        try:
            resolve_couplings({j["uid"]:j for j in rows})
        except ValueError:
            pass  # Show editable data; the worker reports invalid links at start.
    return rows


def box(name, center, size, **cfg):
    from core.mesh import Mesh
    mesh = Mesh()
    x, y, z = (s/2 for s in size)
    pts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
           (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    for indices in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        f = mesh.add_face([QVector3D(*pts[i]) for i in indices])
        f.attrs["color"] = (.25,.55,.85)
    g = Group(mesh, name)
    g.xform = QMatrix4x4()
    g.xform.translate(*center)
    g.ext = {KEY: {**DEFAULTS, **cfg}}
    return g


def demo(kind):
    if kind == "Servo-Tür":
        frame = box("Türrahmen", (-.1,0,1.1), (.2,.3,2.2), mode="static")
        door = box("Türblatt", (.55,0,1.1), (1.1,.12,2), joint=dict(
            type="hinge", drive="position", name="Tür öffnen", parent=frame.uid,
            pivot=[0,0,1.1], axis=[0,0,1], target=0, force=100,
            limited=True, lower=0, upper=math.pi/2))
        return [frame, door]
    if kind == "Linearschlitten":
        rail = box("Schiene", (0,0,.25), (2,.3,.2), mode="static")
        carriage = box("Schlitten", (0,0,.55), (.4,.5,.3), joint=dict(
            type="slide", drive="position", name="Schlittenposition", parent=rail.uid,
            pivot=[0,0,.55], axis=[1,0,0], target=0, force=100,
            limited=True, lower=-.7, upper=.7))
        return [rail, carriage]
    if kind == "Würfel":
        return [box(f"Newton Würfel {i+1}", (.08*(i%2),0,.6+i*.65), (.5,.5,.5))
                for i in range(8)]
    if kind == "Pendel":
        # Initial COM deliberately off-axis: gravity must generate torque.
        return [box("Newton Pendel", (.8,0,2.4), (.25,.25,1.6),
                    joint=dict(pivot=[0,0,3.2], axis=[0,1,0], speed=0, force=0))]
    if kind == "Motorisiertes Rad":
        # Cylinder along Y, with one coloured radial marker as part of the mesh.
        from core.mesh import Mesh
        mesh = Mesh()
        n, r, depth = 32, .8, .24
        rings = [[QVector3D(r*math.cos(i*2*math.pi/n), y,
                             r*math.sin(i*2*math.pi/n)) for i in range(n)]
                 for y in (-depth/2, depth/2)]
        mesh.add_face(rings[0])
        mesh.add_face(list(reversed(rings[1])))
        for i in range(n):
            j = (i+1)%n
            f = mesh.add_face([rings[0][i], rings[1][i], rings[1][j], rings[0][j]])
            f.attrs["color"] = (1,.4,.1) if i < 3 else (.2,.55,.8)
        for f in mesh.faces[:2]:
            f.attrs["color"] = (.25,.55,.8)
        # A radial face slightly in front of the cap makes rotation visible.
        f = mesh.add_face([QVector3D(0,-.122,0), QVector3D(.72,-.122,-.04),
                           QVector3D(.72,-.122,.04)])
        f.attrs["color"] = (1,.65,.1)
        g = Group(mesh, "Newton Motor-Rad")
        g.xform = QMatrix4x4()
        g.xform.translate(0,0,1.5)
        g.ext = {KEY: {**DEFAULTS, "shape": "hull", "joint": dict(
            pivot=[0,0,1.5], axis=[0,1,0], speed=3, force=20)}}
        return [g]
    raise ValueError("Unbekannte Demo")


def project_zero(axis,zero):
    """The 0° direction made perpendicular to the axis, or None if it has none."""
    if zero is None:
        return None
    d = QVector3D(*axis).normalized()
    z = QVector3D(*zero)
    z = z-d*QVector3D.dotProduct(z,d)
    return list(z.normalized().toTuple()) if z.length()>1e-6 else None


def hinge_start(group,joint):
    """Angle of the modelled pose: from the 0° direction to the body's centre, about the axis."""
    zero = project_zero(joint["axis"],joint.get("zero"))
    if zero is None:
        return 0.
    from core.group import placement_points
    points = placement_points(group)
    if not len(points):
        return 0.
    center = QVector3D(*((points.min(axis=0)+points.max(axis=0))/2).tolist())
    arm = QVector3D(*project_zero(joint["axis"],list((center-QVector3D(*joint["pivot"])).toTuple())) or zero)
    d,u = QVector3D(*joint["axis"]).normalized(),QVector3D(*zero)
    return math.atan2(QVector3D.dotProduct(QVector3D.crossProduct(u,arm),d),QVector3D.dotProduct(u,arm))


def fit_limits(joint):
    """A new 0° direction keeps the limits around the modelled pose, as before it existed."""
    start = joint.get("start",0)
    if not joint.get("limited") or joint["lower"]<=start<=joint["upper"]:
        return joint
    shifted = dict(joint,lower=joint["lower"]+start,upper=joint["upper"]+start)
    if joint.get("drive")=="position":
        shifted["target"] = joint.get("target",0)+start
    return shifted


def with_zero(group,joint):
    """Joint data with a consistent 0° direction and start angle (hinges only)."""
    joint = dict(joint)
    zero = project_zero(joint["axis"],joint.get("zero")) if joint.get("type","hinge")=="hinge" else None
    joint["zero"] = zero
    joint["start"] = hinge_start(group,joint) if zero else 0.
    return joint
