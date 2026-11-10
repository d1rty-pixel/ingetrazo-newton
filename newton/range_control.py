"""Wide sidebar slider paired with a compact, precise numeric input."""
from PySide6.QtCore import Qt,QEvent,QObject,Signal
from PySide6.QtWidgets import QWidget,QHBoxLayout,QSlider,QAbstractSpinBox,QStyle,QStyleOptionSlider
from views.tray import style_slider


class ScrollSafeSlider(QSlider):
    def wheelEvent(self,event):
        event.ignore()  # Scroll the sidebar without changing a parameter.

    def mousePressEvent(self,event):
        # The styled groove only page-steps on a click; the handle should jump under the cursor and then follow the drag.
        if event.button()==Qt.LeftButton and self.isEnabled():
            option = QStyleOptionSlider();self.initStyleOption(option)
            groove = self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderGroove,self)
            handle = self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderHandle,self)
            if not handle.contains(event.position().toPoint()):
                span = max(1,groove.width()-handle.width())
                x = event.position().x()-groove.x()-handle.width()/2
                self.setValue(QStyle.sliderValueFromPosition(self.minimum(),self.maximum(),round(x),span))
        super().mousePressEvent(event)


def style_range(slider):
    """The host's slider look with a larger handle, which is easy to miss at 16 px."""
    style_slider(slider)
    slider.setStyleSheet(slider.styleSheet()+
        " QSlider::handle:horizontal { width: 24px; height: 24px; margin: -9px 0; border-radius: 12px; }")
    slider.setMinimumHeight(32)


class WheelGuard(QObject):
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Wheel:
            event.ignore()  # Ignored, so the surrounding scroll area scrolls instead of the value changing.
            return True
        return False


_guard = WheelGuard()


def scroll_safe(widget):
    widget.installEventFilter(_guard)
    return widget


class RangeControl(QWidget):
    gestureStarted = Signal()
    gestureFinished = Signal()
    STEPS = 10000

    def __init__(self,number,low,high):
        super().__init__()
        self.number = number
        self.low,self.high = low,high
        self.expand = True
        self.slider = ScrollSafeSlider(Qt.Horizontal)
        self.slider.setRange(0,self.STEPS)
        style_range(self.slider)
        # Narrow enough that a narrow sidebar does not scroll sideways; the slider still stays usable.
        self.slider.setMinimumWidth(80)
        number.setButtonSymbols(QAbstractSpinBox.NoButtons)
        number.setFixedWidth(104)
        number.setAlignment(Qt.AlignRight)
        layout = QHBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(10)
        layout.addWidget(self.slider,1);layout.addWidget(number)
        self.slider.valueChanged.connect(self.from_slider)
        self.slider.sliderPressed.connect(self.gestureStarted)
        self.slider.sliderReleased.connect(self.gestureFinished)
        number.valueChanged.connect(self.sync)
        number.installEventFilter(self)
        self.sync()

    def set_span(self,low,high,expand=True):
        self.low,self.high,self.expand = float(low),float(high),expand
        self.sync()

    def refresh_style(self):
        style_range(self.slider)

    def sync(self,*args):
        value = self.number.value()
        self.a = min(self.low,value) if self.expand else self.low
        self.b = max(self.high,value) if self.expand else self.high
        self.slider.blockSignals(True)
        self.slider.setValue(round((value-self.a)/(self.b-self.a)*self.STEPS) if self.b>self.a else 0)
        self.slider.blockSignals(False)
        self.slider.setEnabled(self.number.isEnabled() and self.b>self.a)
        self.number.setToolTip(self.number.text())

    def from_slider(self,value):
        self.number.setValue(self.a+(self.b-self.a)*value/self.STEPS)

    def eventFilter(self,obj,event):
        if event.type()==QEvent.EnabledChange:
            self.slider.setEnabled(self.number.isEnabled() and self.b>self.a)
        if event.type()==QEvent.Wheel:
            event.ignore()
            return True
        return False
