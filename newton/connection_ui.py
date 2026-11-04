"""One compact editor for point, pin and rigid connections."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget,QFormLayout,QHBoxLayout,QPushButton,QComboBox,QLabel,QCheckBox
from views.fold_section import narrow
from .environment_ui import number
from .model import settings
from .connections import KINDS,apply_connection,begin
from .interaction import ReferencePickTool
from .reference_table import ReferenceTable
from .i18n import tr
from .toolbar import decorate,pictogram_check


class ConnectionEditor(QWidget):
    def __init__(self,panel):
        super().__init__();self.panel = panel;self.group = None;self.updating = False
        form = QFormLayout(self);form.setContentsMargins(0,0,0,0);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.kind = QComboBox()
        for key,title in KINDS.items():self.kind.addItem(tr(title),key)
        decorate(self.kind,"connection")
        form.addRow(tr("Type"),self.kind)
        self.target = ReferenceTable(lambda _:self.detach());form.addRow(self.target)
        self.add = QPushButton(tr("Connect…"));form.addRow(self.add)
        self.fields = QWidget();detail = self.detail = QFormLayout(self.fields);detail.setContentsMargins(0,0,0,0)
        detail.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.point = [number(-1e9,1e9) for _ in range(3)];self.axis = [number(-1,1) for _ in range(3)]
        for axis,point in zip("XYZ",self.point):
            point.setSuffix(" mm");detail.addRow(tr("Point {axis}",axis=axis),point)
        self.axis_fields = QWidget();axes = QHBoxLayout(self.axis_fields);axes.setContentsMargins(0,0,0,0)
        # Three fields side by side must shrink with the sidebar.
        narrow(*self.axis)
        for label,field in zip("XYZ",self.axis):axes.addWidget(QLabel(label));axes.addWidget(field)
        detail.addRow(tr("Pin axis"),self.axis_fields);form.addRow(self.fields)
        self.lock = pictogram_check(QCheckBox(tr("Lock connection object")),"lock")
        self.lock.setToolTip(tr("Locks the connection object in the model so that no tool moves or rotates it by accident. It still follows its body."))
        self.lock.toggled.connect(lambda on:panel.lock_marker("connection_of",on))
        form.addRow(self.lock)
        self.kind.currentIndexChanged.connect(lambda:self.write("type"))
        for index,field in enumerate(self.point):field.valueChanged.connect(lambda _,i=index:self.write("point",i))
        for index,field in enumerate(self.axis):field.valueChanged.connect(lambda _,i=index:self.write("axis",i))
        self.add.clicked.connect(self.link)

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            value = settings(group).get("point_attachment") if group else None
            self.fields.setVisible(bool(value))
            self.add.setText(tr("Set linked body…") if value else tr("Connect…"))
            rows = []
            if value:
                self.kind.setCurrentIndex(self.kind.findData(value.get("type","ball")))
                target = next((g for g in self.panel.app.scene.groups if g.uid==value["target"]),None)
                rows.append((value["target"],target,target.name if target else tr("Missing body"),""))
            self.target.set_rows(rows)
            if value:
                for field,v in zip(self.point,value["point"]):field.setValue(v*1000)
                for field,v in zip(self.axis,value.get("axis",[0,1,0])):field.setValue(v)
            self.detail.setRowVisible(self.axis_fields,self.kind.currentData()=="hinge")
            self.lock.setVisible(bool(value))
            self.panel.refresh_lock(self.lock,group,"connection_of")
            # A locked object keeps its place; the number fields would move it all the same.
            self.fields.setEnabled(not self.lock.isChecked())
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

    def link(self):
        old = settings(self.group).get("point_attachment") if self.group else None
        if not old:
            begin(self.panel);return
        if self.panel.session.workspace:return
        panel,source,scene = self.panel,self.group,self.panel.app.scene
        def cancel():panel.app.window._activate_tool("select")
        def choose(target):
            if panel.app.scene is not scene or source not in scene.groups:raise ValueError(tr("Document changed."))
            # Only the linked body changes; point, type and pin axis stay where they were placed.
            apply_connection(panel,source,dict(old,target=target.uid))
            QTimer.singleShot(0,cancel)
        panel.app.viewport.set_active_tool(ReferencePickTool(choose,cancel))
        panel.status_message(tr("Pick the other body. Esc cancels."))

    def detach(self):
        if self.group:apply_connection(self.panel,self.group,None,"Connection removed.")
