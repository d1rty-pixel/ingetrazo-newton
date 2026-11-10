"""Which collision exemptions a model needs: the body pairs that would touch along its real motion.

The model runs with its exemptions; after every batch a second copy without any exemption takes the
same pose and reports its contacts. Pairs that never come within the margin can lose their exemption.

    python scripts/lab/needed_exemptions.py models/gear-train-carousel.igz --seconds=12 --margin=0.01
"""
import copy
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
import mujoco
from core.scene import Scene
from formats import igz
from newton.model import prepare
from newton.worker import World


def sweep(path,seconds=12,margin=.01):
    scene = Scene();igz.load_into(scene,Path(path));_,specs,_ = prepare(scene)
    names = {g.uid:g.name for g in scene.groups}
    bare = copy.deepcopy(specs)
    for spec in bare:spec["no_collision"] = []
    moving,probe = World(),World()
    moving.load(dict(bodies=specs,gravity=-9.81,floor=False));probe.load(dict(bodies=bare,gravity=-9.81,floor=False))
    probe.model.geom_margin[:] = margin
    body = {bid:names.get(uid,uid) for uid,bid in probe.bodies.items()}
    samples,closest,active = Counter(),{},0
    for _ in range(round(seconds*30)):
        moving.step(8);active = max(active,int(moving.data.ncon))
        probe.data.qpos[:] = moving.data.qpos;mujoco.mj_forward(probe.model,probe.data)
        for c in probe.data.contact[:probe.data.ncon]:
            if c.dist>=margin:continue
            pair = tuple(sorted(body.get(int(probe.model.geom_bodyid[g]),"world") for g in (c.geom1,c.geom2)))
            samples[pair] += 1;closest[pair] = min(closest.get(pair,margin),float(c.dist))
    simulated = moving.data.time
    moving.close();probe.close()
    return simulated,active,[(a,b,samples[(a,b)],closest[(a,b)]) for a,b in sorted(samples)]


if __name__=="__main__":
    args = dict(a[2:].split("=",1) for a in sys.argv[1:] if a.startswith("--"))
    path = next(a for a in sys.argv[1:] if not a.startswith("--"))
    time,active,pairs = sweep(path,float(args.get("seconds",12)),float(args.get("margin",.01)))
    print(f"{time:.1f} s simulated, at most {active} contacts with the model's own exemptions")
    for a,b,count,distance in pairs:
        print(f"{a:28s} {b:28s} {count:6d} samples, closest {distance*1000:+.1f} mm")
