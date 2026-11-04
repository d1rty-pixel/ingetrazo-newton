"""Build, validate and optionally open a three-servo industrial arm.

python scripts/robot_arm.py --open
python scripts/robot_arm.py --gripper --open
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QVector3D
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import KEY,DEFAULTS,prepare
from newton.worker import World

ORANGE = (.94,.36,.055)
DARK = (.15,.18,.22)
STEEL = (.60,.65,.70)


def face(mesh,points,colour):
    mesh.add_face([QVector3D(*p) for p in points]).attrs["color"] = colour


def beam(mesh,start,end,width,depth,colour):
    import numpy as np
    a,b = np.array(start,dtype=float),np.array(end,dtype=float)
    axis = (b-a)/np.linalg.norm(b-a)
    side = np.array([0.,1.,0.])
    up = np.cross(axis,side)
    up /= np.linalg.norm(up)
    pts = [p+sx*width/2*side+sy*depth/2*up
           for p in (a,b) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    for ids in ((3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
        face(mesh,[pts[i] for i in ids],colour)


def cylinder(mesh,center,axis,radius,length,colour):
    import numpy as np
    c,d = np.array(center),np.array(axis,dtype=float)
    d /= np.linalg.norm(d)
    u = np.cross(d,[1.,0.,0.] if abs(d[0])<.9 else [0.,1.,0.])
    u /= np.linalg.norm(u)
    v = np.cross(d,u)
    rings = [[c+s*length/2*d+radius*(math.cos(t)*u+math.sin(t)*v)
              for t in [i*2*math.pi/24 for i in range(24)]] for s in (-1,1)]
    face(mesh,list(reversed(rings[0])),colour)
    face(mesh,rings[1],colour)
    for i in range(24):
        n = (i+1)%24
        face(mesh,[rings[0][i],rings[0][n],rings[1][n],rings[1][i]],colour)


def body(name,mass,parent=None,joint=None):
    group = Group(Mesh(),name)
    group.ext = {KEY:dict(DEFAULTS,mode="static" if mass==0 else "dynamic",
                          mass=max(mass,.01),shape="hull",reference=parent,joint=joint)}
    return group


def servo(name,pivot,axis,limits,force,parent):
    return dict(type="hinge",drive="position",name=name,pivot=pivot,axis=axis,
                limited=True,lower=math.radians(limits[0]),upper=math.radians(limits[1]),
                target=0,max_speed=math.radians(45),acceleration=math.radians(90),
                force=force,parent=parent)


def build(gripper=False):
    scene = Scene()
    shoulder,elbow,wrist = [0,0,.65],[.45,0,1.30],[1.05,0,1.45]
    base = body("Pedestal",0)
    beam(base.mesh,[0,0,.015],[0,0,.13],.62,.62,DARK)
    cylinder(base.mesh,[0,0,.23],[0,0,1],.23,.20,STEEL)
    turn = body("Turret",5,base.uid,servo("01 Base rotation",[0,0,.33],[0,0,1],(-160,160),200,base.uid))
    cylinder(turn.mesh,[0,0,.37],[0,0,1],.25,.08,ORANGE)
    beam(turn.mesh,[0,0,.41],shoulder,.24,.24,ORANGE)
    cylinder(turn.mesh,shoulder,[0,1,0],.16,.31,DARK)
    upper = body("Upper arm",3,turn.uid,servo("02 Shoulder",shoulder,[0,1,0],(-55,65),160,turn.uid))
    beam(upper.mesh,shoulder,elbow,.18,.22,ORANGE)
    cylinder(upper.mesh,[0,-.19,.65],[0,1,0],.115,.08,STEEL)
    cylinder(upper.mesh,elbow,[0,1,0],.135,.27,DARK)
    fore = body("Forearm",2,upper.uid,servo("03 Elbow",elbow,[0,1,0],(-90,100),100,upper.uid))
    beam(fore.mesh,elbow,wrist,.14,.16,ORANGE)
    cylinder(fore.mesh,[.45,-.17,1.3],[0,1,0],.095,.08,STEEL)
    if gripper:
        import numpy as np
        axis = np.array(wrist)-np.array(elbow)
        axis /= np.linalg.norm(axis)
        w = np.array(wrist)
        cylinder(fore.mesh,w,axis,.105,.09,DARK)
        hand = body("Wrist",.8,fore.uid,
                    servo("04 Wrist rotation",w.tolist(),axis.tolist(),(-180,180),30,fore.uid))
        cylinder(hand.mesh,w+.075*axis,axis,.09,.06,STEEL)
        beam(hand.mesh,w+.10*axis,w+.18*axis,.23,.09,ORANGE)
        fingers = []
        for side,name in ((-1,"Left jaw"),(1,"Right jaw")):
            offset = np.array([0,side*.075,0])
            pivot = w+.17*axis+offset
            joint = dict(type="slide",drive="position",name="05 Close left" if side<0 else "06 Close right",
                         pivot=pivot.tolist(),axis=[0,-side,0],parent=hand.uid,
                         limited=True,lower=0,upper=.05,target=0,
                         max_speed=.025,acceleration=.1,force=30)
            finger = body(name,.8,hand.uid,joint)
            finger.ext[KEY]["friction"] = 1.2
            beam(finger.mesh,w+.17*axis+offset,w+.36*axis+offset,.045,.07,DARK)
            fingers.append(finger)
        # The two axis vectors already point inward: equal coordinates mean
        # equal and opposite world motion. Only the first axis is actuated.
        fingers[0].ext[KEY]["joint"].update(name="Gripper opening",display=dict(scale=-2,offset=.105))
        fingers[1].ext[KEY]["joint"].update(coupling=dict(master=fingers[0].uid,ratio=1))
        scene.groups.extend([base,turn,upper,fore,hand,*fingers])
        return scene
    cylinder(fore.mesh,wrist,[1,0,0],.10,.12,DARK)
    # Fixed tool with two visibly separated fingers, no fourth moving axis.
    beam(fore.mesh,[1.09,0,1.45],[1.20,0,1.45],.20,.09,STEEL)
    for y in (-.075,.075):
        beam(fore.mesh,[1.18,y,1.45],[1.34,y,1.45],.045,.055,DARK)
    scene.groups.extend([base,turn,upper,fore])
    return scene


def validate(scene):
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=-9.81,floor=True))
    driven = [g for g in scene.groups if g.ext[KEY].get("joint")]
    poses = ((30,-20,40,60,.035,.035),(-35,15,-30,-45,.015,.015),(0,0,0,0,0,0))
    for values in poses:
        targets = {g.uid:math.radians(a) if g.ext[KEY]["joint"]["type"]=="hinge" else a
                   for g,a in zip(driven,values) if not g.ext[KEY]["joint"].get("coupling")}
        for _ in range(120):
            result = world.step(8,targets)
        for g in driven:
            actual = result["joints"][g.uid]["position"]
            tolerance = math.radians(3) if g.ext[KEY]["joint"]["type"]=="hinge" else .002
            c = g.ext[KEY]["joint"].get("coupling")
            target = targets[c["master"]]*c["ratio"] if c else targets[g.uid]
            assert abs(actual-target)<tolerance,(g.name,target,actual)
    world.close()
    print(f"Checked: {len(driven)} drives, three target poses, return to the initial position.",flush=True)


def main():
    gripper = "--gripper" in sys.argv
    folder = ROOT/"models"
    folder.mkdir(exist_ok=True)
    path = folder/("industrial-robot-synchronous-gripper.igz" if gripper else "industrial-robot-3-axis.igz")
    if "--existing" in sys.argv:
        if not path.is_file():raise FileNotFoundError(path)
    else:
        if path.exists():raise FileExistsError(f"To open the existing model use --existing --open: {path}")
        scene = build(gripper)
        validate(scene)
        from newton.model import ensure_axis_layer
        ensure_axis_layer(scene)
        igz.save_scene(scene,path)
        loaded = Scene();igz.load_into(loaded,path)
        assert len(loaded.groups)==(7 if gripper else 4)
        assert len([g for g in loaded.groups if g.ext[KEY].get("joint")])==(6 if gripper else 3)
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
    win = MainWindow()
    win.resize(1400,950)
    assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds())
    win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable)
    if "--sidebar" in sys.argv:
        selected = next(g for g in win.viewport.scene.groups if g.name==("Left jaw" if gripper else "Upper arm"))
        win.viewport.scene.select([selected]);win.viewport.notify_scene_changed();panel.show_sidebar()
    else:
        panel.show_controls()
    app.exec()


if __name__=="__main__":
    main()
