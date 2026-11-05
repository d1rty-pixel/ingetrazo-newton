"""Flexible centre lines and segmented preview meshes; engine stays in MuJoCo."""
import copy
import math
from PySide6.QtGui import QMatrix4x4,QVector3D,QQuaternion
from core.mesh import Mesh
from core.group import Group


def validate(raw):
    if not isinstance(raw,dict):raise ValueError("Invalid flexible material.")
    cfg = {**dict(kind="rope",radius=.015,bend=2e4,twist=1e4,damping=.002,start="fixed",end_reference=None),**raw}
    if cfg["kind"] not in ("rope","cable") or cfg["start"] not in ("fixed","pinned","free"):
        raise ValueError("Invalid flexible material.")
    from .worker import vector
    cfg["points"] = [vector(p,"centre line") for p in cfg.get("points",[])]
    if not 3<=len(cfg["points"])<=201:raise ValueError("Use a centre line with 3 to 201 points.")
    for key in ("radius","bend","twist","damping"):
        cfg[key] = float(cfg[key])
        if not math.isfinite(cfg[key]) or cfg[key]<0:raise ValueError("Invalid flexible material.")
    if cfg["radius"]<=0:raise ValueError("Invalid flexible material.")
    for a,b in zip(cfg["points"],cfg["points"][1:]):
        if math.dist(a,b)<1e-5:raise ValueError("Centre line contains coincident points.")
    return cfg


def segment_uid(uid,index):return f"{uid}:flex:{index}"


def centre_line(group):
    mesh = group.mesh
    if group.children or mesh.faces:raise ValueError("Select a group containing one open line without faces.")
    adjacent = {}
    for edge in mesh.edges:
        adjacent.setdefault(edge.v0,[]).append(edge.v1);adjacent.setdefault(edge.v1,[]).append(edge.v0)
    ends = sorted((v for v,n in adjacent.items() if len(n)==1),key=lambda v:v.position.toTuple())
    if len(ends)!=2 or any(len(n)>2 for n in adjacent.values()):
        raise ValueError("Select a group containing one open line without faces.")
    points = [];previous,current = None,ends[0]
    # Persist endpoint order so editing a line cannot swap its attachments.
    old = (group.ext or {}).get("newton",{}).get("flexible") or {}
    if old.get("points"):
        current = min(ends,key=lambda v:math.dist(v.position.toTuple(),old["points"][0]))
    while current is not None:
        points.append(list(current.position.toTuple()))
        previous,current = current,next((v for v in adjacent[current] if v is not previous),None)
        if len(points)>len(adjacent):raise ValueError("Invalid centre line.")
    if len(points)!=len(adjacent):raise ValueError("Invalid centre line.")
    if len(points)==2:
        a,b = points;points = [[a[k]+(b[k]-a[k])*i/20 for k in range(3)] for i in range(21)]
    return points


def tube(length,radius,colour=(.85,.45,.12)):
    mesh = Mesh();n = 10
    rings = [[QVector3D(x,radius*math.cos(i*2*math.pi/n),radius*math.sin(i*2*math.pi/n)) for i in range(n)] for x in (0,length)]
    for i in range(n):
        f = mesh.add_face([rings[0][i],rings[0][(i+1)%n],rings[1][(i+1)%n],rings[1][i]])
        f.attrs["color"] = colour
    for points in (list(reversed(rings[0])),rings[1]):mesh.add_face(points).attrs["color"] = colour
    for e in mesh.edges:e.soft = True
    return mesh


def segment_group(a,b,radius,name,colour=(.85,.45,.12)):
    delta = QVector3D(*b)-QVector3D(*a)
    group = Group(tube(delta.length(),radius,colour),name)
    group.xform = QMatrix4x4();group.xform.translate(*a)
    group.xform.rotate(QQuaternion.rotationTo(QVector3D(1,0,0),delta.normalized()))
    return group


def make(name,points,**values):
    from .model import KEY,DEFAULTS
    mass = values.pop("mass",.3);colour = values.pop("colour",(.85,.45,.12))
    cfg = validate(dict(points=points,**values))
    group = Group(name=name)
    group.adopt([segment_group(a,b,cfg["radius"],name,colour) for a,b in zip(points,points[1:])])
    group.ext = {KEY:dict(DEFAULTS,mass=mass,flexible=cfg)}
    return group


def expand(group,cfg,scene,specs,movers):
    from .model import KEY,reference_id
    flex = validate(cfg["flexible"])
    if flex.get("source")=="line":flex["points"] = validate(dict(flex,points=centre_line(group)))["points"]
    matrix = group.xform or QMatrix4x4()
    points = [list(matrix.map(QVector3D(*p)).toTuple()) for p in flex["points"]]
    flex["points"] = points
    header = dict(uid=group.uid,mass=cfg["mass"],flexible=flex,reference=reference_id(group),
        simulation_override=copy.deepcopy(cfg.get("simulation_override")),friction=cfg["friction"],restitution=cfg["restitution"],
        no_collision=list(cfg.get("no_collision",[])))
    specs.append(header)
    # Preserve the source material colour without changing its geometry.
    from core.group import world_mesh
    faces = world_mesh(group).faces
    colour = next(iter(faces)).attrs.get("color",(.85,.45,.12)) if faces else (.85,.45,.12)
    for i,(a,b) in enumerate(zip(points,points[1:])):
        clone = segment_group(a,b,flex["radius"],group.name,colour)
        clone.uid = segment_uid(group.uid,i);clone.layer = group.layer
        mass = cfg["mass"]/(len(points)-1)
        clone.ext = {KEY:dict(mode="dynamic",flex_owner=group.uid,mass=mass)}
        scene.place(clone.uid,clone.xform);scene.groups.append(clone);movers[clone.uid] = clone
        specs.append(dict(uid=clone.uid,flex_segment=group.uid,mass=mass,joint=None))
