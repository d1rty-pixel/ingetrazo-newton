"""Every axis is also a real scene object, so the host's Move/Rotate/Scale act on it.

The joint data in the body stays authoritative for the simulation. A plain
wire group on the axes layer mirrors it: its frame (``group.axes``, carried by
every host transform) is the pivot and the axis direction. After each history
command one sync step, inside the same undo entry, reconciles both sides: a
moved axis object writes the joint, otherwise the object follows the joint.
"""
import copy
from PySide6.QtGui import QMatrix4x4,QVector3D
from core.group import Group,group_frame,carry_axes
from core.history import Command,CompoundCommand,DeleteGroupCommand
from core.mesh import Mesh
from .model import KEY,AXES_LAYER,Configure,settings,remove_axes_command,ensure_axis_layer,project_zero,with_zero
from .i18n import tr


def owner_id(group):
    return ((group.ext or {}).get(KEY) or {}).get("axis_of")


def markers(scene):
    return [g for g in scene.groups if owner_id(g)]


def axis_matrix(pivot,axis,zero=None):
    """Frame of an axis object: origin at the pivot, z along the axis, x along 0°."""
    d = QVector3D(*axis).normalized()
    ref = QVector3D(0,0,1) if abs(d.z())<.9 else QVector3D(0,1,0)
    zero = project_zero(axis,zero)
    u = QVector3D(*zero) if zero else QVector3D.crossProduct(d,ref).normalized()
    v = QVector3D.crossProduct(d,u).normalized()
    p = QVector3D(*pivot)
    return QMatrix4x4(u.x(),v.x(),d.x(),p.x(),u.y(),v.y(),d.y(),p.y(),u.z(),v.z(),d.z(),p.z(),0,0,0,1)


def placement(marker):
    """Pivot, axis and 0° direction of an axis object."""
    m = group_frame(marker) or QMatrix4x4()
    return tuple(list(t.toTuple()) for t in (m.map(QVector3D()),m.mapVector(QVector3D(0,0,1)).normalized(),
                                               m.mapVector(QVector3D(1,0,0)).normalized()))


def close(a,b):
    # The frame is single precision (QMatrix4x4); stricter checks would resync forever.
    return all(abs(x-y)<=1e-5*max(1,abs(x),abs(y)) for x,y in zip(a,b))


def build(body,joint,size):
    """A rod from the pivot along the axis with a small cross at the pivot."""
    mesh = Mesh()
    m = axis_matrix(joint["pivot"],joint["axis"],joint.get("zero"))
    for a,b in (((0,0,0),(0,0,2)),((-.3,0,0),(.3,0,0)),((0,-.3,0),(0,.3,0))):
        mesh.add_edge(m.map(QVector3D(*a)*size),m.map(QVector3D(*b)*size))
    group = Group(mesh,tr("Axis")+" · "+body.name)
    group.layer = AXES_LAYER
    group.axes = m
    group.ext = {KEY:{"mode":"ignore","axis_of":body.uid}}
    return group


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
    """Placement and owner of each axis object before a command."""
    return {id(g):(placement(g),owner_id(g)) for g in markers(scene)}


def plan(scene,before=None,cmd=None,size=lambda g:.2):
    """Commands that bring axis objects and joints into agreement, or []."""
    before = before or {}
    bodies = {g.uid:g for g in scene.groups if not owner_id(g)}
    commands,kept = [],{}
    # The axis object that already existed wins over a pasted copy.
    for g in sorted(markers(scene),key=lambda g:id(g) not in before):
        body = bodies.get(owner_id(g))
        if body is None or not settings(body).get("joint") or body.uid in kept:
            commands.append(DeleteGroupCommand(g))
        else:
            kept[body.uid] = g
    remaining = {id(g) for g in scene.groups}
    deleted = {owner for key,(_,owner) in before.items() if key not in remaining}
    for body in bodies.values():
        joint = settings(body).get("joint")
        if not joint:
            continue
        marker = kept.get(body.uid)
        if marker is None:
            # Deleting the axis object deletes the axis; anything else that made it vanish does not.
            if body.uid in deleted and cmd is not None and deletes_groups(cmd):
                remove = remove_axes_command([body],scene)
                if remove:commands.append(remove)
            else:
                commands.append(AddMarker(build(body,joint,size(body))))
            continue
        pivot,axis,zero = placement(marker)
        # Without a stored 0° direction any perpendicular frame axis matches.
        wanted = project_zero(joint["axis"],joint.get("zero"))
        if close(pivot,joint["pivot"]) and close(axis,joint["axis"]) and (wanted is None or close(zero,wanted)):
            continue
        if id(marker) in before and before[id(marker)][0]!=(pivot,axis,zero):
            moved = dict(joint,pivot=pivot,axis=axis,zero=zero if wanted is not None else None)
            commands.append(Configure([body],dict(joint=with_zero(body,moved)),partial=True))
        else:
            target = axis_matrix(joint["pivot"],joint["axis"],joint.get("zero"))
            commands.append(MoveMarker(marker,target*axis_matrix(pivot,axis,zero).inverted()[0]))
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
    """Documents saved before axis objects existed get them without an undo step."""
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
