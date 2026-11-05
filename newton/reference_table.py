"""Referenced bodies as table rows: a small picture, the name and a button that removes the reference."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QLabel,QToolButton,QPushButton,QMenu,QSizePolicy
from views.component_thumbs import thumbnail
from .i18n import tr
from .icons import attach
from .glow import offer

SIZE = 32


def picture(group,size=SIZE,ratio=1.):
    """The host tray's hand-drawn thumbnail, sharp on high-density screens."""
    if group is None:
        return QPixmap()
    pm = QPixmap(thumbnail(group,round(size*ratio)))
    pm.setDevicePixelRatio(ratio)
    return pm


class Name(QLabel):
    """Elides instead of wrapping: wrapped labels in the sidebar's forms got too little height."""

    def __init__(self,text,weak=False):
        super().__init__(text)
        self.full = text
        self.setTextFormat(Qt.PlainText)
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        if weak:
            self.setEnabled(False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(self.full,Qt.ElideRight,max(0,self.width())))


class Row(QWidget):
    """One referenced body: hovering outlines it in the viewport, a click selects it."""

    def __init__(self,group,panel):
        super().__init__()
        self.group,self.panel = group,panel
        if self.active():
            self.setCursor(Qt.PointingHandCursor)

    def active(self):
        return self.group is not None and self.panel is not None

    def enterEvent(self,event):
        if self.active():offer(self.panel,self.group)
        super().enterEvent(event)

    def leaveEvent(self,event):
        if self.active():offer(self.panel,None)
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if not (self.active() and event.button()==Qt.LeftButton):
            return super().mousePressEvent(event)
        # The selection rebuilds this table, so no leave event would clear the outline.
        offer(self.panel,None)
        self.panel.select_object(self.group)


class ReferenceTable(QWidget):
    """Rows of ``(key, group or None, name, role)``; ``remove(key)`` runs when a row's button is pressed.

    Without ``remove`` the rows have no button. With ``panel``, a row outlines its body while hovered and selects it when clicked."""

    def __init__(self,remove,empty="",panel=None):
        super().__init__()
        self.remove,self.panel = remove,panel
        self.lines = QVBoxLayout(self)
        self.lines.setContentsMargins(0,0,0,0)
        self.placeholder = QLabel(empty)
        self.placeholder.setTextFormat(Qt.PlainText)
        self.signature = None
        self.rows = []
        self.set_rows([])

    def forget(self):
        """Clear a row's outline; rows that vanish or hide get no leave event."""
        candidate = getattr(self.panel,"glow_candidate",None)
        if candidate is not None and any(isinstance(r,Row) and r.group is candidate for r in self.children()):
            offer(self.panel,None)

    def hideEvent(self,event):
        self.forget()
        super().hideEvent(event)

    def set_rows(self,rows):
        ratio = self.devicePixelRatioF()
        raw = [thumbnail(group,round(SIZE*ratio)) if group is not None else None for _,group,_,_ in rows]
        # Every sidebar refresh lands here; rebuilding unchanged rows would drop focus and hover.
        signature = tuple((key,id(group),name,role,pm.cacheKey() if pm is not None else None) for (key,group,name,role),pm in zip(rows,raw))
        if signature==self.signature:
            return
        self.signature = signature
        self.forget()
        while self.lines.count():
            widget = self.lines.takeAt(0).widget()
            if widget is not None and widget is not self.placeholder:
                widget.deleteLater()
        self.rows = [name for _,_,name,_ in rows]
        self.placeholder.setVisible(not rows)
        hide = not rows and not self.placeholder.text()
        # Showing a widget without a parent would open it as a window of its own.
        if hide or self.parentWidget() is not None:
            self.setHidden(hide)
        if not rows:
            self.lines.addWidget(self.placeholder)
            return
        for (key,group,name,role),pm in zip(rows,raw):
            row = Row(group,self.panel)
            line = QHBoxLayout(row)
            line.setContentsMargins(0,0,0,0)
            image = QLabel()
            image.setFixedSize(SIZE,SIZE)
            image.setAlignment(Qt.AlignCenter)
            if pm is not None:
                pm = QPixmap(pm)
                pm.setDevicePixelRatio(ratio)
                image.setPixmap(pm)
            text = QWidget()
            lines = QVBoxLayout(text)
            lines.setContentsMargins(0,0,0,0)
            lines.setSpacing(0)
            lines.addWidget(Name(name))
            if role:
                lines.addWidget(Name(role,weak=True))
            line.addWidget(image)
            line.addWidget(text,1)
            if self.remove is not None:
                button = attach(QToolButton(),"unlink")
                button.setToolTip(tr("Remove"))
                button.setAccessibleName(tr("Remove")+" "+name)
                button.setAutoRaise(True)
                button.clicked.connect(lambda _=False,k=key:self.remove(k))
                line.addWidget(button)
            self.lines.addWidget(row)

    def names(self):
        return list(self.rows)


class ChooseButton(QPushButton):
    """Opens a menu of the bodies that fit; ``candidates()`` yields ``(key, group, name)``.

    ``offer(group)`` is told which body the hovered entry stands for (None when the menu closes),
    so the viewport can outline it."""

    def __init__(self,text,candidates,choose,nothing,offer=None):
        super().__init__(text)
        self.candidates,self.choose,self.nothing,self.offer = candidates,choose,nothing,offer
        self.offered = []
        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self.fill)
        self.menu.hovered.connect(self.hover)
        self.menu.aboutToHide.connect(lambda:self.offer and self.offer(None))
        self.setMenu(self.menu)

    def hover(self,action):
        index = action.data()
        if self.offer:self.offer(self.offered[index] if isinstance(index,int) and index<len(self.offered) else None)

    def fill(self):
        self.menu.clear()
        self.offered = []
        ratio = self.devicePixelRatioF()
        for key,group,name in self.candidates():
            action = self.menu.addAction(QIcon(picture(group,SIZE,ratio)),name,lambda k=key:self.choose(k))
            # An index, not the group: the action's Python wrapper may be replaced (see toolbar.Actions).
            action.setData(len(self.offered));self.offered.append(group)
        if self.menu.isEmpty():
            self.menu.addAction(self.nothing).setEnabled(False)
