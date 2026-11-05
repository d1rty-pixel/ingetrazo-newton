"""Editor for one virtual control, shown inside the control panel's row; every change is one undo step."""
import copy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QToolButton,
    QDoubleSpinBox, QComboBox, QWidget, QCheckBox)
from .i18n import tr
from .model import joint_rows
from .range_control import scroll_safe
from .virtual_controls import eligible, stored, with_controls

WIDE = 1e9  # The worker clamps targets to the limits; the editor must not change stored values silently.


def shown(row):
    """(display units, scale, offset) as the control panel shows this joint."""
    from .controls import display_units
    units = display_units(row)
    mapping = row.get("display") or {}
    return units, mapping.get("scale", 1), mapping.get("offset", 0)


def to_display(row, value):
    units, scale, offset = shown(row)
    return (value*scale+offset)*units.factor


def from_display(row, value):
    units, scale, offset = shown(row)
    return (value/units.factor-offset)/scale


def remove_button(tip, slot, enabled=True):
    button = QToolButton()
    button.setText("×")
    button.setAutoRaise(True)
    button.setToolTip(tip)
    button.setEnabled(enabled)
    button.clicked.connect(slot)
    return button


class VirtualControlEditor(QFrame):
    """States, axes and values of ``control``; ``console`` is the control panel that owns the row."""

    def __init__(self, console, control):
        super().__init__()
        self.console, self.panel = console, console.panel
        self.id = control["id"]
        self.rows = {r["uid"]: r for r in joint_rows(self.panel.app.scene)}
        switch = control["kind"] == "switch"
        states = control["states"]
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        top = QHBoxLayout()
        grid.addLayout(top, 0, 0, 1, len(states)+2)
        top.addWidget(QLabel(tr("Name")))
        self.name = QLineEdit(control["name"])
        self.name.setMaximumWidth(200)
        self.name.textEdited.connect(self.rename)
        top.addWidget(self.name)
        top.addSpacing(12)
        top.addWidget(QLabel(tr("At start")))
        if switch:
            self.start = scroll_safe(QComboBox())
            self.start.addItems([s["name"] for s in states])
            self.start.setCurrentIndex(int(control["initial"]))
            self.start.activated.connect(lambda i: self.edit(lambda c: c.update(initial=i), keep=True))
        else:
            self.start = scroll_safe(QDoubleSpinBox())
            self.start.setRange(0, 100)
            self.start.setDecimals(0)
            self.start.setSuffix(" %")
            self.start.setValue(control["initial"]*100)
            self.start.valueChanged.connect(lambda n: self.edit(lambda c: c.update(initial=n/100), keep=True))
        top.addWidget(self.start)
        self.sequential = None
        if switch:
            self.sequential = QCheckBox(tr("Move the axes one after another"))
            self.sequential.setChecked(bool(control.get("sequential")))
            self.sequential.setToolTip(tr("Each axis starts when the previous one has reached its target, in the order of the table rows. Off: all axes start together."))
            self.sequential.toggled.connect(lambda on: self.edit(
                lambda c: c.__setitem__("sequential", True) if on else c.pop("sequential", None), keep=True))
            top.addSpacing(12)
            top.addWidget(self.sequential)
        top.addSpacing(24)
        delete = QPushButton(tr("Delete control"))
        delete.clicked.connect(self.delete)
        top.addWidget(delete)
        top.addStretch()

        grid.addWidget(QLabel(""), 1, 0)
        self.state_names, self.state_removes, self.axis_removes, self.values = [], [], [], {}
        for column, state in enumerate(states):
            head = QWidget()
            h = QHBoxLayout(head)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(2)
            edit = QLineEdit(state["name"])
            edit.setMinimumWidth(110)
            edit.setMaximumWidth(150)
            edit.setStyleSheet("font-weight: bold;")
            edit.textEdited.connect(lambda text, c=column: self.edit(
                lambda ctl: ctl["states"][c].update(name=text.strip() or tr("State {number}", number=c+1)), keep=True))
            remove = remove_button(tr("Remove this state"), lambda _=False, c=column: self.remove_state(c), len(states) > 2)
            self.state_names.append(edit)
            self.state_removes.append(remove)
            h.addWidget(edit, 1)
            h.addWidget(remove)
            grid.addWidget(head, 1, column+1)
        add_state = QPushButton(tr("Add state"))
        add_state.clicked.connect(self.add_state)
        grid.addWidget(add_state, 1, len(states)+1)

        for index, uid in enumerate(control["joints"]):
            row = self.rows.get(uid)
            grid.addWidget(QLabel(row["body"]+" "+row["name"] if row else tr("Missing body")), index+2, 0)
            for column, state in enumerate(states):
                self.values[index, column] = self.value_box(row, index, column, state["values"][index])
                grid.addWidget(self.values[index, column], index+2, column+1)
            remove = remove_button(tr("Remove this axis from the control"), lambda _=False, i=index: self.remove_joint(i))
            self.axis_removes.append(remove)
            grid.addWidget(remove, index+2, len(states)+1, Qt.AlignLeft)

        add = QHBoxLayout()
        grid.addLayout(add, len(control["joints"])+2, 0, 1, len(states)+2)
        taken = {uid for c in self.panel.virtual_controls() for uid in c["joints"]}
        self.choice = scroll_safe(QComboBox())
        for uid, row in eligible(list(self.rows.values())).items():
            if uid not in taken:
                self.choice.addItem(row["body"]+" "+row["name"], uid)
        self.add_axis_button = QPushButton(tr("Add axis"))
        self.add_axis_button.setEnabled(self.choice.count() > 0)
        self.add_axis_button.clicked.connect(self.add_joint)
        add.addWidget(self.choice)
        add.addWidget(self.add_axis_button)
        add.addStretch()
        grid.setColumnStretch(len(states)+2, 1)
        grid.setColumnMinimumWidth(0, 190)

    def value_box(self, row, index, column, value):
        box = scroll_safe(QDoubleSpinBox())
        box.setRange(-WIDE, WIDE)
        box.setMaximumWidth(150)
        # Every valueChanged is an undo step; without tracking only Enter, focus loss and arrows emit.
        box.setKeyboardTracking(False)
        if row is None:
            box.setValue(value)
            box.setEnabled(False)
            return box
        units = shown(row)[0]
        box.setDecimals(units.decimals)
        box.setSuffix(units.suffix)
        box.setValue(to_display(row, value))
        box.valueChanged.connect(lambda n: self.edit(
            lambda c: c["states"][column]["values"].__setitem__(index, from_display(row, n)), keep=True))
        return box

    def edit(self, change, keep=False):
        """Apply ``change`` to this control in the document; ``keep``: the rows are not rebuilt (the sender must survive)."""
        data = self.panel.app.document_data()
        controls = copy.deepcopy(stored(data))
        control = next((c for c in controls if c["id"] == self.id), None)
        if control is None:
            return
        change(control)
        self.console.write(with_controls(data, controls), keep=keep)

    def rename(self, text):
        if text.strip():
            self.edit(lambda c: c.update(name=text.strip()), keep=True)
            self.console.rename(self.id, text.strip())

    def delete(self):
        data = self.panel.app.document_data()
        self.console.expanded.discard(("control", self.id))
        self.console.write(with_controls(data, [c for c in stored(data) if c["id"] != self.id]))

    def add_state(self):
        def change(c):
            c["states"].append(dict(name=tr("State {number}", number=len(c["states"])+1), values=list(c["states"][-1]["values"])))
        self.edit(change)

    def remove_state(self, column):
        def change(c):
            del c["states"][column]
            if c["kind"] == "switch":
                c["initial"] = min(int(c["initial"]), len(c["states"])-1)
        self.edit(change)

    def add_joint(self):
        uid = self.choice.currentData()
        if uid is None:
            return
        target = self.rows[uid]["target"]
        def change(c):
            c["joints"].append(uid)
            for state in c["states"]:
                state["values"].append(target)
        self.edit(change)

    def remove_joint(self, index):
        def change(c):
            del c["joints"][index]
            for state in c["states"]:
                del state["values"][index]
        self.edit(change)
