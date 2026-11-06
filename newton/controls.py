"""The control panel: a dock below the 3D view with the transport and one strip per control.

All strips share one grid, so a sequence editor's timeline can later sit beside them. A strip expands
in place for its key binding and, for a virtual control, its states.
"""
from PySide6.QtCore import Qt, QSettings, QTimer, QSize
from PySide6.QtGui import QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QToolButton, QButtonGroup, QDoubleSpinBox, QMenu, QSizePolicy, QDockWidget, QComboBox)
from .i18n import tr
from . import keep_pose
from . import help_texts as help
from .icons import attach, icon, pixmap
from .key_caps import KeyCaps
from .reference_table import ReferenceTable
from .units import signature as units_signature, SPAN_METRES

MAX_BODY_ROWS = 6
KEEP_KEY = "newton/keep_warnings_on_reset"
DETACHED_KEY = "newton/controls_detached"
GEOMETRY_KEY = "newton/controls_geometry"
DEFAULT_HEIGHT = 300
ROW_HEIGHT = 48
COL_ICON, COL_NAME, COL_ACTUAL, COL_TARGET, COL_KEY, COL_MORE = range(6)


def icon_px():
    """The host's toolbar icon size, so the list's icons and its handle follow the preference."""
    from views.icons import toolbar_icon_px
    return toolbar_icon_px()


def keep_on_reset():
    return str(QSettings().value(KEEP_KEY,False)).lower() in ("true","1")


def display_units(joint):
    """Scale of the target and the actual value; the suffix has no leading space."""
    from dataclasses import replace
    from . import units
    velocity = joint["drive"] == "velocity"
    if joint["type"] == "hinge":
        return replace(units.ANGLE_RATE if velocity else units.ANGLE,decimals=1)
    return units.speed() if velocity else units.length()


def muted(label, size=None):
    label.setEnabled(False)
    if size:
        label.setStyleSheet(f"font-size: {size}pt;")
    return label


class DetachedWindow(QWidget):
    """The control panel as a window of its own: movable and resizable by the window manager, closing it hides the panel."""

    def __init__(self, controls, parent):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Controls"))
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        geometry = QSettings().value(GEOMETRY_KEY)
        if not (geometry and self.restoreGeometry(geometry)):
            self.resize(960, 380)

    def take(self, controls):
        controls.layout().insertWidget(0, controls.header)
        controls.header.show()
        self.layout().addWidget(controls)
        controls.show()

    def release(self):
        controls = self.layout().itemAt(0).widget()
        controls.layout().removeWidget(controls.header)
        self.layout().removeWidget(controls)
        self.hide()

    def closeEvent(self, event):
        QSettings().setValue(GEOMETRY_KEY, self.saveGeometry())
        super().closeEvent(event)


