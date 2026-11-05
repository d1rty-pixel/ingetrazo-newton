"""Newton toolbars, dropdown pictograms and labels with drawings of physical quantities."""
import weakref
from collections.abc import Mapping
import shiboken6
from PySide6.QtCore import QRect,QSize,Qt
from PySide6.QtGui import QAction,QIcon
from PySide6.QtWidgets import QCheckBox,QToolBar,QWidget
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


def physical_label(text,art=None):
    """Form label with the drawing left of the text; a wrapped text stays beside the drawing, not below it.

    Without ``art`` the drawing's column stays empty so the texts of all rows start at the same x."""
    from PySide6.QtWidgets import QWidget,QLabel,QHBoxLayout
    widget = QWidget();row = QHBoxLayout(widget);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
    image = QLabel();image.setFixedSize(20,20)
    if art:attach(image,art)
    name = QLabel(text);name.setWordWrap(True)
    row.addWidget(image,0,Qt.AlignTop);row.addWidget(name,1,Qt.AlignVCenter)
    widget.icon_label,widget.text_label = image,name
    return widget


class IconCheck(QCheckBox):
    """Checkbox drawn as "drawing, box, text", like the checkboxes of the preferences pages.

    QCheckBox cannot wrap its text, so a label child carries it; that keeps long texts from
    widening the sidebar."""
    GAP = 6

    def __init__(self,text):
        super().__init__()
        from PySide6.QtWidgets import QLabel,QSizePolicy
        self._icon = QIcon()
        self.label = QLabel(text,self);self.label.setWordWrap(True);self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        policy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred);policy.setHeightForWidth(True)
        self.setSizePolicy(policy);self.setAccessibleName(text)

    def text(self):
        return self.label.text()

    def setIcon(self,icon):
        self._icon = icon;self.update()

    def _indicator(self):
        from PySide6.QtWidgets import QStyle
        style = self.style()
        return style.pixelMetric(QStyle.PM_IndicatorWidth,None,self),style.pixelMetric(QStyle.PM_IndicatorHeight,None,self)

    def _left(self):
        return 20+self.GAP+self._indicator()[0]+self.GAP

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self,width):
        return max(self._indicator()[1],self.label.heightForWidth(max(width-self._left(),1)))+2

    def sizeHint(self):
        hint = self.label.sizeHint()
        return QSize(self._left()+hint.width(),max(self._indicator()[1],hint.height())+2)

    def minimumSizeHint(self):
        return QSize(self._left()+self.label.minimumSizeHint().width(),self._indicator()[1]+2)

    def resizeEvent(self,event):
        left = self._left();width = max(self.width()-left,1)
        self.label.setGeometry(left,1,width,self.label.heightForWidth(width))

    def paintEvent(self,event):
        from PySide6.QtWidgets import QStylePainter,QStyleOptionButton,QStyle
        painter = QStylePainter(self);option = QStyleOptionButton();self.initStyleOption(option)
        option.text = ""
        line = self.label.fontMetrics().height()+2
        width,height = self._indicator()
        option.rect = QRect(20+self.GAP,(line-height)//2,width,height)
        painter.drawPrimitive(QStyle.PE_IndicatorCheckBox,option)
        if self.hasFocus():
            option.rect = self.rect();painter.drawPrimitive(QStyle.PE_FrameFocusRect,option)
        mode = QIcon.Normal if self.isEnabled() else QIcon.Disabled
        self._icon.paint(painter,QRect(0,(line-20)//2,20,20),Qt.AlignCenter,mode)


def pictogram_check(checkbox,art):
    return attach(IconCheck(checkbox.text()),art)


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
    """The "Newton Tools" bar for modelling and the "Newton Simulation" bar to run it."""
    from .connections import begin as begin_connection
    from views.icons import toolbar_icon_px
    size = toolbar_icon_px()
    actions = {}
    def bar(title,name,groups):
        bar = QToolBar(title,panel.app.window)
        bar.setObjectName(name)
        bar.setIconSize(QSize(size,size))
        for index,entries in enumerate(groups):
            if index:
                gap = QWidget()
                gap.setFixedSize(size//2,size//2)
                bar.addWidget(gap).setObjectName(name+"_gap_"+str(index))
            for key,art,label,callback,tip in entries:
                action = bar.addAction(icon(art),tr(label))
                action.setObjectName("newton_"+key)
                action.setProperty("newton_icon",art)
                action.setToolTip(tr(label)+" — "+tr(tip))
                action.triggered.connect(callback)
                actions[key] = action
        panel.app.window.addToolBar(bar)
        return bar
    tools = bar(tr("Newton Tools"),"newton_tools",[
        [("rotate","rotate","Place rotation axis",lambda:panel.edit_joint("hinge"),"Pick the pivot and direction"),
         ("slide","slide","Place linear axis",lambda:panel.edit_joint("slide"),"Pick the origin and direction")],
        [("connect_ball","connection_ball","Ball joint",lambda:begin_connection(panel,"ball"),"Place the point, then pick the other body"),
         ("connect_hinge","connection_hinge","Pin joint",lambda:begin_connection(panel,"hinge"),"Place the point and the pin direction, then pick the other body"),
         ("connect_fixed","connection_fixed","Fixed connection",lambda:begin_connection(panel,"fixed"),"Place the point, then pick the other body")],
        [("link","link","Assign reference body…",panel.pick_reference,"Pick a reference body"),
         ("unlink","unlink","Detach reference body",panel.detach_reference,"Keep the current placement")],
        [("free","movable","Movable",lambda:panel.mark("dynamic"),"Make the selection movable"),
         ("fixed","fixed","Fixed",lambda:panel.mark("static"),"Fix the selection")],
        [("panel","panel","Newton properties",panel.show_sidebar,"Show properties of the selection")],
        [("controls","controls","Controls",panel.show_controls,"Open named actuator controls")]])
    simulation = bar(tr("Newton Simulation"),"newton_simulation",[
        [("play","play","Start / pause",panel.start_or_pause,"Run or pause the simulation"),
         ("reset","reset","Reset",panel.session.reset,"Return to the original model"),
         ("drag","drag","Drag body",panel.activate_drag,"Drag passive bodies")]])
    panel.app.restore_toolbar_layout()
    return tools,simulation,Actions(panel.app.window,actions)
