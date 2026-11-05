"""Per-body environment overrides; global defaults live in Preferences."""
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QCheckBox,QDoubleSpinBox,QLabel,QToolButton
from .model import KEY,settings
from .i18n import tr
from .toolbar import physical_label,pictogram_check
from .icons import attach
from .range_control import scroll_safe
from . import help_texts as help,units


def global_damping():
    st = QSettings()
    return float(st.value("newton/linear_damping",0)),float(st.value("newton/angular_damping",0))


def number(low,high,value=0):
    widget = QDoubleSpinBox();widget.setRange(low,high);widget.setDecimals(3)
    widget.setKeyboardTracking(False);widget.setValue(value)
    return scroll_safe(widget)


# Half a step of the three-decimal spin boxes: what the box shows is what is compared.
TOLERANCE = 5e-4


def same(a,b,tolerance=TOLERANCE):
    return a==b if isinstance(a,bool) or isinstance(b,bool) else abs(a-b)<=tolerance


def dim(widget,on):
    """Draw the text in the disabled colour while the widget stays editable."""
    if not on:
        widget.setPalette(QPalette());return
    palette = QPalette(widget.palette());grey = QApplication.palette().color(QPalette.Disabled,QPalette.WindowText)
    for role in (QPalette.Text,QPalette.WindowText,QPalette.ButtonText):palette.setColor(role,grey)
    widget.setPalette(palette)


