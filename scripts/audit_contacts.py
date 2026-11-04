"""Audit active contact pairs rather than inferring collisions from the picture."""
import json
import sys
import time
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from core.scene import Scene
from formats import igz
from newton.model import prepare
from newton.worker import World


def audit(path,seconds=4):
    scene = Scene();igz.load_into(scene,Path(path));_,specs,_ = prepare(scene)
    names = {s["uid"]:next((g.name for g in scene.groups if g.uid==s.get("flex_segment",s["uid"])),s["uid"]) for s in specs}
    world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=False))
    body_names = {bid:names.get(uid,uid) for uid,bid in world.bodies.items()}
    counts = [];pairs = Counter();kinds = Counter();penetration = 0;started = time.perf_counter()
    def category(name):return "chain" if name.startswith("Glied ") else "cable" if "Netzkabel" in name else "rod" if name=="Pleuelstange" else "wheel" if "Speichenrad" in name else "bed" if name=="Maschinenbett" else "other"
    for _ in range(round(seconds*30)):
        world.step(8);counts.append(int(world.data.ncon))
        for c in world.data.contact[:world.data.ncon]:
            a,b = [body_names.get(int(world.model.geom_bodyid[int(g)]),"world") for g in (c.geom1,c.geom2)]
            pairs[tuple(sorted((a,b)))] += 1;kinds[tuple(sorted((category(a),category(b))))] += 1
            penetration = max(penetration,-float(c.dist))
    report = dict(model=Path(path).name,sim_seconds=world.data.time,wall_seconds=time.perf_counter()-started,
        bodies=world.model.nbody-1,geoms=world.model.ngeom,dofs=world.model.nv,
        contacts_mean=sum(counts)/len(counts),contacts_max=max(counts),max_penetration_m=penetration,
        categories={" / ".join(k):v for k,v in kinds.most_common()},pairs=[dict(a=k[0],b=k[1],samples=v) for k,v in pairs.most_common(16)])
    world.close();return report


if __name__=="__main__":
    path = next((a for a in sys.argv[1:] if not a.startswith("--")),str(ROOT/"models/Kurbeltrieb-mit-Schleppkette.igz"))
    report = audit(path)
    print(json.dumps(report,indent=2))
    output = next((a.split("=",1)[1] for a in sys.argv if a.startswith("--output=")),None)
    if output:Path(output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
