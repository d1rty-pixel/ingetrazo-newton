"""A small profile manager; profiles are independent of the open document."""
from PySide6.QtCore import Qt
import copy
import uuid
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QListWidget,QListWidgetItem,QInputDialog,QLabel,QSplitter
from .i18n import tr
from . import profiles
from . import help_texts as help
from .profile_parameters import ProfileParameters
from . import profile_sync
from .model import settings


class ProfileEditor(QWidget):
    def __init__(self,panel,repository=profiles):
        super().__init__()
        self.panel = panel
        self.repository = repository
        self.sync_ids = set()
        self.sync_scene = None
        self.pending_links = {}
        layout = QVBoxLayout(self)
        note = QLabel(tr(help.PROFILES));note.setWordWrap(True);layout.addWidget(note)
        split = QSplitter()
        self.list = QListWidget()
        self.list.setMinimumWidth(150)
        split.addWidget(self.list)
        self.parameters = ProfileParameters(panel,self.save_parameters)
        split.addWidget(self.parameters);split.setStretchFactor(1,2)
        layout.addWidget(split,1)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.apply_button = QPushButton(tr("Apply to selection"))
        self.save_button = QPushButton(tr("Save selection as…"))
        self.apply_button.clicked.connect(self.apply)
        self.save_button.clicked.connect(self.save_selection)
        row.addWidget(self.apply_button)
        row.addWidget(self.save_button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.rename_button = QPushButton(tr("Rename"))
        self.update_button = QPushButton(tr("Replace from selection"))
        self.delete_button = QPushButton(tr("Delete"))
        self.duplicate_button = QPushButton(tr("Duplicate…"))
        self.duplicate_button.clicked.connect(self.duplicate);row.addWidget(self.duplicate_button)
        for w,callback in ((self.rename_button,self.rename),(self.update_button,self.replace),(self.delete_button,self.delete)):
            w.clicked.connect(callback)
            row.addWidget(w)
        layout.addLayout(row)
        self.sync_button = QPushButton(tr("Sync linked bodies"))
        self.sync_button.setCheckable(repository is not profiles)
        self.sync_button.clicked.connect(self.sync_linked);layout.addWidget(self.sync_button)
        self.link_button = QPushButton(tr('Link selection without changing values'))
        self.link_button.clicked.connect(self.link_selection);layout.addWidget(self.link_button)
        self.list.currentRowChanged.connect(self.selection_changed)
        self.refresh()

    def selection_changed(self,*args):
        self.parameters.load(self.current());self.update_buttons()

    def save_parameters(self,profile):
        p = self.current()
        if not p or p['builtin']:return False
        self.repository.save_custom(profile)
        index = self.list.currentRow();self.values[index] = profile
        self.list.item(index).setText(profile['name'])
        if self.repository is profiles:self.panel.refresh_profiles()
        return True

    def duplicate(self):
        p = self.current()
        if not p:return
        name,ok = QInputDialog.getText(self,tr('Save profile'),tr('Name'),text=tr(p['name']) if p['builtin'] else p['name'])
        if ok and name.strip():
            value = copy.deepcopy(p);value.update(id=uuid.uuid4().hex,name=name,builtin=False)
            self.repository.save_custom(value);self.refresh()
            self.list.setCurrentRow(len(self.values)-1)

    def linked(self,identifier):
        return [g for g in self.panel.app.scene.groups if self.pending_links.get(g.uid,(settings(g).get('profile_link') or {}).get('id'))==identifier]

    def link_selection(self):
        p = self.current();groups = self.panel.selected()
        if not p or not groups or self.panel.session.workspace:return
        if self.repository is profiles:
            from .model import Configure
            from core.history import CompoundCommand
            profile_sync.execute(self.panel,CompoundCommand([Configure([g],profile_sync.association_values(g,p),partial=True) for g in groups]))
        else:
            self.sync_scene = self.panel.app.scene
            self.pending_links.update({g.uid:p['id'] for g in groups})
            self.message.setText(tr('Profile link queued for OK. Object values stay unchanged.'))
        self.update_buttons()

    def sync_linked(self):
        p = self.current()
        if not p or self.panel.session.workspace:return
        try:
            if self.repository is profiles:
                profile_sync.execute(self.panel,profile_sync.command(self.panel.app.scene,{g.uid:p for g in self.linked(p['id'])}))
                self.message.setText(tr('Linked bodies synced.'))
            else:
                self.sync_scene = self.panel.app.scene
                if p['id'] in self.sync_ids:
                    self.sync_ids.remove(p['id']);self.message.clear()
                else:
                    self.sync_ids.add(p['id'])
                    self.message.setText(tr('Sync queued for OK. Local values will be overwritten.'))
                self.update_buttons()
        except (ValueError,TypeError,KeyError) as exc:self.message.setText(tr(str(exc)))

    def prepare_sync(self):
        if self.parameters.error:raise ValueError(self.parameters.error)
        if not self.sync_ids and not self.pending_links:return None
        if self.panel.session.workspace or self.panel.app.scene is not self.sync_scene:raise ValueError('Document changed.')
        available = {p['id']:p for p in self.repository.all_profiles()}
        if (self.sync_ids|set(self.pending_links.values()))-set(available):raise ValueError('Missing profile')
        from .model import Configure
        from core.history import CompoundCommand
        if set(self.pending_links)-{g.uid for g in self.sync_scene.groups}:raise ValueError('Document changed.')
        commands = [Configure([g],profile_sync.association_values(g,available[self.pending_links[g.uid]]),partial=True)
            for g in self.sync_scene.groups if g.uid in self.pending_links]
        updates = {}
        for g in self.sync_scene.groups:
            identifier = self.pending_links.get(g.uid,(settings(g).get('profile_link') or {}).get('id'))
            if identifier in self.sync_ids:updates[g.uid] = available[identifier]
        sync = profile_sync.command(self.sync_scene,updates)
        if sync:commands.append(sync)
        return CompoundCommand(commands) if commands else None

    def current(self):
        index = self.list.currentRow()
        return self.values[index] if 0<=index<len(self.values) else None

    def refresh(self):
        index = self.list.currentRow()
        previous = self.current()['id'] if hasattr(self,'values') and self.current() else None
        self.list.blockSignals(True)
        self.values = self.repository.all_profiles()
        self.list.clear()
        for p in self.values:
            name = tr(p["name"]) if p["builtin"] else p["name"]
            item = QListWidgetItem(name+(" · "+tr("Built-in") if p["builtin"] else ""))
            item.setData(Qt.UserRole,p["id"])
            self.list.addItem(item)
        index = next((i for i,p in enumerate(self.values) if p['id']==previous),max(0,min(index,len(self.values)-1)))
        self.list.setCurrentRow(index)
        self.list.blockSignals(False)
        self.selection_changed()
        if self.repository is profiles:
            self.panel.refresh_profiles()

    def update_buttons(self,*args):
        p = self.current()
        selected = len(self.panel.selected())==1 and not self.panel.session.workspace
        self.apply_button.setEnabled(bool(p) and selected)
        self.save_button.setEnabled(selected)
        self.rename_button.setEnabled(bool(p) and not p["builtin"])
        self.delete_button.setEnabled(bool(p) and not p["builtin"])
        self.update_button.setEnabled(bool(p) and not p["builtin"] and selected)
        count = len(self.linked(p['id'])) if p else 0
        self.sync_button.setText(tr('Sync linked bodies ({count})',count=count))
        self.sync_button.setEnabled(bool(count) and not self.panel.session.workspace)
        self.sync_button.setChecked(bool(p) and p['id'] in self.sync_ids)
        self.duplicate_button.setEnabled(bool(p))
        self.link_button.setEnabled(bool(p) and bool(self.panel.selected()) and not self.panel.session.workspace)

    def apply(self):
        p = self.current()
        if p:
            self.panel.apply_profile(p)

    def save_selection(self):
        groups = self.panel.selected()
        if len(groups)!=1:
            return
        name,ok = QInputDialog.getText(self,tr("Save profile"),tr("Name"),text=groups[0].name)
        if ok and name.strip():
            self.repository.save_custom(profiles.from_group(groups[0],name))
            self.refresh()

    def rename(self):
        p = self.current()
        if not p or p["builtin"]:
            return
        name,ok = QInputDialog.getText(self,tr("Rename profile"),tr("Name"),text=p["name"])
        if ok and name.strip():
            self.repository.save_custom(dict(p,name=name))
            self.refresh()

    def replace(self):
        p,groups = self.current(),self.panel.selected()
        if p and not p["builtin"] and len(groups)==1:
            value = profiles.from_group(groups[0],p["name"])
            value["id"] = p["id"]
            self.repository.save_custom(value)
            self.refresh()

    def delete(self):
        p = self.current()
        if p and not p["builtin"]:
            self.sync_ids.discard(p['id'])
            self.pending_links = {uid:identifier for uid,identifier in self.pending_links.items() if identifier!=p['id']}
            self.repository.delete_custom(p["id"])
            self.refresh()


class ProfileManager(QDialog):
    """Compact save-from-selection dialog, sharing the preferences editor."""
    def __init__(self,panel):
        super().__init__(panel.app.window)
        self.setWindowTitle(tr("Newton profiles"))
        self.resize(850,680)
        layout = QVBoxLayout(self)
        self.editor = ProfileEditor(panel)
        layout.addWidget(self.editor)

    def __getattr__(self,name):
        # Preserve the shared editor API for callers and selection updates.
        editor = self.__dict__.get("editor")
        if editor is not None:
            return getattr(editor,name)
        raise AttributeError(name)
