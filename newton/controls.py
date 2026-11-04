"""Named, live controls in a reusable non-modal window."""
import math
from PySide6.QtCore import Qt,QPoint
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QScrollArea,
    QWidget, QGroupBox, QHBoxLayout, QDoubleSpinBox,QPushButton)
from .i18n import tr
from .icons import icon,pixmap


def display_units(joint):
    if joint["type"] == "hinge":
        return 180/math.pi, "°" if joint["drive"] != "velocity" else "°/s"
    return 1000, "mm" if joint["drive"] != "velocity" else "mm/s"


class Controls(QDialog):
    def __init__(self, panel):
        super().__init__(panel.app.window)
        self.panel = panel
        self.setWindowTitle(tr("Newton controls"))
        self.setMinimumWidth(520)
        self.resize(520, 260)
        self.layout = QVBoxLayout(self)
        self.hint_row = QWidget()
        hint_layout = QHBoxLayout(self.hint_row);hint_layout.setContentsMargins(0,0,0,0)
        self.hint_mark = QLabel();self.hint_mark.setAlignment(Qt.AlignTop)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setTextFormat(Qt.PlainText)
        hint_layout.addWidget(self.hint_mark);hint_layout.addWidget(self.hint,1)
        self.layout.addWidget(self.hint_row)
        self.hint_row.hide()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.layout.addWidget(self.scroll)
        row = QHBoxLayout()
        self.start_button = QPushButton(icon("play"),tr("Start"))
        self.reset_button = QPushButton(icon("reset"),tr("Reset"))
        self.start_button.clicked.connect(self.start)
        self.reset_button.clicked.connect(panel.session.reset)
        row.addWidget(self.start_button)
        row.addWidget(self.reset_button)
        self.layout.addLayout(row)
        self.time_label = QLabel()
        self.layout.addWidget(self.time_label)
        self.performance_label = QLabel();self.performance_label.setWordWrap(True)
        self.layout.addWidget(self.performance_label);self.performance_label.hide()
        panel.session.metrics.connect(self.show_performance)
        panel.session.frame.connect(lambda seconds:self.time_label.setText(tr("Time: {seconds:.2f} s",seconds=seconds)))
        panel.session.message.connect(self.message)
        self.rows = {}
        self.actual_columns = []
        self.range_controls = []
        self.signature = None

    def refresh(self, joints, active):
        joints = [j for j in joints if j["drive"]!="free" and not j.get("coupling")]
        signature = (repr(joints), active)
        if signature != self.signature:
            self.signature = signature
            widget = QWidget()
            layout = QVBoxLayout(widget)
            self.rows = {}
            self.actual_columns = []
            self.range_controls = []
            if not joints:
                label = QLabel(tr("No actuators"))
                label.setWordWrap(True)
                layout.addWidget(label)
            for joint in joints:
                group = QGroupBox(joint["body"]+" "+joint["name"])
                gl = QVBoxLayout(group)
                actual = QLabel(tr("Actual: —"))
                actual.setTextFormat(Qt.PlainText)
                actual.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
                factor, unit = display_units(joint)
                mapping = (joint.get("display") or {})
                scale,offset = mapping.get("scale",1),mapping.get("offset",0)
                if joint["drive"] != "free":
                    if joint["drive"] == "position":
                        low, high = joint["lower"]*factor, joint["upper"]*factor
                        if not joint["limited"]:
                            low, high = (-180,180) if joint["type"] == "hinge" else (-1000,1000)
                    else:
                        extent = joint["max_speed"]*factor
                        low, high = -extent, extent
                    low,high = sorted((low*scale+offset*factor,high*scale+offset*factor))
                    row = QHBoxLayout()
                    row.setSpacing(10)
                    value = QDoubleSpinBox()
                    value.setRange(low, high)
                    value.setDecimals(1)
                    value.setSuffix(" " + unit)
                    target = (self.panel.session.targets.get(joint["uid"], joint["target"])*scale+offset)*factor
                    value.setValue(target)
                    from .range_control import RangeControl
                    control = RangeControl(value,low,high)
                    control.set_span(low,high,expand=False)
                    slider = control.slider
                    value.valueChanged.connect(lambda n, uid=joint["uid"], f=factor,s=scale,o=offset: self.panel.session.set_target(uid, (n/f-o)/s))
                    value.valueChanged.connect(lambda n,uid=joint["uid"]:self.highlight_axis(uid))
                    slider.sliderPressed.connect(lambda uid=joint["uid"]:self.highlight_axis(uid))
                    self.actual_columns.append(actual)
                    self.range_controls.append(control)
                    row.addWidget(actual)
                    row.addWidget(control,1)
                    gl.addLayout(row)
                    slider.setEnabled(active)
                    value.setEnabled(active)
                self.rows[joint["uid"]] = (actual, joint, factor)
                layout.addWidget(group)
            layout.addStretch()
            old = self.scroll.takeWidget()
            self.scroll.setWidget(widget)
            if old:
                old.deleteLater()
            self.align_values()
            self.fit_height()
        self.start_button.setText(tr("Pause") if active and self.panel.session.running else tr("Resume") if active else tr("Start"))
        self.start_button.setEnabled(not active or self.panel.session.ready)
        self.reset_button.setEnabled(active)
        if not active:
            self.time_label.setText(tr("Time: {seconds:.2f} s",seconds=0))
        self.refresh_icons()

    def refresh_icons(self):
        self.start_button.setIcon(icon("pause" if self.panel.session.running else "play"))
        self.reset_button.setIcon(icon("reset"))
        for control in self.range_controls:control.refresh_style()

    def highlight_axis(self,uid):
        self.panel.detail_uid = uid
        self.panel.app.viewport.update()

    def start(self):
        self.panel.start_or_pause()

    def message(self,text,level="info"):
        self.hint.setText(tr(text))
        self.hint_mark.setVisible(level in ("error","warning"))
        if level in ("error","warning"):
            self.hint_mark.setPixmap(pixmap("status_error" if level=="error" else "status_warning",18))
            self.hint_mark.setAccessibleName(tr("Error") if level=="error" else tr("Warning"))
        self.hint_row.show()
        self.fit_height()

    MARGIN = 12

    def place(self,viewport):
        """Top right corner of the 3D view, next to the sidebar, the same gap above and to the right."""
        corner = viewport.mapToGlobal(QPoint(viewport.width(),0))
        self.height_limit = max(200,viewport.height()-2*self.MARGIN)
        self.fit_height()
        frame = self.frameGeometry().size()-self.geometry().size()
        self.move(corner.x()-self.width()-frame.width()-self.MARGIN,corner.y()+self.MARGIN)

    def fit_height(self):
        # As tall as the cards need, up to the 3D view's height; beyond that the cards scroll.
        content = self.scroll.widget()
        if content is None:
            return
        # setWidget() does not invalidate the layout's cached hint of the scroll area.
        self.scroll.updateGeometry()
        chrome = self.layout.sizeHint().height()-self.scroll.sizeHint().height()
        wanted = chrome+content.sizeHint().height()+2*self.scroll.frameWidth()
        width = max(self.width(),self.minimumSizeHint().width())
        self.resize(width,min(getattr(self,"height_limit",600),wanted))

    def telemetry(self, data):
        for uid, state in data.items():
            if uid in self.rows:
                label, joint, factor = self.rows[uid]
                value = state["velocity"] if joint["drive"] == "velocity" else state["position"]
                mapping = (joint.get("display") or {})
                value = value*mapping.get("scale",1)+mapping.get("offset",0)
                label.setText(tr("Actual: {value:.1f} {unit}",value=value*factor,unit=display_units(joint)[1]))
                target = (state.get("target",joint["target"])*mapping.get("scale",1)+mapping.get("offset",0))*factor
                command = (state.get("command",state.get("target",joint["target"]))*mapping.get("scale",1)+mapping.get("offset",0))*factor
                label.setToolTip(tr("Target: {target:.1f} · Ramp: {command:.1f} · Load: {load:.0f}%",target=target,command=command,load=state.get("load",0)*100))
                label.setStyleSheet("color: #e79b38" if state.get("at_limit") else "")
                if state.get("at_limit"):label.setText(label.text()+" · "+tr("Limit"))
        self.align_values()

    def show_performance(self,metrics):
        if self.performance_label.isHidden()==bool(metrics):
            self.performance_label.setVisible(bool(metrics))
            self.fit_height()
        if not metrics:return
        speed = metrics.get("speed")
        text = tr("Paused") if metrics.get("paused") else tr("{speed:.2f}× real time",speed=speed) if speed is not None else tr("Measuring…")
        self.performance_label.setText(text)
        self.performance_label.setToolTip(tr("Newton: {newton:.1f} ms\nDisplay preparation: {ui:.1f} ms\nRound trip: {roundtrip:.1f} ms\nBodies: {bodies} · Contacts: {contacts}\nSolver iterations: {iterations} · Substeps: {substeps}",
            newton=metrics.get("newton_ms",0),ui=metrics.get("ui_ms",0),roundtrip=metrics.get("roundtrip_ms",0),
            bodies=metrics.get("bodies",0),contacts=metrics.get("contacts",0),iterations=metrics.get("iterations",0),substeps=metrics.get("substeps",1)))

    def align_values(self):
        # Equal actual-value columns keep every fader aligned; RangeControl
        # supplies the same 104 px right-hand input and styling as the sidebar.
        if not self.actual_columns:
            return
        width = max(max(label.minimumWidth(),label.sizeHint().width()) for label in self.actual_columns)
        for label in self.actual_columns:label.setFixedWidth(width)
        self.setMinimumWidth(max(520,width+370))
