"""Every axis and every connection point is also a real scene object, so the host's Move/Rotate/Scale act on it.

The data in the body (``joint`` or ``point_attachment``) stays authoritative
for the simulation. A plain wire group on the axes layer mirrors it: its frame
(``group.axes``, carried by every host transform) is the pivot or connection
point and the axis direction. After each history command one sync step, inside
the same undo entry, reconciles both sides: a moved object writes the data,
otherwise the object follows the data.
"""
from PySide6.QtGui import QMatrix4x4,QVector3D
from core.group import Group,group_frame,carry_axes
from core.history import Command,CompoundCommand,DeleteGroupCommand
from core.mesh import Mesh
from .model import KEY,AXES_LAYER,Configure,settings,remove_axes_command,ensure_axis_layer,project_zero,with_zero
from .i18n import tr

AXIS,CONNECTION = "axis_of","connection_of"


def owner_key(group):
    cfg = (group.ext or {}).get(KEY) or {}
    return next((k for k in (AXIS,CONNECTION) if cfg.get(k)),None)


def owner_id(group):
    key = owner_key(group)
    return group.ext[KEY][key] if key else None


def markers(scene,key=None):
    return [g for g in scene.groups if owner_key(g) and key in (None,owner_key(g))]


def data(body,key):
    return settings(body).get("joint" if key==AXIS else "point_attachment")


def wanted(key,value):
    """Pivot, axis and 0° direction the object must show; None where any value fits."""
    if key==AXIS:
        return value["pivot"],value["axis"],project_zero(value["axis"],value.get("zero"))
    return value["point"],value["axis"] if value.get("type")=="hinge" else None,None


def axis_matrix(pivot,axis,zero=None):
    """Frame of an axis object: origin at the pivot, z along the axis, x along 0°."""
    d = QVector3D(*axis).normalized()
    ref = QVector3D(0,0,1) if abs(d.z())<.9 else QVector3D(0,1,0)
    zero = project_zero(axis,zero)
    u = QVector3D(*zero) if zero else QVector3D.crossProduct(d,ref).normalized()
    v = QVector3D.crossProduct(d,u).normalized()
    p = QVector3D(*pivot)
    return QMatrix4x4(u.x(),v.x(),d.x(),p.x(),u.y(),v.y(),d.y(),p.y(),u.z(),v.z(),d.z(),p.z(),0,0,0,1)


def target_matrix(key,value):
    pivot,axis,zero = wanted(key,value)
    return axis_matrix(pivot,axis or (0,0,1),zero)


def placement(marker):
    """Pivot, axis and 0° direction of an axis or connection object."""
    m = group_frame(marker) or QMatrix4x4()
    return tuple(list(t.toTuple()) for t in (m.map(QVector3D()),m.mapVector(QVector3D(0,0,1)).normalized(),
                                               m.mapVector(QVector3D(1,0,0)).normalized()))


def close(a,b):
    # The frame is single precision (QMatrix4x4); stricter checks would resync forever.
    return all(abs(x-y)<=1e-5*max(1,abs(x),abs(y)) for x,y in zip(a,b))


def build(body,key,value,size):
    """An axis is a rod with a small cross at the pivot; a connection draws the glyph of its type (see connections.glyph)."""
    mesh = Mesh()
    m = target_matrix(key,value)
    if key==AXIS:
        lines = [((0,0,0),(0,0,2)),((-.3,0,0),(.3,0,0)),((0,-.3,0),(0,.3,0))]
    else:
        from .connections import glyph
        lines = [segment for line in glyph(value.get("type","ball")) for segment in zip(line,line[1:])]
    for a,b in lines:
        mesh.add_edge(m.map(QVector3D(*a)*size),m.map(QVector3D(*b)*size))
    group = Group(mesh,tr("Axis" if key==AXIS else "Connection")+" · "+body.name)
    group.layer = AXES_LAYER
    group.axes = m
    group.ext = {KEY:{"mode":"ignore",key:body.uid}}
    if key==CONNECTION:
        group.ext[KEY]["glyph"] = value.get("type","ball")
    return group


def written(body,key,value,pivot,axis,zero):
    """The command that writes a moved object back into the body."""
    if key==AXIS:
        has_zero = project_zero(value["axis"],value.get("zero")) is not None
        moved = dict(value,pivot=pivot,axis=axis,zero=zero if has_zero else None)
        return Configure([body],dict(joint=with_zero(body,moved)),partial=True)
    moved = dict(value,point=pivot)
    if value.get("type")=="hinge":
        moved["axis"] = axis
    return Configure([body],dict(point_attachment=moved),partial=True)


def removal(body,key,scene):
    if key==AXIS:
        return remove_axes_command([body],scene)
    return Configure([body],dict(point_attachment=None),partial=True)


class AddMarker(Command):
    keeps_groups = True

    def __init__(self,group):
        self.group = group

    def do(self,scene):
        scene.groups.append(self.group)
        scene.version += 1

    def undo(self,scene):
        if self.group in scene.groups:
            scene.groups.remove(self.group)
        scene.selection.discard(self.group)
        scene.version += 1


def marker_of(scene,body,key):
    return next((m for m in markers(scene,key) if owner_id(m)==body.uid),None)


