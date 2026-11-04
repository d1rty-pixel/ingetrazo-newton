"""Thirty upright dominoes triggered by a passive pendulum on a freestanding frame.

python scripts/domino_pendulum.py --open
python scripts/domino_pendulum.py --existing --open
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"scripts"),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QMatrix4x4
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import box,KEY,DEFAULTS,prepare,ensure_axis_layer
from newton.worker import World
from domino import build as domino_build,validate as validate_domino
from robot_arm import beam,cylinder


def build(release_angle=-32):
    scene = domino_build()
    base = box("Support",(.55,.65,.03),(3.15,1.9,.06),mode="static",friction=.8,restitution=0)
    for f in base.mesh.faces:
        f.attrs["color"] = (.19,.23,.28)
    scene.groups[0] = base
    # The first tile is now completely upright; there is no hidden push.
    first = scene.groups[1]
    first.xform = QMatrix4x4();first.xform.translate(0,0,.235)
    supports = []
    for y,label in ((-.24,"front"),(.24,"rear")):
        foot = box("Pendulum foot "+label,(-.23,y,.08),(.42,.16,.04),mode="static",reference=base.uid)
        post = box("Pendulum post "+label,(-.23,y,.47),(.055,.055,.74),mode="static",reference=base.uid)
        supports.extend([foot,post])
    crossbar = box("Pendulum crossbeam",(-.23,0,.86),(.08,.59,.06),mode="static",reference=base.uid)
    supports.append(crossbar)
    for g in supports:
        for f in g.mesh.faces: f.attrs["color"] = (.54,.59,.65)
    pivot = [-.23,0,.86]
    angle,length = math.radians(release_angle),.58
    bob = [pivot[0]+length*math.sin(angle),0,pivot[2]-length*math.cos(angle)]
    pendulum = Group(Mesh(),"Starting pendulum")
    pendulum.ext = {KEY:dict(DEFAULTS,mass=.4,shape="hull",friction=.4,restitution=0,
        reference=crossbar.uid,joint=dict(type="hinge",drive="free",name="Pendulum bearing",
            pivot=pivot,axis=[0,1,0],parent=crossbar.uid,force=0,limited=False))}
    beam(pendulum.mesh,pivot,bob,.018,.018,(.70,.73,.76))
    cylinder(pendulum.mesh,bob,[0,1,0],.065,.085,(.86,.18,.10))
    scene.groups.extend([*supports,pendulum])
    ensure_axis_layer(scene)
    # Keep the exhibit unobstructed; its hinge can be shown using the layer eye.
    next(l for l in scene.layers if l.name=="Newton Axes").visible = False
    return scene


def validate(scene):
    _,specs,_ = prepare(scene)
    world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=True))
    first = next(g for g in scene.groups if g.name=="Domino 01")
    pendulum = next(g for g in scene.groups if g.name=="Starting pendulum")
    first_bid,pendulum_bid = world.bodies[first.uid],world.bodies[pendulum.uid]
    assert abs(world.data.xmat[first_bid][8]-1)<1e-6
    contact_time = fall_time = None
    for _ in range(480):
        result = world.step(1)
        if any({int(world.model.geom_bodyid[c.geom1]),int(world.model.geom_bodyid[c.geom2])}=={first_bid,pendulum_bid}
               for c in world.data.contact):
            contact_time = contact_time or result["time"]
        if abs(world.data.xmat[first_bid][8])<.55:
            fall_time = result["time"];break
    world.close()
    assert contact_time and fall_time and contact_time<fall_time,"The pendulum must actually hit the first stone."
    print(f"Pendulum contact after {contact_time:.2f} s; first stone falls after {fall_time:.2f} s.",flush=True)
    validate_domino(scene)


def main():
    folder = ROOT/"models";folder.mkdir(exist_ok=True)
    path = folder/"domino-30-with-pendulum.igz"
    if "--existing" in sys.argv:
        scene = Scene();igz.load_into(scene,path)
    else:
        if path.exists(): raise FileExistsError(f"Existing model not overwritten: {path}")
        scene = build()
    validate(scene)
    if "--existing" not in sys.argv: igz.save_scene(scene,path)
    print(path,flush=True)
    if "--open" not in sys.argv: return
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    app.setOrganizationName("NewtonPreview");app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    autosave_folder = ROOT/".test-state/autosave";autosave_folder.mkdir(parents=True,exist_ok=True)
    autosave.autosave_dir = lambda:autosave_folder
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1400,950)
    assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds());win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable);panel.show_controls()
    app.exec()


if __name__=="__main__": main()
