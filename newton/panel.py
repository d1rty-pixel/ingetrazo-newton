"""Newton sidebar: edit parameters here, place and connect in the viewport."""
from __future__ import annotations

import json
import math
from pathlib import Path
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QPen, QVector3D
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QFileDialog, QScrollArea)
from views.fold_section import FoldSection
from .model import KEY, settings, Configure, prepare, hidden_mode, joint_rows, reference_id,remove_axes_command,ensure_axis_layer,unlink_followers,with_zero,fit_limits
from .session import Session
from .controls import Controls
from .joints import PlacementTool
from .interaction import ReferencePickTool
from .references import install,validate_reference
from .worker import joint_settings,resolve_couplings
from .icons import attach,icon
from .toolbar import build,decorate,redecorate,physical_label,pictogram_check,compact
from .range_control import scroll_safe
from .i18n import tr
from .units import signature as units_signature
from . import profiles
from . import help_texts as help


def spin(low,high,value):
    w = QDoubleSpinBox()
    w.setDecimals(3)
    w.setRange(low,high)
    w.setKeyboardTracking(False)
    w.setValue(value)
    return scroll_safe(w)


def section(title,key,open=True):
    # The host's own fold header (Render, AI tabs); its open state survives restarts.
    return FoldSection(title.replace("&","&&"),"newton/open_"+key,default_open=open)


def settings_section(title,key,description,auto=False):
    group = section(title,key,open=False)
    if auto:
        # The rule in refresh_auto_sections decides; a stored open state would fight it on the next selection.
        group.header.toggled.disconnect(group._toggled)
        group.header.toggled.connect(group._show)
    # The wrapped explanation sits above the form: inside a QFormLayout its height-for-width came out short and squashed the rows.
    outer = QVBoxLayout(group.body)
    explanation = QLabel(description)
    explanation.setWordWrap(True)
    explanation.setTextFormat(Qt.PlainText)
    outer.addWidget(explanation)
    fields = QWidget()
    form = QFormLayout(fields)
    form.setContentsMargins(0,0,0,0)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    outer.addWidget(fields)
    return group,form,explanation



def body_mode(group):
    """The behaviour the simulation gives a body; unconfigured groups are fixed, face-me figures excluded."""
    if KEY in (group.ext or {}):
        return settings(group)["mode"]
    return "ignore" if group.billboard else "static"


