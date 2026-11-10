from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDoubleSpinBox

from newton.range_control import RangeControl


def test_click_in_the_groove_jumps_the_handle_there(qtapp):
    number = QDoubleSpinBox()
    number.setRange(0, 100)
    control = RangeControl(number, 0, 100)
    control.resize(400, 40)
    control.show()
    qtapp.processEvents()
    slider = control.slider
    QTest.mouseClick(slider, Qt.LeftButton, Qt.NoModifier, QPoint(slider.width()*3//4, slider.height()//2))
    assert 65 < number.value() < 85
    assert "24px" in slider.styleSheet()
