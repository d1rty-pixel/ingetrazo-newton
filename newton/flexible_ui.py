"""Compact material editor; a selected grouped polyline supplies the path."""
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox
from .environment_ui import number
from . import units
from .model import settings,reference_id
from .i18n import tr
from .toolbar import decorate,physical_label
from .flexible import validate,centre_line
from .reference_table import ReferenceTable,ChooseButton
from .glow import offer


class FlexibleEditor(QWidget):
    def __init__(self,panel):
        super().__init__();self.panel = panel;self.group = None;self.updating = False
        form = QFormLayout(self);form.setContentsMargins(0,0,0,0);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.kind = QComboBox()
        for title,key in (("Rigid","rigid"),("Rope","rope"),("Cable","cable")):self.kind.addItem(tr(title),key)
        decorate(self.kind,"flexible")
        form.addRow(tr("Material"),self.kind)
        self.fields = QWidget();detail = QFormLayout(self.fields);detail.setContentsMargins(0,0,0,0)
        # Long labels move above their field in a narrow sidebar instead of widening it.
        detail.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.radius = number(.001,10,.015)
        self.bend,self.twist,self.damping = number(0,1e10,2e4),number(0,1e10,1e4),number(0,100,.002)
        for title,widget,art in (("Radius",self.radius,"radius"),("Bending modulus",self.bend,"bending"),
                                 ("Torsion modulus",self.twist,"torsion"),("Joint damping",self.damping,"joint_damping")):
            detail.addRow(physical_label(tr(title),art),widget)
        self.bend.setSuffix(" Pa");self.twist.setSuffix(" Pa")
        self.start = QComboBox()
        for title,key in (("Clamped","fixed"),("Pinned","pinned"),("Free","free")):self.start.addItem(tr(title),key)
        decorate(self.start,"attachment")
        detail.addRow(physical_label(tr("Start")),self.start)
        self.end_uid = None
        self.end = ChooseButton(tr("Choose…"),self.end_candidates,self.attach_end,tr("No suitable body"),lambda g:offer(panel,g))
        self.end_table = ReferenceTable(lambda _:self.attach_end(None),tr("Free"),panel)
        detail.addRow(physical_label(tr("End attachment")),self.end);detail.addRow(self.end_table)
        form.addRow(self.fields)
        self.kind.currentIndexChanged.connect(self.write)
        for field in (self.radius,self.bend,self.twist,self.damping):field.valueChanged.connect(self.write)
        self.start.currentIndexChanged.connect(self.write)

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            raw = settings(group).get("flexible") if group else None
            cfg = raw or {}
            self.kind.setCurrentIndex(self.kind.findData(cfg.get("kind","rigid")))
            self.fields.setVisible(bool(raw))
            scale = units.length();units.apply(self.radius,scale,scale.show(.001),scale.show(10))
            units.show(self.radius,cfg.get("radius",.015))
            for widget,key,value in ((self.bend,"bend",2e4),(self.twist,"twist",1e4),(self.damping,"damping",.002)):
                widget.setValue(cfg.get(key,value))
            self.start.setCurrentIndex(self.start.findData(cfg.get("start","fixed")))
            self.end_uid = cfg.get("end_reference")
            end = next((g for g in self.panel.app.scene.groups if g.uid==self.end_uid),None)
            self.end_table.set_rows([(self.end_uid,end,end.name if end else tr("Missing body"),"")] if self.end_uid else [])
        finally:self.updating = False

    def end_candidates(self):
        from .panel import body_mode
        # body_mode, not the stored mode: an unconfigured face-me figure (the scale person) never simulates.
        for g in self.panel.app.scene.groups:
            if g is not self.group and not settings(g).get("flexible") and body_mode(g)!="ignore":yield g.uid,g,g.name

    def attach_end(self,uid):
        self.end_uid = uid;self.write()

    def write(self,*args):
        if self.updating or self.group is None or self.panel.session.workspace:return
        try:
            if self.kind.currentData()=="rigid":cfg = None
            else:
                old = settings(self.group).get("flexible") or {}
                points = old.get("points") or centre_line(self.group)
                if old.get("kind")!=self.kind.currentData():
                    self.updating = True
                    try:
                        bend = 2e6 if self.kind.currentData()=="cable" else 2e4
                        self.bend.setValue(bend);self.twist.setValue(bend/2)
                    finally:self.updating = False
                cfg = validate(dict(kind=self.kind.currentData(),points=points,radius=units.stored(self.radius),source=old.get("source","line" if not old else "mesh"),
                    bend=self.bend.value(),twist=self.twist.value(),damping=self.damping.value(),
                    start=self.start.currentData(),end_reference=self.end_uid))
                if settings(self.group).get("joint"):raise ValueError("Flexible bodies cannot also have a motion axis.")
            patch = dict(flexible=cfg,**(dict(mode="dynamic") if cfg else {}))
            if cfg and cfg["start"]=="free" and reference_id(self.group):patch["reference"] = None
            self.panel.patch(patch,[self.group])
        except (ValueError,TypeError) as exc:
            self.panel.status_message(str(exc));self.refresh(self.group)