def gizmo_size(group):
    from core.group import placement_points
    points = placement_points(group)
    extent = float((points.max(axis=0)-points.min(axis=0)).max()) if len(points) else 1
    return max(.002,min(1.,extent*.2))

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
        from .collision_view import CollisionView
        self.collision_view = CollisionView(self)
        self.placement = self.dialog = None
        self.profile_manager = None
        self.reference_names = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6,9,6,9)  # the narrowest dock width must still fit the widest unwrappable checkbox
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
        layout.setSpacing(12)
        layout.setContentsMargins(0,0,0,0)
        self.profile_box = section(tr("Profile"),"profile")
        profile_outer = QVBoxLayout(self.profile_box.body)
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
        self.editor = section(tr("Generic"),"generic")
        form = QFormLayout(self.editor.body)
        self.selection_label = QLabel(tr("Select a body and place an axis."),self)
        self.selection_label.setWordWrap(True)
        self.selection_label.setTextFormat(Qt.PlainText)
        self.selection_label.hide()
        self.mode = QComboBox()
        for label,value in [(tr("Movable"),"dynamic"),(tr("Fixed"),"static"),(tr("Exclude from simulation"),"ignore")]:
            self.mode.addItem(label,value)
        decorate(self.mode,"mode")
        form.addRow(tr("Behaviour"),self.mode)
        from .reference_table import ReferenceTable
        pick = attach(QPushButton(tr("Assign")),"link")
        pick.clicked.connect(self.pick_reference)
        form.addRow(tr("Reference body"),pick)
        self.reference_table = ReferenceTable(lambda _:self.detach_reference(),tr("None"),self)
        form.addRow(self.reference_table)
        self.reference_buttons = (pick,self.reference_table)

        self.joint_box = section(tr("Motion"),"motion")
        self.joint_form = form = QFormLayout(self.joint_box.body)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.kind_label = QLabel(tr("No axis"))
        form.addRow(self.kind_label)
        self.name_edit = QLineEdit()
        form.addRow(physical_label(tr("Control name")),self.name_edit)
        self.drive = QComboBox()
        for label,value in [(tr("Free / passive"),"free"),(tr("Servo / position"),"position"),(tr("Motor / speed"),"velocity")]:
            self.drive.addItem(label,value)
        decorate(self.drive,"drive")
        form.addRow(physical_label(tr("Actuator")),self.drive)
        self.limited = pictogram_check(QCheckBox(tr("Use limits")),"limits")
        form.addRow(self.limited)
        self.lower,self.upper = spin(-1e6,0,-90),spin(0,1e6,90)
        self.hardness = spin(0,100,100)
        self.hardness.setDecimals(0)
        self.hardness.setSuffix(" %")
        self.target = spin(-1e6,1e6,0)
        self.max_speed,self.acceleration = spin(.01,1e6,180),spin(.01,1e6,360)
        self.deceleration = spin(.01,1e6,360)
        self.deceleration_sync = attach(QPushButton(),"sync")
        self.deceleration_sync.setAccessibleName(tr("Synchronize acceleration and deceleration"))
        self.deceleration_sync.setCheckable(True)
        self.deceleration_sync.setChecked(True)
        self.deceleration_sync.setFixedWidth(34)
        self.deceleration_sync.setToolTip(tr("Keep deceleration equal to acceleration"))
        self.deceleration_row = QWidget()
        brake_layout = QHBoxLayout(self.deceleration_row);brake_layout.setContentsMargins(0,0,0,0)
        brake_layout.addWidget(self.deceleration,1);brake_layout.addWidget(self.deceleration_sync)
        self.force = spin(0,1e6,100)
        form.addRow(physical_label(tr("Minimum"),"limit_min"),self.range_field("lower",self.lower,-180,0))
        form.addRow(physical_label(tr("Maximum"),"limit_max"),self.range_field("upper",self.upper,0,180))
        hardness = physical_label(tr("Limit hardness"),"limit_hardness")
        form.addRow(hardness,self.range_field("limit_hardness",self.hardness,0,100))
        for widget in (hardness,self.ranges["limit_hardness"]):
            widget.setToolTip(tr(help.LIMIT_HARDNESS))
        form.addRow(physical_label(tr("Initial target"),"target"),self.range_field("target",self.target,-180,180))
        form.addRow(physical_label(tr("Speed"),"speed"),self.max_speed)
        form.addRow(physical_label(tr("Acceleration"),"acceleration"),self.acceleration)
        form.addRow(physical_label(tr("Deceleration"),"deceleration"),self.deceleration_row)
        form.addRow(physical_label(tr("Max. force"),"force"),self.force)
        self.axis_lock = pictogram_check(QCheckBox(tr("Lock axis object")),"lock")
        self.axis_lock.setToolTip(tr("Locks the axis object in the model so that no tool moves or rotates it by accident. It still follows its body."))
        self.axis_lock.toggled.connect(lambda on:self.lock_marker("axis_of",on))
        form.addRow(self.axis_lock)
        clear = QPushButton(tr("Remove axis"))
        clear.clicked.connect(self.remove_axes)
        form.addRow(clear)
        self.drive.currentIndexChanged.connect(self.update_units)
        self.limited.toggled.connect(self.update_units)

        self.coupling_section,form,self.coupling_help = settings_section(tr("Axis coupling"),"coupling","",auto=True)
        from .coupling_ui import CouplingEditor
        self.coupling_editor = CouplingEditor(self)
        form.addRow(self.coupling_editor)
        self.connection_section,form,_ = settings_section(tr("Mechanical connection"),"connection",tr(help.CONNECTION),auto=True)
        from .connection_ui import ConnectionEditor
        self.connection_editor = ConnectionEditor(self);form.addRow(self.connection_editor)
        self.flexible_section,form,_ = settings_section(tr("Material"),"flexible",tr(help.FLEXIBLE),auto=True)
        from .flexible_ui import FlexibleEditor
        self.flexible_editor = FlexibleEditor(self);form.addRow(self.flexible_editor)
        self.body_section,form,_ = settings_section(tr("Body"),"body",tr(help.BODY))
        self.body_form = form
        self.mass,self.friction,self.bounce = spin(.001,1e6,1),spin(0,10,.5),spin(0,.95,.1)
        form.addRow(physical_label(tr("Mass (kg)"),"mass"),self.mass)
        form.addRow(physical_label(tr("Friction"),"friction"),self.range_field("friction",self.friction,0,10))
        form.addRow(physical_label(tr("Bounce (approx.)"),"bounce"),self.range_field("bounce",self.bounce,0,.95))
        self.collisions_section,form,_ = settings_section(tr("Collisions"),"collisions",tr(help.COLLISION_SHAPE))
        self.collision_form = form
        self.shape = QComboBox()
        for label,value in [(tr("Box"),"box"),(tr("Sphere"),"sphere"),(tr("Convex hull"),"hull"),(tr("Child components"),"compound")]:
            self.shape.addItem(label,value)
        decorate(self.shape,"shape")
        form.addRow(physical_label(tr("Collision shape")),self.shape)
        self.show_colliders = QCheckBox(tr("Show collision shapes"))
        self.show_colliders.setParent(self)
        self.show_colliders.hide()
        self.show_colliders.toggled.connect(self.collision_view.toggle)
        self.show_collider = pictogram_check(QCheckBox(tr("Show collision shape")),"collision_shape")
        self.show_collider.setToolTip(tr("Shows or hides the collision shape of this body only. The global setting in the preferences stays as it is."))
        self.show_collider.toggled.connect(self.show_body_collider)
        self.collision_view.changed.connect(self.refresh_collider_check)
        form.addRow(self.show_collider)
        self.collision_box = QWidget()
        box_layout = QVBoxLayout(self.collision_box);box_layout.setContentsMargins(0,8,0,0)
        heading = QLabel(tr("Collision exemptions"));heading.setStyleSheet("font-weight: bold")
        explanation = QLabel(tr(help.COLLISIONS));explanation.setWordWrap(True);explanation.setTextFormat(Qt.PlainText)
        from .collision_ui import CollisionPairs
        self.collision_pairs = CollisionPairs(self)
        for widget in (heading,explanation,self.collision_pairs):box_layout.addWidget(widget)
        self.collisions_section.body.layout().addWidget(self.collision_box)
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
        self.environment_section,form,_ = settings_section(tr("Simulation overrides"),"overrides",tr(help.OVERRIDES),auto=True)
        self.environment = EnvironmentOverrides(self)
        form.addRow(self.environment)
        from . import tooltips
        tooltips.apply(self)
        self.sections = (self.editor,self.profile_box,self.flexible_section,self.body_section,self.collisions_section,
            self.joint_box,self.connection_section,self.coupling_section,self.environment_section)
        for fold in self.sections:layout.addWidget(fold)
        # Only the closing stretch takes spare height: folded sections report vertical growth through their layout.
        layout.addStretch(1)
        self._auto_state = {}
        self.selection_widgets = (intro,scroll)
        self.controls = Controls(self)
        from .key_slots import KeySlots
        self.key_slots = KeySlots(self)
        self.session.changed.connect(self.refresh)
        self.session.telemetry.connect(self.controls.telemetry)
        app.add_overlay(self.draw_joints)
        from .axis_guides import Quiet
        Quiet(self,app.viewport)
        app.add_context_menu(self.context_menu)
        self.toolbar,self.simulation_bar,self.actions = build(self)
        self.refresh_profiles()
        self.name_edit.editingFinished.connect(lambda:self.live_joint("name",self.name_edit.text()))
        self.drive.currentIndexChanged.connect(lambda:self.live_joint("drive",self.drive.currentData()))
        self.limited.toggled.connect(lambda value:self.live_joint("limited",value))
        for widget,key in ((self.lower,"lower"),(self.upper,"upper"),(self.hardness,"limit_hardness"),(self.target,"target"),
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
            self.profile_sync.setToolTip(tr(help.TIP_PROFILE_SYNC))

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
                      pivot=(old or {}).get("pivot",[0,0,0]),axis=(old or {}).get("axis",[0,0,1]),zero=(old or {}).get("zero"),
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
            action.setIcon(icon("pause" if key=="play" and self.session.running else action.property("newton_icon")))
        self.controls.refresh_icons()
        self.environment.restyle()
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
        from . import runtime_setup
        saved = QSettings().value("newton/python","")
        if saved and Path(saved).is_file():
            return saved
        return runtime_setup.resolve()

    def browse(self):
        path,_ = QFileDialog.getOpenFileName(self,tr("Choose Python with MuJoCo"),self.python.text(),tr("Python (python.exe python);;All files (*)"))
        if path:
            self.python.setText(path)
            self.collision_view.request()

    def status_message(self,text):
        # Timed, because the host replaces an untimed message with the active tool's hint.
        self.app.window.statusBar().showMessage(tr(text),8000)

    def selected(self):
        """Selected bodies; a selected axis or connection object stands for its body."""
        from .axis_objects import owner_id
        chosen = [g for g in self.app.scene.groups if g in self.app.scene.selection]
        owners = {owner_id(g) for g in chosen}
        return [g for g in self.app.scene.groups if not owner_id(g) and (g in chosen or g.uid in owners)]

    def current_joint(self):
        groups = self.selected()
        return settings(groups[0]).get("joint") if len(groups)==1 else None

    def apply_units(self,rotation):
        """Suffix and precision of the motion fields, in the document's unit for a slide axis."""
        from . import units
        position,rate,acceleration = (units.ANGLE,units.ANGLE_RATE,units.ANGLE_ACCELERATION) if rotation else (units.length(),units.speed(),units.acceleration())
        for w in (self.lower,self.upper,self.target):
            units.apply(w,position)
        for w,scale in ((self.max_speed,rate),(self.acceleration,acceleration),(self.deceleration,acceleration)):
            units.apply(w,scale,.01 if rotation else scale.step)

    @staticmethod
    def joint_scales(kind,key):
        """Scale of a stored motion value: degrees for a hinge, the document's length unit for a slide."""
        from . import units
        if kind=="hinge":
            return units.ANGLE_RATE if key=="max_speed" else units.ANGLE_ACCELERATION if key in ("acceleration","deceleration") else units.ANGLE
        return units.speed() if key=="max_speed" else units.acceleration() if key in ("acceleration","deceleration") else units.length()

    def update_units(self,*args):
        from . import units
        j = self.current_joint()
        rotation = not j or j.get("type","hinge")=="hinge"
        self.apply_units(rotation)
        span = 180 if rotation else units.length().show(units.SPAN_METRES)
        velocity = self.drive.currentData()=="velocity"
        self.target.setSuffix(self.max_speed.suffix() if velocity else self.lower.suffix())
        self.force.setSuffix(" Nm" if rotation else " N")
        self.drive.setItemText(1,tr("Servo / angle") if rotation else tr("Position / distance"))
        self.joint_form.setRowVisible(self.ranges["target"],self.drive.currentData()!="free")
        self.ranges["lower"].set_span(-span,0)
        self.ranges["upper"].set_span(0,span)
        drive = self.drive.currentData()
        if drive=="position" and self.limited.isChecked() and self.upper.value()>self.lower.value():
            low,high = self.lower.value(),self.upper.value()
            bounded = True
        elif drive=="velocity":
            low,high = -self.max_speed.value(),self.max_speed.value()
            bounded = True
        else:
            low,high = -span,span
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
        for w in (self.lower,self.upper,self.hardness):
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
            value = self.joint_scales(changed["type"],key).si(value)
        if key=="limit_hardness":
            value /= 100
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

    def show_body_collider(self,shown):
        groups = self.selected()
        if len(groups)==1:
            self.collision_view.show_body(groups[0].uid,shown)

    def refresh_auto_sections(self,groups):
        """Fold a section whose content is empty or at its default, open it otherwise.

        Applied when the selection or the section's own state changes, so a manual toggle holds until then."""
        if len(groups)!=1:
            # Hidden sections: forget the state so the next single selection applies the rule again.
            self._auto_state = {}
            return
        group = groups[0];cfg = settings(group)
        engaged = {
            self.coupling_section:self.coupling_editor.engaged(),
            self.connection_section:bool(cfg.get("point_attachment")),
            self.flexible_section:bool(cfg.get("flexible")),
            self.environment_section:bool(cfg.get("simulation_override")),
        }
        for fold,on in engaged.items():
            state = (group.uid,on)
            if self._auto_state.get(fold)!=state:
                self._auto_state[fold] = state
                fold.set_open(on)

    def refresh_collider_check(self):
        groups = self.selected()
        blocked = self.show_collider.blockSignals(True)
        self.show_collider.setChecked(len(groups)==1 and self.collision_view.shown(groups[0].uid))
        self.show_collider.setEnabled(len(groups)==1)
        self.show_collider.blockSignals(blocked)

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

    def marker(self,group,key):
        from .axis_objects import marker_of
        return marker_of(self.app.scene,group,key) if group is not None else None

    def refresh_lock(self,check,group,key):
        marker = self.marker(group,key)
        previous = check.blockSignals(True)
        check.setChecked(bool(getattr(marker,"locked",False)))
        check.setEnabled(marker is not None)
        check.blockSignals(previous)

    def lock_marker(self,key,on):
        groups = self.selected()
        marker = self.marker(groups[0],key) if len(groups)==1 and not self.session.workspace else None
        if marker is None or bool(getattr(marker,"locked",False))==on:
            return
        from .axis_objects import LockMarker
        self.app.viewport.history.execute(LockMarker(marker,on))
        self.app.viewport.notify_scene_changed()

    def usable_settings(self,groups):
        """Which settings act on at least one selected body: a fixed body has no motion, an excluded one nothing."""
        modes = {body_mode(g) for g in groups} or {"dynamic"}
        moving,simulated = "dynamic" in modes,modes!={"ignore"}
        # A fixed body carried by a reference body still adds its mass to that body.
        carried = moving or any(body_mode(g)=="static" and reference_id(g) for g in groups)
        usable = {fold:simulated for fold in (self.body_section,self.collisions_section,self.connection_section,self.environment_section)}
        usable.update({fold:moving for fold in (self.joint_box,self.coupling_section,self.flexible_section)})
        usable[self.environment_section] = carried
        usable.update(mass=carried,reference=simulated)
        return usable

    def refresh_widgets(self,*args):
        active = self.session.workspace is not None
        if getattr(self,"was_active",False) and not active:
            # One hint area: the notice would hide the warning the user asked to keep.
            if self.controls.keep.isChecked() and self.controls.kept:
                self.controls.restore_kept(self.app.scene)
            else:
                self.controls.message(tr("The simulation was reset and the original model is restored."))
        self.was_active = active
        groups = self.selected()
        if active:
            groups = getattr(self,"_sidebar_groups",[])
        else:
            self._sidebar_groups = groups
        usable = self.usable_settings(groups)
        # Only the bodies: sections stay foldable while the simulation runs or a setting has no effect.
        for fold in self.sections:
            fold.body.setEnabled(not active and usable.get(fold,True))
        self.mass.setEnabled(usable["mass"])
        for button in self.reference_buttons:button.setEnabled(usable["reference"])
        if (self._slider_history is not None and (self.app.viewport.history is not self._slider_history
            or tuple(g.uid for g in groups)!=self._slider_selection)):
            self.end_slider_edit()
        if not active:
            self.detail_uid = groups[0].uid if len(groups)==1 else None
        self.profile_box.body.setEnabled(not active and len(groups)==1)
        if not active:self.refresh_profile_link()
        if self.profile_manager is not None:
            self.profile_manager.update_buttons();self.profile_manager.parameters.follow_units()
        for widget in self.selection_widgets:
            widget.setVisible(bool(groups))
        for key in ("rotate","slide","link","unlink","free","fixed"):
            self.actions[key].setEnabled(not active and bool(groups) and (len(groups)==1 or key in ("unlink","free","fixed")))
        if len(groups)==1 and settings(groups[0]).get("flexible"):
            self.actions["rotate"].setEnabled(False);self.actions["slide"].setEnabled(False)
        for key in ("connect_ball","connect_hinge","connect_fixed"):
            self.actions[key].setEnabled(not active and len(groups)==1 and not settings(groups[0]).get("flexible"))
        self.actions["drag"].setEnabled(active and self.session.ready)
        self.actions["reset"].setEnabled(active)
        self.actions["play"].setEnabled(not active or self.session.ready)
        self.actions["play"].setIcon(icon("pause" if active and self.session.running else "play"))
        if active:
            self.collision_view.stop()
            self.controls.refresh(self.control_rows,True)
            return
        self.collision_view.request()
        from .axis_objects import install as install_axis_objects,sync_loaded
        for vp in self.app.window.all_viewports():
            install(vp)
            install_axis_objects(self,vp)
        sync_loaded(self,self.app.viewport)
        from .axis_edit import install as install_axis_edit
        install_axis_edit(self)
        signature = (id(self.app.scene),units_signature(),tuple(g.uid for g in groups),
            tuple((g.uid,g.name,repr((g.ext or {}).get(KEY)),bool(getattr(g,"locked",False))) for g in self.app.scene.groups))
        if signature==self.selection_signature:
            self.controls.refresh(self.control_rows,False)
            return
        self.selection_signature = signature
        self.control_rows = joint_rows(self.app.scene)
        self.axis_rows = joint_rows(self.app.scene,include_fixed=True)
        if self.axis_rows:
            ensure_axis_layer(self.app.scene)
        self.reference_names = {g.uid:g.name for g in self.app.scene.groups}
        self.gizmo_sizes = {g.uid:gizmo_size(g) for g in self.app.scene.groups if settings(g).get("joint")}
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
        self.collision_box.setVisible(len(groups)==1)
        self.collision_pairs.refresh()
        self.environment_section.setVisible(len(groups)==1)
        self.environment.refresh(groups[0] if len(groups)==1 else None)
        self.flexible_section.setVisible(len(groups)==1)
        self.flexible_editor.refresh(groups[0] if len(groups)==1 else None)
        self.connection_section.setVisible(len(groups)==1 and not settings(groups[0]).get("flexible"))
        self.connection_editor.refresh(groups[0] if len(groups)==1 else None)
        self.refresh_lock(self.axis_lock,groups[0] if len(groups)==1 else None,"axis_of")
        self.refresh_auto_sections(groups)
        if not groups:
            self.reference_table.set_rows([])
            return
        group = groups[0]
        cfg = settings(group)
        self.mode.setCurrentIndex(self.mode.findData(body_mode(group)))
        parent = next((g for g in self.app.scene.groups if g.uid==reference_id(group)),None)
        rigid = not cfg.get("joint") and not cfg.get("flexible")
        uid = reference_id(group)
        self.reference_table.set_rows([(uid,parent,parent.name if parent else tr("Missing body"),tr("rigid attachment") if rigid and parent else "")] if uid else [])
        self.shape.setCurrentIndex(self.shape.findData(cfg["shape"]))
        self.collision_form.setRowVisible(self.shape,not bool(cfg.get("flexible")))
        self.refresh_collider_check()
        for widget,key in ((self.mass,"mass"),(self.friction,"friction"),(self.bounce,"restitution")):
            widget.setValue(cfg[key])
        if cfg.get("joint"):
            j = joint_settings(cfg["joint"])
            previous = self.target.blockSignals(True)
            self.target.setRange(-1e6,1e6)
            self.target.blockSignals(previous)
            self.apply_units(j["type"]=="hinge")
            self.kind_label.setText(tr("Rotation axis") if j["type"]=="hinge" else tr("Linear axis"))
            self.name_edit.setText(j["name"])
            self.drive.setCurrentIndex(self.drive.findData(j["drive"]))
            self.limited.setChecked(j["limited"])
            for w,key in ((self.lower,"lower"),(self.upper,"upper"),(self.target,"target"),
                          (self.max_speed,"max_speed"),(self.acceleration,"acceleration"),(self.deceleration,"deceleration")):
                w.setValue(self.joint_scales(j["type"],key).show(j[key]))
            self.deceleration_sync.setChecked(j["deceleration_sync"])
            self.hardness.setValue(j["limit_hardness"]*100)
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
        stored = lambda key,widget:self.joint_scales(j["type"],key).si(widget.value())
        j.update(name=self.name_edit.text().strip() or groups[0].name,drive=self.drive.currentData(),
            limited=self.limited.isChecked(),lower=stored("lower",self.lower),upper=stored("upper",self.upper),
            limit_hardness=self.hardness.value()/100,
            target=stored("target",self.target),max_speed=stored("max_speed",self.max_speed),
            acceleration=stored("acceleration",self.acceleration),deceleration=stored("deceleration",self.deceleration),
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
            self.status_message(tr("Axis removed."))

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
        values = with_zero(group,values)
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
        def finish(anchor,axis,zero=None):
            self.placement = None
            try:
                placed = fit_limits(with_zero(group,dict(values,pivot=anchor,axis=axis,zero=zero)))
                self.commit_joint(scene,group,placed,body_values=body_values)
            except ValueError as exc:
                self.status_message(str(exc))
            finally:
                if self.app.viewport is vp:
                    self.app.window._activate_tool("select")
        preview = dict(joint_settings(dict(values,pivot=[0,0,0],axis=[0,0,1])),uid=group.uid)
        self.gizmo_sizes.setdefault(group.uid,gizmo_size(group))
        self.placement = PlacementTool(finish,cancel,preview,zero=values.get("type","hinge")=="hinge")
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
        def accepts(parent):
            try:validate_reference(scene,child,parent.uid)
            except ValueError:return False
            return True
        vp.set_active_tool(ReferencePickTool(choose,cancel,accepts))
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
        if not groups:
            return
        if len(groups)==1:
            menu.addAction(icon("link"),tr("Assign reference body…"),lambda:QTimer.singleShot(0,self.pick_reference))
        menu.addAction(icon("unlink"),tr("Detach reference body"),lambda:QTimer.singleShot(0,self.detach_reference))
        if len(groups)!=1:
            return
        from .connections import KINDS,begin
        menu.addSeparator()
        connect = menu.addMenu(icon("connect"),tr("Connect bodies"))
        for kind,label in KINDS.items():
            connect.addAction(icon("connection_"+kind),tr(label),lambda *_,k=kind:QTimer.singleShot(0,lambda:begin(self,k)))
        if settings(groups[0]).get("point_attachment"):
            menu.addAction(icon("unlink"),tr("Remove connection"),lambda:QTimer.singleShot(0,self.connection_editor.detach))
        menu.addSeparator()
        from .axis_objects import AXIS,CONNECTION,markers,owner_id
        body = groups[0]
        for key,text,name in ((AXIS,"Select axis object","rotate"),(CONNECTION,"Select connection object","connect")):
            marker = None if owner_id(body) else next((m for m in markers(self.app.scene,key) if owner_id(m)==body.uid),None)
            action = menu.addAction(icon(name),tr(text),lambda *_,m=marker:QTimer.singleShot(0,lambda:self.select_object(m)))
            action.setEnabled(marker is not None and not getattr(marker,"locked",False))

    def select_object(self,marker):
        if marker in self.app.scene.groups:
            self.app.scene.select([marker])
            self.app.viewport.notify_scene_changed()

    def draw_joints(self,viewport,painter):
        from .glow import draw as draw_glow
        draw_glow(self,viewport,painter)
        self.collision_view.draw(viewport,painter)
        from .axis_guides import draw
        draw(self,viewport,painter)
        from .connections import draw as draw_connections
        draw_connections(self,viewport,painter)

    def activate_drag(self):
        self.session.activate_drag()

    def show_controls(self):
        self.controls.refresh(self.control_rows,self.session.workspace is not None)
        opening = not self.controls.isVisible()
        if opening:
            self.controls.place(self.app.viewport)
        self.controls.show()
        if opening:
            # The window frame is known only once shown; Wayland ignores both moves.
            self.controls.place(self.app.viewport)
        self.controls.raise_()
        self.controls.activateWindow()

    def virtual_controls(self):
        """The controls the control panel shows; during a simulation the ones it started with."""
        if self.session.workspace:
            return list(self.session.virtual.values())
        from .virtual_controls import resolve,stored
        try:
            return resolve(stored(self.app.document_data()),joint_rows(self.app.scene))
        except ValueError:
            return []  # Start reports the problem; the panel still shows the joints.

    def edit_virtual_controls(self,select=None):
        if self.session.workspace:
            return  # The simulation's history refuses the change; the button is disabled then.
        from .virtual_editor import VirtualControlEditor
        try:
            editor = VirtualControlEditor(self,select)
        except ValueError as exc:
            self.controls.message(str(exc),"error")
            return
        editor.exec()

    def start_or_pause(self):
        if self.session.workspace:
            self.session.toggle()
            return
        if self.placement:
            self.app.window._activate_tool("select")
        try:
            self.controls.kept = None
            self.app.viewport.end_group_edit()
            self.refresh()
            from .virtual_controls import resolve,stored
            rows = joint_rows(self.app.scene)
            controls = resolve(stored(self.app.document_data()),rows)
            from . import key_bindings
            bindings = key_bindings.resolve(key_bindings.stored(self.app.document_data()),rows,controls)
            scene,specs,movers = prepare(self.app.scene,hidden=hidden_mode())
            python = self.python.text().strip()
            QSettings().setValue("newton/python",python)
            from .environment_ui import global_damping
            linear,angular = global_damping()
            quality = QSettings().value("newton/quality","balanced")
            self.session.start(python,scene,specs,movers,self.gravity.value(),self.floor.isChecked(),linear,angular,quality,controls,bindings)
            self.controls.message(tr("Drag passive bodies with the mouse. Move actuators with the controls."))
            self.warn_ground_contact(specs,movers)
        except Exception as exc:
            self.controls.message(str(exc),"error")
        self.show_controls()

    def warn_ground_contact(self,specs,movers):
        if str(QSettings().value("newton/warn_ground_contact",True)).lower() not in ("true","1"):return
        from .model import ground_scrapers
        from .model import lowest_z
        from core.units import fmt_len_fine
        by_uid = {s["uid"]:s for s in specs}
        # The clones are what the simulation view shows and selects, so the rows must be the clones.
        bodies = [(movers[uid],movers[uid].name,tr("{depth} below",depth=fmt_len_fine(-lowest_z(by_uid[uid]))))
                  for uid in ground_scrapers(specs,self.floor.isChecked())]
        if bodies:
            self.controls.message(tr("These bodies reach below Z = 0 and scrape along the ground, which distorts the result. Lift them above Z = 0 or switch off their ground contact."),"warning",bodies)

    def shutdown(self,*args):
        self.collision_view.stop()
        self.session.stop_worker()
        self.controls.ending_silently = True
        self.controls.close()
