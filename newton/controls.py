"""Named, live controls in a reusable non-modal window."""
import math
from PySide6.QtCore import Qt,QPoint,QSettings
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QScrollArea,
    QWidget, QGroupBox, QHBoxLayout, QDoubleSpinBox,QPushButton,QCheckBox,QButtonGroup)
from .i18n import tr
from . import help_texts as help
from .icons import icon,pixmap
from .reference_table import ReferenceTable
from .toolbar import pictogram_check
from .units import signature as units_signature, SPAN_METRES

MAX_BODY_ROWS = 6
KEEP_KEY = "newton/keep_warnings_on_reset"


def keep_on_reset():
    return str(QSettings().value(KEEP_KEY,False)).lower() in ("true","1")


def display_units(joint):
    """Scale of the target and the actual value; the suffix has no leading space."""
    from dataclasses import replace
    from . import units
    velocity = joint["drive"] == "velocity"
    if joint["type"] == "hinge":
        return replace(units.ANGLE_RATE if velocity else units.ANGLE,decimals=1)
    return units.speed() if velocity else units.length()


class Controls(QDialog):
    def __init__(self, panel):
        super().__init__(panel.app.window)
        self.panel = panel
        self.ending_silently = False
        self.setWindowTitle(tr("Newton controls"))
        self.setMinimumWidth(520)
        self.resize(520, 260)
        self.layout = QVBoxLayout(self)
        self.hint_row = QWidget()
        rows = QVBoxLayout(self.hint_row);rows.setContentsMargins(0,0,0,0)
        text_row = QWidget();rows.addWidget(text_row)
        hint_layout = QHBoxLayout(text_row);hint_layout.setContentsMargins(0,0,0,0)
        self.hint_mark = QLabel();self.hint_mark.setAlignment(Qt.AlignTop)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setTextFormat(Qt.PlainText)
        hint_layout.addWidget(self.hint_mark);hint_layout.addWidget(self.hint,1)
        self.bodies = ReferenceTable(None,panel=panel)
        rows.addWidget(self.bodies);self.bodies.hide()
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
        self.edit_button = QPushButton(tr("Virtual controls…"))
        self.edit_button.setToolTip(tr(help.VIRTUAL_CONTROLS))
        self.edit_button.clicked.connect(lambda:panel.edit_virtual_controls())
        row.addWidget(self.edit_button)
        self.keep = pictogram_check(QCheckBox(tr("Keep warnings and errors on reset")),"keep_warnings")
        self.keep.setToolTip(tr(help.KEEP_WARNINGS))
        self.keep.setChecked(keep_on_reset())
        self.keep.toggled.connect(lambda on:QSettings().setValue(KEEP_KEY,on))
        row.addWidget(self.keep,1)
        self.layout.addLayout(row)
        self.time_label = QLabel()
        self.layout.addWidget(self.time_label)
        self.performance_label = QLabel();self.performance_label.setWordWrap(True)
        self.layout.addWidget(self.performance_label);self.performance_label.hide()
        panel.session.metrics.connect(self.show_performance)
        panel.session.frame.connect(lambda seconds:self.time_label.setText(tr("Time: {seconds:.2f} s",seconds=seconds)))
        panel.session.message.connect(self.message)
        self.rows = {}
        self.virtual_cards = {}
        self.actual_columns = []
        self.range_controls = []
        self.signature = None
        self.kept = None

    def refresh(self, joints, active):
        from .virtual_controls import managed
        virtual = self.panel.virtual_controls()
        taken = managed(virtual)
        joints = [j for j in joints if j["drive"]!="free" and not j.get("coupling") and j["uid"] not in taken]
        signature = (repr(joints), repr(virtual), active, units_signature())
        if signature != self.signature:
            self.signature = signature
            widget = QWidget()
            layout = QVBoxLayout(widget)
            self.rows = {}
            self.virtual_cards = {}
            self.actual_columns = []
            self.range_controls = []
            if not joints and not virtual:
                label = QLabel(tr("No actuators"))
                label.setWordWrap(True)
                layout.addWidget(label)
            for control in virtual:
                layout.addWidget(self.virtual_card(control,active))
            for joint in joints:
                group = QGroupBox(joint["body"]+" "+joint["name"])
                gl = QVBoxLayout(group)
                actual = QLabel(tr("Actual: —"))
                actual.setTextFormat(Qt.PlainText)
                actual.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
                shown = display_units(joint)
                factor = shown.factor
                mapping = (joint.get("display") or {})
                scale,offset = mapping.get("scale",1),mapping.get("offset",0)
                if joint["drive"] != "free":
                    if joint["drive"] == "position":
                        low, high = joint["lower"]*factor, joint["upper"]*factor
                        if not joint["limited"]:
                            low, high = (-180,180) if joint["type"] == "hinge" else (-shown.show(SPAN_METRES),shown.show(SPAN_METRES))
                    else:
                        extent = joint["max_speed"]*factor
                        low, high = -extent, extent
                    low,high = sorted((low*scale+offset*factor,high*scale+offset*factor))
                    row = QHBoxLayout()
                    row.setSpacing(10)
                    value = QDoubleSpinBox()
                    value.setRange(low, high)
                    value.setDecimals(shown.decimals)
                    value.setSuffix(shown.suffix)
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
                self.rows[joint["uid"]] = (actual, joint, shown)
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
        self.edit_button.setEnabled(not active)
        if not active:
            self.time_label.setText(tr("Time: {seconds:.2f} s",seconds=0))
        self.refresh_icons()

    def virtual_card(self, control, active):
        from .virtual_controls import clamp
        from .range_control import RangeControl
        group = QGroupBox(control["name"])
        row = QHBoxLayout(group)
        value = clamp(control,self.panel.session.virtual_values.get(control["id"],control["initial"]))
        def change(v,control_id=control["id"]):
            self.panel.session.set_virtual(control_id,v)
        if control["kind"] == "switch":
            buttons = QButtonGroup(group)
            for index,state in enumerate(control["states"]):
                button = QPushButton(state["name"])
                button.setCheckable(True)
                button.setChecked(index == value)
                button.setEnabled(active)
                buttons.addButton(button,index)
                row.addWidget(button)
            buttons.idClicked.connect(change)
        else:
            number = QDoubleSpinBox()
            number.setRange(0,100)
            number.setDecimals(0)
            number.setSuffix(" %")
            number.setValue(value*100)
            slider = RangeControl(number,0,100)
            slider.set_span(0,100,expand=False)
            number.valueChanged.connect(lambda n:change(n/100))
            slider.slider.setEnabled(active)
            number.setEnabled(active)
            self.range_controls.append(slider)
            row.addWidget(slider,1)
        self.virtual_cards[control["id"]] = group
        return group

    def refresh_icons(self):
        self.start_button.setIcon(icon("pause" if self.panel.session.running else "play"))
        self.reset_button.setIcon(icon("reset"))
        for control in self.range_controls:control.refresh_style()

    def highlight_axis(self,uid):
        self.panel.detail_uid = uid
        self.panel.app.viewport.update()

    def start(self):
        self.panel.start_or_pause()

    def message(self,text,level="info",bodies=()):
        """``bodies``: ``(group, name, role)`` rows listed below the text, so a long list stays readable."""
        if level in ("error","warning"):
            self.kept = (text,level,[(getattr(group,"uid",None),name,role) for group,name,role in bodies])
        self.hint.setText(tr(text))
        rows = [(i,group,name,role) for i,(group,name,role) in enumerate(bodies[:MAX_BODY_ROWS])]
        if len(bodies)>MAX_BODY_ROWS:
            rows.append((None,None,tr("… and {count} more",count=len(bodies)-MAX_BODY_ROWS),""))
        self.bodies.set_rows(rows)
        self.bodies.setVisible(bool(rows))
        self.hint_mark.setVisible(level in ("error","warning"))
        if level in ("error","warning"):
            self.hint_mark.setPixmap(pixmap("status_error" if level=="error" else "status_warning",18))
            self.hint_mark.setAccessibleName(tr("Error") if level=="error" else tr("Warning"))
        self.hint_row.show()
        self.fit_height()

    def restore_kept(self,scene):
        """Show the last warning again after Reset; the rows then point at the restored document's groups, not at clones."""
        text,level,rows = self.kept
        groups = {g.uid:g for g in scene.groups}
        self.message(text,level,[(groups[uid] if uid is not None else None,name,role)
                                 for uid,name,role in rows if uid is None or uid in groups])

    MARGIN = 12

    def done(self,result):
        # X, Esc and close() all end here; shutdown must not reset a session it already stopped.
        super().done(result)
        session = self.panel.session
        if session.workspace and not self.ending_silently:
            session.reset()

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
                label, joint, shown = self.rows[uid]
                factor = shown.factor
                digits = shown.decimals
                value = state["velocity"] if joint["drive"] == "velocity" else state["position"]
                mapping = (joint.get("display") or {})
                value = value*mapping.get("scale",1)+mapping.get("offset",0)
                label.setText(tr("Actual: {value} {unit}",value=f"{value*factor:.{digits}f}",unit=shown.unit))
                target = (state.get("target",joint["target"])*mapping.get("scale",1)+mapping.get("offset",0))*factor
                command = (state.get("command",state.get("target",joint["target"]))*mapping.get("scale",1)+mapping.get("offset",0))*factor
                label.setToolTip(tr("Target: {target} · Ramp: {command} · Load: {load:.0f}%",target=f"{target:.{digits}f}",command=f"{command:.{digits}f}",load=state.get("load",0)*100))
                label.setStyleSheet("color: #e79b38" if state.get("at_limit") else "")
                if state.get("at_limit"):label.setText(label.text()+" · "+tr("At limit"))
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
