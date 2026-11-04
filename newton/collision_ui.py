"""Pick pairwise contact exemptions in the model; one undoable command."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QPushButton
from core.history import CompoundCommand
from .model import KEY,settings,Configure
from .interaction import ReferencePickTool
from .reference_table import ReferenceTable
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
        self.table = ReferenceTable(self.restore,panel=panel)
        self.add = QPushButton(tr("Exempt body…"))
        self.add.clicked.connect(self.pick)
        layout.addWidget(self.table);layout.addWidget(self.add)

    def refresh(self):
        groups = self.panel.selected()
        self.group = groups[0] if len(groups)==1 else None
        self.setVisible(self.group is not None)
        others = [g for g in self.panel.app.scene.groups if g is not self.group and excludes(self.group,g)] if self.group else []
        self.table.set_rows([(g.uid,g,g.name,"") for g in others])

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

    def restore(self,uid):
        if self.group is None or self.panel.session.workspace:return
        other = next((g for g in self.panel.app.scene.groups if g.uid==uid),None)
        if other:
            self.panel.app.viewport.history.execute(pair_command(self.group,other,True))
            self.panel.app.viewport.notify_scene_changed()
