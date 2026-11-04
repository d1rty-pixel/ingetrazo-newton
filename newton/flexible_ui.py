"""Compact material editor; a selected grouped polyline supplies the path."""
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox
from .environment_ui import number
from .model import settings,reference_id
from .i18n import tr
from .flexible import validate,centre_line


class FlexibleEditor(QWidget):
    def __init__(self,panel):
        super().__init__();self.panel = panel;self.group = None;self.updating = False
        form = QFormLayout(self);form.setContentsMargins(0,0,0,0)
        self.kind = QComboBox()
        for title,key in (("Rigid","rigid"),("Rope","rope"),("Cable","cable")):self.kind.addItem(tr(title),key)
        form.addRow(tr("Material"),self.kind)
        self.fields = QWidget();detail = QFormLayout(self.fields);detail.setContentsMargins(0,0,0,0)
        self.radius = number(.001,10,.015);self.radius.setSuffix(" m")
        self.bend,self.twist,self.damping = number(0,1e10,2e4),number(0,1e10,1e4),number(0,100,.002)
        for title,widget in (("Radius",self.radius),("Bending modulus",self.bend),("Torsion modulus",self.twist),("Joint damping",self.damping)):
            detail.addRow(tr(title),widget)
        self.bend.setSuffix(" Pa");self.twist.setSuffix(" Pa")
        self.start = QComboBox()
        for title,key in (("Clamped","fixed"),("Pinned","pinned"),("Free","free")):self.start.addItem(tr(title),key)
        detail.addRow(tr("Start"),self.start)
        self.end = QComboBox();detail.addRow(tr("End attachment"),self.end)
        form.addRow(self.fields)
        self.kind.currentIndexChanged.connect(self.write)
        for field in (self.radius,self.bend,self.twist,self.damping):field.valueChanged.connect(self.write)
        self.start.currentIndexChanged.connect(self.write);self.end.currentIndexChanged.connect(self.write)

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            raw = settings(group).get("flexible") if group else None
            cfg = raw or {}
            self.kind.setCurrentIndex(self.kind.findData(cfg.get("kind","rigid")))
            self.fields.setVisible(bool(raw))
            for widget,key,value in ((self.radius,"radius",.015),(self.bend,"bend",2e4),(self.twist,"twist",1e4),(self.damping,"damping",.002)):
                widget.setValue(cfg.get(key,value))
            self.start.setCurrentIndex(self.start.findData(cfg.get("start","fixed")))
            self.end.clear();self.end.addItem(tr("Free"),None)
            for g in self.panel.app.scene.groups:
                if g is not group and not settings(g).get("flexible") and settings(g)["mode"]!="ignore":self.end.addItem(g.name,g.uid)
            self.end.setCurrentIndex(max(0,self.end.findData(cfg.get("end_reference"))))
        finally:self.updating = False

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
                cfg = validate(dict(kind=self.kind.currentData(),points=points,radius=self.radius.value(),source=old.get("source","line" if not old else "mesh"),
                    bend=self.bend.value(),twist=self.twist.value(),damping=self.damping.value(),
                    start=self.start.currentData(),end_reference=self.end.currentData()))
                if settings(self.group).get("joint"):raise ValueError("Flexible bodies cannot also have a motion axis.")
            patch = dict(flexible=cfg,**(dict(mode="dynamic") if cfg else {}))
            if cfg and cfg["start"]=="free" and reference_id(self.group):patch["reference"] = None
            self.panel.patch(patch,[self.group])
        except (ValueError,TypeError) as exc:
            self.panel.status_message(str(exc));self.refresh(self.group)
