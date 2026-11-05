"""Fields for one key binding, shared by the control panel cards and the sidebar section.

Values are shown like the control panel shows the target (display units and
mapping for joints, state names for switches, percent for sliders) and stored
in internal units. A field writes only its own value back, so rounding in the
display never alters the values the user did not touch.
"""
from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QDoubleSpinBox, QStackedWidget, QLabel

from . import help_texts as help
from .i18n import tr
from .key_slots import slot_name
from .key_bindings import fresh, replaced, stored, target_range, with_bindings
from .range_control import scroll_safe
from views.fold_section import narrow
from .toolbar import compact


def slot_labels(panel, keep=()):
    """``[(number, label)]`` of every slot with its key; ``keep``: numbers still in use whose slot was removed."""
    labels = {}
    for n, action in enumerate(panel.key_slots.actions, 1):
        key = action.shortcut().toString(QKeySequence.NativeText)
        name = slot_name(n)
        labels[n] = f"{name} ({key})" if key else name
    for n in keep:
        if n is not None:
            labels.setdefault(n, tr("Key {n} (removed)", n=n))
    return sorted(labels.items())


def store(panel, kind, ident, binding):
    """Write one target's binding (``None`` removes it) as one undo step; False when nothing changed."""
    data = panel.app.document_data()
    bindings = stored(data)
    changed = replaced(bindings, kind, ident, binding)
    if changed == bindings:
        return False
    panel.app.set_document_data(with_bindings(data, changed))
    return True


class Scale:
    """Internal value to the number the control panel shows, and back."""

    def __init__(self, kind, subject):
        if kind == "joint":
            from .virtual_editor import shown
            units, self.scale, self.offset = shown(subject)
            self.factor, self.decimals, self.suffix = units.factor, units.decimals, units.suffix
        else:
            self.scale, self.offset, self.factor, self.decimals, self.suffix = 1, 0, 100, 0, " %"

    def show(self, value):
        return (value*self.scale+self.offset)*self.factor

    def read(self, value):
        return (value/self.factor-self.offset)/self.scale

    def show_step(self, value):
        return value*abs(self.scale)*self.factor

    def read_step(self, value):
        return value/self.factor/abs(self.scale)


