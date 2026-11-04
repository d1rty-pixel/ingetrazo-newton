"""A compact axis picker; coupling details stay under More settings."""
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox,QDoubleSpinBox
from PySide6.QtGui import QVector3D
from .model import settings,joint_rows
from .worker import joint_settings,resolve_couplings
from .i18n import tr
from . import help_texts as help


class CouplingEditor(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        self.updating = False
        self.form = form = QFormLayout(self)
        form.setContentsMargins(0,0,0,0)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.master = QComboBox()
        self.direction = QComboBox()
        self.direction.addItem(tr("Same direction"),1)
        self.direction.addItem(tr("Opposite direction"),-1)
        self.ratio = QDoubleSpinBox()
        self.ratio.setRange(.001,100)
        self.ratio.setDecimals(3)
        self.ratio.setValue(1)
        self.ratio.setKeyboardTracking(False)
        form.addRow(tr("Follow axis"),self.master)
        form.addRow(tr("Direction"),self.direction)
        form.addRow(tr("Ratio"),self.ratio)
        self.master.activated.connect(self.change)
        self.direction.activated.connect(self.change)
        self.ratio.valueChanged.connect(self.change)

    def refresh(self,group):
        self.updating = True
        self.group = group
        try:
            j = joint_settings(settings(group)["joint"]) if group and settings(group).get("joint") else None
            self.setEnabled(bool(j))
            self.master.clear()
            self.master.addItem(tr("Independent"),None)
            self.axes = {r["uid"]:r for r in joint_rows(self.panel.app.scene)}
            if j:
                for uid,row in self.axes.items():
                    if uid!=group.uid and row["type"]==j["type"] and row["drive"]=="position" and not row.get("coupling"):
                        self.master.addItem(row["body"]+" · "+row["name"],uid)
                c = j.get("coupling")
                if c and c["master"] in self.axes:
                    self.master.setCurrentIndex(max(0,self.master.findData(c["master"])))
                    sign = self.orientation(j,self.axes[c["master"]])
                    self.direction.setCurrentIndex(0 if c["ratio"]*sign>0 else 1)
                    self.ratio.setValue(abs(c["ratio"]))
                else:
                    self.ratio.setValue(1)
            linked = self.master.currentData() is not None
            self.direction.setEnabled(linked)
            self.ratio.setEnabled(linked)
            self.form.setRowVisible(self.direction,linked)
            self.form.setRowVisible(self.ratio,linked)
        finally:
            self.updating = False

    def description(self):
        followers = [row["body"] for row in self.axes.values()
                     if self.group and (row.get("coupling") or {}).get("master")==self.group.uid]
        if followers:
            return tr(help.COUPLING_LEADER,bodies=", ".join(followers))
        if self.master.currentData():
            return tr(help.COUPLING_FOLLOWER)
        return tr(help.COUPLING_FREE)

    @staticmethod
    def orientation(a,b):
        return 1 if QVector3D.dotProduct(QVector3D(*a["axis"]),QVector3D(*b["axis"]))>=0 else -1

    def change(self,*args):
        if self.updating or self.panel.session.workspace:
            return
        groups = self.panel.selected()
        if len(groups)!=1 or not settings(groups[0]).get("joint"):
            return
        group = groups[0]
        j = joint_settings(settings(group)["joint"])
        uid = self.master.currentData()
        j["coupling"] = (dict(master=uid,ratio=self.orientation(j,self.axes[uid])*self.direction.currentData()*self.ratio.value())
                         if uid else None)
        try:
            joints = {r["uid"]:r for r in joint_rows(self.panel.app.scene)}
            joints[group.uid] = j
            resolve_couplings(joints)
            self.panel.commit_joint(self.panel.app.scene,group,j)
        except ValueError as exc:
            self.panel.status_message(tr(str(exc)))
            self.refresh(group)
