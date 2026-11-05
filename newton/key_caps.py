"""Key caps: a shortcut drawn as one small cap per key, in the palette's colours."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QWidget


def key_names(text):
    """``"Ctrl+Shift+A"`` to ``["Ctrl", "Shift", "A"]``; a trailing "+" is the plus key itself."""
    if not text:
        return []
    if text.endswith("+"):
        return [name for name in text[:-1].rstrip("+").split("+") if name] + ["+"]
    return text.split("+")


class KeyCaps(QWidget):
    GAP = 4

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.names = []
        self.set_text(text)

    def set_text(self, text):
        self.names = key_names(text)
        self.updateGeometry()
        self.update()

    def widths(self):
        metrics = self.fontMetrics()
        return [max(metrics.height(), metrics.horizontalAdvance(name)+12) for name in self.names]

    def sizeHint(self):
        widths = self.widths()
        return QSize(sum(widths)+self.GAP*max(0, len(widths)-1), self.fontMetrics().height()+8)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        palette = self.palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        x = 0.5
        for name, width in zip(self.names, self.widths()):
            cap = QRectF(x, 0.5, width-1, self.height()-4)
            painter.setPen(palette.color(QPalette.Mid))
            painter.setBrush(palette.color(QPalette.Button))
            painter.drawRoundedRect(cap.adjusted(0, 0, 0, 0), 4, 4)
            # The thicker lower edge is what makes it read as a key.
            painter.drawLine(cap.left()+3, cap.bottom()+2, cap.right()-3, cap.bottom()+2)
            painter.setPen(palette.color(QPalette.ButtonText))
            painter.drawText(cap, Qt.AlignCenter, name)
            x += width+self.GAP
