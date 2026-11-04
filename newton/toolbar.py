"""Newton toolbar, dropdown pictograms and labels with drawings of physical quantities."""
import weakref
from collections.abc import Mapping
import shiboken6
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar
from .i18n import tr
from .icons import attach,icon,repaint


# One drawing per fixed dropdown value; it shows how the bodies involved interact.
CHOICES = {
 "mode": {"dynamic":"movable","static":"fixed","ignore":"ignored"},
 "shape": {"box":"shape_box","sphere":"shape_sphere","hull":"shape_hull","compound":"shape_compound"},
 "drive": {"free":"drive_free","position":"drive_position","velocity":"drive_velocity"},
 "connection": {"ball":"connection_ball","hinge":"connection_hinge","fixed":"connection_fixed"},
 "flexible": {"rigid":"rigid","rope":"rope","cable":"cable"},
 "attachment": {"fixed":"attachment_clamped","pinned":"attachment_pinned","free":"attachment_free"},
 "direction": {1:"direction_same",-1:"direction_reverse"},
 "axis": {None:"no_axis","hinge":"rotate","slide":"slide"},
}
_decorated = weakref.WeakKeyDictionary()


def decorate(combo,kind):
    """Give each fixed choice of a dropdown its interaction pictogram; dynamic entries stay plain."""
    _decorated[combo] = kind
    combo.setIconSize(QSize(22,22))
    compact(combo)
    drawings = CHOICES[kind]
    for index in range(combo.count()):
        key = combo.itemData(index)
        if key in drawings:combo.setItemIcon(index,icon(drawings[key]))


def compact(combo):
    """Let a dropdown shrink with a narrow sidebar instead of sizing itself to its longest entry."""
    from PySide6.QtWidgets import QComboBox
    combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(6)
    from .range_control import scroll_safe
    return scroll_safe(combo)


def redecorate():
    # A Python wrapper can outlive its deleted widget, so the weak registries keep the entry.
    for combo,kind in list(_decorated.items()):
        if shiboken6.isValid(combo):decorate(combo,kind)
        else:del _decorated[combo]
    repaint()


def physical_label(text,art):
    """Form label with a small drawing of the physical quantity at its right end, so label texts stay aligned."""
    from PySide6.QtWidgets import QWidget,QLabel,QHBoxLayout
    widget = QWidget();row = QHBoxLayout(widget);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
    row.addWidget(QLabel(text));row.addStretch()
    row.addWidget(attach(QLabel(),art))
    return widget


def physical_check(checkbox,art):
    checkbox.setIconSize(QSize(20,20))
    return attach(checkbox,art)


class Actions(Mapping):
    """Toolbar actions by key; a dead wrapper is looked up again by object name.

    PySide 6.11 can invalidate the Python wrapper of a live QAction when other code walks a
    menu's actions (see IngeTrazo's views/theme.py _redraw_icons), so a cached wrapper is not
    reliable."""

    def __init__(self,window,actions):
        self.window = window
        self._actions = actions

    def __getitem__(self,key):
        action = self._actions[key]
        if not shiboken6.isValid(action):
            action = self.window.findChild(QAction,"newton_"+key)
            if action is None:
                raise KeyError(key)
            self._actions[key] = action
        return action

    def __iter__(self):
        return iter(self._actions)

    def __len__(self):
        return len(self._actions)


def build(panel):
    from .connections import begin as begin_connection
    bar = QToolBar(tr("Newton"),panel.app.window)
    bar.setObjectName("newton_toolbar")
    from views.icons import toolbar_icon_px
    size = toolbar_icon_px()
    bar.setIconSize(QSize(size,size))
    actions = {}
    def add(key,art,label,callback,tip):
        action = bar.addAction(icon(art),tr(label))
        action.setObjectName("newton_"+key)
        action.setProperty("newton_icon",art)
        action.setToolTip(tr(label)+" — "+tr(tip))
        action.triggered.connect(callback)
        actions[key] = action
    groups = [
        ("Axes",[("rotate","rotate","Place rotation axis",lambda:panel.edit_joint("hinge"),"Pick the pivot and direction"),
            ("slide","slide","Place linear axis",lambda:panel.edit_joint("slide"),"Pick the origin and direction"),
            ("connect_ball","connection_ball","Ball joint",lambda:begin_connection(panel,"ball"),"Place the point, then pick the other body"),
            ("connect_hinge","connection_hinge","Pin joint",lambda:begin_connection(panel,"hinge"),"Place the point and the pin direction, then pick the other body"),
            ("connect_fixed","connection_fixed","Fixed connection",lambda:begin_connection(panel,"fixed"),"Place the point, then pick the other body")]),
        ("Bodies",[("free","movable","Movable",lambda:panel.mark("dynamic"),"Make the selection movable"),
            ("fixed","fixed","Fixed",lambda:panel.mark("static"),"Fix the selection")]),
        ("References",[("link","link","Assign reference body",panel.pick_reference,"Pick a reference body"),
            ("unlink","unlink","Detach reference body",panel.detach_reference,"Keep the current placement")]),
        ("Simulation",[("play","play","Start / pause",panel.start_or_pause,"Run or pause the simulation"),
            ("reset","reset","Reset",panel.session.reset,"Return to the original model"),
            ("drag","drag","Drag body",panel.activate_drag,"Drag passive bodies"),
            ("controls","controls","Controls",panel.show_controls,"Open named actuator controls")]),
        ("Extension",[("panel","panel","Newton properties",panel.show_sidebar,"Show properties of the selection")])]
    for index,(title,entries) in enumerate(groups):
        if index:
            separator = bar.addSeparator()
            separator.setObjectName("newton_separator_"+str(index))
            separator.setToolTip(tr(title))
        for entry in entries:
            add(*entry)
    panel.app.window.addToolBar(bar)
    panel.app.restore_toolbar_layout()
    return bar,Actions(panel.app.window,actions)
