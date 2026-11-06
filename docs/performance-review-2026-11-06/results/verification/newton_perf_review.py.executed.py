"""Isolated, non-mutating Newton performance probes (offscreen, synthetic scenes)."""
import ast
import cProfile
import importlib.util
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import time
from types import SimpleNamespace as NS

ROOT = Path('/home/equinox/git/private/ingetrazo-newton')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QSettings, Qt, QPointF
from PySide6.QtGui import QImage, QPainter, QMatrix4x4, QQuaternion, QVector3D, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import numpy as np
spec = importlib.util.spec_from_file_location('review_worker', ROOT / 'newton/worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
World = worker.World

def extracted_method(file, cls, method):
    """Run the exact Newton method, without importing any host-dependent modules."""
    tree = ast.parse((ROOT / 'newton' / file).read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    fn = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == method)
    namespace = dict(globals(), tr=lambda text, **values:text.format(**values))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(ROOT / 'newton' / file), 'exec'), namespace)
    return namespace[method]

Controls = NS(telemetry=extracted_method('controls.py', 'Controls', 'telemetry'))
CollisionView = NS(draw=extracted_method('collision_view.py', 'CollisionView', 'draw'))

app = QApplication([])
app.setOrganizationName('NewtonPerfReview')
app.setApplicationName('Isolated')
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, '/tmp/opencode/newton-review-ws2aulis')

def timed(fn, repeat=7):
    samples = []
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(samples), 3)

def specs(n, damping=False, attract=False):
    return [dict(uid=str(i), center=[i*2., 0., 10.], half=[.1]*3,
                 mass=1., shape='box',
                 simulation_override=dict(attraction=.001 if attract else 0.))
            for i in range(n)]

print('WORKER: median ms per batch of 8 physics steps (33.3ms simulated)', flush=True)
for n in (10, 50, 100):
    for mode in ('base', 'damping', 'attraction-all'):
        w = World()
        w.load(dict(bodies=specs(n, attract=mode=='attraction-all'), gravity=0., floor=False,
                    linear_damping=2. if mode=='damping' else 0.))
        w.step(8)
        ms = timed(lambda: w.step(8), repeat=5)
        print(json.dumps(dict(n=n, mode=mode, step8_ms=ms, nv=w.model.nv)), flush=True)
        if n == 100 and mode != 'base':
            pr = cProfile.Profile()
            pr.runcall(w.step, 8)
            buf = io.StringIO()
            pstats.Stats(pr, stream=buf).sort_stats('cumtime').print_stats(12)
            print(buf.getvalue(), flush=True)
        w.close()

class CachedStyleLabel(QLabel):
    """Counterfactual: skip only identical stylesheet writes, same telemetry otherwise."""
    def setStyleSheet(self, text):
        if text != self.styleSheet():
            super().setStyleSheet(text)

print('TELEMETRY: median ms per update including offscreen Qt event processing', flush=True)
for n in (10, 50, 100):
    for cached in (False, True):
        window = QWidget()
        layout = QVBoxLayout(window)
        label_cls = CachedStyleLabel if cached else QLabel
        rows = {}
        data = {}
        for i in range(n):
            label = label_cls()
            layout.addWidget(label)
            rows[str(i)] = (label, dict(drive='position', target=0.), NS(factor=1., decimals=2, unit='m'))
            data[str(i)] = dict(position=.5, target=.5, command=.5, load=.1, at_limit=False)
        obj = NS(rows=rows)
        window.resize(300, 1200)
        window.show()
        app.processEvents()
        def frame():
            Controls.telemetry(obj, data)
            app.processEvents()
        frame()
        print(json.dumps(dict(n=n, cached_style=cached, ms=timed(frame, repeat=20))), flush=True)
        window.close()
        window.deleteLater()
        app.processEvents()

print('COLLIDER DRAW: synthetic boxes, no host rendering; median ms per draw', flush=True)
image = QImage(1000, 800, QImage.Format_ARGB32)
shape = dict(points=[[a,b,c] for a in (-.1,.1) for b in (-.1,.1) for c in (-.1,.1)],
             edges=[(0,1),(0,2),(0,4),(1,3),(1,5),(2,3),(2,6),(3,7),(4,5),(4,6),(5,7),(6,7)], faces=[])
def project(points):
    p = np.asarray(points)
    return p[:,0]*10+100, p[:,1]*10+100, np.ones(len(points),dtype=bool)
vp = NS(world_to_pixels=project)
for n in (100, 500, 1000):
    scene = NS(groups=[NS(uid=str(i), hidden=False, layer='default') for i in range(n)], layers=[])
    panel = NS(app=NS(scene=scene, viewport=vp), selected=lambda: [], session=NS(workspace=None))
    cv = NS(panel=panel, active=lambda:True, shown=lambda uid:True,
            colliders={str(i):shape for i in range(n)},
            poses={str(i):([i*.01,0.,0.],[0.,0.,0.,1.]) for i in range(n)})
    def draw():
        painter = QPainter(image)
        CollisionView.draw(cv, vp, painter)
        painter.end()
    print(json.dumps(dict(n=n, ms=timed(draw, repeat=7))), flush=True)
    if n==1000:
        pr = cProfile.Profile(); pr.runcall(draw)
        buf = io.StringIO();pstats.Stats(pr, stream=buf).sort_stats('cumtime').print_stats(12)
        print(buf.getvalue(),flush=True)