class Controls(QWidget):
    def __init__(self, panel):
        super().__init__(panel.app.window)
        self.panel = panel
        self.kept = None
        self.expanded = set()
        self.key_editing = set()
        self.holding = False
        self.signature = None
        self.last = ([], False)
        self.rows = {}
        self.name_labels = {}
        self.virtual_state_labels = {}
        self.joint_inputs = {}
        self.virtual_inputs = {}
        self.range_controls = []
        self.following = False

        # The header is the dock's title bar: transport, status and options.
        self.header = QFrame()
        bar = QHBoxLayout(self.header)
        bar.setContentsMargins(12, 6, 10, 6)
        bar.setSpacing(10)
        title = QLabel(tr("Controls"))
        title.setStyleSheet("font-size: 13px; font-weight: bold;")
        bar.addWidget(title)
        bar.addSpacing(6)
        self.start_button = QPushButton(icon("play"), tr("Start"))
        self.start_button.setMinimumWidth(96)
        self.reset_button = QPushButton(icon("reset"), tr("Reset"))
        self.start_button.clicked.connect(panel.start_or_pause)
        self.reset_button.clicked.connect(panel.session.reset)
        bar.addWidget(self.start_button)
        bar.addWidget(self.reset_button)
        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-family: monospace;")
        self.time_label.setMinimumWidth(92)
        self.performance_label = QLabel()
        self.performance_label.setEnabled(False)
        self.performance_label.hide()
        bar.addWidget(self.time_label)
        bar.addWidget(self.performance_label)
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.PlainText)
        self.hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        bar.addWidget(self.hint, 1)
        self.new_button = QPushButton(tr("New virtual control"))
        self.new_button.setToolTip(tr(help.VIRTUAL_CONTROLS))
        menu = QMenu(self.new_button)
        menu.addAction(tr("Add switch"), lambda: self.add_control("switch"))
        menu.addAction(tr("Add slider"), lambda: self.add_control("slider"))
        self.new_button.setMenu(menu)
        bar.addWidget(self.new_button)
        self.options_button = QPushButton(tr("Options"))
        options = QMenu(self.options_button)
        self.keep = options.addAction(icon("keep_warnings"), tr("Keep warnings and errors on reset"))
        self.keep.setCheckable(True)
        self.keep.setToolTip(tr(help.KEEP_WARNINGS))
        self.keep.setChecked(keep_on_reset())
        self.keep.toggled.connect(lambda on: QSettings().setValue(KEEP_KEY, on))
        self.keep_pose = options.addAction(icon("keep_pose"), tr("Keep the pose on reset"))
        self.keep_pose.setCheckable(True)
        self.keep_pose.setToolTip(tr(help.KEEP_POSE))
        self.keep_pose.setChecked(keep_pose.enabled())
        self.keep_pose.toggled.connect(lambda on: QSettings().setValue(keep_pose.SETTING, on))
        self.options_button.setMenu(options)
        bar.addWidget(self.options_button)
        self.float_button = attach(QToolButton(), "dock_float")
        self.float_button.clicked.connect(self.toggle_detached)
        bar.addWidget(self.float_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.banner = QFrame()
        banner = QVBoxLayout(self.banner)
        banner.setContentsMargins(12, 6, 12, 6)
        text_row = QHBoxLayout()
        banner.addLayout(text_row)
        self.banner_mark = QLabel()
        self.banner_mark.setAlignment(Qt.AlignTop)
        self.banner_text = QLabel()
        self.banner_text.setWordWrap(True)
        self.banner_text.setTextFormat(Qt.PlainText)
        text_row.addWidget(self.banner_mark)
        text_row.addWidget(self.banner_text, 1)
        self.bodies = ReferenceTable(None, panel=panel)
        banner.addWidget(self.bodies)
        self.bodies.hide()
        layout.addWidget(self.banner)
        self.banner.hide()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.scroll, 1)

        self.dock = self.make_dock()
        self.detached = None
        self.show_detached(False)

        panel.session.metrics.connect(self.show_performance)
        panel.session.frame.connect(self.show_time)
        panel.session.message.connect(self.message)
        panel.session.targets_changed.connect(self.follow_targets)
        self.show_time(0)

    def make_dock(self):
        """Host adapter: API 2 offers only the side tray, so the dock joins through the main window's QMainWindow API.

        The host saves and restores it with its window state (floating, size, visibility) by object name,
        when the toolbars are restored; it starts hidden until Start or the toolbar button shows it.
        """
        window = self.panel.app.window
        dock = QDockWidget(tr("Controls"), window)
        dock.setObjectName("newton_console_dock")
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        dock.setWidget(self)
        dock.setTitleBarWidget(self.header)
        self.keep_sidebar_height()
        window.addDockWidget(Qt.BottomDockWidgetArea, dock)
        window.resizeDocks([dock], [DEFAULT_HEIGHT], Qt.Vertical)
        dock.hide()
        return dock

    def show_detached(self, detached):
        self.float_button.setToolTip(tr("Attach the control panel") if detached else tr("Detach the control panel"))

    def toggle_detached(self):
        self.attach() if self.detached is not None and self.detached.isVisible() else self.detach()

    def detach(self):
        """A floating QDockWidget cannot be moved on Wayland, so the panel moves into a window of its own and the dock stays hidden."""
        if self.detached is None:
            self.detached = DetachedWindow(self, self.panel.app.window)
        self.dock.setWidget(None)
        self.dock.setTitleBarWidget(None)
        self.dock.hide()
        self.detached.take(self)
        self.detached.show()
        self.detached.raise_()
        QSettings().setValue(DETACHED_KEY, True)
        self.show_detached(True)

    def attach(self):
        QSettings().setValue(DETACHED_KEY, False)
        self.detached.release()
        self.dock.setWidget(self)
        self.dock.setTitleBarWidget(self.header)
        self.dock.show()
        self.show_detached(False)

    def is_open(self):
        return self.detached.isVisible() if self.detached is not None and self.detached.isVisible() else not self.dock.isHidden()

    def open(self):
        if QSettings().value(DETACHED_KEY, False, type=bool) and (self.detached is None or not self.detached.isVisible()):
            self.detach()
        elif self.detached is not None and self.detached.isVisible():
            self.detached.raise_()
        else:
            self.dock.show()

    def keep_sidebar_height(self):
        """Host adapter: the sidebar keeps the full window height and the dock sits under the 3D view only; the host's restoreState undoes it."""
        self.panel.app.window.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

    def toggle(self):
        if not self.is_open():
            self.panel.show_controls()
        elif self.detached is not None and self.detached.isVisible():
            self.detached.close()
        else:
            self.dock.hide()

    def open_control(self, control_id):
        """Show the dock with the row of a virtual control expanded."""
        self.expanded.add(("control", control_id))
        self.panel.show_controls()

    # ---- rebuild -----------------------------------------------------------------------
    def bindings(self):
        """The key bindings the rows show: the running session's, otherwise the document's; None when damaged."""
        from .key_bindings import stored
        if self.panel.session.workspace:
            return list(self.panel.session.bindings)
        try:
            return stored(self.panel.app.document_data())
        except ValueError:
            return None

    def refresh(self, joints, active):
        from .virtual_controls import managed
        from .binding_fields import slot_labels
        self.keep_sidebar_height()
        self.last = (joints, active)
        virtual = self.panel.virtual_controls()
        taken = managed(virtual)
        joints = [j for j in joints if j["drive"] != "free" and not j.get("coupling") and j["uid"] not in taken]
        bindings = self.bindings()
        signature = (repr(joints), repr(virtual), active, units_signature(), repr(slot_labels(self.panel)),
                     repr(bindings), self.panel.detail_uid, tuple(sorted(self.expanded)), tuple(sorted(self.key_editing)), icon_px(),
                     self.palette().color(QPalette.Window).name())
        if signature != self.signature and not self.holding:
            self.signature = signature
            self.build(joints, virtual, active, bindings)
        self.start_button.setText(tr("Pause") if active and self.panel.session.running else tr("Resume") if active else tr("Start"))
        self.start_button.setEnabled(not active or self.panel.session.ready)
        self.reset_button.setEnabled(active)
        self.new_button.setEnabled(not active)
        if not active:
            self.show_time(0)
        self.refresh_icons()

    def write(self, data, keep=False):
        """Write document data; ``keep``: a field edit, so the rows keep their widgets (the sender must survive)."""
        self.holding = keep
        try:
            self.panel.app.set_document_data(data)
        finally:
            self.holding = False
        if not keep:
            self.panel.refresh()

    def add_control(self, kind):
        from .virtual_controls import new_control, stored, with_controls
        data = self.panel.app.document_data()
        control = new_control(kind, tr("New switch") if kind == "switch" else tr("New slider"))
        self.expanded.add(("control", control["id"]))
        self.write(with_controls(data, stored(data)+[control]))

    def rename(self, control_id, name):
        self.name_labels[control_id].setText(name)

    def build(self, joints, virtual, active, bindings):
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(0)
        self.rows = {}
        self.name_labels = {}
        self.virtual_state_labels = {}
        self.joint_inputs = {}
        self.virtual_inputs = {}
        self.range_controls = []
        grid.setColumnMinimumWidth(COL_ICON, icon_px()+8)
        grid.setColumnMinimumWidth(COL_NAME, 190)
        grid.setColumnMinimumWidth(COL_ACTUAL, 118)
        grid.setColumnMinimumWidth(COL_TARGET, 330)
        grid.setColumnMinimumWidth(COL_KEY, 215)
        grid.setColumnMinimumWidth(COL_MORE, icon_px()+10)
        grid.setColumnStretch(COL_TARGET, 3)
        grid.setRowMinimumHeight(0, 26)
        for col, text in ((COL_NAME, tr("Control")), (COL_ACTUAL, tr("Actual")), (COL_TARGET, tr("Target")), (COL_KEY, tr("Key"))):
            caption = muted(QLabel(text), 8)
            if col == COL_ACTUAL:
                caption.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(caption, 0, col)
        row = 1

        def stripe(r, selected=False):
            frame = QFrame()
            frame.setObjectName("stripe")
            pal = self.palette()
            mid = pal.color(QPalette.Mid)
            base = QColor(pal.color(QPalette.Highlight)) if selected else QColor(mid)
            base.setAlpha(60 if selected else 34 if r % 2 else 0)
            frame.setStyleSheet(f"QFrame#stripe {{ background: rgba({base.red()},{base.green()},{base.blue()},{base.alpha()}); "
                                f"border-top: 1px solid rgba({mid.red()},{mid.green()},{mid.blue()},90); }}")
            grid.addWidget(frame, r, 0, 1, COL_MORE+1)
            grid.setRowMinimumHeight(r, max(ROW_HEIGHT, icon_px()+14))

        def group_caption(text):
            nonlocal row
            label = muted(QLabel(text.upper()), 7)
            label.setContentsMargins(0, 8, 0, 2)
            grid.addWidget(label, row, COL_NAME, 1, 3)
            row += 1

        if not joints and not virtual:
            grid.addWidget(QLabel(tr("No actuators")), row, COL_NAME, 1, 3)
            row += 1
        if virtual:
            group_caption(tr("Virtual controls"))
        for control in virtual:
            stripe(row)
            row = self.virtual_row(grid, row, control, active, bindings)
        if joints:
            group_caption(tr("Axes"))
        for joint in joints:
            stripe(row, joint["uid"] == self.panel.detail_uid)
            row = self.joint_row(grid, row, joint, active, bindings)
        grid.setRowStretch(row, 1)
        old = self.scroll.takeWidget()
        self.scroll.setWidget(widget)
        if old:
            old.deleteLater()

    def icon_cell(self, grid, r, name):
        mark = QLabel()
        mark.setPixmap(pixmap(name, icon_px()))
        mark.setAlignment(Qt.AlignCenter)
        grid.addWidget(mark, r, COL_ICON)

    def value_label(self, grid, r):
        label = QLabel()
        label.setTextFormat(Qt.PlainText)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("font-family: monospace;")
        grid.addWidget(label, r, COL_ACTUAL)
        return label

    def joint_row(self, grid, r, joint, active, bindings):
        from .range_control import RangeControl
        uid = joint["uid"]
        self.icon_cell(grid, r, "drive_velocity" if joint["drive"] == "velocity" else "drive_position")
        kind = tr("Motor") if joint["drive"] == "velocity" else tr("Servo")
        grid.addWidget(self.name_cell(joint["name"], kind+" · "+joint["body"])[0], r, COL_NAME)
        actual = self.value_label(grid, r)
        actual.setText(tr("—"))
        shown = display_units(joint)
        factor = shown.factor
        mapping = joint.get("display") or {}
        scale, offset = mapping.get("scale", 1), mapping.get("offset", 0)
        if joint["drive"] == "position":
            low, high = joint["lower"]*factor, joint["upper"]*factor
            if not joint["limited"]:
                low, high = (-180, 180) if joint["type"] == "hinge" else (-shown.show(SPAN_METRES), shown.show(SPAN_METRES))
        else:
            extent = joint["max_speed"]*factor
            low, high = -extent, extent
        low, high = sorted((low*scale+offset*factor, high*scale+offset*factor))
        value = QDoubleSpinBox()
        value.setRange(low, high)
        value.setDecimals(shown.decimals)
        value.setSuffix(shown.suffix)
        value.setValue((self.panel.session.targets.get(uid, joint["target"])*scale+offset)*factor)
        control = RangeControl(value, low, high)
        control.set_span(low, high, expand=False)
        value.valueChanged.connect(lambda n: None if self.following else self.panel.session.set_target(uid, (n/factor-offset)/scale))
        value.valueChanged.connect(lambda n: None if self.following else self.highlight_axis(uid))
        control.slider.sliderPressed.connect(lambda: self.highlight_axis(uid))
        control.slider.setEnabled(active)
        value.setEnabled(active)
        self.joint_inputs[uid] = (value, factor, scale, offset)
        self.range_controls.append(control)
        grid.addWidget(control, r, COL_TARGET)
        self.rows[uid] = (actual, joint, shown)
        self.key_cell(grid, r, "joint", uid, joint, bindings, active)
        return self.expansion(grid, r+1, "joint", uid, joint, bindings, active)

    def virtual_row(self, grid, r, control, active, bindings):
        from .virtual_controls import clamp
        from .range_control import RangeControl
        control_id = control["id"]
        self.icon_cell(grid, r, "controls")
        switch = control["kind"] == "switch"
        kind = tr("Switch") if switch else tr("Slider")
        cell, self.name_labels[control_id] = self.name_cell(control["name"], kind+" · "+tr("{count} axes", count=len(control["joints"])))
        grid.addWidget(cell, r, COL_NAME)
        value = clamp(control, self.panel.session.virtual_values.get(control_id, control["initial"]))
        self.virtual_state_labels[control_id] = self.value_label(grid, r)

        def change(v):
            if not self.following:
                self.panel.session.set_virtual(control_id, v)
            self.show_virtual(control_id, control, v)
        if switch:
            holder = QWidget()
            h = QHBoxLayout(holder)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)
            buttons = QButtonGroup(holder)
            for i, state in enumerate(control["states"]):
                button = QPushButton(state["name"])
                button.setCheckable(True)
                button.setChecked(i == value)
                button.setEnabled(active)
                # The pressed state has to stand out from the others, so the checked button takes the accent.
                button.setStyleSheet("QPushButton:checked { background: palette(highlight); color: palette(highlighted-text); font-weight: bold; }")
                buttons.addButton(button, i)
                h.addWidget(button)
            buttons.idClicked.connect(change)
            h.addStretch()
            grid.addWidget(holder, r, COL_TARGET)
            self.virtual_inputs[control_id] = ("switch", buttons)
        else:
            number = QDoubleSpinBox()
            number.setRange(0, 100)
            number.setDecimals(0)
            number.setSuffix(" %")
            number.setValue(value*100)
            slider = RangeControl(number, 0, 100)
            slider.set_span(0, 100, expand=False)
            number.valueChanged.connect(lambda n: change(n/100))
            slider.slider.setEnabled(active)
            number.setEnabled(active)
            self.range_controls.append(slider)
            grid.addWidget(slider, r, COL_TARGET)
            self.virtual_inputs[control_id] = ("slider", number)
        self.show_virtual(control_id, control, value)
        self.key_cell(grid, r, "control", control_id, control, bindings, active)
        return self.expansion(grid, r+1, "control", control_id, control, bindings, active)

    def show_virtual(self, control_id, control, value):
        label = self.virtual_state_labels.get(control_id)
        if label is None:
            return
        if control["kind"] == "switch":
            label.setText(control["states"][max(0, min(len(control["states"])-1, int(round(value))))]["name"])
        else:
            label.setText(f"{value*100:.0f} %")

    def name_cell(self, name, sub):
        cell = QWidget()
        v = QVBoxLayout(cell)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        title = QLabel(name)
        title.setTextFormat(Qt.PlainText)
        title.setStyleSheet("font-weight: bold;")
        small = muted(QLabel(sub), 8)
        small.setTextFormat(Qt.PlainText)
        v.addStretch()
        v.addWidget(title)
        v.addWidget(small)
        v.addStretch()
        return cell, title

    def key_cell(self, grid, r, kind, ident, subject, bindings, active):
        from .key_bindings import find
        from .key_slots import slot_name
        binding = find(bindings or [], kind, ident)
        editable = not active and bindings is not None
        cell = QWidget()
        h = QHBoxLayout(cell)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        if binding is None or (kind, ident) in self.key_editing:
            h.addWidget(self.slot_picker(kind, ident, subject, binding, editable))
        else:
            key = ""
            slots = self.panel.key_slots.actions
            n = binding["slot"]
            key = slots[n-1].shortcut().toString(QKeySequence.NativeText) if n <= len(slots) else ""
            if key:
                caps = KeyCaps(key)
                caps.setFixedHeight(caps.sizeHint().height())
                h.addWidget(caps, 0, Qt.AlignVCenter)
            else:
                h.addWidget(muted(QLabel(tr("No key"))))
            text = QWidget()
            t = QVBoxLayout(text)
            t.setContentsMargins(0, 0, 0, 0)
            t.setSpacing(0)
            t.addStretch()
            t.addWidget(QLabel(slot_name(binding["slot"])))
            t.addWidget(muted(QLabel(tr("Toggle") if binding["mode"] == "toggle" else tr("Step")), 8))
            t.addStretch()
            h.addWidget(text)
            modify = QPushButton(tr("Modify"))
            modify.setEnabled(editable)
            modify.clicked.connect(lambda: self.modify_key((kind, ident)))
            h.addWidget(modify)
        h.addStretch()
        grid.addWidget(cell, r, COL_KEY)
        more = QToolButton()
        more.setAutoRaise(True)
        px = icon_px()
        more.setIconSize(QSize(px, px))
        more.setFixedSize(px+8, px+8)
        more.setArrowType(Qt.DownArrow if (kind, ident) in self.expanded else Qt.RightArrow)
        more.setToolTip(tr("Key binding") if kind == "joint" else tr("Key binding and states"))
        more.setEnabled(self.has_more(kind, binding))
        more.clicked.connect(lambda: self.toggle_row((kind, ident)))
        grid.addWidget(more, r, COL_MORE)

    def has_more(self, kind, binding):
        """A virtual control always has its states to show; an axis has only the settings of a key binding it does not have yet."""
        return kind == "control" or binding is not None

    def slot_picker(self, kind, ident, subject, binding, editable):
        from .binding_fields import slot_labels
        from .key_bindings import fresh
        from .toolbar import compact
        combo = compact(QComboBox())
        combo.addItem(tr("No key"), None)
        for n, label in slot_labels(self.panel, (binding["slot"],) if binding else ()):
            combo.addItem(label, n)
        combo.setCurrentIndex(max(0, combo.findData(binding["slot"] if binding else None)))
        combo.setToolTip(tr(help.KEY_BINDING_SLOT))
        combo.setEnabled(editable)

        def chosen(_index):
            slot = combo.currentData()
            self.key_editing.discard((kind, ident))
            if slot is None:
                new = None
            elif binding is None:
                new = fresh(kind, ident, subject, slot, "toggle")
            else:
                new = dict(binding, slot=slot)
            self.store_binding(kind, ident, new)
            QTimer.singleShot(0, lambda: self.refresh(*self.last))
        combo.activated.connect(chosen)
        return combo

    def modify_key(self, key):
        self.key_editing.add(key)
        self.refresh(*self.last)

    def toggle_row(self, key):
        self.expanded.symmetric_difference_update({key})
        self.refresh(*self.last)

    def expansion(self, grid, r, kind, ident, subject, bindings, active):
        from .key_bindings import find
        binding = find(bindings or [], kind, ident)
        if (kind, ident) not in self.expanded or not self.has_more(kind, binding):
            return r
        box = QFrame()
        v = QVBoxLayout(box)
        v.setContentsMargins(42, 6, 12, 12)
        v.setSpacing(8)
        if kind == "control":
            from .virtual_editor import VirtualControlEditor
            v.addWidget(muted(QLabel(tr("States").upper()), 7))
            editor = VirtualControlEditor(self, subject)
            editor.setEnabled(not active)
            editor.setMaximumWidth(760)
            v.addWidget(editor, 0, Qt.AlignLeft)
        if binding is not None:
            v.addWidget(muted(QLabel(tr("Key binding").upper()), 7))
            fields = self.key_fields(kind, ident, subject, bindings, active)
            fields.slot.hide()
            fields.setMaximumWidth(760)
            v.addWidget(fields, 0, Qt.AlignLeft)
        grid.addWidget(box, r, 0, 1, COL_MORE+1)
        return r+1

    # ---- key bindings ------------------------------------------------------------------
    def key_fields(self, kind, ident, subject, bindings, active):
        from .binding_fields import BindingFields
        from .key_bindings import find
        fields = BindingFields(self.panel, kind, ident, subject, find(bindings or [], kind, ident))
        fields.setEnabled(not active and bindings is not None)
        fields.changed.connect(lambda binding: self.store_binding(kind, ident, binding))
        return fields

    def store_binding(self, kind, ident, binding):
        from .binding_fields import store
        # The strip's key summary changes too; rebuilding inside the sender's signal would delete the sender.
        self.holding = True
        try:
            changed = store(self.panel, kind, ident, binding)
        finally:
            self.holding = False
        if changed:
            QTimer.singleShot(0, lambda: self.refresh(*self.last))

    # ---- running state -----------------------------------------------------------------
    def follow_targets(self):
        """Show targets the session changed (a key press); the inputs must not write them back, rounding would alter the target."""
        session = self.panel.session
        self.following = True
        try:
            for uid, (spin, factor, scale, offset) in self.joint_inputs.items():
                if uid in session.targets:
                    spin.setValue((session.targets[uid]*scale+offset)*factor)
            controls = {c["id"]: c for c in self.panel.virtual_controls()}
            for control_id, (kind, widget) in self.virtual_inputs.items():
                if control_id not in session.virtual_values:
                    continue
                value = session.virtual_values[control_id]
                if kind == "switch":
                    button = widget.button(int(value))
                    if button:
                        button.setChecked(True)
                else:
                    widget.setValue(value*100)
                if control_id in controls:
                    self.show_virtual(control_id, controls[control_id], value)
        finally:
            self.following = False

    def refresh_icons(self):
        self.start_button.setIcon(icon("pause" if self.panel.session.running else "play"))
        self.reset_button.setIcon(icon("reset"))
        for control in self.range_controls:
            control.refresh_style()

    def highlight_axis(self, uid):
        self.panel.detail_uid = uid
        self.panel.app.viewport.update()

    def show_time(self, seconds):
        self.time_label.setText(tr("Time: {seconds:.2f} s", seconds=seconds))

    def message(self, text, level="info", bodies=()):
        """Errors and warnings go to the banner above the rows, with ``bodies`` (``(group, name, role)``) listed below the text; anything else to the header."""
        if level in ("error", "warning"):
            self.kept = (text, level, [(getattr(group, "uid", None), name, role) for group, name, role in bodies])
            self.banner_text.setText(tr(text))
            rows = [(i, group, name, role) for i, (group, name, role) in enumerate(bodies[:MAX_BODY_ROWS])]
            if len(bodies) > MAX_BODY_ROWS:
                rows.append((None, None, tr("… and {count} more", count=len(bodies)-MAX_BODY_ROWS), ""))
            self.bodies.set_rows(rows)
            self.bodies.setVisible(bool(rows))
            self.banner_mark.setPixmap(pixmap("status_error" if level == "error" else "status_warning", 18))
            self.banner_mark.setAccessibleName(tr("Error") if level == "error" else tr("Warning"))
            self.banner.show()
            self.hint.setText("")
        else:
            self.banner.hide()
            self.bodies.set_rows([])
            self.bodies.hide()
            self.hint.setText(tr(text))
            self.hint.setToolTip(self.hint.text())

    def restore_kept(self, scene):
        """Show the last warning again after Reset; the rows then point at the restored document's groups, not at clones."""
        text, level, rows = self.kept
        groups = {g.uid: g for g in scene.groups}
        self.message(text, level, [(groups[uid] if uid is not None else None, name, role)
                                   for uid, name, role in rows if uid is None or uid in groups])

    def telemetry(self, data):
        for uid, state in data.items():
            if uid in self.rows:
                label, joint, shown = self.rows[uid]
                factor, digits = shown.factor, shown.decimals
                mapping = joint.get("display") or {}
                scale, offset = mapping.get("scale", 1), mapping.get("offset", 0)
                value = state["velocity"] if joint["drive"] == "velocity" else state["position"]
                target = (state.get("target", joint["target"])*scale+offset)*factor
                command = (state.get("command", state.get("target", joint["target"]))*scale+offset)*factor
                tip = tr("Target: {target} · Ramp: {command} · Load: {load:.0f}%", target=f"{target:.{digits}f}", command=f"{command:.{digits}f}", load=state.get("load", 0)*100)
                at_limit = state.get("at_limit")
                # setStyleSheet repolishes the label, so write only on change
                for current, new, write in ((label.toolTip(), tip+"\n"+tr("At limit") if at_limit else tip, label.setToolTip),
                                            (label.styleSheet(), "font-family: monospace; color: #e79b38" if at_limit else "font-family: monospace;", label.setStyleSheet),
                                            (label.text(), f"{(value*scale+offset)*factor:.{digits}f} {shown.unit}"+(" !" if at_limit else ""), label.setText)):
                    if new != current:
                        write(new)

    def show_performance(self, metrics):
        self.performance_label.setVisible(bool(metrics))
        if not metrics:
            return
        speed = metrics.get("speed")
        self.performance_label.setText(tr("Paused") if metrics.get("paused") else tr("{speed:.2f}× real time", speed=speed) if speed is not None else tr("Measuring…"))
        self.performance_label.setToolTip(tr("Newton: {newton:.1f} ms\nDisplay preparation: {ui:.1f} ms\nRound trip: {roundtrip:.1f} ms\nBodies: {bodies} · Contacts: {contacts}\nSolver iterations: {iterations} · Substeps: {substeps}",
            newton=metrics.get("newton_ms",0),ui=metrics.get("ui_ms",0),roundtrip=metrics.get("roundtrip_ms",0),
            bodies=metrics.get("bodies",0),contacts=metrics.get("contacts",0),iterations=metrics.get("iterations",0),substeps=metrics.get("substeps",1)))
