"""A compact axis picker; coupling details stay in the folded Axis coupling section."""
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox,QDoubleSpinBox
from PySide6.QtGui import QVector3D
from .model import settings,joint_rows
from .worker import joint_settings,resolve_couplings
from .i18n import tr
from .toolbar import decorate,physical_label
from .reference_table import ReferenceTable,ChooseButton
from .glow import offer
from .range_control import scroll_safe
from . import help_texts as help


class CouplingEditor(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        self.updating = False
        self.form = form = QFormLayout(self)
        form.setContentsMargins(0,0,0,0)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.group,self.joint,self.axes,self.leader = None,None,{},None
        self.master = ChooseButton(tr("Choose…"),self.candidates,self.follow,tr("No suitable axis"),lambda g:offer(panel,g))
        self.table = ReferenceTable(lambda _:self.follow(None),tr("Independent"),panel)
        self.direction = QComboBox()
        self.direction.addItem(tr("Same direction"),1)
        self.direction.addItem(tr("Opposite direction"),-1)
        decorate(self.direction,"direction")
        self.ratio = scroll_safe(QDoubleSpinBox())
        self.ratio.setRange(.001,100)
        self.ratio.setDecimals(3)
        self.ratio.setValue(1)
        self.ratio.setKeyboardTracking(False)
        form.addRow(physical_label(tr("Follow axis")),self.master)
        form.addRow(self.table)
        form.addRow(physical_label(tr("Direction")),self.direction)
        form.addRow(physical_label(tr("Ratio"),"ratio"),self.ratio)
        self.direction.activated.connect(self.change)
        self.ratio.valueChanged.connect(self.change)

    def refresh(self,group):
        self.updating = True
        self.group = group
        try:
            j = joint_settings(settings(group)["joint"]) if group and settings(group).get("joint") else None
            self.setEnabled(bool(j))
            self.axes = {r["uid"]:r for r in joint_rows(self.panel.app.scene)}
            self.joint = j
            c = j.get("coupling") if j else None
            self.leader = c["master"] if c and c["master"] in self.axes else None
            if self.leader:
                sign = self.orientation(j,self.axes[self.leader])
                self.direction.setCurrentIndex(0 if c["ratio"]*sign>0 else 1)
                self.ratio.setValue(abs(c["ratio"]))
            else:
                self.ratio.setValue(1)
            row = self.axes.get(self.leader)
            body = next((g for g in self.panel.app.scene.groups if g.uid==self.leader),None)
            self.table.set_rows([(self.leader,body,row["body"],row["name"])] if row else [])
            linked = self.leader is not None
            self.direction.setEnabled(linked)
            self.ratio.setEnabled(linked)
            self.form.setRowVisible(self.direction,linked)
            self.form.setRowVisible(self.ratio,linked)
        finally:
            self.updating = False

    def engaged(self):
        """Following an axis or leading at least one."""
        if self.group is None:
            return False
        return self.leader is not None or any((row.get("coupling") or {}).get("master")==self.group.uid
                                              for row in self.axes.values())

    def description(self):
        followers = [row["body"] for row in self.axes.values()
                     if self.group and (row.get("coupling") or {}).get("master")==self.group.uid]
        if followers:
            return tr(help.COUPLING_LEADER,bodies=", ".join(followers))
        if self.leader:
            return tr(help.COUPLING_FOLLOWER)
        return tr(help.COUPLING_FREE)

    def candidates(self):
        j = self.joint
        if not j:
            return
        for uid,row in self.axes.items():
            if uid!=self.group.uid and row["type"]==j["type"] and row["drive"] in ("position","velocity") and not row.get("coupling"):
                body = next((g for g in self.panel.app.scene.groups if g.uid==uid),None)
                yield uid,body,row["body"]+" · "+row["name"]

    def follow(self,uid):
        self.leader = uid
        self.change()

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
        uid = self.leader
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
