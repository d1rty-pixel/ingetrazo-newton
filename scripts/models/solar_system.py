"""Two freely moving bodies in a scaled, mutual Newtonian orbit."""
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QVector3D,QMatrix4x4
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import DEFAULTS,KEY,prepare
from newton.worker import World

G = .16
MASSES = (100.,5.)
DISTANCE = 4.
SOFTENING = .05
OMEGA = math.sqrt(G*sum(MASSES)/(DISTANCE**2+SOFTENING**2)**1.5)
PERIOD = 2*math.pi/OMEGA


def sphere(name,radius,position,colour,mass,velocity):
    mesh = Mesh();segments,rings = 32,16
    def point(j,i):
        theta,phi = math.pi*j/rings,2*math.pi*i/segments
        return QVector3D(radius*math.sin(theta)*math.cos(phi),radius*math.sin(theta)*math.sin(phi),radius*math.cos(theta))
    for j in range(rings):
        for i in range(segments):
            points = [point(j,i),point(j+1,i),point(j+1,i+1),point(j,i+1)]
            if j==0:points = points[:3]
            elif j==rings-1:points = [points[0],points[1],points[3]]
            face = mesh.add_face(points)
            face.attrs["color"] = colour
    for edge in mesh.edges:edge.soft = True
    body = Group(mesh,name);body.xform = QMatrix4x4();body.xform.translate(*position)
    body.ext = {KEY:dict(DEFAULTS,shape="sphere",mass=mass,restitution=0,
        simulation_override=dict(gravity=[0,0,0],floor=False,linear_damping=0,angular_damping=0,
            attraction=G*mass,softening=SOFTENING,initial_velocity=velocity))}
    return body


def build():
    sun_x = -DISTANCE*MASSES[1]/sum(MASSES)
    planet_x = DISTANCE*MASSES[0]/sum(MASSES)
    scene = Scene()
    scene.groups = [sphere("Sun",.7,(sun_x,0,2),(1.,.61,.08),MASSES[0],[0,OMEGA*sun_x,0]),
                    sphere("Planet",.28,(planet_x,0,2),(.12,.48,.93),MASSES[1],[0,OMEGA*planet_x,0])]
    return scene


def validate(scene):
    import numpy as np
    _,specs,_ = prepare(scene)
    world = World();initial = world.load(dict(bodies=specs,gravity=0,floor=False))
    sun,planet = [g.uid for g in scene.groups]
    origin = np.array(initial["poses"][sun][0])
    largest_sun_motion = 0
    try:
        for _ in range(round(3*PERIOD*30)):
            poses = world.step(8)["poses"]
            a,b = [np.array(poses[uid][0]) for uid in (sun,planet)]
            assert abs(np.linalg.norm(b-a)-DISTANCE)<.025
            assert np.linalg.norm((MASSES[0]*a+MASSES[1]*b)/sum(MASSES)-[0,0,2])<1e-5
            largest_sun_motion = max(largest_sun_motion,np.linalg.norm(a-origin))
        assert largest_sun_motion>.35
        print(f"Checked: 3 orbits, distance 4 m, centre of mass stable, sun moves along. Orbital period {PERIOD:.2f} s.",flush=True)
    finally:world.close()


def main():
    path = ROOT/"models/sun-and-planet.igz"
    if "--existing" in sys.argv:
        scene = Scene();igz.load_into(scene,path)
    else:
        if path.exists():raise FileExistsError(f"Existing model kept: {path}")
        scene = build()
    validate(scene)
    if "--existing" not in sys.argv:igz.save_scene(scene,path)
    print(path,flush=True)
    if "--open" not in sys.argv:return
    from PySide6.QtCore import QSettings,QTimer
    from PySide6.QtWidgets import QApplication,QScrollArea
    app = QApplication([]);app.setOrganizationName("NewtonPreview");app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    st = QSettings()
    for key,value in dict(gravity_z=0,floor=False,linear_damping=0,angular_damping=0).items():
        st.setValue("newton/"+key,value)
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    folder = ROOT/".test-state/autosave";folder.mkdir(parents=True,exist_ok=True)
    autosave.autosave_dir = lambda:folder
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1400,950);assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds());win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable)
    win.viewport.scene.select([win.viewport.scene.groups[1]]);win.viewport.notify_scene_changed()
    panel.show_sidebar();panel.advanced_toggle.setChecked(True)
    QTimer.singleShot(500,lambda:panel.findChild(QScrollArea).ensureWidgetVisible(panel.environment_section))
    app.exec()


if __name__=="__main__":main()
