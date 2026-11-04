"""Referenced bodies as table rows: a small picture, the name and a button that removes the reference."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import QWidget,QGridLayout,QVBoxLayout,QLabel,QToolButton,QPushButton,QMenu,QSizePolicy
from views.component_thumbs import thumbnail
from .i18n import tr
from .toolbar import icon

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


class ReferenceTable(QWidget):
    """Rows of ``(key, group or None, name, role)``; ``remove(key)`` runs when a row's button is pressed."""

    def __init__(self,remove,empty=""):
        super().__init__()
        self.remove = remove
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setColumnStretch(1,1)
        self.placeholder = QLabel(empty)
        self.placeholder.setTextFormat(Qt.PlainText)
        self.signature = None
        self.rows = []
        self.set_rows([])

    def set_rows(self,rows):
        ratio = self.devicePixelRatioF()
        raw = [thumbnail(group,round(SIZE*ratio)) if group is not None else None for _,group,_,_ in rows]
        # Every sidebar refresh lands here; rebuilding unchanged rows would drop focus and hover.
        signature = tuple((key,name,role,pm.cacheKey() if pm is not None else None) for (key,_,name,role),pm in zip(rows,raw))
        if signature==self.signature:
            return
        self.signature = signature
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget is not None and widget is not self.placeholder:
                widget.deleteLater()
        self.rows = [name for _,_,name,_ in rows]
        self.placeholder.setVisible(not rows)
        hide = not rows and not self.placeholder.text()
        # Showing a widget without a parent would open it as a window of its own.
        if hide or self.parentWidget() is not None:
            self.setHidden(hide)
        if not rows:
            self.grid.addWidget(self.placeholder,0,0,1,3)
            return
        for index,((key,group,name,role),pm) in enumerate(zip(rows,raw)):
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
            button = QToolButton()
            button.setIcon(icon("unlink"))
            button.setToolTip(tr("Remove"))
            button.setAccessibleName(tr("Remove")+" "+name)
            button.setAutoRaise(True)
            button.clicked.connect(lambda _=False,k=key:self.remove(k))
            self.grid.addWidget(image,index,0)
            self.grid.addWidget(text,index,1)
            self.grid.addWidget(button,index,2)

    def names(self):
        return list(self.rows)


class ChooseButton(QPushButton):
    """Opens a menu of the bodies that fit; ``candidates()`` yields ``(key, group, name)``."""

    def __init__(self,text,candidates,choose,nothing):
        super().__init__(text)
        self.candidates,self.choose,self.nothing = candidates,choose,nothing
        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self.fill)
        self.setMenu(self.menu)

    def fill(self):
        self.menu.clear()
        ratio = self.devicePixelRatioF()
        for key,group,name in self.candidates():
            self.menu.addAction(QIcon(picture(group,SIZE,ratio)),name,lambda k=key:self.choose(k))
        if self.menu.isEmpty():
            self.menu.addAction(self.nothing).setEnabled(False)
