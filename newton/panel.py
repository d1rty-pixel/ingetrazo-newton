"""Newton sidebar: edit parameters here, place and connect in the viewport."""
from __future__ import annotations

import json
import math
from pathlib import Path
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QPen, QVector3D
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QFileDialog, QGroupBox, QScrollArea)
from .model import KEY, settings, Configure, prepare, joint_rows, reference_id,remove_axes_command,ensure_axis_layer,unlink_followers
from .session import Session
from .controls import Controls
from .joints import PlacementTool
from .interaction import ReferencePickTool
from .references import install,validate_reference
from .worker import joint_settings,resolve_couplings
from .toolbar import build,icon,decorate,redecorate,physical_label,compact
from .range_control import scroll_safe
from .i18n import tr
from . import profiles
from . import help_texts as help


def spin(low,high,value):
    w = QDoubleSpinBox()
    w.setDecimals(3)
    w.setRange(low,high)
    w.setKeyboardTracking(False)
    w.setValue(value)
    return scroll_safe(w)


def settings_section(title,description):
    group = QGroupBox(title.replace("&","&&"))
    form = QFormLayout(group)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    explanation = QLabel(description)
    explanation.setWordWrap(True)
    explanation.setTextFormat(Qt.PlainText)
    form.addRow(explanation)
    return group,form,explanation


