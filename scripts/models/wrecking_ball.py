"""Build and validate a wrecking ball that swings into a brick wall.

python scripts/models/wrecking_ball.py
python scripts/models/wrecking_ball.py --open
python scripts/models/wrecking_ball.py --existing --open
"""
import colorsys
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QMatrix4x4,QVector3D
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import DEFAULTS,KEY,box,prepare,ensure_axis_layer
from newton.worker import World

NAME = "wrecking-ball-and-brick-wall.igz"
STEEL = (.62,.67,.72)
BALL = (.30,.33,.38)
DARK = (.17,.20,.25)
YELLOW = (.98,.78,.10)
PLATE_TOP = .06
PIVOT = (0.,0.,2.6)
LENGTH = 2.0
RADIUS = .22
BALL_MASS = 25.
START_ANGLE = 58.
BRICK = (.14,.28,.09)
ROWS = 12
PER_ROW = 4
WALL_X = .45


def swing_back(point):
    """The pendulum is modelled raised on the side away from the wall."""
    a = math.radians(-START_ANGLE)
    x,z = point[0]-PIVOT[0],point[2]-PIVOT[2]
    return (PIVOT[0]+x*math.cos(a)-z*math.sin(a),point[1],PIVOT[2]+x*math.sin(a)+z*math.cos(a))


def quads(mesh,pts,faces,colour,tf=lambda p:p):
    for ids in faces:
        mesh.add_face([QVector3D(*tf(pts[i])) for i in ids]).attrs["color"] = colour


CUBE = ((3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))


def add_box(mesh,low,high,colour,tf=lambda p:p):
    ring = lambda z:[(low[0],low[1],z),(high[0],low[1],z),(high[0],high[1],z),(low[0],high[1],z)]
    quads(mesh,ring(low[2])+ring(high[2]),CUBE,colour,tf)


