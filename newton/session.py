"""Async external-engine bridge and temporary simulation document."""
from __future__ import annotations
from .i18n import tr

import json
import math
import time
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtGui import QMatrix4x4, QQuaternion
from core.history import History
from . import keep_pose
from .worker import joint_settings


def worker_environment():
    """The bundle's LD_LIBRARY_PATH must not reach the runtime's own interpreter."""
    from PySide6.QtCore import QProcessEnvironment
    from .runtime_setup import clean_env
    env = QProcessEnvironment()
    for key,value in clean_env().items():
        env.insert(key,value)
    return env


class ReadOnlyHistory(History):
    """Refuses every command before it runs.

    The host's rollback only restores the active mesh, so a command that
    touched any other mesh could not be taken back once it had run.
    """

    def __init__(self, scene, refused):
        super().__init__(scene)
        self.refused = refused

    def execute(self, cmd):
        self.last_error = None
        self.last_rejected = tr("The model cannot be edited during the simulation. Reset the simulation first.")
        self.refused(self.last_rejected)


def mesh_marks(scene):
    """What every mesh in ``scene`` looks like now, cheaply (see ``changed_meshes``)."""
    from core.purge import iter_groups
    meshes = {id(scene.mesh): scene.mesh}
    for g in iter_groups(scene.groups):
        if g.mesh is not None:
            meshes[id(g.mesh)] = g.mesh
    return {key: (m, m._mut_serial, len(m.vertices), len(m.edges), len(m.faces))
            for key, m in meshes.items()}


def pending_redraws(scene):
    """Render flags the document view has not consumed yet; drawing a clone clears them on the shared mesh."""
    from core.purge import iter_groups
    defaults = {"_chunk_dirty": True, "_attrs_dirty": False}  # As the host's renderer reads them.
    return [(g.mesh, flag) for g in iter_groups(scene.groups) for flag, default in defaults.items() if getattr(g.mesh, flag, default)]


def changed_meshes(marks):
    """Meshes whose geometry changed since ``mesh_marks``.

    Winding and face attributes change without a mark; ReadOnlyHistory is
    what keeps those out.
    """
    return [m for m, *mark in marks.values()
            if mark != [m._mut_serial, len(m.vertices), len(m.edges), len(m.faces)]]


class Workspace:
    allowed_tools = {"select"}  # navigation/selection, no modelling tools

    def __init__(self, session, scene):
        self.session = session
        self.scene = scene
        self.history = ReadOnlyHistory(scene, lambda text: session.message.emit(text, "warning"))
        self.marks = mesh_marks(scene)
        self.redraws = pending_redraws(session.app.scene)

    def title(self):
        return tr("Newton — temporary simulation")

    def is_dirty(self):
        return False

    def save(self):
        self.session.message.emit(tr("The model cannot be saved during the simulation. Reset the simulation first."),"warning")
        return False

    save_as = save

    def confirm_leave(self):
        return True

    def new(self):
        self.session.reset(keep=False)

    def left(self):
        self.session.stop_worker()
        self.session.workspace = None
        for mesh, flag in self.redraws:
            setattr(mesh, flag, True)
        self.session.changed.emit()
        # After changed: the panel then says "The simulation was reset and the original model is restored.", which must not hide this.
        if changed_meshes(self.marks):
            self.session.message.emit(tr("The geometry changed during the simulation. Check the model before saving it."), "error")


