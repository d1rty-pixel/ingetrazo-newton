"""Newton page in the native preferences dialog (API 2 compatibility adapter)."""
import copy
import json
import uuid
from weakref import WeakKeyDictionary,ref
from PySide6.QtCore import QObject,QEvent,QSettings,QTimer,Qt
from PySide6.QtWidgets import (QWidget,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QCheckBox,QPushButton,
                               QLabel,QTabWidget,QScrollArea,QLineEdit,QFileDialog)
from .i18n import tr
from . import profiles
from . import help_texts as help


class ProfileDraft:
    """Keep profile edits local until the host preferences dialog is accepted."""
    def __init__(self):
        self.values = profiles.custom_profiles()

    def all_profiles(self):
        return profiles.builtins()+copy.deepcopy(self.values)

    def save_custom(self,profile):
        p = profiles.validate(profile)
        p["builtin"] = False
        if p["id"].startswith("builtin_"):
            p["id"] = uuid.uuid4().hex
        self.values = [v for v in self.values if v["id"]!=p["id"]]+[p]

    def delete_custom(self,identifier):
        self.values = [v for v in self.values if v["id"]!=identifier]


class SettingsPage:
    """One preferences tab: headed categories separated by a line; every setting explains itself."""
    def __init__(self,tabs,title,intro=None,pictograms=False):
        self.pictograms = pictograms
        area = QScrollArea();area.setWidgetResizable(True);area.setFrameShape(QFrame.NoFrame)
        content = QWidget();area.setWidget(content)
        self.box = QVBoxLayout(content);self.box.setSpacing(10)
        self.categories = 0
        if intro:
            note = QLabel(intro);note.setWordWrap(True);self.box.addWidget(note)
        tabs.addTab(area,title)

    def category(self,title):
        if self.categories or self.box.count():
            line = QFrame();line.setFrameShape(QFrame.HLine);line.setFrameShadow(QFrame.Sunken)
            self.box.addSpacing(4);self.box.addWidget(line)
        self.categories += 1
        heading = QLabel(title)
        font = heading.font();font.setBold(True);font.setPointSizeF(font.pointSizeF()*1.1);heading.setFont(font)
        self.box.addWidget(heading)

    def setting(self,art,label,control,description,extra=None):
        from .icons import attach
        row = QWidget();grid = QGridLayout(row);grid.setContentsMargins(0,2,0,2)
        grid.setHorizontalSpacing(12);grid.setVerticalSpacing(3);grid.setColumnStretch(2,1)
        if self.pictograms:
            image = QLabel();image.setFixedWidth(44);image.setAlignment(Qt.AlignTop|Qt.AlignHCenter)
            if art:attach(image,art,40)
            grid.addWidget(image,0,0,2,1)
        if label:
            name = QLabel(label);name.setMinimumWidth(150);name.setBuddy(control)
            grid.addWidget(name,0,1,Qt.AlignTop);grid.addWidget(control,0,2)
        else:
            grid.addWidget(control,0,1,1,2)
        text = QLabel(description);text.setWordWrap(True)
        if extra is not None:        # full-width content between the control and its explanation
            grid.addWidget(extra,1,1,1,2)
        grid.addWidget(text,2,1,1,2)
        control.setToolTip(description)
        self.box.addWidget(row)

    def finish(self):
        self.box.addStretch()


