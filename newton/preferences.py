"""Newton page in the native preferences dialog (API 2 compatibility adapter)."""
import copy
import json
import uuid
from weakref import WeakKeyDictionary,ref
from PySide6.QtCore import QObject,QEvent,QSettings,QTimer
from PySide6.QtWidgets import QWidget,QFormLayout,QComboBox,QVBoxLayout,QCheckBox,QPushButton,QLabel,QTabWidget,QScrollArea,QLineEdit,QFileDialog
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


class NewtonPreferences(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        self.setObjectName("newton_preferences")
        self.draft = ProfileDraft()
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget();layout.addWidget(self.tabs)
        def page(title,description):
            area = QScrollArea();area.setWidgetResizable(True)
            content = QWidget();area.setWidget(content)
            box = QVBoxLayout(content)
            if description:
                note = QLabel(description);note.setWordWrap(True);box.addWidget(note)
            form = QFormLayout();form.setRowWrapPolicy(QFormLayout.WrapLongRows)
            box.addLayout(form);box.addStretch()
            self.tabs.addTab(area,tr(title))
            return form
        form = page("Appearance",tr(help.APPEARANCE))
        self.icons = QComboBox()
        for label,key in (("IngeTrazo","native"),("Outline","outline"),("Accent","accent")):
            self.icons.addItem(tr(label),key)
        self.icons.setCurrentIndex(max(0,self.icons.findData(QSettings().value("newton/icon_set","native"))))
        form.addRow(tr("Icon set"),self.icons)
        self.colliders = QCheckBox(tr("Show collision shapes at startup"))
        self.colliders.setChecked(str(QSettings().value("newton/show_colliders_by_default",False)).lower() in ("true","1"))
        form.addRow(self.colliders)
        self.shortcuts_button = QPushButton(tr("Configure collision display shortcut…"))
        self.shortcuts_button.setEnabled(getattr(panel,"collision_action",None) is not None)
        self.shortcuts_button.clicked.connect(self.configure_shortcut)
        form.addRow(self.shortcuts_button)
        form = page("Simulation",tr(help.SIMULATION))
        self.quality = QComboBox()
        for label,key in (("Quick","quick"),("Balanced","balanced"),("Precise","precise")):self.quality.addItem(tr(label),key)
        self.quality.setCurrentIndex(max(0,self.quality.findData(QSettings().value("newton/quality","balanced"))))
        self.quality.setToolTip(tr(help.QUALITY))
        form.addRow(tr("Quality"),self.quality)
        from .environment_ui import number,global_damping
        from .range_control import RangeControl
        self.gravity = number(-100,100,panel.gravity.value());self.gravity.setSuffix(" m/s²")
        form.addRow(tr("Gravity Z"),RangeControl(self.gravity,-100,100))
        self.floor = QCheckBox(tr("Ground at Z = 0"));self.floor.setChecked(panel.floor.isChecked());form.addRow(self.floor)
        linear,angular = global_damping()
        self.linear,self.angular = number(0,100,linear),number(0,100,angular)
        self.linear.setSuffix(" /s");self.angular.setSuffix(" /s")
        form.addRow(tr("Linear damping"),self.linear);form.addRow(tr("Angular damping"),self.angular)
        from .profile_ui import ProfileEditor
        self.profiles = ProfileEditor(panel,repository=self.draft)
        # Preferences manage presets; applying them stays in the model sidebar.
        self.profiles.apply_button.hide()
        self.tabs.addTab(self.profiles,tr("Profiles"))
        form = page("Runtime",tr(help.RUNTIME))
        self.python = QLineEdit(panel.python.text());form.addRow(tr("Python with MuJoCo"),self.python)
        browse = QPushButton(tr("Choose runtime…"));browse.clicked.connect(self.browse);form.addRow(browse)

    def commit(self):
        from .profile_sync import execute
        command = self.profiles.prepare_sync()
        st = QSettings()
        st.setValue("newton/icon_set",self.icons.currentData())
        st.setValue("newton/show_colliders_by_default",self.colliders.isChecked())
        st.setValue("newton/gravity_z",self.gravity.value())
        st.setValue("newton/floor",self.floor.isChecked())
        st.setValue("newton/quality",self.quality.currentData())
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