class NewtonPanel(QWidget):
    def __init__(self,app):
        super().__init__()
        self.app = app
        self.session = Session(app,self)
        self.selection_signature = None
        self._refreshing = False
        self._slider_history = self._slider_command = None
        self.ranges = {}
        self.hover_axis = None
        self.control_rows = []
        self.axis_rows = []
        self.gizmo_sizes = {}
        self.detail_uid = None
        self.axis_preview = None
        from .collision_view import CollisionView
        self.collision_view = CollisionView(self)
        self.placement = self.dialog = None
        self.profile_manager = None
        self.reference_names = {}
        outer = QVBoxLayout(self)
        self.heading = intro = QLabel(tr("Newton properties"))
        intro.setTextFormat(Qt.PlainText)
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 16px; font-weight: bold")
        outer.addWidget(intro)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll,1)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        self.profile_box = QGroupBox(tr("Profile"))
        profile_outer = QVBoxLayout(self.profile_box)
        profile_layout = QHBoxLayout();profile_outer.addLayout(profile_layout)
        self.profile_combo = compact(QComboBox())
        self.profile_combo.activated.connect(self.apply_profile_index)
        profile_layout.addWidget(self.profile_combo,1)
        self.profile_save = QPushButton(tr("Save as…"))
        self.profile_save.clicked.connect(self.save_profile)
        profile_layout.addWidget(self.profile_save)
        link_row = QHBoxLayout();profile_outer.addLayout(link_row)
        self.profile_status = QLabel();self.profile_status.setWordWrap(True);link_row.addWidget(self.profile_status,1)
        self.profile_sync = QPushButton(tr('Sync'));self.profile_sync.clicked.connect(self.sync_profile);link_row.addWidget(self.profile_sync)
        self.profile_unlink = QPushButton(tr('Unlink'));self.profile_unlink.clicked.connect(lambda:self.patch(dict(profile_link=None)));link_row.addWidget(self.profile_unlink)
        layout.addWidget(self.profile_box)
        self.editor = QGroupBox(tr("Generic"))
        form = QFormLayout(self.editor)
        self.selection_label = QLabel(tr("Select a body and place an axis."),self)
        self.selection_label.setWordWrap(True)
        self.selection_label.setTextFormat(Qt.PlainText)
        self.selection_label.hide()
        self.mode = QComboBox()
        for label,value in [(tr("Movable"),"dynamic"),(tr("Fixed"),"static"),(tr("Exclude from simulation"),"ignore")]:
            self.mode.addItem(label,value)
        decorate(self.mode,"mode")
        form.addRow(tr("Behaviour"),self.mode)
        self.reference_label = QLabel(tr("None"))
        self.reference_label.setWordWrap(True)
        self.reference_label.setTextFormat(Qt.PlainText)
        form.addRow(tr("Reference body"),self.reference_label)
        row = QHBoxLayout()
        pick = QPushButton(icon("link"),tr("Assign"))
        detach = QPushButton(icon("unlink"),tr("Detach"))
        pick.clicked.connect(self.pick_reference)
        detach.clicked.connect(self.detach_reference)
        row.addWidget(pick)
        row.addWidget(detach)
        form.addRow(row)
        layout.addWidget(self.editor)
        layout.removeWidget(self.editor)
        layout.insertWidget(0,self.editor)

        self.joint_box = QGroupBox(tr("Motion"))
        self.joint_form = form = QFormLayout(self.joint_box)
        self.joint_box.setToolTip(tr(help.MOTION))
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.kind_label = QLabel(tr("No axis"))
        form.addRow(self.kind_label)
        self.name_edit = QLineEdit()
        form.addRow(tr("Control name"),self.name_edit)
        self.drive = QComboBox()
        for label,value in [(tr("Free / passive"),"free"),(tr("Servo / position"),"position"),(tr("Motor / speed"),"velocity")]:
            self.drive.addItem(label,value)
        decorate(self.drive,"drive")
        form.addRow(tr("Actuator"),self.drive)
        self.limited = QCheckBox(tr("Use limits"))
        form.addRow(self.limited)
        self.lower,self.upper = spin(-1e6,0,-90),spin(0,1e6,90)
        self.target = spin(-1e6,1e6,0)
        self.max_speed,self.acceleration = spin(.01,1e6,180),spin(.01,1e6,360)
        self.deceleration = spin(.01,1e6,360)
        self.deceleration_sync = QPushButton(icon("link"),"")
        self.deceleration_sync.setAccessibleName(tr("Synchronize acceleration and deceleration"))
        self.deceleration_sync.setCheckable(True)
        self.deceleration_sync.setChecked(True)
        self.deceleration_sync.setFixedWidth(34)
        self.deceleration_sync.setToolTip(tr("Keep braking deceleration equal to acceleration"))
        self.deceleration_row = QWidget()
        brake_layout = QHBoxLayout(self.deceleration_row);brake_layout.setContentsMargins(0,0,0,0)
        brake_layout.addWidget(self.deceleration,1);brake_layout.addWidget(self.deceleration_sync)
        self.force = spin(0,1e6,100)
        form.addRow(physical_label(tr("Minimum"),"limit_min"),self.range_field("lower",self.lower,-180,0))
        form.addRow(physical_label(tr("Maximum"),"limit_max"),self.range_field("upper",self.upper,0,180))
        form.addRow(physical_label(tr("Initial target"),"target"),self.range_field("target",self.target,-180,180))
        form.addRow(physical_label(tr("Speed"),"speed"),self.max_speed)
        form.addRow(physical_label(tr("Acceleration"),"acceleration"),self.acceleration)
        form.addRow(physical_label(tr("Deceleration"),"deceleration"),self.deceleration_row)
        form.addRow(physical_label(tr("Max. force"),"force"),self.force)
        clear = QPushButton(tr("Remove axis"))
        clear.clicked.connect(self.remove_axes)
        form.addRow(clear)
        self.drive.currentIndexChanged.connect(self.update_units)
        self.limited.toggled.connect(self.update_units)
        layout.addWidget(self.joint_box)

        self.advanced_toggle = QCheckBox(tr("More settings"))
        layout.addWidget(self.advanced_toggle)
        self.advanced = QWidget()
        advanced_layout = QVBoxLayout(self.advanced)
        advanced_layout.setContentsMargins(0,0,0,0)
        self.coupling_section,form,self.coupling_help = settings_section(tr("Axis coupling"),"")
        from .coupling_ui import CouplingEditor
        self.coupling_editor = CouplingEditor(self)
        form.addRow(self.coupling_editor)
        advanced_layout.addWidget(self.coupling_section)
        self.connection_section,form,_ = settings_section(tr("Mechanical connection"),tr(help.CONNECTION))
        from .connection_ui import ConnectionEditor
        self.connection_editor = ConnectionEditor(self);form.addRow(self.connection_editor)
        advanced_layout.addWidget(self.connection_section)
        self.flexible_section,form,_ = settings_section(tr("Flexible material"),tr(help.FLEXIBLE))
        from .flexible_ui import FlexibleEditor
        self.flexible_editor = FlexibleEditor(self);form.addRow(self.flexible_editor)
        advanced_layout.addWidget(self.flexible_section)
        self.body_section,form,_ = settings_section(tr("Body & contact"),tr(help.BODY))
        self.shape = QComboBox()
        for label,value in [(tr("Box"),"box"),(tr("Sphere"),"sphere"),(tr("Convex hull"),"hull"),(tr("Child components"),"compound")]:
            self.shape.addItem(label,value)
        decorate(self.shape,"shape")
        self.mass,self.friction,self.bounce = spin(.001,1e6,1),spin(0,10,.5),spin(0,.95,.1)
        form.addRow(tr("Collision shape"),self.shape)
        form.addRow(physical_label(tr("Mass (kg)"),"mass"),self.mass)
        form.addRow(physical_label(tr("Friction"),"friction"),self.range_field("friction",self.friction,0,10))
        form.addRow(physical_label(tr("Bounce (approx.)"),"bounce"),self.range_field("bounce",self.bounce,0,.95))
        self.show_colliders = QCheckBox(tr("Show collision shapes"))
        self.show_colliders.setParent(self)
        self.show_colliders.hide()
        self.show_colliders.toggled.connect(self.collision_view.toggle)
        advanced_layout.addWidget(self.body_section)
        self.collision_section,form,_ = settings_section(tr("Collision exceptions"),tr(help.COLLISIONS))
        from .collision_ui import CollisionPairs
        self.collision_pairs = CollisionPairs(self)
        form.addRow(self.collision_pairs)
        advanced_layout.addWidget(self.collision_section)
        # Compatibility fields hold committed preferences, never sidebar rows.
        pref = QSettings()
        self.gravity = spin(-100,100,float(pref.value("newton/gravity_z",-9.81)))
        self.floor = QCheckBox()
        self.floor.setChecked(str(pref.value("newton/floor",True)).lower() in ("true","1"))
        self.python = QLineEdit(self.default_python())
        self.python.editingFinished.connect(self.collision_view.request)
        for field in (self.gravity,self.floor,self.python):
            field.setParent(self);field.hide()
        from .environment_ui import EnvironmentOverrides
        self.environment_section,form,_ = settings_section(tr("Simulation overrides"),tr(help.OVERRIDES))
        self.environment = EnvironmentOverrides(self)
        form.addRow(self.environment)
        advanced_layout.addWidget(self.environment_section)
        self.advanced.hide()
        self.advanced_toggle.toggled.connect(self.advanced.setVisible)
        layout.addWidget(self.advanced)
        layout.addStretch()
        self.selection_widgets = (intro,scroll)
        self.controls = Controls(self)
        self.session.changed.connect(self.refresh)
        self.session.message.connect(self.status_message)
        self.session.telemetry.connect(self.controls.telemetry)
        app.add_overlay(self.draw_joints)
        app.add_context_menu(self.context_menu)
        self.toolbar,self.actions = build(self)
        self.refresh_profiles()
        self.name_edit.editingFinished.connect(lambda:self.live_joint("name",self.name_edit.text()))
        self.drive.currentIndexChanged.connect(lambda:self.live_joint("drive",self.drive.currentData()))
        self.limited.toggled.connect(lambda value:self.live_joint("limited",value))
        for widget,key in ((self.lower,"lower"),(self.upper,"upper"),(self.target,"target"),
                           (self.max_speed,"max_speed"),(self.acceleration,"acceleration"),(self.deceleration,"deceleration"),(self.force,"force")):
            widget.valueChanged.connect(lambda value,k=key:self.live_joint(k,value))
        self.deceleration_sync.toggled.connect(lambda value:self.live_joint("deceleration_sync",value))
        self.mode.currentIndexChanged.connect(self.live_mode)
        self.shape.currentIndexChanged.connect(lambda:self.live_body("shape",self.shape.currentData()))
        for widget,key in ((self.mass,"mass"),(self.friction,"friction"),(self.bounce,"restitution")):
            widget.valueChanged.connect(lambda value,k=key:self.live_body(k,value))
        from .eraser import NewtonEraser
        app.window._tools["eraser"] = NewtonEraser(self)
        app.add_outliner_kind(self.browser_kind)
        from .preferences import PaletteWatcher,install_preferences
        self.palette_watcher = PaletteWatcher(self)
        app.window.installEventFilter(self.palette_watcher)
        install_preferences(self)
        from .axis_edit import install as install_axis_edit
        install_axis_edit(self)
        self.show_colliders.setChecked(str(QSettings().value("newton/show_colliders_by_default",False)).lower() in ("true","1"))
        from .connections import install as install_connections
        install_connections(self)
        self.refresh()

    def show_sidebar(self):
        if getattr(self,"dock",None):
            self.app.show_panel(self.dock)

    def range_field(self,key,number,low,high):
        from .range_control import RangeControl
        control = RangeControl(number,low,high)
        control.gestureStarted.connect(self.begin_slider_edit)
        control.gestureFinished.connect(self.end_slider_edit)
        self.ranges[key] = control
        return control

    def begin_slider_edit(self):
        self._slider_history = self.app.viewport.history
        self._slider_command = None
        self._slider_selection = tuple(g.uid for g in self.selected())

    def end_slider_edit(self):
        self._slider_history = self._slider_command = None

    def refresh_profiles(self):
        self.available_profiles = profiles.all_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem(tr("Apply profile…"),None)
        for p in self.available_profiles:
            self.profile_combo.addItem(tr(p["name"]) if p["builtin"] else p["name"],p["id"])
        self.profile_combo.blockSignals(False)
        self.refresh_profile_link()

    def refresh_profile_link(self):
        from .profile_sync import status
        groups = self.selected()
        link = settings(groups[0]).get('profile_link') if len(groups)==1 else None
        p = next((p for p in self.available_profiles if link and p['id']==link.get('id')),None)
        self.profile_status.setVisible(bool(link));self.profile_sync.setVisible(bool(link));self.profile_unlink.setVisible(bool(link))
        self.profile_sync.setEnabled(p is not None)
        if link:
            name = (tr(p['name']) if p['builtin'] else p['name']) if p else tr('Missing profile')
            self.profile_status.setText(name+' · '+tr(status(groups[0],p)))
            self.profile_sync.setToolTip(tr('Overwrite profile parameters; keep axis placement and reference bodies.'))

    def sync_profile(self):
        groups = self.selected()
        if len(groups)!=1 or self.session.workspace:return
        link = settings(groups[0]).get('profile_link') or {}
        p = next((p for p in profiles.all_profiles() if p['id']==link.get('id')),None)
        if p:
            if p['joint'] and not settings(groups[0]).get('joint'):
                self.apply_profile(p)
            else:
                from .profile_sync import command,execute
                try:execute(self,command(self.app.scene,{groups[0].uid:p}))
                except (ValueError,TypeError,KeyError) as exc:self.status_message(tr(str(exc)))

    def apply_profile_index(self,index):
        if index>0:
            self.apply_profile(self.available_profiles[index-1])
        self.profile_combo.setCurrentIndex(0)

    def apply_profile(self,profile):
        groups = self.selected()
        if len(groups)!=1 or self.session.workspace:
            self.status_message(tr("Select one body."))
            return
        try:
            p = profiles.validate(profile)
            from .profile_sync import link
            p['body']['profile_link'] = link(p)
            group = groups[0]
            if p['joint'] and settings(group).get('flexible'):
                raise ValueError(tr('Flexible bodies cannot also have a motion axis.'))
            if p["body"]["shape"]=="compound" and not group.children:
                raise ValueError(tr("Compound collision needs child groups or components."))
            old = settings(group).get("joint")
            parent = reference_id(group)
            if p["joint"] is None:
                self.patch(dict(p["body"],joint=None,reference=parent),[group])
            else:
                j = joint_settings(dict(p["joint"],name=(old or {}).get("name",group.name),parent=parent,
                      pivot=(old or {}).get("pivot",[0,0,0]),axis=(old or {}).get("axis",[0,0,1]),
                      coupling=(old or {}).get("coupling"),display=(old or {}).get("display")))
                if old:
                    self.commit_joint(self.app.scene,group,j,body_values=p["body"])
                else:
                    self.begin_placement(self.app.scene,group,j,body_values=p["body"])
                    self.show_sidebar()
                    return
            self.status_message(tr("Profile applied."))
        except (ValueError,TypeError,KeyError) as exc:
            self.status_message(tr(str(exc)))

    def show_profiles(self):
        from .profile_ui import ProfileManager
        if self.profile_manager is None:
            self.profile_manager = ProfileManager(self)
        self.profile_manager.refresh()
        self.profile_manager.show()
        self.profile_manager.raise_()

    def save_profile(self):
        self.show_profiles()
        self.profile_manager.save_selection()

    def refresh_icons(self):
        for control in self.ranges.values():
            control.refresh_style()
        for key,action in self.actions.items():
            action.setIcon(icon("pause" if key=="play" and self.session.running else key))
        self.controls.refresh_icons()
        redecorate()

    def browser_kind(self,group):
        if KEY not in (group.ext or {}):
            return None
        cfg = settings(group)
        j = cfg.get("joint")
        if cfg.get("flexible"):
            kind = tr("Rope") if cfg["flexible"]["kind"]=="rope" else tr("Cable")
            props = [(tr("Material"),kind)]
        elif j:
            j = joint_settings(j)
            names = {("hinge","free"):"Free rotation",("hinge","position"):"Rotary servo",
                ("hinge","velocity"):"Rotary motor",("slide","free"):"Free linear axis",
                ("slide","position"):"Linear positioning",("slide","velocity"):"Linear motor"}
            kind = tr(names[j["type"],j["drive"]])+" · "+j["name"]
            props = [(tr("Actuator"),j["name"])]
        elif cfg.get("point_attachment"):
            from .connections import KINDS
            kind = tr(KINDS[cfg["point_attachment"].get("type","ball")])
            props = []
        else:
            kind = tr("Fixed body") if cfg["mode"]=="static" else tr("Free body")
            props = []
        parent = reference_id(group)
        props.append((tr("Reference body"),self.reference_names.get(parent,tr("World"))))
        return dict(type=tr("Newton")+" · "+kind,props=props)

    def default_python(self):
        saved = QSettings().value("newton/python","")
        if saved and Path(saved).is_file():
            return saved
        config = Path(__file__).with_name("runtime.json")
        if config.is_file():
            try:
                return json.loads(config.read_text(encoding="utf-8-sig"))["python"]
            except (ValueError,KeyError):
                pass
        local = Path(__file__).parent.parent/".venv"/"Scripts"/"python.exe"
        return str(local) if local.is_file() else ""

    def browse(self):
        path,_ = QFileDialog.getOpenFileName(self,tr("Choose Python with MuJoCo"),self.python.text(),tr("Python (python.exe python);;All files (*)"))
        if path:
            self.python.setText(path)
            self.collision_view.request()

    def status_message(self,text):
        self.app.window.statusBar().showMessage(tr(text))

    def selected(self):
        return [g for g in self.app.scene.groups if g in self.app.scene.selection]

    def current_joint(self):
        groups = self.selected()
        return settings(groups[0]).get("joint") if len(groups)==1 else None

    def update_units(self,*args):
        j = self.current_joint()
        rotation = not j or j.get("type","hinge")=="hinge"
        unit = " °" if rotation else " mm"
        for w in (self.lower,self.upper):
            w.setSuffix(unit)
        self.target.setSuffix(unit+("/s" if self.drive.currentData()=="velocity" else ""))
        self.max_speed.setSuffix(unit+"/s")
        self.acceleration.setSuffix(unit+"/s²")
        self.deceleration.setSuffix(unit+"/s²")
        self.force.setSuffix(" Nm" if rotation else " N")
        self.drive.setItemText(1,tr("Servo / angle") if rotation else tr("Position / distance"))
        self.joint_form.setRowVisible(self.ranges["target"],self.drive.currentData()!="free")
        self.ranges["lower"].set_span(-180 if rotation else -1000,0)
        self.ranges["upper"].set_span(0,180 if rotation else 1000)
        drive = self.drive.currentData()
        if drive=="position" and self.limited.isChecked() and self.upper.value()>self.lower.value():
            low,high = self.lower.value(),self.upper.value()
            bounded = True
        elif drive=="velocity":
            low,high = -self.max_speed.value(),self.max_speed.value()
            bounded = True
        else:
            low,high = (-180,180) if rotation else (-1000,1000)
            bounded = False
        previous = self.target.blockSignals(True)
        self.target.setRange(low,high) if bounded else self.target.setRange(-1e6,1e6)
        self.target.blockSignals(previous)
        self.ranges["target"].set_span(low,high,expand=not bounded)
        driven = self.drive.currentData()!="free"
        self.joint_form.setRowVisible(self.deceleration_row,driven)
        for w in (self.max_speed,self.acceleration,self.force):
            w.setEnabled(driven)
        self.deceleration.setEnabled(driven and not self.deceleration_sync.isChecked())
        self.deceleration_sync.setEnabled(driven)
        for w in (self.lower,self.upper):
            w.setEnabled(self.limited.isChecked())
        if driven and j and j.get("drive","free")=="free" and j.get("force",0)<=0:
            previous = self.force.blockSignals(True)
            self.force.setValue(100)
            self.force.blockSignals(previous)

    def refresh(self,*args):
        previous = self._refreshing
        self._refreshing = True
        try:
            self.refresh_widgets(*args)
        finally:
            self._refreshing = previous

    def live_joint(self,key,value):
        if self._refreshing or self.session.workspace:
            return
        groups = self.selected()
        if len(groups)!=1 or not self.current_joint():
            return
        original = joint_settings(self.current_joint())
        changed = dict(original)
        if key in ("lower","upper","target","max_speed","acceleration","deceleration"):
            value *= math.pi/180 if changed["type"]=="hinge" else .001
        if key=="name":
            value = value.strip() or groups[0].name
        changed[key] = value
        if key=="drive" and value!="free" and changed["force"]<=0:
            changed["force"] = 100
        try:
            changed = joint_settings(changed)
            if changed!=original:
                self.commit_joint(self.app.scene,groups[0],changed)
            self.status_message(tr("Motion updated."))
        except ValueError as exc:
            self.status_message(str(exc))

    def live_mode(self,*args):
        if not self._refreshing:
            self.mark(self.mode.currentData())

    def live_body(self,key,value):
        if not self._refreshing:
            if key=="shape" and value=="compound" and any(not g.children for g in self.selected()):
                self.status_message(tr("Compound collision needs child groups or components."))
                groups = self.selected()
                blocked = self.shape.blockSignals(True)
                if groups:self.shape.setCurrentIndex(self.shape.findData(settings(groups[0])["shape"]))
                self.shape.blockSignals(blocked)
                return
            self.patch({key:value})

    def refresh_widgets(self,*args):
        active = self.session.workspace is not None
        if getattr(self,"was_active",False) and not active:
            self.status_message(tr("Original model restored."))
        self.was_active = active
        for w in (self.editor,self.joint_box,self.advanced,self.profile_box,self.advanced_toggle):
            w.setEnabled(not active)
        groups = self.selected()
        if active:
            groups = getattr(self,"_sidebar_groups",[])
        else:
            self._sidebar_groups = groups
        if (self._slider_history is not None and (self.app.viewport.history is not self._slider_history
            or tuple(g.uid for g in groups)!=self._slider_selection)):
            self.end_slider_edit()
        if not active:
            self.detail_uid = groups[0].uid if len(groups)==1 else None
        self.profile_box.setEnabled(not active and len(groups)==1)
        if not active:self.refresh_profile_link()
        if self.profile_manager is not None:
            self.profile_manager.update_buttons()
        for widget in self.selection_widgets:
            widget.setVisible(bool(groups))
        for key in ("rotate","slide","link","unlink","free","fixed"):
            self.actions[key].setEnabled(not active and bool(groups) and (len(groups)==1 or key in ("unlink","free","fixed")))
        if len(groups)==1 and settings(groups[0]).get("flexible"):
            self.actions["rotate"].setEnabled(False);self.actions["slide"].setEnabled(False)
        self.actions["connect"].setEnabled(not active and len(groups)==1 and not settings(groups[0]).get("flexible"))
        self.actions["drag"].setEnabled(active and self.session.ready)
        self.actions["reset"].setEnabled(active)
        self.actions["play"].setEnabled(not active or self.session.ready)
        self.actions["play"].setIcon(icon("pause" if active and self.session.running else "play"))
        if active:
            self.collision_view.stop()
            self.controls.refresh(self.control_rows,True)
            return
        self.collision_view.request()
        for vp in self.app.window.all_viewports():
            install(vp)
        from .axis_edit import install as install_axis_edit
        install_axis_edit(self)
        from .connections import install as install_connections
        install_connections(self)
        signature = (id(self.app.scene),tuple(g.uid for g in groups),
            tuple((g.uid,g.name,repr((g.ext or {}).get(KEY))) for g in self.app.scene.groups))
        if signature==self.selection_signature:
            self.controls.refresh(self.control_rows,False)
            return
        self.selection_signature = signature
        self.control_rows = joint_rows(self.app.scene)
        self.axis_rows = joint_rows(self.app.scene,include_fixed=True)
        if self.axis_rows:
            ensure_axis_layer(self.app.scene)
        self.reference_names = {g.uid:g.name for g in self.app.scene.groups}
        from core.group import placement_points
        self.gizmo_sizes = {}
        for g in self.app.scene.groups:
            if settings(g).get("joint"):
                points = placement_points(g)
                extent = float((points.max(axis=0)-points.min(axis=0)).max()) if len(points) else 1
                self.gizmo_sizes[g.uid] = max(.002,min(1.,extent*.2))
        self.controls.refresh(self.control_rows,False)
        browser = getattr(self.app.window,"project_browser",None)
        if browser is not None:
            browser.outliner.refresh()
        self.selection_label.setText(tr("Select a body.") if not groups else
                                     groups[0].name if len(groups)==1 else tr("{count} bodies selected",count=len(groups)))
        self.heading.setText(tr("Newton properties")+(" · "+(groups[0].name if len(groups)==1 else tr("{count} bodies selected",count=len(groups))) if groups else ""))
        self.joint_box.setVisible(len(groups)==1 and bool(settings(groups[0]).get("joint")))
        self.coupling_editor.refresh(groups[0] if len(groups)==1 else None)
        self.coupling_section.setVisible(len(groups)==1 and bool(settings(groups[0]).get("joint")))
        self.coupling_help.setText(self.coupling_editor.description())
        self.collision_section.setVisible(len(groups)==1)
        self.collision_pairs.refresh()
        self.environment_section.setVisible(len(groups)==1)
        self.environment.refresh(groups[0] if len(groups)==1 else None)
        self.flexible_section.setVisible(len(groups)==1)
        self.flexible_editor.refresh(groups[0] if len(groups)==1 else None)
        self.connection_section.setVisible(len(groups)==1 and not settings(groups[0]).get("flexible"))
        self.connection_editor.refresh(groups[0] if len(groups)==1 else None)
        if not groups:
            self.reference_label.setText(tr("None"))
            return
        group = groups[0]
        cfg = settings(group)
        self.mode.setCurrentIndex(self.mode.findData(cfg["mode"] if KEY in (group.ext or {}) else "static"))
        parent = next((g for g in self.app.scene.groups if g.uid==reference_id(group)),None)
        self.reference_label.setText(parent.name+(tr(" · rigid attachment") if not cfg.get("joint") and not cfg.get("flexible") else "") if parent else tr("None"))
        self.shape.setCurrentIndex(self.shape.findData(cfg["shape"]))
        self.body_section.layout().setRowVisible(self.shape,not bool(cfg.get("flexible")))
        for widget,key in ((self.mass,"mass"),(self.friction,"friction"),(self.bounce,"restitution")):
            widget.setValue(cfg[key])
        if cfg.get("joint"):
            j = joint_settings(cfg["joint"])
            previous = self.target.blockSignals(True)
            self.target.setRange(-1e6,1e6)
            self.target.blockSignals(previous)
            factor = 180/math.pi if j["type"]=="hinge" else 1000
            self.kind_label.setText(tr("Rotation axis") if j["type"]=="hinge" else tr("Linear axis"))
            self.name_edit.setText(j["name"])
            self.drive.setCurrentIndex(self.drive.findData(j["drive"]))
            self.limited.setChecked(j["limited"])
            for w,key in ((self.lower,"lower"),(self.upper,"upper"),(self.target,"target"),
                          (self.max_speed,"max_speed"),(self.acceleration,"acceleration"),(self.deceleration,"deceleration")):
                w.setValue(j[key]*factor)
            self.deceleration_sync.setChecked(j["deceleration_sync"])
            self.force.setValue(j["force"])
            self.update_units()
            self.drive.setEnabled(not j.get("coupling"))
            self.target.setEnabled(not j.get("coupling"))
            self.force.setEnabled(not j.get("coupling"))

    def patch(self,values,groups=None):
        if self.session.workspace:
            return
        groups = self.selected() if groups is None else groups
        groups = [g for g in groups if KEY not in (g.ext or {}) or any(settings(g).get(k)!=v for k,v in values.items())]
        if groups:
            command = Configure(groups,values,partial=True)
            if ("joint" in values and values["joint"] is None) or values.get("mode") in ("static","ignore"):
                from core.history import CompoundCommand
                extra = unlink_followers(self.app.scene,{g.uid for g in groups})
                if extra:
                    command = CompoundCommand([command,*extra])
            history = self.app.viewport.history
            previous = self._slider_command
            if (history is self._slider_history and isinstance(command,Configure) and previous is not None
                and history.undo_stack and history.undo_stack[-1] is previous
                and previous.groups==command.groups):
                previous.values.update(command.values)
                previous.do(self.app.scene)
            else:
                history.execute(command)
                if history is self._slider_history and isinstance(command,Configure):
                    self._slider_command = command
            self.app.viewport.notify_scene_changed()
            self.refresh()

    def mark(self,mode):
        self.patch(dict(mode=mode))

    def configure(self):
        self.patch(dict(shape=self.shape.currentData(),mass=self.mass.value(),
                        friction=self.friction.value(),restitution=self.bounce.value()))

    def configure_joint(self):
        groups = self.selected()
        if len(groups)!=1 or not self.current_joint():
            return
        j = joint_settings(self.current_joint())
        factor = math.pi/180 if j["type"]=="hinge" else .001
        j.update(name=self.name_edit.text().strip() or groups[0].name,drive=self.drive.currentData(),
            limited=self.limited.isChecked(),lower=self.lower.value()*factor,upper=self.upper.value()*factor,
            target=self.target.value()*factor,max_speed=self.max_speed.value()*factor,
            acceleration=self.acceleration.value()*factor,deceleration=self.deceleration.value()*factor,
            deceleration_sync=self.deceleration_sync.isChecked(),force=self.force.value())
        try:
            validated = joint_settings(j)
            if validated != joint_settings(self.current_joint()):
                self.commit_joint(self.app.scene,groups[0],validated)
            self.status_message(tr("Motion updated."))
        except ValueError as exc:
            self.status_message(str(exc))

    def remove_axes(self):
        if self.session.workspace:
            return
        command = remove_axes_command(self.selected(),self.app.scene)
        if command:
            self.app.viewport.history.execute(command)
            self.app.viewport.notify_scene_changed()
            self.refresh()

    def edit_joint(self,kind="hinge",uid=None):
        if self.session.workspace:
            return
        self.app.viewport.end_group_edit()
        groups = [g for g in self.app.scene.groups if g.uid==uid] if uid else self.selected()
        if len(groups)!=1:
            self.status_message(tr("Select one group or component."))
            return
        g = groups[0]
        old = settings(g).get("joint")
        if old and old.get("type","hinge")==kind:
            values = joint_settings(old)
        else:
            values = joint_settings(dict(type=kind,drive="free",name=g.name,pivot=[0,0,0],
                axis=[0,0,1] if kind=="hinge" else [1,0,0],force=100))
        values["parent"] = reference_id(g)
        self.begin_placement(self.app.scene,g,values)
        self.show_sidebar()

    def commit_joint(self,scene,group,values,body_values=None):
        if self.session.workspace or self.app.scene is not scene or group not in scene.groups:
            raise ValueError(tr("Document changed. Place the axis again."))
        validate_reference(scene,group,values.get("parent"))
        joints = {row["uid"]:row for row in joint_rows(scene)}
        joints[group.uid] = joint_settings(values)
        resolve_couplings(joints)
        self.patch({"mode":"dynamic",**(body_values or {}),"joint":values,"reference":values.get("parent")},[group])
        self.status_message(tr("Axis placed."))

    def begin_placement(self,scene,group,values,body_values=None):
        vp = self.app.viewport
        def cancel():
            self.placement = None
            if self.app.viewport is vp and isinstance(vp.active_tool,PlacementTool):
                self.app.window._activate_tool("select")
            self.status_message(tr("Placement cancelled."))
        def finish(anchor,axis):
            self.placement = None
            try:
                self.commit_joint(scene,group,dict(values,pivot=anchor,axis=axis),body_values=body_values)
            except ValueError as exc:
                self.status_message(str(exc))
            finally:
                if self.app.viewport is vp:
                    self.app.window._activate_tool("select")
        self.placement = PlacementTool(finish,cancel)
        vp.set_active_tool(self.placement)
        self.status_message(tr("Pick the origin, then a direction or X/Y/Z. Esc cancels."))

    def pick_reference(self):
        if self.session.workspace:
            return
        groups = self.selected()
        if len(groups)!=1:
            self.status_message(tr("Select one dependent body."))
            return
        scene,child,vp = self.app.scene,groups[0],self.app.viewport
        def cancel():
            self.app.window._activate_tool("select")
            self.status_message(tr("Assignment cancelled."))
        def choose(parent):
            if self.app.scene is not scene or child not in scene.groups:
                raise ValueError(tr("Document changed. Pick the reference body again."))
            validate_reference(scene,child,parent.uid)
            values = dict(reference=parent.uid)
            old = settings(child).get("joint")
            if old:
                values["joint"] = dict(old,parent=parent.uid)
            self.patch(values,[child])
            QTimer.singleShot(0,lambda:self.app.window._activate_tool("select"))
            self.status_message(tr("Reference body assigned: ")+parent.name)
        vp.set_active_tool(ReferencePickTool(choose,cancel))
        self.status_message(tr("Pick the reference body."))

    def detach_reference(self):
        for g in self.selected():
            if not reference_id(g):
                continue
            values = dict(reference=None)
            old = settings(g).get("joint")
            if old:
                values["joint"] = dict(old,parent=None)
            self.patch(values,[g])
        self.status_message(tr("Reference body detached."))

    def context_menu(self,menu,selection):
        if self.session.workspace:
            return
        groups = [g for g in self.app.scene.groups if g in selection]
        if len(groups)==1:
            menu.addAction(icon("link"),tr("Assign reference body…"),lambda:QTimer.singleShot(0,self.pick_reference))
            from .connections import begin
            menu.addAction(icon("connect"),tr("Connect bodies…"),lambda:QTimer.singleShot(0,lambda:begin(self)))
            if settings(groups[0]).get("point_attachment"):
                menu.addAction(icon("unlink"),tr("Remove connection"),lambda:QTimer.singleShot(0,self.connection_editor.detach))
        if groups:
            menu.addAction(icon("unlink"),tr("Detach reference body"),lambda:QTimer.singleShot(0,self.detach_reference))

    def draw_joints(self,viewport,painter):
        self.collision_view.draw(viewport,painter)
        from .axis_guides import draw
        draw(self,viewport,painter)
        from .connections import draw as draw_connections
        draw_connections(self,viewport,painter)

    def activate_drag(self):
        self.session.activate_drag()

    def show_controls(self):
        self.controls.refresh(self.control_rows,self.session.workspace is not None)
        if not self.controls.isVisible():
            self.controls.resize(420,min(600,max(260,len(self.control_rows)*145+110)))
            frame = self.app.window.frameGeometry()
            available = self.app.window.screen().availableGeometry()
            x = frame.right()+12
            if x+self.controls.width()>available.right():
                x = max(available.left(),frame.right()-self.controls.width()-12)
            y = max(available.top(),min(frame.top()+100,available.bottom()-self.controls.height()-40))
            self.controls.move(x,y)
        self.controls.show()
        self.controls.raise_()
        self.controls.activateWindow()

    def start_or_pause(self):
        if self.session.workspace:
            self.session.toggle()
            return
        if self.placement:
            self.app.window._activate_tool("select")
        try:
            self.app.viewport.end_group_edit()
            self.refresh()
            scene,specs,movers = prepare(self.app.scene)
            python = self.python.text().strip()
            QSettings().setValue("newton/python",python)
            from .environment_ui import global_damping
            linear,angular = global_damping()
            quality = QSettings().value("newton/quality","balanced")
            self.session.start(python,scene,specs,movers,self.gravity.value(),self.floor.isChecked(),linear,angular,quality)
            self.status_message(tr("Drag passive bodies. Use controls for actuators."))
            self.show_controls()
        except Exception as exc:
            self.status_message(str(exc))

    def shutdown(self,*args):
        self.collision_view.stop()
        self.session.stop_worker()
        self.controls.close()
