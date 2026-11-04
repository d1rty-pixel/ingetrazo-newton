"""Create and validate 30 free dominoes on a U-shaped track.

python scripts/domino.py --open
python scripts/domino.py --existing --open
"""
import colorsys
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QMatrix4x4
from core.scene import Scene
from formats import igz
from newton.model import box,prepare,KEY
from newton.worker import World


def build():
    scene = Scene()
    length,radius = 1.2,.65
    total = 2*length+math.pi*radius
    height,thickness,width,top = .35,.045,.16,.06
    base = box("Support",(.8,.65,.03),(2.65,1.9,.06),mode="static",friction=.8,restitution=0)
    for f in base.mesh.faces:
        f.attrs["color"] = (.19,.23,.28)
    scene.groups.append(base)
    for i in range(30):
        distance = i*total/29
        if distance<=length:
            x,y,yaw = distance,0,0
        elif distance<=length+math.pi*radius:
            angle = -math.pi/2+(distance-length)/radius
            x,y = length+radius*math.cos(angle),radius+radius*math.sin(angle)
            yaw = math.degrees(angle+math.pi/2)
        else:
            x,y,yaw = length-(distance-length-math.pi*radius),2*radius,180
        tile = box(f"Domino {i+1:02d}",(0,0,0),(thickness,width,height),mass=.08,
                   shape="hull",friction=.65,restitution=0)
        colour = colorsys.hsv_to_rgb(.03+.58*i/29,.74,.94)
        for f in tile.mesh.faces:
            f.attrs["color"] = colour
        transform = QMatrix4x4()
        transform.translate(x,y,top)
        transform.rotate(yaw,0,0,1)
        if i==0:
            transform.translate(thickness/2,0,0)
            transform.rotate(12,0,1,0)
            transform.translate(-thickness/2,0,height/2)
        else:
            transform.translate(0,0,height/2)
        tile.xform = transform
        scene.groups.append(tile)
    return scene


def validate(scene):
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=-9.81,floor=True))
    tiles = [g for g in scene.groups if g.name.startswith("Domino ")]
    fallen = {}
    import numpy as np
    resting = []
    for step in range(150):
        result = world.step(24)
        for g in tiles:
            bid = world.bodies[g.uid]
            if abs(float(world.data.xmat[bid][8]))<.55:
                fallen.setdefault(g.uid,result["time"])
        if step>=100:
            resting.append([world.data.xpos[world.bodies[g.uid]].copy() for g in tiles])
    count = len(fallen)
    drift = float(np.max(np.ptp(np.asarray(resting),axis=0)))
    world.close()
    assert count==30,f"Only {count}/30 stones have fallen."
    assert fallen[tiles[-1].uid]>fallen[tiles[1].uid]
    assert drift<.001,f"Residual motion too large: {drift*1000:.2f} mm"
    print(f"Checked: {count}/30 stones fallen; last stone after {fallen[tiles[-1].uid]:.1f} s; residual motion {drift*1000:.2f} mm (10–15 s).",flush=True)


def main():
    folder = ROOT/"models"
    folder.mkdir(exist_ok=True)
    path = folder/"domino-30.igz"
    if "--existing" in sys.argv:
        scene = Scene()
        igz.load_into(scene,path)
    else:
        if path.exists():
            raise FileExistsError(f"Model already exists, not overwritten: {path}; use --existing --open to open it.")
        scene = build()
    validate(scene)
    if "--existing" not in sys.argv:
        igz.save_scene(scene,path)
    loaded = Scene();igz.load_into(loaded,path)
    assert len([g for g in loaded.groups if g.ext[KEY]["mode"]=="dynamic"])==30
    print(path,flush=True)
    if "--open" not in sys.argv:
        return
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    app.setOrganizationName("NewtonPreview")
    app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    autosave_folder = ROOT/".test-state/autosave"
    autosave_folder.mkdir(parents=True,exist_ok=True)
    autosave.autosave_dir = lambda:autosave_folder
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1400,950)
    assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds())
    win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable)
    panel.show_controls()
    app.exec()


if __name__=="__main__":
    main()
