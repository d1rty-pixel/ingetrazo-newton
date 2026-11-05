"""Keep the pose: write the bodies' simulated frames into the model as one undo step."""
import copy

from PySide6.QtCore import QSettings
from PySide6.QtGui import QMatrix4x4

from core.history import Command

from .i18n import tr
from .model import settings
from .references import TransformDependent, carries_metadata, carry_metadata, different

SETTING = "newton/keep_pose"


def enabled():
    return QSettings().value(SETTING, False, type=bool)


def deltas(session):
    """``{uid: matrix}`` moving each simulated body from its model pose to its pose now; None when the geometry changed.

    The body frame sits at the joint pivot (or the centre), so the delta is that frame
    times the translation back to the origin, applied from the left like a native move.
    """
    from .session import changed_meshes
    workspace = session.workspace
    if changed_meshes(workspace.marks):
        return None    # Workspace.left reports it; this must not hide that error
    result = {}
    for uid, spec in session.specs.items():
        if not spec["mass"] > 0:
            continue
        origin = spec["joint"]["pivot"] if spec.get("joint") else spec["center"]
        back = QMatrix4x4()
        back.translate(*[-v for v in origin])
        matrix = workspace.scene.frames[uid]*back
        if different(matrix, QMatrix4x4()):
            result[uid] = matrix
    return result


def command(scene, moved):
    """The undoable write of ``moved``; ValueError (fail-closed) when a body cannot simply be moved."""
    bodies = {g.uid: g for g in scene.groups}
    moves = []
    for uid, matrix in moved.items():
        group = bodies.get(uid)
        if group is None:
            raise ValueError(tr("A flexible body cannot keep its pose."))
        if getattr(group, "locked", False):
            raise ValueError(tr("The body \"{name}\" is locked.", name=group.name))
        if group.xform is None and group.children:
            raise ValueError(tr("The body \"{name}\" contains groups and cannot be moved this way.", name=group.name))
        moves.append((group, matrix))
    return KeepPose(moves) if moves else None


class KeepPose(Command):
    keeps_paint = True

    def __init__(self, moves):
        self.moves = [TransformDependent(group, matrix) for group, matrix in moves]
        self.before, self.after = [], []
        for group, matrix in moves:
            if carries_metadata(group):
                self.before.append((group, copy.deepcopy(group.ext)))
                carry_metadata(group, matrix)
                self.after.append((group, copy.deepcopy(group.ext)))
                group.ext = copy.deepcopy(self.before[-1][1])

    def do(self, scene):
        for cmd in self.moves:
            cmd.do(scene)
        for group, ext in self.after:
            group.ext = copy.deepcopy(ext)

    def undo(self, scene):
        for cmd in reversed(self.moves):
            cmd.undo(scene)
        for group, ext in self.before:
            group.ext = copy.deepcopy(ext)