class NewtonPreferences(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        self.setObjectName("newton_preferences")
        self.draft = ProfileDraft()
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget();layout.addWidget(self.tabs)

        page = SettingsPage(self.tabs,tr("Appearance"))
        page.category(tr("Collision display"))
        self.colliders = QCheckBox(tr("Show collision shapes in new windows"))
        self.colliders.setChecked(str(QSettings().value("newton/show_colliders_by_default",False)).lower() in ("true","1"))
        page.setting(None,None,self.colliders,tr(help.SHOW_COLLIDERS))
        self.shortcuts_button = QPushButton(tr("Configure collision display shortcut…"))
        self.shortcuts_button.setEnabled(getattr(panel,"collision_action",None) is not None)
        self.shortcuts_button.clicked.connect(self.configure_shortcut)
        page.setting(None,None,self.shortcuts_button,tr(help.COLLIDER_SHORTCUT))
        page.finish()

        page = SettingsPage(self.tabs,tr("Simulation"),tr(help.SIMULATION),pictograms=True)
        page.category(tr("Accuracy"))
        from .range_control import RangeControl,scroll_safe
        self.quality = scroll_safe(QComboBox())
        for label,key in (("Quick","quick"),("Balanced","balanced"),("Precise","precise")):self.quality.addItem(tr(label),key)
        self.quality.setCurrentIndex(max(0,self.quality.findData(QSettings().value("newton/quality","balanced"))))
        page.setting("quality",tr("Quality"),self.quality,tr(help.QUALITY))
        page.category(tr("Hidden geometry"))
        from .model import hidden_mode
        self.hidden = scroll_safe(QComboBox())
        for label,key in (("When needed","needed"),("Always","always"),("Never","never")):self.hidden.addItem(tr(label),key)
        self.hidden.setCurrentIndex(max(0,self.hidden.findData(hidden_mode())))
        page.setting("hidden_geometry",tr("Include"),self.hidden,tr(help.HIDDEN_GEOMETRY))
        from .environment_ui import number,global_damping
        page.category(tr("Gravity and ground"))
        self.gravity = number(-100,100,panel.gravity.value());self.gravity.setSuffix(" m/s²")
        page.setting("gravity",tr("Gravity Z"),RangeControl(self.gravity,-100,100),tr(help.GRAVITY))
        self.floor = QCheckBox(tr("Ground at Z = 0"));self.floor.setChecked(panel.floor.isChecked())
        page.setting("ground",None,self.floor,tr(help.GROUND))
        self.warn_ground = QCheckBox(tr("Warn about bodies below Z = 0"))
        self.warn_ground.setChecked(str(QSettings().value("newton/warn_ground_contact",True)).lower() in ("true","1"))
        page.setting("ground_below",None,self.warn_ground,tr(help.WARN_GROUND))
        page.category(tr("Damping"))
        linear,angular = global_damping()
        self.linear,self.angular = number(0,100,linear),number(0,100,angular)
        self.linear.setSuffix(" /s");self.angular.setSuffix(" /s")
        page.setting("linear_damping",tr("Linear damping"),self.linear,tr(help.LINEAR_DAMPING))
        page.setting("angular_damping",tr("Angular damping"),self.angular,tr(help.ANGULAR_DAMPING))
        page.finish()

        from .profile_ui import ProfileEditor
        self.profiles = ProfileEditor(panel,repository=self.draft)
        # Preferences manage presets; applying them stays in the model sidebar.
        self.profiles.apply_button.hide()
        self.tabs.addTab(self.profiles,tr("Profiles"))

        page = SettingsPage(self.tabs,tr("Runtime"))
        page.category(tr("Python environment"))
        self.python = QLineEdit(panel.python.text())
        browse = QPushButton(tr("Choose runtime…"));browse.clicked.connect(self.browse)
        from .runtime_ui import RuntimeSetupBox
        setup = RuntimeSetupBox(self.python)
        control = QWidget();column = QVBoxLayout(control);column.setContentsMargins(0,0,0,0)
        column.addWidget(self.python)       # buttons below: one row does not fit the 420 px page
        row = QHBoxLayout();column.addLayout(row)
        row.addWidget(browse);row.addWidget(setup.verify);row.addStretch()
        page.setting(None,tr("Python with MuJoCo"),control,tr(help.RUNTIME),extra=setup.log)
        page.category(tr("Set up automatically"))
        page.setting(None,None,setup,tr(help.RUNTIME_SETUP))
        page.category(tr("Manual installation"))
        from .runtime_ui import link_label
        page.setting(None,None,link_label(tr("Follow the {link} to set up Python and MuJoCo yourself.")),tr(help.RUNTIME_MANUAL))
        page.finish()

    def commit(self):
        from .profile_sync import execute
        command = self.profiles.prepare_sync()
        st = QSettings()
        st.setValue("newton/show_colliders_by_default",self.colliders.isChecked())
        st.setValue("newton/gravity_z",self.gravity.value())
        st.setValue("newton/floor",self.floor.isChecked())
        st.setValue("newton/warn_ground_contact",self.warn_ground.isChecked())
        st.setValue("newton/quality",self.quality.currentData())
        st.setValue("newton/hidden_geometry",self.hidden.currentData())
        st.setValue("newton/linear_damping",self.linear.value())
        st.setValue("newton/angular_damping",self.angular.value())
        st.setValue("newton/python",self.python.text().strip())
        st.setValue(profiles.STORE,json.dumps(self.draft.values,ensure_ascii=False,allow_nan=False))
        st.sync()
        execute(self.panel,command)
        self.panel.refresh_profiles()
        if self.panel.profile_manager is not None:
            self.panel.profile_manager.refresh()
        self.panel.refresh_icons()
        self.panel.show_colliders.setChecked(self.colliders.isChecked())
        self.panel.gravity.setValue(self.gravity.value());self.panel.floor.setChecked(self.floor.isChecked())
        self.panel.python.setText(self.python.text().strip())
        self.panel.selection_signature = None
        self.panel.refresh();self.panel.collision_view.request()

    def browse(self):
        path,_ = QFileDialog.getOpenFileName(self,tr("Choose Python with MuJoCo"),self.python.text(),tr("Python (python.exe python);;All files (*)"))
        if path:self.python.setText(path)

    def configure_shortcut(self):
        dialog = self.window()
        if hasattr(dialog,"show_shortcut_of"):
            dialog.show_shortcut_of(self.panel.collision_action)


_panels = WeakKeyDictionary()


def install_preferences(panel):
    """Add a page only for extension-owning windows; keep host navigation intact.

    API 2 has no preferences registration hook. Wrap its dialog class once,
    leaving open_preferences, shortcuts, units navigation and host accept intact.
    """
    from views import preferences_dialog as host
    _panels[panel.app.window] = ref(panel)
    if getattr(host.PreferencesDialog,"_newton_adapter",False):
        return
    original = host.PreferencesDialog

    class PreferencesWithNewton(original):
        _newton_adapter = True

        def __init__(self,window):
            super().__init__(window)
            owner_ref = _panels.get(window)
            owner = owner_ref() if owner_ref is not None else None
            if owner is not None:
                self.newton_page = NewtonPreferences(owner)
                self._tabs.addTab(self.newton_page,tr("Newton"))
                self.accepted.connect(self.newton_page.commit)

        def accept(self):
            if hasattr(self,'newton_page'):
                try:self.newton_page.profiles.prepare_sync()
                except (ValueError,TypeError,KeyError) as exc:
                    page = self.newton_page
                    self._tabs.setCurrentWidget(page);page.tabs.setCurrentWidget(page.profiles)
                    page.profiles.message.setText(tr(str(exc)))
                    return
            super().accept()

    host.PreferencesDialog = PreferencesWithNewton


class PaletteWatcher(QObject):
    def __init__(self,panel):
        super().__init__(panel)
        self.panel = panel
        self.pending = False

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.PaletteChange,QEvent.ApplicationPaletteChange,QEvent.ThemeChange) and not self.pending:
            self.pending = True
            QTimer.singleShot(0,self.refresh)
        return False

    def refresh(self):
        self.pending = False
        self.panel.refresh_icons()
