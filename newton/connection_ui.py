"""One compact editor for point, pin and rigid connections."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QFormLayout,QHBoxLayout,QPushButton,QComboBox,QLabel
from .environment_ui import number
from .model import settings
from .connections import KINDS,apply_connection,begin
from .i18n import tr
from .toolbar import decorate


class ConnectionEditor(QWidget):
    def __init__(self,panel):
        super().__init__();self.panel = panel;self.group = None;self.updating = False
        form = QFormLayout(self);form.setContentsMargins(0,0,0,0)
        self.kind = QComboBox()
        for key,title in KINDS.items():self.kind.addItem(tr(title),key)
        decorate(self.kind,"connection")
        form.addRow(tr("Type"),self.kind)
        row = QHBoxLayout();self.add = QPushButton(tr("Connect…"));self.remove = QPushButton(tr("Remove connection"))
        row.addWidget(self.add);row.addWidget(self.remove);form.addRow(row)
        self.target = QLabel();self.target.setWordWrap(True);self.target.setTextFormat(Qt.PlainText);form.addRow(self.target)
        self.fields = QWidget();detail = self.detail = QFormLayout(self.fields);detail.setContentsMargins(0,0,0,0)
        self.point = [number(-1e9,1e9) for _ in range(3)];self.axis = [number(-1,1) for _ in range(3)]
        for axis,point in zip("XYZ",self.point):
            point.setSuffix(" mm");detail.addRow(tr("Point {axis}",axis=axis),point)
        self.axis_fields = QWidget();axes = QHBoxLayout(self.axis_fields);axes.setContentsMargins(0,0,0,0)
        for label,field in zip("XYZ",self.axis):axes.addWidget(QLabel(label));axes.addWidget(field)
        detail.addRow(tr("Pin axis"),self.axis_fields);form.addRow(self.fields)
        self.kind.currentIndexChanged.connect(lambda:self.write("type"))
        for index,field in enumerate(self.point):field.valueChanged.connect(lambda _,i=index:self.write("point",i))
        for index,field in enumerate(self.axis):field.valueChanged.connect(lambda _,i=index:self.write("axis",i))
        self.add.clicked.connect(lambda:begin(panel));self.remove.clicked.connect(self.detach)

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            value = settings(group).get("point_attachment") if group else None
            self.fields.setVisible(bool(value));self.remove.setVisible(bool(value));self.target.setVisible(bool(value))
            self.add.setText(tr("Replace…") if value else tr("Connect…"))
            if value:
                self.kind.setCurrentIndex(self.kind.findData(value.get("type","ball")))
                target = next((g.name for g in self.panel.app.scene.groups if g.uid==value["target"]),tr("Missing body"))
                self.target.setText(target)
                for field,v in zip(self.point,value["point"]):field.setValue(v*1000)
                for field,v in zip(self.axis,value.get("axis",[0,1,0])):field.setValue(v)
            self.detail.setRowVisible(self.axis_fields,self.kind.currentData()=="hinge")
        finally:self.updating = False

    def write(self,key,index=None):
        self.detail.setRowVisible(self.axis_fields,self.kind.currentData()=="hinge")
        if self.updating or self.group is None or self.panel.session.workspace:return
        old = settings(self.group).get("point_attachment")
        if old:
            value = dict(old)
            if key=="type":value["type"] = self.kind.currentData()
            else:
                value[key] = list(old.get(key,[0,1,0]));value[key][index] = (self.point[index].value()/1000 if key=="point" else self.axis[index].value())
            try:apply_connection(self.panel,self.group,value)
            except (ValueError,TypeError) as exc:self.panel.status_message(str(exc));self.refresh(self.group)

    def detach(self):
        if self.group:apply_connection(self.panel,self.group,None)