class LockMarker(Command):
    """The host's object lock: no tool picks or moves the object, it still follows its body."""
    keeps_paint = True

    def __init__(self,group,locked):
        self.group,self.locked = group,bool(locked)
        self.before = bool(getattr(group,"locked",False))

    def apply(self,scene,locked):
        self.group.locked = locked
        if locked:
            scene.selection.discard(self.group)
        scene.version += 1

    def do(self,scene):self.apply(scene,self.locked)
    def undo(self,scene):self.apply(scene,self.before)


class Reshape(Command):
    """Swaps a connection object's wire for the glyph of a changed connection type; lock and selection stay."""
    keeps_paint = True

    def __init__(self,group,fresh):
        self.group,self.state = group,(fresh.mesh,fresh.axes,fresh.ext[KEY]["glyph"])

    def swap(self,scene):
        old = (self.group.mesh,self.group.axes,self.group.ext[KEY].get("glyph"))
        self.group.mesh,self.group.axes,self.group.ext[KEY]["glyph"] = self.state
        self.state = old
        scene.version += 1

    def do(self,scene):self.swap(scene)
    def undo(self,scene):self.swap(scene)


class MoveMarker(Command):
    keeps_paint = True

    def __init__(self,group,matrix):
        self.group,self.matrix = group,QMatrix4x4(matrix)
        self.inverse = self.matrix.inverted()[0]

    def apply(self,scene,m):
        for v in list(self.group.mesh.vertices):
            self.group.mesh.move_vertex(v,m.map(v.position)-v.position)
        carry_axes(self.group,m)
        scene.version += 1

    def do(self,scene):self.apply(scene,self.matrix)
    def undo(self,scene):self.apply(scene,self.inverse)


def deletes_groups(cmd):
    if type(cmd).__name__=="DeleteGroupCommand":
        return True
    children = list(getattr(cmd,"commands",None) or [])+[getattr(cmd,"command",None)]
    return any(deletes_groups(c) for c in children if c is not None)


def capture(scene):
    """Placement and owner of each axis and connection object before a command."""
    return {id(g):(placement(g),(owner_key(g),owner_id(g))) for g in markers(scene)}


def plan(scene,before=None,cmd=None,size=lambda g:.2):
    """Commands that bring the objects and the body data into agreement, or []."""
    before = before or {}
    bodies = {g.uid:g for g in scene.groups if not owner_id(g)}
    commands,kept = [],{}
    # The object that already existed wins over a pasted copy.
    for g in sorted(markers(scene),key=lambda g:id(g) not in before):
        key,body = owner_key(g),bodies.get(owner_id(g))
        if body is None or not data(body,key) or (key,body.uid) in kept:
            commands.append(DeleteGroupCommand(g))
        else:
            kept[key,body.uid] = g
    remaining = {id(g) for g in scene.groups}
    deleted = {owner for k,(_,owner) in before.items() if k not in remaining}
    for body in bodies.values():
        for key in (AXIS,CONNECTION):
            value = data(body,key)
            if not value:
                continue
            marker = kept.get((key,body.uid))
            if marker is None:
                # Deleting the object deletes the axis or connection; anything else that made it vanish does not.
                if (key,body.uid) in deleted and cmd is not None and deletes_groups(cmd):
                    remove = removal(body,key,scene)
                    if remove:commands.append(remove)
                else:
                    commands.append(AddMarker(build(body,key,value,size(body))))
                continue
            if key==CONNECTION and marker.ext[KEY].get("glyph")!=value.get("type","ball"):
                commands.append(Reshape(marker,build(body,key,value,size(body))))
                continue
            pivot,axis,zero = placement(marker)
            want_pivot,want_axis,want_zero = wanted(key,value)
            if close(pivot,want_pivot) and (want_axis is None or close(axis,want_axis)) and (want_zero is None or close(zero,want_zero)):
                continue
            if id(marker) in before and before[id(marker)][0]!=(pivot,axis,zero):
                commands.append(written(body,key,value,pivot,axis,zero))
            else:
                commands.append(MoveMarker(marker,target_matrix(key,value)*axis_matrix(pivot,axis,zero).inverted()[0]))
    return commands


class SyncAxes(CompoundCommand):
    """Applied after the command it belongs to; replayed on redo."""


def install(panel,viewport):
    history = viewport.history
    if getattr(history,"_newton_axis_objects",False):
        return
    original = history.execute

    def execute(cmd):
        scene = history.scene
        active = panel.session.workspace is None and getattr(scene,"edit_group",None) is None
        before = capture(scene) if active else None
        top = history.undo_stack[-1] if history.undo_stack else None
        result = original(cmd)
        done = history.undo_stack[-1] if history.undo_stack else None
        if active and done is not None and done is not top and not isinstance(done,SyncAxes):
            commands = plan(scene,before,cmd,size=gizmo_size)
            if commands:
                ensure_axis_layer(scene)
                sync = SyncAxes(commands)
                sync.do(scene)
                entry = CompoundCommand([done,sync])
                entry._history_mesh = getattr(done,"_history_mesh",None)
                history.undo_stack[-1] = entry
        return result
    history.execute = execute
    history._newton_axis_objects = True


def gizmo_size(group):
    from .panel import gizmo_size as size
    return size(group)


def sync_loaded(panel,viewport):
    """Documents saved before these objects existed get them without an undo step."""
    history = viewport.history
    scene = history.scene
    if panel.session.workspace is not None or getattr(scene,"edit_group",None) is not None:
        return
    if history.undo_stack or history.redo_stack:
        return
    commands = plan(scene,capture(scene),size=gizmo_size)
    if commands:
        ensure_axis_layer(scene)
        SyncAxes(commands).do(scene)
