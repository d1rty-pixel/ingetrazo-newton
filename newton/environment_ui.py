"""Per-body environment overrides; global defaults live in Preferences."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QCheckBox,QDoubleSpinBox,QLabel
from .model import KEY,settings
from .i18n import tr
from . import help_texts as help


def global_damping():
    st = QSettings()
    return float(st.value("newton/linear_damping",0)),float(st.value("newton/angular_damping",0))


def number(low,high,value=0):
    widget = QDoubleSpinBox();widget.setRange(low,high);widget.setDecimals(3)
    widget.setKeyboardTracking(False);widget.setValue(value)
    return widget


class EnvironmentOverrides(QWidget):
    def __init__(self,panel):
        super().__init__()
        self.panel = panel;self.updating = False;self.group = None
        layout = QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.enabled = QCheckBox(tr("Use own simulation settings"));layout.addWidget(self.enabled)
        self.fields = QWidget();form = QFormLayout(self.fields)
        form.setContentsMargins(0,0,0,0);form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.gravity = [number(-1e6,1e6) for _ in range(3)]
        from .range_control import RangeControl
        for axis,widget in zip(("X","Y","Z"),self.gravity):
            widget.setSuffix(" m/s²")
            control = RangeControl(widget,-100,100)
            control.gestureStarted.connect(panel.begin_slider_edit);control.gestureFinished.connect(panel.end_slider_edit)
            panel.ranges["override_gravity_"+axis] = control
            form.addRow(tr("Gravity {axis}",axis=axis),control)
        self.linear,self.angular = number(0,100),number(0,100)
        self.linear.setSuffix(" /s");self.angular.setSuffix(" /s")
        form.addRow(tr("Linear damping"),self.linear);form.addRow(tr("Angular damping"),self.angular)
        self.floor = QCheckBox(tr("Ground contact at Z = 0"));form.addRow(self.floor)
        note = QLabel(tr(help.FIELDS))
        note.setWordWrap(True);form.addRow(note)
        self.attraction = number(0,1e12);self.attraction.setSuffix(" m³/s²")
        self.softening = number(0,1e6,.01);self.softening.setSuffix(" m")
        form.addRow(tr("Attraction"),self.attraction);form.addRow(tr("Softening radius"),self.softening)
        self.velocity = [number(-1e6,1e6) for _ in range(3)]
        for axis,widget in zip(("X","Y","Z"),self.velocity):
            widget.setSuffix(" m/s");form.addRow(tr("Initial velocity {axis}",axis=axis),widget)
        layout.addWidget(self.fields)
        for field in [*self.gravity,self.linear,self.angular,self.attraction,self.softening,*self.velocity]:field.valueChanged.connect(self.write)
        self.enabled.toggled.connect(self.write);self.floor.toggled.connect(self.write)
        self.fields.hide()

    def refresh(self,group):
        self.updating = True;self.group = group
        try:
            cfg = settings(group).get("simulation_override") if group else None
            linear,angular = global_damping()
            defaults = dict(gravity=[0,0,self.panel.gravity.value()],linear_damping=linear,angular_damping=angular,floor=self.panel.floor.isChecked())
            values = {**defaults,**(cfg or {})}
            self.enabled.setChecked(bool(cfg));self.fields.setVisible(bool(cfg))
            for field,value in zip(self.gravity,values["gravity"]):field.setValue(value)
            self.linear.setValue(values["linear_damping"]);self.angular.setValue(values["angular_damping"])
            self.floor.setChecked(values["floor"])
            self.attraction.setValue(values.get("attraction",0));self.softening.setValue(values.get("softening",.01))
            free = not settings(group).get("joint") and not settings(group).get("reference") and settings(group)["mode"]=="dynamic" if group else False
            for field,value in zip(self.velocity,values.get("initial_velocity",[0,0,0])):
                field.setValue(value);field.setEnabled(free)
        finally:self.updating = False

    def write(self,*args):
        if self.updating or self.group is None or self.panel.session.workspace:return
        self.fields.setVisible(self.enabled.isChecked())
        value = dict(gravity=[w.value() for w in self.gravity],linear_damping=self.linear.value(),
                     angular_damping=self.angular.value(),floor=self.floor.isChecked(),attraction=self.attraction.value(),
                     softening=self.softening.value(),initial_velocity=[w.value() for w in self.velocity]) if self.enabled.isChecked() else None
        patch = dict(simulation_override=value)
        if KEY not in (self.group.ext or {}):patch["mode"] = "ignore" if self.group.billboard else "static"
        self.panel.patch(patch,[self.group])
