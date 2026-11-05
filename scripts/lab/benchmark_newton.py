"""Repeatable solver benchmark; JSON report includes machine-local timings."""
import cProfile
import json
import pstats
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from core.scene import Scene
from formats import igz
from newton.model import prepare
from newton.worker import World


def benchmark(path,seconds=2,profile=False,quality="balanced"):
    scene = Scene();igz.load_into(scene,Path(path))
    _,specs,_ = prepare(scene)
    world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=False,quality=quality))
    profiler = cProfile.Profile();start = time.perf_counter()
    if profile:profiler.enable()
    for _ in range(round(seconds*30)):result = world.step(8)
    if profile:profiler.disable()
    elapsed = time.perf_counter()-start
    report = dict(model=Path(path).name,sim_seconds=result["time"],wall_seconds=elapsed,
        realtime=result["time"]/elapsed,bodies=world.model.nbody-1,dofs=world.model.nv,
        substeps=world.substeps,contacts=world.data.ncon,quality=quality)
    if profile:pstats.Stats(profiler).sort_stats("cumtime").print_stats(12)
    world.close();return report


if __name__=="__main__":
    report = benchmark(ROOT/"models/crank-drive-drag-chain.igz",profile="--profile" in sys.argv,
        quality=next((v.split("=",1)[1] for v in sys.argv if v.startswith("--quality=")),"balanced"))
    print(json.dumps(report,indent=2))
    output = next((v.split("=",1)[1] for v in sys.argv if v.startswith("--output=")),None)
    if output:Path(output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