class Session(QObject):
    changed = Signal()
    message = Signal(str,str)  # text, level: info, warning or error
    frame = Signal(float)
    telemetry = Signal(object)
    metrics = Signal(object)
    targets_changed = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.workspace = None
        self.process = None
        self.running = False
        self.ready = False
        self.pending = False
        self.buffer = b""
        self.stderr = ""
        self.movers = {}
        self.elapsed = 0.0
        self.targets = {}
        self.virtual = {}
        self.virtual_values = {}
        self.bindings = []
        self.sequences = {}
        self.step_serial = 0
        self.joint_states = {}
        self.colliders = {}
        self.drag = None
        self.drag_serial = 0
        self.specs = {}
        from .performance import RealtimeMeter
        self.meter = RealtimeMeter();self.performance = {}
        self.original_set_tool = None
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.watchdog = QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.timeout.connect(lambda: self.fail(tr("The Newton process did not answer within 15 seconds. The simulation was reset.")))

    def start(self, python, scene, specs, movers, gravity, floor,linear_damping=0,angular_damping=0,quality="balanced",controls=(),bindings=()):
        if self.workspace or self.app.workspace() is not None:
            raise ValueError(tr("The simulation cannot start while another workspace is open. Close that workspace first."))
        if not Path(python).is_file():
            raise ValueError(tr("No Newton runtime was found. Set it up under Preferences > Newton > Runtime."))
        self.movers = movers
        self.specs = {s["uid"]:s for s in specs}
        self.targets = {s["uid"]: joint_settings(s["joint"])["target"]
                          for s in specs if s.get("joint") and not s["joint"].get("coupling")}
        self.virtual = {c["id"]: c for c in controls}
        self.virtual_values = {}
        self.bindings = list(bindings)
        self.sequences = {}
        for control in controls:
            self.set_virtual(control["id"], control["initial"], one_by_one=False)
        self.workspace = Workspace(self, scene)
        if not self.app.enter_workspace(self.workspace):
            self.workspace = None
            raise ValueError(tr("The simulation workspace could not be opened, so the simulation did not start."))
        # SimulationScene refuses too; this only replaces the host's "Editing …" status.
        self.app.viewport.begin_group_edit = lambda group: self.message.emit(
            tr("The model cannot be edited during the simulation. Reset the simulation first."), "warning")
        self.ready, self.running, self.pending = False, True, False
        self.meter.reset();self.performance = {}
        self.buffer, self.stderr = b"", ""
        process = self.process = QProcess(self)
        process.setProgram(python)
        process.setProcessEnvironment(worker_environment())
        # -E: the host's PYTHONPATH (e.g. Flatpak's /app site-packages) must not leak into the worker's interpreter.
        process.setArguments(["-E", "-u", str(Path(__file__).with_name("worker.py"))])
        process.setWorkingDirectory(str(Path(__file__).parent))
        process.started.connect(lambda: self.send(dict(op="init", bodies=specs,
                                                       gravity=gravity, floor=floor,
                                                       linear_damping=linear_damping,angular_damping=angular_damping,quality=quality)))
        process.readyReadStandardOutput.connect(self.read)
        process.readyReadStandardError.connect(self.read_stderr)
        process.errorOccurred.connect(lambda error: self.fail(
            tr("The Newton process failed: {error}. The simulation was reset.",error=process.errorString()))
            if self.process is process else None)
        process.finished.connect(lambda code, status: self.fail(
            (tr("The Newton process stopped unexpectedly (exit code {code}). The simulation was reset.",code=code)
             +" "+self.stderr[-1500:]).rstrip())
            if self.process is process else None)
        process.start()
        self.watchdog.start(15000)
        self.changed.emit()

    def send(self, payload):
        if self.process is None:
            return
        self.pending = True
        self.request_started = time.perf_counter()
        self.watchdog.start(15000)
        self.process.write((json.dumps(payload, allow_nan=False)+"\n").encode("utf-8"))

    def read_stderr(self):
        if self.process:
            self.stderr = (self.stderr + bytes(self.process.readAllStandardError()).decode("utf-8", "replace"))[-4000:]

    def read(self):
        if not self.process:
            return
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if not line.startswith(b"NEWTON:"):
                continue
            try:
                result = json.loads(line[len(b"NEWTON:"):])
                if not result.get("ok"):
                    raise ValueError(result.get("error", tr("The Newton process reported an error without details. The simulation was reset.")))
                self.pending = False
                self.watchdog.stop()
                self.apply(result)
                if not self.ready:
                    self.ready = True
                    self.last_tick = time.monotonic()
                    self.elapsed = 0.0
                    self.timer.start()
                    self.install_drag()
                    self.changed.emit()
            except Exception as exc:
                self.fail(str(exc))
                return

    def apply(self, result):
        started = time.perf_counter()
        if not self.workspace:
            return
        self.joint_states = result.get("joints",{})
        self.advance_sequences()
        if "colliders" in result:
            self.colliders = result["colliders"]
        for uid, (position, quaternion) in result["poses"].items():
            if not all(math.isfinite(v) for v in position + quaternion):
                raise ValueError(tr("The Newton process returned invalid body positions. The simulation was reset."))
            m = QMatrix4x4()
            m.translate(*position)
            x, y, z, w = quaternion
            m.rotate(QQuaternion(w, x, y, z))
            self.movers[uid].xform = self.workspace.scene.place(uid, m)
        # Only the throwaway scene changes. No history entry or model mutation.
        self.workspace.scene.version += 1
        self.app.viewport.update()
        self.frame.emit(result["time"])
        self.telemetry.emit(result.get("joints", {}))
        if "performance" in result:
            speed = self.meter.observe(result["time"],started) if self.running else None
            self.performance = dict(result["performance"],speed=speed,ui_ms=(time.perf_counter()-started)*1000,
                roundtrip_ms=(started-getattr(self,"request_started",started))*1000,paused=not self.running)
            self.metrics.emit(self.performance)

    def frame_of(self, uid):
        """The body frame of a simulated body; its mover's xform also holds the shared mesh's offset."""
        return self.workspace.scene.frames.get(uid) if self.workspace else None

    def tick(self):
        now = time.monotonic()
        delta, self.last_tick = now-self.last_tick, now
        if not self.running or not self.ready:
            return
        self.elapsed = min(self.elapsed + delta, .1)
        count = min(int(self.elapsed * 240), 24)
        if count and not self.pending:
            self.elapsed -= count/240
            self.step_serial += 1
            self.send(dict(op="step", count=count, targets=self.targets,drag=self.drag))

    def can_drag(self,uid):
        spec = self.specs.get(uid,{})
        joint = spec.get("joint")
        return spec.get("mass",0)>0 and (not joint or (joint_settings(joint)["drive"]=="free" and not joint.get("coupling")))

    def install_drag(self):
        from .interaction import DragTool
        vp = self.app.viewport
        self.drag_tool = DragTool(self)
        self.original_set_tool = vp.set_active_tool
        def set_tool(tool):
            if self.workspace and type(tool).__name__ == "SelectTool":
                tool = self.drag_tool
            self.original_set_tool(tool)
        vp.set_active_tool = set_tool
        vp.set_active_tool(self.drag_tool)

    def activate_drag(self):
        if self.ready and self.workspace:
            self.app.viewport.set_active_tool(self.drag_tool)

    def set_target(self, uid, value):
        if uid in self.targets and math.isfinite(float(value)):
            self.targets[uid] = float(value)

    def set_virtual(self, control_id, value, one_by_one=True):
        """``one_by_one=False`` at Start: the initial state applies at once, like every other start target."""
        from .virtual_controls import clamp, targets
        control = self.virtual.get(control_id)
        if control is None or not math.isfinite(float(value)):
            return
        self.virtual_values[control_id] = clamp(control, value)
        moves = list(targets(control, value).items())
        self.sequences.pop(control_id, None)
        if one_by_one and control.get("sequential") and control["kind"] == "switch" and moves:
            (uid, target), rest = moves[0], moves[1:]
            self.set_target(uid, target)
            self.sequences[control_id] = dict(waiting=uid, since=self.step_serial, rest=rest)
            return
        for uid, target in moves:
            self.set_target(uid, target)

    def press(self, slot):
        """A key slot was pressed: move every bound target one toggle or step."""
        if not (self.ready and self.workspace):
            return
        from .key_bindings import next_value, target_of
        changed = False
        for binding in self.bindings:
            if binding["slot"] == slot:
                down = False
            elif binding["mode"] == "step" and binding.get("slot_down") == slot:
                down = True
            else:
                continue
            kind, ident = target_of(binding)
            if kind == "joint":
                if ident not in self.targets:
                    continue
                self.set_target(ident, next_value(binding, self.targets[ident], down))
            else:
                control = self.virtual.get(ident)
                if control is None:
                    continue
                self.set_virtual(ident, next_value(binding, self.virtual_values.get(ident, control["initial"]), down))
            changed = True
        if changed:
            self.targets_changed.emit()

    def advance_sequences(self):
        """Start the next axis of a one-by-one switch once the previous axis's ramp has reached its target."""
        for control_id, sequence in list(self.sequences.items()):
            state = self.joint_states.get(sequence["waiting"])
            # A result from a step sent before the target was set says nothing about the new move.
            if self.step_serial <= sequence["since"] or state is None:
                continue
            if abs(state.get("command", state["target"])-state["target"]) > 1e-9:
                continue
            if not sequence["rest"]:
                del self.sequences[control_id]
                continue
            uid, target = sequence["rest"].pop(0)
            self.set_target(uid, target)
            sequence.update(waiting=uid, since=self.step_serial)

    def toggle(self):
        if self.ready:
            self.running = not self.running
            self.elapsed = 0.0
            self.last_tick = time.monotonic()
            self.meter.reset()
            self.metrics.emit(dict(self.performance,paused=not self.running))
            self.changed.emit()

    def reset(self, *_, keep=True):
        """Back to the model; with the keep-pose setting on, the simulated pose becomes the model's."""
        moved = None
        if self.workspace:
            if keep and keep_pose.enabled() and self.ready:
                moved = keep_pose.deltas(self)
            if self.app.workspace() is self.workspace:
                self.app.leave_workspace()
            else:
                self.stop_worker()
                self.workspace = None
        self.changed.emit()
        if moved:
            self.write_pose(moved)

    def write_pose(self, moved):
        # After changed: the panel then says "The simulation was reset and the original model is restored.", which must not hide this.
        try:
            cmd = keep_pose.command(self.app.scene, moved)
            if cmd is not None:
                self.app.viewport.history.execute(cmd)
        except ValueError as exc:
            self.message.emit(tr("The pose was not kept: {reason} The original model is restored.", reason=exc), "warning")
            return
        self.message.emit(tr("The simulated pose was written into the model. Undo restores the original pose."), "info")

    def stop_worker(self):
        self.timer.stop()
        self.watchdog.stop()
        process, self.process = self.process, None
        if process:
            process.kill()
            process.waitForFinished(1000)
            process.deleteLater()
        self.running = self.ready = self.pending = False
        self.movers = {}
        self.targets = {}
        self.virtual = {}
        self.virtual_values = {}
        self.bindings = []
        self.sequences = {}
        self.joint_states = {}
        self.colliders = {}
        self.drag = None
        self.specs = {}
        self.meter.reset();self.performance = {};self.metrics.emit({})
        self.app.viewport.__dict__.pop("begin_group_edit", None)
        if self.original_set_tool:
            self.app.viewport.set_active_tool = self.original_set_tool
            self.original_set_tool = None
            tool = getattr(self.app.window,"_tools",{}).get("select")
            if tool:
                self.app.viewport.set_active_tool(tool)

    def fail(self, text):
        self.reset(keep=False)
        self.message.emit(text,"error")
