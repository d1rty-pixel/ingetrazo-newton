"""Overlay benchmark: selection refresh and overlay painting for N jointed bodies.

Runs its own offscreen IngeTrazo window with an isolated settings profile; never touches a running instance.
Usage: benchmark_overlays.py [--sizes=5,20,60] [--profile] [--repeat=5] [--images=DIR]
--images writes the painted overlays (no 3D view offscreen) as overlay-<n>.png for a visual check.
"""
import cProfile
import math
import os
import pstats
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "ingetrazo-source")]
from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setOrganizationName("NewtonBenchmark")
app.setApplicationName("NewtonBenchmark")
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(ROOT / ".test-state"))
from core import autosave, extensions
extensions.plugin_dirs = lambda: [ROOT]
folder = ROOT / ".test-state" / "autosave"
folder.mkdir(parents=True, exist_ok=True)
autosave.autosave_dir = lambda: folder
from newton.model import AddDemo, box


def model(count):
    """Static base plus `count` hinged leaves on a grid; every leaf carries a hinge axis object."""
    side = math.ceil(math.sqrt(count))
    base = box("Base", (0, 0, -.1), (side * 1.2 + 1, side * 1.2 + 1, .2), mode="static")
    groups = [base]
    for i in range(count):
        x, y = (i % side) * 1.2, (i // side) * 1.2
        groups.append(box(f"Leaf {i+1}", (x + .3, y, 1), (.6, .1, .8), joint=dict(
            type="hinge", drive="position", name=f"Hinge {i+1}", parent=base.uid,
            pivot=[x, y, 1], axis=[0, 0, 1], target=0, force=100, limited=True, lower=0, upper=math.pi / 2)))
    return groups


def timed(fn, repeat):
    best = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best.append(time.perf_counter() - start)
    return min(best) * 1000, sum(best) / len(best) * 1000


def run(count, repeat, profile, images=None):
    from views.main_window import MainWindow
    win = MainWindow()
    win.resize(1400, 950)
    dock = next(d for d in win._extension_docks if d.objectName() == "extension_newton")
    panel = dock.widget()
    panel.python.setText(sys.executable)
    win.show()
    vp = win.viewport
    groups = model(count)
    start = time.perf_counter()
    vp.history.execute(AddDemo(groups))
    load_ms = (time.perf_counter() - start) * 1000
    lo, hi = vp.scene.bounds()
    vp.camera.fit_to(lo, hi)
    app.processEvents()
    leaves = [g for g in vp.scene.groups if g.name.startswith("Leaf ")]
    image = QImage(vp.width(), vp.height(), QImage.Format_ARGB32)

    def paint():
        image.fill(0)
        painter = QPainter(image)
        panel.draw_joints(vp, painter)
        painter.end()

    def select(items):
        vp.scene.select(items)
        vp.notify_scene_changed()
        app.processEvents()

    report = dict(bodies=count, objects=len(vp.scene.groups), load_ms=round(load_ms, 1))
    select([])
    report["paint_none_ms"] = round(timed(paint, repeat)[0], 1)
    select(leaves[:1])
    report["paint_one_ms"] = round(timed(paint, repeat)[0], 1)
    if images:
        Path(images).mkdir(parents=True, exist_ok=True)
        paint()
        image.save(str(Path(images) / f"overlay-{count}-one.png"))
    select(leaves)
    report["paint_all_ms"] = round(timed(paint, repeat)[0], 1)
    if images:
        paint()
        Path(images).mkdir(parents=True, exist_ok=True)
        image.save(str(Path(images) / f"overlay-{count}.png"))
    report["select_all_ms"] = round(timed(lambda: (select([]), select(leaves)), repeat)[0], 1)
    report["select_none_ms"] = round(timed(lambda: (select(leaves), select([])), repeat)[0], 1)
    if profile:
        select(leaves)
        profiler = cProfile.Profile()
        profiler.enable()
        paint()
        profiler.disable()
        print(f"--- profile: paint, {count} bodies selected")
        pstats.Stats(profiler).sort_stats("cumtime").print_stats(14)
        select([])
        profiler = cProfile.Profile()
        profiler.enable()
        select(leaves)
        profiler.disable()
        print(f"--- profile: select all, {count} bodies")
        pstats.Stats(profiler).sort_stats("cumtime").print_stats(18)
    win._saved_version = vp.scene.version
    panel.controls.close()
    win.close()
    return report


if __name__ == "__main__":
    sizes = next((v.split("=", 1)[1] for v in sys.argv if v.startswith("--sizes=")), "5,20,60")
    repeat = int(next((v.split("=", 1)[1] for v in sys.argv if v.startswith("--repeat=")), 5))
    images = next((v.split("=", 1)[1] for v in sys.argv if v.startswith("--images=")), None)
    for n in (int(s) for s in sizes.split(",")):
        print(run(n, repeat, "--profile" in sys.argv, images), flush=True)
