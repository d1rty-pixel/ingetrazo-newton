"""Directed reference-body relationships integrated with native transform undo.

No host files are modified. Per-history/per-viewport adapters extend native group
transforms and their preview to include dependent bodies, exactly once.
"""
import copy
from PySide6.QtGui import QMatrix4x4, QVector3D
from core.group import group_frame, carry_axes, _remap_uvws
from core.history import Command
from .model import KEY, settings


def reference(group):
    cfg = settings(group)
    return cfg.get("reference", (cfg.get("joint") or {}).get("parent"))


def descendants(scene, groups):
    result = list(dict.fromkeys(groups))
    ids = {g.uid for g in result}
    while True:
        added = [g for g in scene.groups if g.uid not in ids and reference(g) in ids]
        if not added:
            return result
        result.extend(added)
        ids.update(g.uid for g in added)


def validate_reference(scene, group, parent):
    if parent and (settings(group).get("flexible") or {}).get("start")=="free":
        raise ValueError("Choose a clamped or pinned start before assigning a reference body.")
    by_id = {g.uid:g for g in scene.groups}
    seen = {group.uid}
    while parent:
        if parent in seen:
            raise ValueError("This reference would create a cycle.")
        seen.add(parent)
        if parent not in by_id:
            raise ValueError("Reference body is missing. Reassign or detach it.")
        g = by_id[parent]
        if g.hidden or settings(g)["mode"] == "ignore":
            raise ValueError("The reference body must be visible and participate in the simulation.")
        if settings(g).get("flexible"):
            raise ValueError("Use a rigid reference body.")
        parent = reference(g)


def frame(group):
    return QMatrix4x4(group_frame(group) or QMatrix4x4())


def different(a,b):
    return any(abs(x-y)>1e-6 for x,y in zip(a.data(),b.data()))


class TransformDependent(Command):
    keeps_paint = True

    def __init__(self, group, matrix):
        self.group, self.matrix = group, QMatrix4x4(matrix)
        self.inverse, ok = self.matrix.inverted()
        if not ok:
            raise ValueError("Singular reference body transform.")

    def apply(self, scene, matrix):
        g = self.group
        if g.xform is not None:
            g.xform = matrix*g.xform
        else:
            for v in list(g.mesh.vertices):
                g.mesh.move_vertex(v, matrix.map(v.position)-v.position)
            _remap_uvws(g.mesh,matrix)
            carry_axes(g,matrix)
        scene.version += 1

    def do(self,scene):
        self.apply(scene,self.matrix)

    def undo(self,scene):
        self.apply(scene,self.inverse)


class FollowTransform(Command):
    """The native operation, dependent transforms and joint frames: ONE undo."""
    def __init__(self, command):
        self.command = command
        self.extra = None
        self.metadata_before = self.metadata_after = None

    @property
    def keeps_paint(self):
        return getattr(self.command,"keeps_paint",False)

    @property
    def keeps_groups(self):
        return getattr(self.command,"keeps_groups",False)

    def do(self,scene):
        if self.extra is not None:
            self.command.do(scene)
            for cmd in self.extra:
                cmd.do(scene)
            for g,ext in self.metadata_after:
                g.ext = copy.deepcopy(ext)
            return
        before = {g:frame(g) for g in scene.groups}
        self.command.do(scene)
        deltas = {}
        for g, old in before.items():
            if g in scene.groups and different(old,frame(g)):
                inverse,ok = old.inverted()
                if ok:
                    deltas[g.uid] = frame(g)*inverse
        self.extra = []
        # Explicitly selected descendants already transformed by the host win.
        for _ in range(len(scene.groups)):
            added = False
            for g in scene.groups:
                parent = reference(g)
                if g.uid not in deltas and parent in deltas:
                    cmd = TransformDependent(g,deltas[parent])
                    cmd.do(scene)
                    self.extra.append(cmd)
                    deltas[g.uid] = deltas[parent]
                    added = True
            if not added:
                break
        self.metadata_before, self.metadata_after = [], []
        for g in scene.groups:
            if g.uid not in deltas:
                continue
            cfg = settings(g)
            classic_flex = cfg.get("flexible") and g.xform is None
            if not cfg.get("joint") and not cfg.get("point_attachment") and not classic_flex:
                continue
            self.metadata_before.append((g,copy.deepcopy(g.ext)))
            g.ext = copy.deepcopy(g.ext)
            m = deltas[g.uid]
            if cfg.get("joint"):
                j = g.ext[KEY]["joint"]
                point = m.map(QVector3D(*j["pivot"]))
                direction = m.mapVector(QVector3D(*j["axis"])).normalized()
                j["pivot"],j["axis"] = list(point.toTuple()),list(direction.toTuple())
                if j.get("zero"):
                    j["zero"] = list(m.mapVector(QVector3D(*j["zero"])).normalized().toTuple())
            if classic_flex:
                g.ext[KEY]["flexible"]["points"] = [list(m.map(QVector3D(*p)).toTuple()) for p in cfg["flexible"]["points"]]
            if cfg.get("point_attachment"):
                g.ext[KEY]["point_attachment"]["point"] = list(m.map(QVector3D(*cfg["point_attachment"]["point"])).toTuple())
                if cfg["point_attachment"].get("type")=="hinge":
                    axis = m.mapVector(QVector3D(*cfg["point_attachment"]["axis"])).normalized()
                    g.ext[KEY]["point_attachment"]["axis"] = list(axis.toTuple())
            self.metadata_after.append((g,copy.deepcopy(g.ext)))

    def undo(self,scene):
        for cmd in reversed(self.extra):
            cmd.undo(scene)
        self.command.undo(scene)
        for g,ext in self.metadata_before:
            g.ext = copy.deepcopy(ext)


def transforms_groups(cmd):
    if type(cmd).__name__ in ("MoveGroupCommand","RotateGroupCommand","ScaleGroupCommand"):
        return True
    return any(transforms_groups(c) for c in getattr(cmd,"commands",[]))


def install(viewport):
    history = viewport.history
    if not getattr(history,"_newton_reference_hook",False):
        original = history.execute
        def execute(cmd):
            if transforms_groups(cmd):
                cmd = FollowTransform(cmd)
            return original(cmd)
        history.execute = execute
        history._newton_reference_hook = True
    if not getattr(viewport,"_newton_preview_hook",False):
        original_preview = viewport.begin_groups_preview
        def preview(groups=(),external=False):
            from .axis_objects import markers,owner_id
            expanded = groups if external else descendants(viewport.scene,groups)
            if not external:
                uids = {g.uid for g in expanded}
                expanded = list(expanded)+[m for m in markers(viewport.scene) if owner_id(m) in uids and m not in expanded]
            viewport._newton_preview_bodies = set() if external else {g.uid for g in expanded if not owner_id(g)}
            # A dragged axis object previews its body's axis glyph, not the body.
            viewport._newton_preview_axes = set() if external else {owner_id(g) or g.uid for g in expanded}
            return original_preview(expanded,external=external)
        viewport.begin_groups_preview = preview
        original_end = viewport.end_groups_preview
        def end():
            viewport._newton_preview_bodies = viewport._newton_preview_axes = set()
            return original_end()
        viewport.end_groups_preview = end
        viewport._newton_preview_hook = True
