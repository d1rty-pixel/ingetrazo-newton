"""Typed, categorized values for built-in inspection and custom profile editing."""
import copy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QTabWidget,QScrollArea,QLineEdit,QLabel,QComboBox,QCheckBox
from .i18n import tr
from . import profiles,units,help_texts as help
from .environment_ui import number,EnvironmentOverrides
from .toolbar import decorate,physical_label,pictogram_check


class ProfileParameters(QWidget):
    def __init__(self,panel,changed):
        super().__init__();self.panel = panel;self.changed = changed;self.profile = None;self.updating = False;self.error = None;self.shown_units = None
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
        def choice(form,title,values,callback,pictograms):
            field = QComboBox()
            for text,key in values:field.addItem(tr(text),key)
            decorate(field,pictograms)
            form.addRow(physical_label(tr(title)),field);self.choices.append(field)
            field.currentIndexChanged.connect(callback);return field
        def numeric(form,title,low,high,callback,art):
            field = number(low,high);form.addRow(physical_label(tr(title),art),field);self.numbers.append(field)
            field.valueChanged.connect(callback);return field
        body = page("Body",help.BODY)
        self.mode = choice(body,"Behaviour",[("Movable","dynamic"),("Fixed","static"),("Exclude from simulation","ignore")],lambda:self.edit("body","mode",self.mode.currentData()),"mode")
        self.mass = numeric(body,"Mass (kg)",.001,1e12,lambda v:self.edit("body","mass",v),"mass")
        self.friction = numeric(body,"Friction",0,1e6,lambda v:self.edit("body","friction",v),"friction")
        self.bounce = numeric(body,"Bounce (approx.)",0,1,lambda v:self.edit("body","restitution",v),"bounce")
        collisions = page("Collisions",help.COLLISION_SHAPE)
        self.shape = choice(collisions,"Collision shape",[("Box","box"),("Sphere","sphere"),("Convex hull","hull"),("Child components","compound")],lambda:self.edit("body","shape",self.shape.currentData()),"shape")
        motion = page("Motion",help.MOTION)
        self.axis_type = choice(motion,"Axis",[("No axis",None),("Rotation axis","hinge"),("Linear axis","slide")],self.change_axis,"axis")
        self.motion_fields = QWidget();self.motion_form = mf = QFormLayout(self.motion_fields);mf.setContentsMargins(0,0,0,0)
        motion.addRow(self.motion_fields)
        self.drive = choice(mf,"Actuator",[("Free / passive","free"),("Servo / position","position"),("Motor / speed","velocity")],lambda:self.edit("joint","drive",self.drive.currentData()),"drive")
        self.limited = pictogram_check(QCheckBox(tr("Use limits")),"limits");mf.addRow(self.limited);self.choices.append(self.limited)
        self.limited.toggled.connect(lambda v:self.edit("joint","limited",v))
        self.motion = {}
        for key,title,low,art in (("lower","Minimum",-1e12,"limit_min"),("upper","Maximum",-1e12,"limit_max"),
                              ("limit_hardness","Limit hardness",0,"limit_hardness"),("target","Initial target",-1e12,"target"),
                              ("max_speed","Speed",.000001,"speed"),("acceleration","Acceleration",.000001,"acceleration"),
                              ("deceleration","Deceleration",.000001,"deceleration"),("force","Max. force",0,"force")):
            self.motion[key] = numeric(mf,title,low,1e12,lambda v,k=key:self.edit("joint",k,v/self.factor(k)),art)
        self.motion["limit_hardness"].setMaximum(100)
        self.motion["limit_hardness"].setToolTip(tr(help.LIMIT_HARDNESS))
        self.sync = pictogram_check(QCheckBox(tr("Synchronize acceleration and deceleration")),"sync");mf.addRow(self.sync);self.choices.append(self.sync)
        self.sync.toggled.connect(lambda v:self.edit("joint","deceleration_sync",v))
        overrides = page("Simulation overrides",help.PROFILE_OVERRIDES)
        self.overrides = ProfileOverrides(panel,self);overrides.addRow(self.overrides)
        for _,_,widget,_,_ in self.overrides.rows:(self.choices if isinstance(widget,QCheckBox) else self.numbers).append(widget)
        self.name.editingFinished.connect(lambda:self.edit("name",None,self.name.text()))

    def factor(self,key):
        joint = (self.profile or {}).get("joint") or {}
        if key in ("force","limit_hardness"):return 1 if key=="force" else 100
        return self.panel.joint_scales(joint.get("type"),key).factor

    def follow_units(self):
        if self.profile and self.shown_units!=units.signature():self.load(self.profile)

    def load(self,profile):
        self.shown_units = units.signature()
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
                    if key in ("force","limit_hardness"):
                        field.setSuffix((" Nm" if angle else " N") if key=="force" else " %");field.setValue(joint[key]*self.factor(key));continue
                    scale = self.panel.joint_scales(joint["type"],"max_speed" if key=="target" and joint["drive"]=="velocity" else key)
                    units.apply(field,scale);field.setValue(joint[key]*scale.factor)
                self.motion["deceleration"].setReadOnly(builtin or joint["deceleration_sync"])
            self.overrides.refresh(profile)
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
        elif section=="joint" and p["joint"] is None:return
        else:p[section][key] = value
        self.accept(p)

    def change_axis(self):
        if self.updating or not self.profile or self.profile["builtin"]:return
        p = copy.deepcopy(self.profile);kind = self.axis_type.currentData()
        if kind is None:p["joint"] = None
        else:
            drive = (p.get("joint") or {}).get("drive","free")
            p["joint"] = next(copy.deepcopy(v["joint"]) for v in profiles.builtins() if v["id"]==f"builtin_{kind}_{drive}")
        self.accept(p)


class ProfileOverrides(EnvironmentOverrides):
    """The sidebar's override rows, reading and writing the profile's stored override."""
    sliders = False

    def __init__(self,panel,parameters):
        self.parameters = parameters
        super().__init__(panel)

    def stored(self,profile):
        return profile["body"]["simulation_override"] if profile else None

    def velocity_editable(self,profile):
        return True

    def save(self,value):
        p = self.parameters
        if p.updating or not p.profile or p.profile["builtin"]:return
        q = copy.deepcopy(p.profile);q["body"]["simulation_override"] = value;p.accept(q)