class BindingFields(QWidget):
    """Slot, mode and the mode's values of one target; ``changed`` carries the new binding or None."""
    changed = Signal(object)

    def __init__(self, panel, kind, ident, subject, binding, parent=None, stacked=False):
        super().__init__(parent)
        self.kind, self.ident, self.subject = kind, ident, subject
        self.binding = binding
        self.low, self.high, self.integer = target_range(kind, subject)
        self.states = subject["states"] if kind == "control" and subject["kind"] == "switch" else None
        self.units = None if self.states else Scale(kind, subject)
        self.updating = False
        self.stacked = stacked
        keep = (binding["slot"], binding.get("slot_down")) if binding else ()
        slots = slot_labels(panel, keep)
        layout = QVBoxLayout(self) if stacked else QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # The sidebar is too narrow for all fields in one row.
        top = QHBoxLayout() if stacked else layout
        self.slot = self.slot_choice(tr("No key"), slots)
        self.slot.setToolTip(tr(help.KEY_BINDING_SLOT))
        self.mode = compact(QComboBox())
        self.mode.addItem(tr("Toggle"), "toggle")
        self.mode.addItem(tr("Step"), "step")
        self.mode.setToolTip(tr(help.KEY_BINDING_MODE))
        self.pages = QStackedWidget()
        toggle = QWidget()
        row = QHBoxLayout(toggle)
        row.setContentsMargins(0, 0, 0, 0)
        self.value, self.rest = self.value_field(), self.value_field()
        self.value.setToolTip(tr(help.KEY_BINDING_VALUE))
        self.rest.setToolTip(tr(help.KEY_BINDING_REST))
        row.addWidget(self.captioned(tr("Set to"), self.value))
        row.addWidget(self.captioned(tr("Back to"), self.rest))
        self.pages.addWidget(toggle)
        step = QWidget()
        row = QHBoxLayout(step)
        row.setContentsMargins(0, 0, 0, 0)
        self.step = self.step_field()
        self.step.setToolTip(tr(help.KEY_BINDING_STEP))
        self.down = self.slot_choice(tr("No key"), slots)
        self.down.setToolTip(tr(help.KEY_BINDING_DOWN))
        row.addWidget(self.captioned(tr("Step"), self.step))
        row.addWidget(self.captioned(tr("Down key"), self.down))
        self.pages.addWidget(step)
        top.addWidget(self.slot)
        top.addWidget(self.mode, 1 if stacked else 0)
        if stacked:
            layout.addLayout(top)
        layout.addWidget(self.pages, 1)
        self.show_binding(binding)
        self.slot.activated.connect(lambda _index: self.edit("slot"))
        self.mode.activated.connect(lambda _index: self.edit("mode"))
        self.down.activated.connect(lambda _index: self.edit("slot_down"))
        for key, field in (("value", self.value), ("rest", self.rest)):
            if self.states:
                field.activated.connect(lambda _index, key=key: self.edit(key))
            else:
                field.valueChanged.connect(lambda _number, key=key: self.edit(key))
        self.step.valueChanged.connect(lambda _number: self.edit("step"))

    def captioned(self, text, field):
        # Above the field, not beside it: the sidebar has no room for a second column of text.
        box = QWidget()
        column = QVBoxLayout(box)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(1)
        caption = QLabel(text)
        caption.setToolTip(field.toolTip())
        caption.setStyleSheet("font-size: 8pt;")
        column.addWidget(caption)
        column.addWidget(field)
        return box

    def slot_choice(self, none, slots):
        combo = compact(QComboBox())
        combo.addItem(none, None)
        for n, label in slots:
            combo.addItem(label, n)
        return combo

    def spin(self):
        box = scroll_safe(QDoubleSpinBox())
        # On a card every valueChanged is an undo step; without tracking only Enter, focus loss and arrows emit.
        box.setKeyboardTracking(False)
        if self.stacked:
            narrow(box)
        return box

    def value_field(self):
        if self.states:
            combo = compact(QComboBox())
            for index, state in enumerate(self.states):
                combo.addItem(state["name"], index)
            return combo
        box = self.spin()
        box.setDecimals(self.units.decimals)
        box.setSuffix(self.units.suffix)
        return box

    def step_field(self):
        box = self.spin()
        if self.states:
            box.setDecimals(0)
            box.setRange(1, max(1, len(self.states)-1))
            return box
        box.setDecimals(self.units.decimals)
        box.setSuffix(self.units.suffix)
        smallest = 10**-self.units.decimals
        box.setRange(smallest, max(smallest, self.units.show_step(self.high-self.low)))
        return box

    def show_binding(self, binding):
        self.updating = True
        try:
            self.slot.setCurrentIndex(self.slot.findData(binding["slot"] if binding else None))
            self.mode.setVisible(binding is not None)
            self.pages.setVisible(binding is not None)
            if binding is None:
                return
            self.mode.setCurrentIndex(self.mode.findData(binding["mode"]))
            self.pages.setCurrentIndex(0 if binding["mode"] == "toggle" else 1)
            if binding["mode"] == "toggle":
                self.show_value(self.value, binding["value"])
                self.show_value(self.rest, binding["rest"])
            else:
                self.step.setValue(binding["step"] if self.states else self.units.show_step(binding["step"]))
                self.down.setCurrentIndex(self.down.findData(binding.get("slot_down")))
        finally:
            self.updating = False

    def show_value(self, field, value):
        if self.states:
            field.setCurrentIndex(max(0, min(len(self.states)-1, int(round(value)))))
            return
        low, high = sorted((self.units.show(self.low), self.units.show(self.high)))
        shown = self.units.show(value)
        # A stored value beyond the current range (limits changed later) must not be clamped silently.
        field.setRange(min(low, shown), max(high, shown))
        field.setValue(shown)

    def read_value(self, field):
        return field.currentData() if self.states else self.units.read(field.value())

    def edit(self, key):
        if self.updating:
            return
        slot = self.slot.currentData()
        mode = self.mode.currentData()
        old = self.binding
        if slot is None:
            binding = None
        elif old is None or mode != old["mode"]:
            binding = fresh(self.kind, self.ident, self.subject, slot, mode if old else "toggle")
        else:
            binding = dict(old, slot=slot)
            if key in ("value", "rest"):
                binding[key] = self.read_value(self.value if key == "value" else self.rest)
            elif key == "step":
                binding["step"] = int(self.step.value()) if self.states else self.units.read_step(self.step.value())
            elif key == "slot_down":
                down = self.down.currentData()
                if down is None:
                    binding.pop("slot_down", None)
                else:
                    binding["slot_down"] = down
        if binding == old:
            return
        self.binding = binding
        self.show_binding(binding)
        self.changed.emit(binding)
