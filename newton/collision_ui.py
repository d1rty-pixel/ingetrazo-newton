"""Pick pairwise contact exceptions in the model; one undoable command."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QListWidget,QListWidgetItem
from core.history import CompoundCommand
from .model import KEY,settings,Configure
from .interaction import ReferencePickTool
from .i18n import tr


def excludes(a,b):
    return b.uid in settings(a).get("no_collision",[]) or a.uid in settings(b).get("no_collision",[])


def pair_command(a,b,enabled):
    commands = []
    for group,other in ((a,b),(b,a)):
        cfg = settings(group)
        links = set(cfg.get("no_collision",[]))
        if enabled:links.discard(other.uid)
        else:links.add(other.uid)
        values = dict(no_collision=sorted(links))
        if KEY not in (group.ext or {}):values["mode"] = "ignore" if group.billboard else "static"
        commands.append(Configure([group],values,partial=True))
    return CompoundCommand(commands)


class CollisionPairs(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        layout = QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.list = QListWidget();self.list.setMaximumHeight(100)
        layout.addWidget(self.list)
        row = QHBoxLayout()
        self.add = QPushButton(tr("Exclude body…"))
        self.remove = QPushButton(tr("Remove exception"))
        self.add.clicked.connect(self.pick);self.remove.clicked.connect(self.restore)
        self.list.currentRowChanged.connect(lambda:self.remove.setEnabled(self.list.currentItem() is not None))
        row.addWidget(self.add);row.addWidget(self.remove);layout.addLayout(row)

    def refresh(self):
        groups = self.panel.selected()
        self.group = groups[0] if len(groups)==1 else None
        self.setVisible(self.group is not None)
        self.list.clear()
        if self.group:
            for other in self.panel.app.scene.groups:
                if other is not self.group and excludes(self.group,other):
                    item = QListWidgetItem(other.name);item.setData(Qt.UserRole,other.uid);self.list.addItem(item)
        self.list.setVisible(self.list.count()>0)
        self.remove.setVisible(self.list.count()>0)
        self.remove.setEnabled(False)

    def pick(self):
        if not self.group or self.panel.session.workspace:return
        source,scene = self.group,self.panel.app.scene
        def cancel():self.panel.app.window._activate_tool("select")
        def choose(other):
            if other is source:return
            if self.panel.app.scene is not scene or source not in scene.groups:raise ValueError(tr("Document changed."))
            self.panel.app.viewport.history.execute(pair_command(source,other,False))
            self.panel.app.viewport.notify_scene_changed()
            QTimer.singleShot(0,cancel)
        self.panel.app.viewport.set_active_tool(ReferencePickTool(choose,cancel))
        self.panel.status_message(tr("Pick the body that should pass through this body. Esc cancels."))

    def restore(self):
        item = self.list.currentItem()
        if item is None or self.group is None or self.panel.session.workspace:return
        other = next((g for g in self.panel.app.scene.groups if g.uid==item.data(Qt.UserRole)),None)
        if other:
            self.panel.app.viewport.history.execute(pair_command(self.group,other,True))
            self.panel.app.viewport.notify_scene_changed()
