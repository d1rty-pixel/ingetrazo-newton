"""Editor for virtual controls; OK stores every change as one undo step."""
import copy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
    QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QDoubleSpinBox, QComboBox, QDialogButtonBox, QFormLayout,
    QWidget, QAbstractItemView, QHeaderView, QCheckBox)
from .i18n import tr
from .model import joint_rows
from .range_control import scroll_safe
from .virtual_controls import eligible, new_control, stored, with_controls

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


class VirtualControlEditor(QDialog):
    def __init__(self, panel, select=None):
        super().__init__(panel.app.window)
        self.panel = panel
        self.setWindowTitle(tr("Virtual controls"))
        self.resize(760, 420)
        self.data = panel.app.document_data()
        self.controls = copy.deepcopy(stored(self.data))
        self.rows = {r["uid"]: r for r in joint_rows(panel.app.scene)}
        self.current = None
        layout = QVBoxLayout(self)
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        left = QVBoxLayout()
        body.addLayout(left)
        self.list = QListWidget()
        self.list.setMinimumWidth(180)
        self.list.currentRowChanged.connect(self.show_control)
        left.addWidget(self.list, 1)
        self.add_switch = QPushButton(tr("Add switch"))
        self.add_slider = QPushButton(tr("Add slider"))
        self.remove_control = QPushButton(tr("Remove"))
        self.add_switch.clicked.connect(lambda: self.add("switch"))
        self.add_slider.clicked.connect(lambda: self.add("slider"))
        self.remove_control.clicked.connect(self.remove)
        for button in (self.add_switch, self.add_slider, self.remove_control):
            left.addWidget(button)
        self.detail = QWidget()
        body.addWidget(self.detail, 1)
        right = QVBoxLayout(self.detail)
        right.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        right.addLayout(form)
        self.name = QLineEdit()
        self.name.textEdited.connect(self.rename)
        form.addRow(tr("Name"), self.name)
        self.kind = QLabel()
        form.addRow(tr("Kind"), self.kind)
        self.initial_state = scroll_safe(QComboBox())
        self.initial_state.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.initial_state.activated.connect(self.set_initial)
        self.initial_position = scroll_safe(QDoubleSpinBox())
        self.initial_position.setRange(0, 100)
        self.initial_position.setDecimals(0)
        self.initial_position.setSuffix(" %")
        self.initial_position.valueChanged.connect(lambda n: self.set_initial(n/100))
        initial = QHBoxLayout()
        initial.addWidget(self.initial_state)
        initial.addWidget(self.initial_position)
        initial.addStretch()
        form.addRow(tr("At start"), initial)
        self.one_by_one = QCheckBox(tr("Move the axes one after another"))
        self.one_by_one.setToolTip(tr("Each axis starts when the previous one has reached its target, in the order of the table rows. Off: all axes start together."))
        self.one_by_one.toggled.connect(self.set_one_by_one)
        form.addRow("", self.one_by_one)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self.rename_state)
        right.addWidget(self.table, 1)
        tools = QHBoxLayout()
        right.addLayout(tools)
        self.joint_choice = scroll_safe(QComboBox())
        self.add_joint_button = QPushButton(tr("Add axis"))
        self.add_joint_button.clicked.connect(self.add_joint)
        self.remove_joint_button = QPushButton(tr("Remove axis"))
        self.remove_joint_button.clicked.connect(self.remove_joint)
        self.add_state_button = QPushButton(tr("Add state"))
        self.add_state_button.clicked.connect(self.add_state)
        self.remove_state_button = QPushButton(tr("Remove state"))
        self.remove_state_button.clicked.connect(self.remove_state)
        tools.addWidget(self.joint_choice, 1)
        for button in (self.add_joint_button, self.remove_joint_button, self.add_state_button, self.remove_state_button):
            tools.addWidget(button)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for control in self.controls:
            self.list.addItem(control["name"])
        index = next((i for i, c in enumerate(self.controls) if c["id"] == select), 0)
        self.list.setCurrentRow(index if self.controls else -1)
        self.show_control(self.list.currentRow())

    # ---- list ----------------------------------------------------------------
    def add(self, kind):
        control = new_control(kind, tr("New switch") if kind == "switch" else tr("New slider"))
        self.controls.append(control)
        self.list.addItem(control["name"])
        self.list.setCurrentRow(len(self.controls)-1)
        self.name.setFocus()
        self.name.selectAll()

    def remove(self):
        row = self.list.currentRow()
        if row < 0:
            return
        del self.controls[row]
        self.list.takeItem(row)
        self.show_control(self.list.currentRow())

    def rename(self, text):
        if self.current is not None and text.strip():
            self.current["name"] = text.strip()
            self.list.currentItem().setText(self.current["name"])

    # ---- one control -----------------------------------------------------------
    def show_control(self, row):
        self.current = self.controls[row] if 0 <= row < len(self.controls) else None
        self.detail.setEnabled(self.current is not None)
        self.remove_control.setEnabled(self.current is not None)
        control = self.current
        self.table.blockSignals(True)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        if control is None:
            self.name.clear()
            self.kind.clear()
            self.table.blockSignals(False)
            return
        self.name.setText(control["name"])
        switch = control["kind"] == "switch"
        self.kind.setText(tr("Switch") if switch else tr("Slider"))
        states = control["states"]
        self.table.setColumnCount(len(states))
        self.table.setHorizontalHeaderLabels([tr("State {number}", number=i+1) for i in range(len(states))])
        self.table.setRowCount(1+len(control["joints"]))
        self.table.setVerticalHeaderItem(0, QTableWidgetItem(tr("Name")))
        for column, state in enumerate(states):
            self.table.setItem(0, column, QTableWidgetItem(state["name"]))
        for index, uid in enumerate(control["joints"]):
            row = self.rows.get(uid)
            label = row["body"]+" "+row["name"] if row else tr("Missing body")
            self.table.setVerticalHeaderItem(index+1, QTableWidgetItem(label))
            for column, state in enumerate(states):
                self.table.setCellWidget(index+1, column, self.value_box(row, control, index, column))
        self.table.blockSignals(False)
        self.initial_state.setVisible(switch)
        self.one_by_one.setVisible(switch)
        self.one_by_one.blockSignals(True)
        self.one_by_one.setChecked(bool(control.get("sequential")))
        self.one_by_one.blockSignals(False)
        self.initial_position.setVisible(not switch)
        self.initial_state.clear()
        self.initial_state.addItems([s["name"] for s in states])
        self.initial_position.blockSignals(True)
        if switch:
            self.initial_state.setCurrentIndex(int(control["initial"]))
        else:
            self.initial_position.setValue(control["initial"]*100)
        self.initial_position.blockSignals(False)
        self.remove_state_button.setEnabled(len(states) > 2)
        self.fill_joint_choice()

    def value_box(self, row, control, index, column):
        box = scroll_safe(QDoubleSpinBox())
        box.setRange(-WIDE, WIDE)
        value = control["states"][column]["values"][index]
        if row is None:
            box.setValue(value)
            box.setEnabled(False)
            return box
        units = shown(row)[0]
        box.setDecimals(units.decimals)
        box.setSuffix(units.suffix)
        box.setValue(to_display(row, value))
        def store(number, row=row):
            control["states"][column]["values"][index] = from_display(row, number)
        box.valueChanged.connect(store)
        return box

    def rename_state(self, item):
        if self.current is not None and item.row() == 0:
            name = item.text().strip() or tr("State {number}", number=item.column()+1)
            self.current["states"][item.column()]["name"] = name
            self.initial_state.setItemText(item.column(), name)

    def set_initial(self, value):
        if self.current is not None:
            self.current["initial"] = value

    def set_one_by_one(self, on):
        if self.current is not None:
            if on:
                self.current["sequential"] = True
            else:
                self.current.pop("sequential", None)

    def fill_joint_choice(self):
        taken = {uid for c in self.controls for uid in c["joints"]}
        self.joint_choice.clear()
        for uid, row in eligible(list(self.rows.values())).items():
            if uid not in taken:
                self.joint_choice.addItem(row["body"]+" "+row["name"], uid)
        self.add_joint_button.setEnabled(self.joint_choice.count() > 0)

    def add_joint(self):
        uid = self.joint_choice.currentData()
        if self.current is None or uid is None:
            return
        target = self.rows[uid]["target"]
        self.current["joints"].append(uid)
        for state in self.current["states"]:
            state["values"].append(target)
        self.show_control(self.list.currentRow())

    def remove_joint(self):
        index = self.table.currentRow()-1
        if self.current is None or not 0 <= index < len(self.current["joints"]):
            return
        del self.current["joints"][index]
        for state in self.current["states"]:
            del state["values"][index]
        self.show_control(self.list.currentRow())

    def add_state(self):
        if self.current is None:
            return
        last = self.current["states"][-1]
        self.current["states"].append(dict(name=tr("State {number}", number=len(self.current["states"])+1),
                                           values=list(last["values"])))
        self.show_control(self.list.currentRow())

    def remove_state(self):
        states = self.current["states"] if self.current else []
        column = self.table.currentColumn()
        if len(states) <= 2:
            return
        del states[column if 0 <= column < len(states) else -1]
        if self.current["kind"] == "switch":
            self.current["initial"] = min(int(self.current["initial"]), len(states)-1)
        self.show_control(self.list.currentRow())

    # ---- result ----------------------------------------------------------------
    def accept(self):
        if self.controls != stored(self.data):
            self.panel.app.set_document_data(with_controls(self.data, self.controls))
            self.panel.refresh()
        super().accept()
