"""Read-only extension microbenchmarks: changing telemetry and indexed collider lookup."""
import ast
import copy
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace as NS

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPainter, QMatrix4x4, QQuaternion, QVector3D, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import numpy as np
ROOT = Path('/home/equinox/git/private/ingetrazo-newton/newton')
app = QApplication([])

def method(file, cls, name, indexed=False):
    klass = next(n for n in ast.parse((ROOT/file).read_text()).body if isinstance(n,ast.ClassDef) and n.name==cls)
    fn = copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name==name))
    if indexed:
        # Include the per-paint index construction in the measurement, not just its lookups.
        for index,node in enumerate(fn.body):
            if isinstance(node,ast.For):
                fn.body.insert(index,ast.parse('groups_by_uid = {g.uid:g for g in self.panel.app.scene.groups}').body[0])
                for inner in node.body:
                    if isinstance(inner,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='g' for t in inner.targets):
                        inner.value=ast.parse('groups_by_uid.get(uid)',mode='eval').body
                break
    ns=dict(globals(),tr=lambda text,**values:text.format(**values))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(ROOT/file),'exec'),ns)
    return ns[name]

def timed(fn,n=20):
    samples=[]
    for _ in range(n):
        start=time.perf_counter();fn();samples.append((time.perf_counter()-start)*1000)
    return round(statistics.median(samples),3)

telemetry=method('controls.py','Controls','telemetry')
class CachedLabel(QLabel):
    def setStyleSheet(self,text):
        if text!=self.styleSheet():super().setStyleSheet(text)

for n in (10,50,100):
    for cached in (False,True):
        window=QWidget();layout=QVBoxLayout(window);rows={};data={}
        for i in range(n):
            label=(CachedLabel if cached else QLabel)();layout.addWidget(label)
            rows[str(i)]=(label,dict(drive='position',target=0.),NS(factor=1.,decimals=2,unit='m'))
            data[str(i)]=dict(position=0.,target=.5,command=.5,load=.1,at_limit=False)
        obj=NS(rows=rows);window.resize(300,1200);window.show();app.processEvents()
        def frame():
            for state in data.values():state['position']+=.01;state['load']+=.001
            telemetry(obj,data);app.processEvents()
        frame();print(dict(probe='changing telemetry',n=n,cached=cached,ms=timed(frame)),flush=True)
        window.close();window.deleteLater();app.processEvents()

original=method('collision_view.py','CollisionView','draw')
indexed=method('collision_view.py','CollisionView','draw',True)
image=QImage(1000,800,QImage.Format_ARGB32)
shape=dict(points=[[a,b,c] for a in (-.1,.1) for b in (-.1,.1) for c in (-.1,.1)],
           edges=[(0,1),(0,2),(0,4),(1,3),(1,5),(2,3),(2,6),(3,7),(4,5),(4,6),(5,7),(6,7)],faces=[])
def project(points):
    p=np.asarray(points);return p[:,0]*10+100,p[:,1]*10+100,np.ones(len(points),dtype=bool)
vp=NS(world_to_pixels=project)
for n in (100,500,1000):
    scene=NS(groups=[NS(uid=str(i),hidden=False,layer='default') for i in range(n)],layers=[])
    cv=NS(panel=NS(app=NS(scene=scene,viewport=vp),selected=lambda:[],session=NS(workspace=None)),
          active=lambda:True,shown=lambda uid:True,colliders={str(i):shape for i in range(n)},
          poses={str(i):([i*.01,0.,0.],[0.,0.,0.,1.]) for i in range(n)})
    for label,fn in [('original',original),('indexed',indexed)]:
        def draw():
            painter=QPainter(image)
            try:fn(cv,vp,painter)
            finally:painter.end()
        draw();print(dict(probe='collider draw',n=n,variant=label,ms=timed(draw,10)),flush=True)