def add_rod(mesh,top,bottom,half,colour,tf):
    ring = lambda p:[(p[0]+sx*half,p[1]+sy*half,p[2]) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    quads(mesh,ring(top)+ring(bottom),CUBE,colour,tf)


def add_cylinder_y(mesh,center,radius,length,colour,tf=lambda p:p,segments=24):
    cx,cy,cz = center
    point = lambda side,i:(cx+radius*math.cos(2*math.pi*i/segments),cy+side*length/2,cz+radius*math.sin(2*math.pi*i/segments))
    for side in (-1,1):
        ring = [tf(point(side,i)) for i in range(segments)]
        mesh.add_face([QVector3D(*p) for p in (ring if side>0 else ring[::-1])]).attrs["color"] = colour
    for i in range(segments):
        n = (i+1)%segments
        quads(mesh,[point(-1,i),point(-1,n),point(1,n),point(1,i)],[(0,1,2,3)],colour,tf)


def add_sphere(mesh,center,radius,colour,tf,segments=32,rings=16):
    cx,cy,cz = center
    def point(j,i):
        theta,phi = math.pi*j/rings,2*math.pi*i/segments
        return tf((cx+radius*math.sin(theta)*math.cos(phi),cy+radius*math.sin(theta)*math.sin(phi),cz+radius*math.cos(theta)))
    for j in range(rings):
        for i in range(segments):
            points = [point(j,i),point(j+1,i),point(j+1,i+1),point(j,i+1)]
            if j==0:points = points[:3]
            elif j==rings-1:points = [points[0],points[1],points[3]]
            mesh.add_face([QVector3D(*p) for p in points]).attrs["color"] = colour


def colour_faces(group,colour):
    for face in group.mesh.faces:
        face.attrs["color"] = colour
    return group


def build():
    scene = Scene()
    plate = colour_faces(box("Base plate",(.8,0,PLATE_TOP/2),(4.2,2.2,PLATE_TOP),mode="static",friction=.9,restitution=0),DARK)
    frame = Group(Mesh(),"Gantry")
    frame.xform = QMatrix4x4()
    frame.ext = {KEY:dict(DEFAULTS,mode="static",shape="hull",friction=.5,restitution=0)}
    for y in (-.75,.75):
        add_box(frame.mesh,(-.12,y-.07,PLATE_TOP),(.12,y+.07,PIVOT[2]+.1),YELLOW)
    add_box(frame.mesh,(-.12,-.85,PIVOT[2]+.1),(.12,.85,PIVOT[2]+.28),YELLOW)
    pendulum = Group(Mesh(),"Wrecking ball")
    pendulum.xform = QMatrix4x4()
    ball = (PIVOT[0],0,PIVOT[2]-LENGTH)
    add_cylinder_y(pendulum.mesh,PIVOT,.07,1.38,STEEL,swing_back)
    add_rod(pendulum.mesh,PIVOT,(ball[0],0,ball[2]+RADIUS),.022,STEEL,swing_back)
    add_sphere(pendulum.mesh,ball,RADIUS,BALL,swing_back)
    add_cylinder_y(pendulum.mesh,(ball[0],0,ball[2]+RADIUS+.02),.06,.10,YELLOW,swing_back)
    pendulum.ext = {KEY:dict(DEFAULTS,mode="dynamic",shape="hull",mass=BALL_MASS,friction=.4,restitution=.05,
        reference=frame.uid,joint=dict(type="hinge",drive="free",name="Pendulum",pivot=list(PIVOT),axis=[0,1,0],
                                      parent=frame.uid,limited=False))}
    scene.groups.extend([plate,frame,pendulum])
    rng = random.Random(7)
    for row in range(ROWS):
        shift = BRICK[1]/4*(1 if row%2 else -1)
        for i in range(PER_ROW):
            y = (i-(PER_ROW-1)/2)*BRICK[1]+shift
            colour = colorsys.hsv_to_rgb(.02+.05*rng.random(),.62+.2*rng.random(),.62+.28*rng.random())
            brick = colour_faces(box(f"Brick {row+1:02d}-{i+1}",(WALL_X+BRICK[0]/2,y,PLATE_TOP+BRICK[2]*(row+.5)),BRICK,
                                     mass=.6,shape="box",friction=.7,restitution=0),colour)
            scene.groups.append(brick)
    return scene


def validate(scene):
    import numpy as np
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=-9.81,floor=True))
    bricks = [g for g in scene.groups if g.name.startswith("Brick")]
    ball = next(g for g in scene.groups if g.name=="Wrecking ball")
    where = lambda g:world.data.xpos[world.bodies[g.uid]].copy()
    # The soft contacts let the stack settle by about 1 cm in the first 0.2 s; measure from there.
    while world.step(24)["time"]<.2:
        pass
    start = {g.uid:where(g) for g in bricks}
    moved_early,hit_time = 0.,None
    while True:
        t = world.step(24)["time"]
        shift = max(float(np.linalg.norm(where(g)-start[g.uid])) for g in bricks)
        if t<.3:
            moved_early = max(moved_early,shift)
        if hit_time is None and shift>.02:
            hit_time = t
        if t>=5:
            break
    scattered = sum(float(np.linalg.norm(where(g)-start[g.uid]))>.3 for g in bricks)
    ball_x = float(world.data.xpos[world.bodies[ball.uid]][0])
    world.close()
    assert moved_early<.003,f"The wall moves before the impact: {moved_early*1000:.1f} mm"
    assert hit_time is not None and .5<hit_time<2.5,f"Implausible impact time: {hit_time}"
    assert scattered>=len(bricks)//4,f"Only {scattered}/{len(bricks)} bricks moved more than 30 cm."
    print(f"Checked: impact at {hit_time:.2f} s, {scattered}/{len(bricks)} bricks moved over 30 cm, ball at x = {ball_x:.2f} m after 5 s.",flush=True)


def main():
    folder = ROOT/"models"
    folder.mkdir(exist_ok=True)
    path = folder/NAME
    if "--existing" in sys.argv:
        if not path.is_file():raise FileNotFoundError(path)
    else:
        if path.exists():raise FileExistsError(f"To open the existing model use --existing --open: {path}")
        scene = build()
        validate(scene)
        ensure_axis_layer(scene)
        igz.save_scene(scene,path)
        loaded = Scene();igz.load_into(loaded,path)
        assert len(loaded.groups)==3+ROWS*PER_ROW
        assert len([g for g in loaded.groups if g.ext[KEY].get("joint")])==1
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
    panel.show_controls()
    app.exec()


if __name__=="__main__":
    main()
