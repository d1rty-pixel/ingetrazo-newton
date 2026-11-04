"""Typed, categorized values for built-in inspection and custom profile editing."""
import copy
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QTabWidget,QScrollArea,QLineEdit,QLabel,QComboBox,QCheckBox
from .i18n import tr
from . import profiles,help_texts as help
from .environment_ui import number,global_damping


class ProfileParameters(QWidget):
    def __init__(self,panel,changed):
        super().__init__();self.panel = panel;self.changed = changed;self.profile = None;self.updating = False;self.error = None
        layout = QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.name = QLineEdit();layout.addWidget(self.name)
        self.notice = QLabel();self.notice.setWordWrap(True);layout.addWidget(self.notice)
        self.tabs = QTabWidget();layout.addWidget(self.tabs)
        self.numbers = [];self.choices = []
        def page(title,description):
            area = QScrollArea();area.setWidgetResizable(True);content = QWidget();area.setWidget(content)
            box = QVBoxLayout(content);note = QLabel(tr(description));note.setWordWrap(True);box.addWidget(note)
            form = QFormLayout();form.setRowWrapPolicy(QFormLayout.WrapLongRows);box.addLayout(form);box.addStretch()
            self.tabs.addTab(area,tr(title).replace('&','&&'));return form
        def choice(form,title,values,callback):
            field = QComboBox()
            for text,key in values:field.addItem(tr(text),key)
            form.addRow(tr(title),field);self.choices.append(field)
            field.currentIndexChanged.connect(callback);return field
        def numeric(form,title,low,high,callback):
            field = number(low,high);form.addRow(tr(title),field);self.numbers.append(field)
            field.valueChanged.connect(callback);return field
        body = page("Body & contact",help.BODY)
        self.mode = choice(body,"Behaviour",[("Movable","dynamic"),("Fixed","static"),("Exclude from simulation","ignore")],lambda:self.edit("body","mode",self.mode.currentData()))
        self.shape = choice(body,"Collision shape",[("Box","box"),("Sphere","sphere"),("Convex hull","hull"),("Child components","compound")],lambda:self.edit("body","shape",self.shape.currentData()))
        self.mass = numeric(body,"Mass (kg)",.001,1e12,lambda v:self.edit("body","mass",v))
        self.friction = numeric(body,"Friction",0,1e6,lambda v:self.edit("body","friction",v))
        self.bounce = numeric(body,"Bounce (approx.)",0,1,lambda v:self.edit("body","restitution",v))
        motion = page("Motion",help.MOTION)
        self.axis_type = choice(motion,"Axis",[("No axis",None),("Rotation axis","hinge"),("Linear axis","slide")],self.change_axis)
        self.motion_fields = QWidget();self.motion_form = mf = QFormLayout(self.motion_fields);mf.setContentsMargins(0,0,0,0)
        motion.addRow(self.motion_fields)
        self.drive = choice(mf,"Actuator",[("Free / passive","free"),("Servo / position","position"),("Motor / speed","velocity")],lambda:self.edit("joint","drive",self.drive.currentData()))
        self.limited = QCheckBox(tr("Use limits"));mf.addRow(self.limited);self.choices.append(self.limited)
        self.limited.toggled.connect(lambda v:self.edit("joint","limited",v))
        self.motion = {}
        for key,title,low in (("lower","Minimum",-1e12),("upper","Maximum",-1e12),("target","Initial target",-1e12),
                              ("max_speed","Speed",.000001),("acceleration","Acceleration",.000001),("deceleration","Deceleration",.000001),("force","Max. force",0)):
            self.motion[key] = numeric(mf,title,low,1e12,lambda v,k=key:self.edit("joint",k,v/self.factor(k)))
        self.sync = QCheckBox(tr("Synchronize acceleration and deceleration"));mf.addRow(self.sync);self.choices.append(self.sync)
        self.sync.toggled.connect(lambda v:self.edit("joint","deceleration_sync",v))
        overrides = page("Simulation overrides",help.PROFILE_OVERRIDES)
        self.own = QCheckBox(tr("Use own simulation settings"));overrides.addRow(self.own);self.choices.append(self.own)
        self.own.toggled.connect(self.enable_overrides)
        self.override_fields = QWidget();of = QFormLayout(self.override_fields);of.setContentsMargins(0,0,0,0);overrides.addRow(self.override_fields)
        self.gravity = [];self.velocity = []
        for i,axis in enumerate("XYZ"):
            field = numeric(of,tr("Gravity {axis}",axis=axis),-1e6,1e6,lambda v,n=i:self.edit_vector("gravity",n,v));field.setSuffix(" m/s²");self.gravity.append(field)
        self.override_numbers = {}
        for key,title,high,suffix in (("linear_damping","Linear damping",100," /s"),("angular_damping","Angular damping",100," /s"),
                                     ("attraction","Attraction",1e12," m³/s²"),("softening","Softening radius",1e6," m")):
            field = numeric(of,title,0,high,lambda v,k=key:self.edit("override",k,v));field.setSuffix(suffix);self.override_numbers[key] = field
        self.floor = QCheckBox(tr("Ground contact at Z = 0"));of.addRow(self.floor);self.choices.append(self.floor)
        self.floor.toggled.connect(lambda v:self.edit("override","floor",v))
        for i,axis in enumerate("XYZ"):
            field = numeric(of,tr("Initial velocity {axis}",axis=axis),-1e6,1e6,lambda v,n=i:self.edit_vector("initial_velocity",n,v));field.setSuffix(" m/s");self.velocity.append(field)
        self.name.editingFinished.connect(lambda:self.edit("name",None,self.name.text()))

    def factor(self,key):
        joint = (self.profile or {}).get("joint") or {}
        return 1 if key=="force" else 180/math.pi if joint.get("type")=="hinge" else 1000

    def defaults(self):
        linear,angular = global_damping()
        return dict(gravity=[0,0,self.panel.gravity.value()],linear_damping=linear,angular_damping=angular,
            floor=self.panel.floor.isChecked(),attraction=0,softening=.01,initial_velocity=[0,0,0])

    def load(self,profile):
        self.updating = True;self.profile = copy.deepcopy(profile);self.error = None
        try:
            if not profile:self.hide();return
            self.show();builtin = profile["builtin"];body = profile["body"];joint = profile["joint"]
            self.name.setText(tr(profile["name"]) if builtin else profile["name"]);self.name.setReadOnly(builtin)
            self.notice.setText(tr("Built-in · read-only") if builtin else tr("Custom profile"))
            for widget in self.numbers:widget.setReadOnly(builtin)
            for widget in self.choices:
                # Locked controls must remain readable in both host themes.
                palette = widget.palette()
                for role in (QPalette.Text,QPalette.WindowText,QPalette.ButtonText):
                    palette.setColor(QPalette.Disabled,role,palette.color(QPalette.Active,role))
                widget.setPalette(palette);widget.setEnabled(not builtin)
            self.mode.setCurrentIndex(self.mode.findData(body["mode"]));self.shape.setCurrentIndex(self.shape.findData(body["shape"]))
            for field,key in ((self.mass,"mass"),(self.friction,"friction"),(self.bounce,"restitution")):field.setValue(body[key])
            self.axis_type.setCurrentIndex(self.axis_type.findData(joint["type"] if joint else None));self.motion_fields.setVisible(bool(joint))
            if joint:
                self.drive.setCurrentIndex(self.drive.findData(joint["drive"]));self.limited.setChecked(joint["limited"]);self.sync.setChecked(joint["deceleration_sync"])
                angle = joint["type"]=="hinge"
                for key,field in self.motion.items():
                    unit = (" Nm" if angle else " N") if key=="force" else ("°" if angle else " mm")
                    if key=="max_speed" or (key=="target" and joint["drive"]=="velocity"):unit += "/s"
                    if key in ("acceleration","deceleration"):unit += "/s²"
                    field.setSuffix(unit);field.setValue(joint[key]*self.factor(key))
                self.motion["deceleration"].setReadOnly(builtin or joint["deceleration_sync"])
            own = body.get("simulation_override");self.own.setChecked(own is not None);self.override_fields.setVisible(own is not None)
            values = {**self.defaults(),**(own or {})}
            for field,value in zip(self.gravity,values["gravity"]):field.setValue(value)
            for field,value in zip(self.velocity,values["initial_velocity"]):field.setValue(value)
            for key,field in self.override_numbers.items():field.setValue(values[key])
            self.floor.setChecked(values["floor"])
        finally:self.updating = False

    def accept(self,value):
        try:
            joint = value.get("joint")
            if joint and joint["limited"] and not joint["lower"]<=0<=joint["upper"]:
                raise ValueError("Keep zero inside the limits and set minimum below maximum.")
            normalized = profiles.validate(value)
            if self.changed(normalized):self.load(normalized)
        except (ValueError,TypeError,KeyError) as exc:
            self.error = str(exc);self.notice.setText(tr(str(exc)))

    def edit(self,section,key,value):
        if self.updating or not self.profile or self.profile["builtin"]:return
        p = copy.deepcopy(self.profile)
        if section=="name":p["name"] = value
        elif section=="override":
            if p["body"]["simulation_override"] is None:return
            p["body"]["simulation_override"][key] = value
        elif section=="joint" and p["joint"] is None:return
        else:p[section][key] = value
        self.accept(p)

    def edit_vector(self,key,index,value):
        if self.updating or not self.profile or self.profile["builtin"]:return
        p = copy.deepcopy(self.profile);override = p["body"]["simulation_override"]
        if override is None:return
        override[key] = list(override.get(key,self.defaults()[key]));override[key][index] = value;self.accept(p)

    def enable_overrides(self,enabled):
        self.edit("body","simulation_override",self.defaults() if enabled else None)

    def change_axis(self):
        if self.updating or not self.profile or self.profile["builtin"]:return
        p = copy.deepcopy(self.profile);kind = self.axis_type.currentData()
        if kind is None:p["joint"] = None
        else:
            drive = (p.get("joint") or {}).get("drive","free")
            p["joint"] = next(copy.deepcopy(v["joint"]) for v in profiles.builtins() if v["id"]==f"builtin_{kind}_{drive}")
        self.accept(p)
