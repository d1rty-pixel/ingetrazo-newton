"""Counterfactual algorithm timings; all replacements are process-local only."""
import ast
import importlib.util
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace as NS

ROOT = Path('/home/equinox/git/private/ingetrazo-newton')
spec = importlib.util.spec_from_file_location('review_worker', ROOT/'newton/worker.py')
worker = importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
World = worker.World

def timed(fn, repeats=7):
    data=[]
    for _ in range(repeats):
        start=time.perf_counter();fn();data.append((time.perf_counter()-start)*1000)
    return round(statistics.median(data),3)

def bodies(n, attracts=False):
    return [dict(uid=str(i),center=[i*2.,0.,10.],half=[.1]*3,mass=1.,shape='box',
                 simulation_override=dict(attraction=.001 if attracts else 0.)) for i in range(n)]

def attraction_summed(self):
    # Same pair forces; combine per target, then apply its Jacobian just once.
    for target in self.bodies.values():
        total = self.np.zeros(3)
        for source,mu,softening in self.attractors:
            if target==source:continue
            delta = self.data.xipos[source]-self.data.xipos[target]
            d2 = float(delta@delta)+softening**2
            if d2>=1e-18:
                total += self.model.body_mass[target]*mu*delta/d2**1.5
        jp = self.np.zeros((3,self.model.nv))
        self.mj.mj_jacBodyCom(self.model,self.data,jp,None,target)
        self.data.qfrc_applied[:] += jp.T@total

def attraction_vectorized(self):
    sources=self.np.array([s for s,_,_ in self.attractors],dtype=int)
    strengths=self.np.array([mu for _,mu,_ in self.attractors])
    softenings=self.np.array([s*s for _,_,s in self.attractors])
    for target in self.bodies.values():
        delta=self.data.xipos[sources]-self.data.xipos[target]
        d2=self.np.einsum('ij,ij->i',delta,delta)+softenings
        valid=(sources!=target)&(d2>=1e-18)
        total=self.model.body_mass[target]*self.np.sum(delta[valid]*(strengths[valid]/d2[valid]**1.5)[:,None],axis=0)
        jp=self.np.zeros((3,self.model.nv))
        self.mj.mj_jacBodyCom(self.model,self.data,jp,None,target)
        self.data.qfrc_applied[:]+=jp.T@total

print('ATTRACTION: per-pair vs per-target Jacobian (same force math)',flush=True)
for n in (50,100):
    w=World();w.load(dict(bodies=bodies(n,True),gravity=0.,floor=False));w.step(8)
    original=timed(lambda:w.step(8),5)
    w.data.qfrc_applied[:]=0;w.apply_attraction();expected=w.data.qfrc_applied.copy()
    w.apply_attraction=attraction_summed.__get__(w)
    w.data.qfrc_applied[:]=0;w.apply_attraction()
    error=float(abs(w.data.qfrc_applied-expected).max())
    changed=timed(lambda:w.step(8),5)
    print(dict(n=n,original_ms=original,per_target_ms=changed,force_max_abs_error=error),flush=True)
    w.apply_attraction=attraction_vectorized.__get__(w)
    w.data.qfrc_applied[:]=0;attraction_summed(w);reference=w.data.qfrc_applied.copy()
    w.data.qfrc_applied[:]=0;w.apply_attraction()
    import numpy as np
    np.testing.assert_allclose(w.data.qfrc_applied,reference,rtol=1e-12,atol=1e-12)
    print(dict(n=n,vectorized_ms=timed(lambda:w.step(8),5),force_check='passed'),flush=True)
    w.close()

print('WORKER PROTOCOL INITIALIZATION: unused vertices on analytic boxes',flush=True)
for count in (1000,100000,250000):
    b=bodies(1);b[0]['vertices']=[[.1,.2,.3]]*count
    req=dict(op='init',bodies=b,gravity=0.,floor=False)
    payload=json.dumps(req)
    print(dict(vertices=count,payload_bytes=len(payload),encode_ms=timed(lambda:json.dumps(req),5),
               decode_ms=timed(lambda:json.loads(payload),5)),flush=True)

print('STOP: exact CollisionView.stop with a non-responding fake worker (500ms kill/reap latency)',flush=True)
tree=ast.parse((ROOT/'newton/collision_view.py').read_text())
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CollisionView')
fn=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='stop')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'newton/collision_view.py','exec'),ns)
class Timer:
    def stop(self):pass
class Process:
    def kill(self):pass
    def waitForFinished(self,timeout):time.sleep(.5)
    def deleteLater(self):pass
def stop():ns['stop'](NS(timer=Timer(),timeout=Timer(),process=Process()))
print(dict(blocked_ui_ms=timed(stop,3)),flush=True)
