"""Launch a separate test window with the extension and a motor demo.

Uses an isolated settings profile; does not open or alter the user's models.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "ingetrazo-source")]
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication,QScrollArea

app = QApplication([])
app.setOrganizationName("NewtonPreview")
app.setApplicationName("NewtonPreview")
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(ROOT / ".test-state"))
from core import extensions, autosave
extensions.plugin_dirs = lambda: [ROOT]
folder = ROOT / ".test-state" / "autosave"
folder.mkdir(parents=True, exist_ok=True)
autosave.autosave_dir = lambda: folder
from views.main_window import MainWindow
win = MainWindow()
win.resize(1400, 950)
dock = next(d for d in win._extension_docks if d.objectName() == "extension_newton")
panel = dock.widget()
panel.python.setText(sys.executable)
from newton.model import demo,AddDemo
groups = demo(sys.argv[1] if len(sys.argv)>1 else "Servo-Tür")
win.viewport.history.execute(AddDemo(groups))
win.viewport.scene.select(groups)
win.viewport.notify_scene_changed()
lo,hi = win.viewport.scene.bounds()
win.viewport.camera.fit_to(lo,hi)
win.show()
dock.show()
dock.raise_()
if "--settings" in sys.argv:
    win.viewport.scene.select([next(g for g in groups if (g.ext or {}).get("newton",{}).get("joint"))])
    win.viewport.notify_scene_changed()
    panel.advanced_toggle.setChecked(True)
    QTimer.singleShot(300,lambda:panel.findChild(QScrollArea).ensureWidgetVisible(panel.coupling_section))
if "--edit" not in sys.argv:
    QTimer.singleShot(1500, panel.start_or_pause)
app.exec()
