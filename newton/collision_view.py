"""Optional collider wireframes from the same external worker as simulation."""
import json
from pathlib import Path
from PySide6.QtCore import QObject,QProcess,QTimer,Signal,Qt,QPointF
from PySide6.QtGui import QMatrix4x4,QQuaternion,QVector3D,QColor,QPen,QPolygonF
from .model import prepare,hidden_mode
from .i18n import tr


class CollisionView(QObject):
    changed = Signal()

    def __init__(self,panel):
        super().__init__(panel)
        self.panel = panel
        self.enabled = False
        self.overrides,self.override_scene = {},None
        self.key = None
        self.process = None
        self.colliders,self.poses = {},{}
        self.timer = QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(150)
        self.timer.timeout.connect(self.inspect)
        self.timeout = QTimer(self);self.timeout.setSingleShot(True);self.timeout.setInterval(15000)
        self.timeout.timeout.connect(self.failed)
        self.changed.connect(lambda:panel.app.viewport.update())

    def toggle(self,enabled):
        self.enabled = enabled
        self.key = None
        if self.active():self.request()
        else:self.stop()
        self.changed.emit()

    def body_overrides(self):
        """Per-body exceptions to the global setting, for this document only and never saved."""
        if self.override_scene!=id(self.panel.app.scene):
            self.overrides,self.override_scene = {},id(self.panel.app.scene)
        return self.overrides

    def shown(self,uid):
        return self.body_overrides().get(uid,self.enabled)

    def active(self):
        return self.enabled or any(self.body_overrides().values())

    def show_body(self,uid,shown):
        overrides = self.body_overrides()
        if shown==self.enabled:overrides.pop(uid,None)
        else:overrides[uid] = shown
        if self.active():self.request()
        self.changed.emit()

    def request(self):
        if not self.active() or self.panel.session.workspace:
            return
        key = (id(self.panel.app.scene),self.panel.app.scene.version,self.panel.python.text())
        if key!=self.key:
            self.key = key
            self.colliders,self.poses = {},{}
            self.stop()
            self.timer.start()

    def stop(self):
        self.timer.stop();self.timeout.stop()
        process,self.process = self.process,None
        if process:
            process.kill();process.waitForFinished(1000);process.deleteLater()

    def failed(self):
        self.stop()
        self.panel.status_message(tr("Could not inspect collision shapes. Check the Newton Runtime."))

    def inspect(self):
        if not self.active() or self.panel.session.workspace:return
        try:
            _,specs,_ = prepare(self.panel.app.scene,require_movable=False,hidden=hidden_mode())
            python = self.panel.python.text().strip()
            if not Path(python).is_file():raise ValueError()
            process = self.process = QProcess(self)
            self.buffer = b""
            process.setProgram(python)
            from .session import worker_environment
            process.setProcessEnvironment(worker_environment())
            process.setArguments(["-E","-u",str(Path(__file__).with_name("worker.py"))])
            process.started.connect(lambda:process.write((json.dumps(dict(op="init",bodies=specs,gravity=0,floor=False))+"\n").encode()))
            process.readyReadStandardOutput.connect(lambda:self.read(process))
            process.errorOccurred.connect(lambda error:self.failed() if self.process is process else None)
            self.timeout.start();process.start()
        except (ValueError,TypeError,KeyError):
            self.failed()

    def read(self,process):
        if self.process is not process:return
        self.buffer += bytes(process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line,self.buffer = self.buffer.split(b"\n",1)
            if not line.startswith(b"NEWTON:"):continue
            try:
                result = json.loads(line[len(b"NEWTON:"):])
                if not result.get("ok"):raise ValueError()
                self.colliders,self.poses = result["colliders"],result["poses"]
                self.stop();self.changed.emit()
            except (ValueError,KeyError):self.failed()
            return

    def draw(self,viewport,painter):
        if not self.active() or viewport is not self.panel.app.viewport:return
        session = self.panel.session
        colliders = session.colliders if session.workspace else self.colliders
        selected = {g.uid for g in self.panel.selected()}
        painter.save()
        for uid,shape in colliders.items():
            if not self.shown(uid):continue
            g = next((g for g in self.panel.app.scene.groups if g.uid==uid),None)
            if g is None or g.hidden or any(l.name==g.layer and not l.visible for l in self.panel.app.scene.layers):continue
            if session.workspace:
                matrix = session.frame_of(uid)
            else:
                pos,q = self.poses[uid]
                matrix = QMatrix4x4();matrix.translate(*pos);matrix.rotate(QQuaternion(q[3],*q[:3]))
            points = [list(matrix.map(QVector3D(*p)).toTuple()) for p in shape["points"]]
            if not points:continue
            xs,ys,front = viewport.world_to_pixels(points)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255,190,50,24) if uid in selected else QColor(20,180,230,24))
            for face in shape.get("faces",[]):
                if all(front[i] for i in face):
                    painter.drawPolygon(QPolygonF([QPointF(float(xs[i]),float(ys[i])) for i in face]))
            painter.setPen(QPen(QColor(255,190,50) if uid in selected else QColor(20,180,230),3 if uid in selected else 2))
            for a,b in shape["edges"]:
                if front[a] and front[b]:painter.drawLine(int(xs[a]),int(ys[a]),int(xs[b]),int(ys[b]))
        painter.restore()