class EnvironmentOverrides(QWidget):
    """Every environment setting of the body; a value equal to the global default is greyed and not stored."""
    VECTORS = ("gravity","initial_velocity")
    KEYS = ("gravity","linear_damping","angular_damping","floor","attraction","softening","initial_velocity")

    def __init__(self,panel):
        super().__init__()
        self.panel = panel;self.updating = False;self.group = None;self.rows = []
        layout = QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        # The field note sits between two forms: a word-wrapped label inside a QFormLayout
        # gets too little height and is overlapped by the following rows.
        form = QFormLayout();form.setContentsMargins(0,0,0,0);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        layout.addLayout(form)
        self.gravity = [number(-1e6,1e6) for _ in range(3)]
        from .range_control import RangeControl
        for i,(axis,widget) in enumerate(zip(("X","Y","Z"),self.gravity)):
            widget.setSuffix(" m/s²")
            control = RangeControl(widget,-100,100)
            control.slider.setMinimumWidth(60)  # the reset button must still fit a 260 px sidebar
            control.gestureStarted.connect(panel.begin_slider_edit);control.gestureFinished.connect(panel.end_slider_edit)
            panel.ranges["override_gravity_"+axis] = control
            self.add(form,tr("Gravity {axis}",axis=axis),"gravity",widget,"gravity",i,control)
        self.linear,self.angular = number(0,100),number(0,100)
        self.linear.setSuffix(" /s");self.angular.setSuffix(" /s")
        self.add(form,tr("Linear damping"),"linear_damping",self.linear,"linear_damping")
        self.add(form,tr("Angular damping"),"angular_damping",self.angular,"angular_damping")
        self.floor = pictogram_check(QCheckBox(tr("Ground contact at Z = 0")),"ground")
        self.add(form,None,"ground",self.floor,"floor",dimmed=self.floor.label)
        note = QLabel(tr(help.FIELDS))
        note.setWordWrap(True);layout.addWidget(note)
        form = QFormLayout();form.setContentsMargins(0,0,0,0);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        layout.addLayout(form)
        self.attraction = number(0,1e12);self.attraction.setSuffix(" m³/s²")
        self.softening = number(0,1e6,.01)
        self.add(form,tr("Attraction"),"attraction",self.attraction,"attraction")
        self.add(form,tr("Softening radius"),"softening",self.softening,"softening")
        self.velocity = [number(-1e6,1e6) for _ in range(3)]
        for i,(axis,widget) in enumerate(zip(("X","Y","Z"),self.velocity)):
            self.add(form,tr("Initial velocity {axis}",axis=axis),"velocity",widget,"initial_velocity",i)
        # Inherited values show the global default, so they follow it.
        panel.gravity.valueChanged.connect(self.follow_default);panel.floor.toggled.connect(self.follow_default)

    def add(self,form,text,art,widget,key,index=0,control=None,dimmed=None):
        """One row: the control (inside ``control`` when given) and a reset button to its right."""
        button = attach(QToolButton(),"reset");button.setAutoRaise(True);button.setFixedSize(22,22)
        button.setToolTip(tr("Reset to default"));button.setAccessibleName(tr("Reset to default"))
        row = QWidget();box = QHBoxLayout(row);box.setContentsMargins(0,0,0,0);box.setSpacing(3)
        box.addWidget(control or widget,1);box.addWidget(button,0)
        if text is None:form.addRow(row)
        else:form.addRow(physical_label(text,art),row)
        self.rows.append((key,index,widget,button,dimmed or widget))
        button.clicked.connect(lambda _=False,r=self.rows[-1]:self.reset(r))
        signal = widget.toggled if isinstance(widget,QCheckBox) else widget.valueChanged
        signal.connect(self.write)

    def apply_units(self):
        scale = units.length();units.apply(self.softening,scale)
        for field in self.velocity:units.apply(field,units.speed())

    def defaults(self):
        linear,angular = global_damping()
        return dict(gravity=[0,0,self.panel.gravity.value()],linear_damping=linear,angular_damping=angular,
                    floor=self.panel.floor.isChecked(),attraction=0,softening=.01,initial_velocity=[0,0,0])

    @staticmethod
    def current(widget):
        return widget.isChecked() if isinstance(widget,QCheckBox) else units.stored(widget)

    def follow_default(self,*args):
        if self.group is not None:self.refresh(self.group)

    def restyle(self,*args):
        defaults = self.defaults()
        for key,index,widget,button,dimmed in self.rows:
            default = defaults[key][index] if key in self.VECTORS else defaults[key]
            at_default = same(self.current(widget),default,units.tolerance(widget))
            dim(dimmed,at_default);button.setEnabled(not at_default and widget.isEnabled())

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            cfg = settings(group).get("simulation_override") if group else None
            values = {**self.defaults(),**(cfg or {})}
            self.apply_units()
            for key,index,widget,button,dimmed in self.rows:
                value = values[key][index] if key in self.VECTORS else values[key]
                widget.setChecked(value) if isinstance(widget,QCheckBox) else units.show(widget,value)
            free = not settings(group).get("joint") and not settings(group).get("reference") and settings(group)["mode"]=="dynamic" if group else False
            for field in self.velocity:field.setEnabled(free)
        finally:self.updating = False
        self.restyle()

    def reset(self,row):
        key,index,widget,_,_ = row
        default = self.defaults()[key]
        default = default[index] if key in self.VECTORS else default
        widget.setChecked(default) if isinstance(widget,QCheckBox) else units.show(widget,default)

    def write(self,*args):
        if self.updating or self.group is None or self.panel.session.workspace:return
        defaults = self.defaults();values = {}
        for key,index,widget,_,_ in self.rows:
            if key in self.VECTORS:values.setdefault(key,[0,0,0])[index] = units.stored(widget)
            else:values[key] = self.current(widget)
        tolerance = {key:units.tolerance(widget) for key,_,widget,_,_ in self.rows if not isinstance(widget,QCheckBox)}
        # A value equal to the default is left out, so the body inherits it again.
        value = {key:values[key] for key in self.KEYS if not (
            all(same(a,b,tolerance[key]) for a,b in zip(values[key],defaults[key])) if key in self.VECTORS else same(values[key],defaults[key],tolerance.get(key,TOLERANCE)))}
        patch = dict(simulation_override=value or None)
        if KEY not in (self.group.ext or {}):patch["mode"] = "ignore" if self.group.billboard else "static"
        self.panel.patch(patch,[self.group])
        self.restyle()
