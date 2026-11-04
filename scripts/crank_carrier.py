"""Motor shaft → flywheel → crank/rod → piston → energy chain with real cable."""
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QMatrix4x4,QVector3D,QQuaternion
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import KEY,DEFAULTS,box,prepare,ensure_axis_layer
from newton.flexible import make,segment_group,segment_uid
from newton.worker import World
from scripts.flexible_demos import carrier,coloured

STEEL = (.66,.73,.78)
DARK = (.12,.18,.23)
BLUE = (.14,.34,.47)
ORANGE = (.95,.48,.09)
CHROME = (.83,.87,.9)
CRANK = .15
ROD = .85
SPEED = .65


def cylinder(name,a,b,radius,colour,sides=32,inner=0):
    delta = QVector3D(*b)-QVector3D(*a);length = delta.length();mesh = Mesh()
    def point(x,r,i):return QVector3D(x,r*math.cos(2*math.pi*i/sides),r*math.sin(2*math.pi*i/sides))
    for i in range(sides):
        j = (i+1)%sides
        for r,reverse in ((radius,False), *(([(inner,True)]) if inner else [])):
            pts = [point(0,r,i),point(0,r,j),point(length,r,j),point(length,r,i)]
            mesh.add_face(list(reversed(pts)) if reverse else pts).attrs["color"] = colour
        if inner:
            for x,reverse in ((0,True),(length,False)):
                pts = [point(x,inner,i),point(x,radius,i),point(x,radius,j),point(x,inner,j)]
                mesh.add_face(list(reversed(pts)) if reverse else pts).attrs["color"] = colour
    if not inner:
        mesh.add_face([point(0,radius,i) for i in reversed(range(sides))]).attrs["color"] = colour
        mesh.add_face([point(length,radius,i) for i in range(sides)]).attrs["color"] = colour
    for edge in mesh.edges:edge.soft = True
    group = Group(mesh,name);group.xform = QMatrix4x4();group.xform.translate(*a)
    group.xform.rotate(QQuaternion.rotationTo(QVector3D(1,0,0),delta.normalized()))
    return group


def block(name,center,size,colour):return coloured(box(name,center,size),colour)


def body(name,parts,mode="static",mass=.1,**values):
    group = Group(name=name);group.adopt(parts)
    group.ext = {KEY:dict(DEFAULTS,mode=mode,mass=mass,shape="hull",restitution=0,**values)}
    return group


def resample(points,spacing=.10):
    result = [points[0]]
    for a,b in zip(points,points[1:]):
        n = max(1,round(math.dist(a,b)/spacing))
        result.extend([[a[k]+(b[k]-a[k])*i/n for k in range(3)] for i in range(1,n+1)])
    return result


def build():
    from scripts.energy_chain import build as build_energy_chain
    scene = build_energy_chain()
    base,slider = scene.groups[:2]
    old_cable = scene.groups.pop()
    path = old_cable.ext[KEY]["flexible"]["points"]
    endpoint = path[-1];sx,_,height = endpoint
    wheel_x = sx-math.sqrt(ROD**2-CRANK**2)
    wheel_y = -.48
    rod_y = wheel_y+.105
    centre = [wheel_x,wheel_y,height]
    pin = [wheel_x,rod_y,height+CRANK]
    slider_pin = [sx,rod_y,height]
    base.mesh = box("",(-.35,-.25,.02),(4.15,2.1,.04)).mesh
    base.xform = QMatrix4x4();base.xform.translate(-.35,-.25,.02)
    for face in base.mesh.faces:face.attrs["color"] = (.20,.25,.29)
    base.name = "Machine bed"
    # The existing chain is passive. Only the motor shaft supplies power.
    slider.name = "Piston rod · Crosshead"
    slider.ext[KEY]["joint"].update(drive="free",force=0,name="Piston stroke")
    slider.adopt([
        block("Crosshead",(sx,wheel_y,height),(.16,.17,.17),BLUE),
        cylinder("Piston rod",[sx,wheel_y,height],[.32,wheel_y,height],.024,CHROME),
        block("Chain driver",(sx,-.22,height-.1),(.12,.62,.05),ORANGE),
        block("Chain mount",(sx,0,height-.055),(.14,.16,.09),BLUE),
        cylinder("Connecting rod pin",[sx,wheel_y-.10,height],[sx,rod_y+.04,height],.031,ORANGE),
    ])
    # adopt retains the old placement; parts above are already world-space.
    slider.xform = QMatrix4x4()
    slider.mesh = Mesh()
    frame = body("Cylinder and linear guide",[
        cylinder("Cylinder housing",[-.08,wheel_y,height],[.40,wheel_y,height],.065,STEEL),
        block("Front flange",(-.08,wheel_y,height),(.055,.19,.19),BLUE),
        block("Rear flange",(.40,wheel_y,height),(.055,.19,.19),BLUE),
        *[cylinder("Guide rail",[-.99,y,height-.16],[.45,y,height-.16],.017,CHROME) for y in (-.60,-.32)],
        *[block("Guide pedestal",(x,wheel_y,.32),(.15,.46,.53),DARK) for x in (-.92,.35)],
    ])
    motor = body("Electric motor",[
        cylinder("Motor housing",[wheel_x,-1.03,height],[wheel_x,-.72,height],.105,BLUE),
        cylinder("Fan cover",[wheel_x,-1.1,height],[wheel_x,-1.03,height],.112,DARK),
        *[cylinder("Cooling fin",[wheel_x,y,height],[wheel_x,y+.015,height],.117,BLUE) for y in (-1.0,-.95,-.90,-.85,-.80)],
        block("Terminal box",(wheel_x,-.87,height+.13),(.14,.15,.085),DARK),
        block("Motor foot",(wheel_x,-.86,height-.15),(.30,.43,.07),STEEL),
        block("Motor pedestal",(wheel_x,-.86,(height-.19)/2),(.34,.45,height-.19),DARK),
    ])
    shaft = body("Drive shaft",[
        cylinder("Shaft",[wheel_x,-.76,height],[wheel_x,-.39,height],.025,CHROME),
        cylinder("Coupling",[wheel_x,-.72,height],[wheel_x,-.61,height],.045,ORANGE),
        block("Feather key",(wheel_x+.026,-.65,height),(.014,.08,.014),DARK),
    ],mode="dynamic",mass=.15,joint=dict(type="hinge",drive="velocity",parent=motor.uid,
        pivot=[wheel_x,-.74,height],axis=[0,1,0],limited=False,target=SPEED,force=25,max_speed=1.2,acceleration=.4,name="Motor speed"))
    wheel_parts = [
        cylinder("Wheel rim",[wheel_x,wheel_y-.025,height],[wheel_x,wheel_y+.025,height],.18,BLUE,64,inner=.132),
        cylinder("Wheel hub",[wheel_x,wheel_y-.045,height],[wheel_x,wheel_y+.045,height],.047,STEEL),
        cylinder("Crank pin",[pin[0],wheel_y-.04,pin[2]],[pin[0],rod_y+.04,pin[2]],.028,ORANGE),
        cylinder("Pin retainer",[pin[0],rod_y+.026,pin[2]],[pin[0],rod_y+.04,pin[2]],.035,CHROME,6),
    ]
    for i in range(8):
        theta = i*math.pi/4
        p = block("Spoke",(0,0,0),(.145,.035,.023),STEEL)
        p.xform = QMatrix4x4();p.xform.translate(wheel_x,wheel_y,height);p.xform.rotate(-math.degrees(theta),0,1,0);p.xform.translate(.086,0,0)
        wheel_parts.append(p)
    wheel = body("Spoked wheel with outer crank pin",wheel_parts,mode="dynamic",mass=12,reference=shaft.uid)
    rod = body("Connecting rod bar",[
        cylinder("Connecting rod eye crank",[pin[0],rod_y-.020,pin[2]],[pin[0],rod_y+.020,pin[2]],.044,STEEL,32,inner=.029),
        cylinder("Connecting rod eye piston",[sx,rod_y-.020,height],[sx,rod_y+.020,height],.045,STEEL,32,inner=.032),
        segment_group(pin,slider_pin,.018,"Connecting rod",STEEL),
    ],mode="dynamic",mass=.16,joint=dict(type="hinge",drive="free",parent=wheel.uid,pivot=pin,axis=[0,1,0],limited=False),
        point_attachment=dict(target=slider.uid,point=slider_pin))
    socket = body("Socket with plug",[
        block("Socket housing",(-1.06,.38,.17),(.16,.16,.23),(.86,.88,.87)),
        cylinder("Socket rim",[-1.06,.30,.18],[-1.06,.28,.18],.057,DARK),
        cylinder("Power plug",[-1.06,.28,.18],[-1.06,.22,.18],.041,ORANGE),
        block("Socket holder",(-1.06,.39,.055),(.25,.24,.05),STEEL),
    ])
    # A stationary drive needs a service loop after the moving chain exit.
    inlet = resample([[-1.06,.22,.18],[-1.06,.12,.14],[-1.06,0,.14],path[0]])
    terminal = [wheel_x,-.88,height+.17]
    tail = resample([endpoint,[sx-.14,0,height],[-1.0,.12,.70],[-1.30,.38,.58],
                     [-1.62,.48,.38],[-1.96,.30,.28],[-2.08,0,.35],[-2.02,-.35,.5],
                     [-1.85,-.7,.78],[-1.63,-.90,height+.17],terminal])
    cable = make("Power cable · Socket → Drag chain → Motor",inlet+path[1:]+tail[1:],kind="cable",radius=.01,
        bend=2e5,twist=8e4,damping=.001,mass=.16,colour=ORANGE,end_reference=motor.uid)
    cable.ext[KEY]["reference"] = socket.uid
    scene.groups.extend([frame,motor,shaft,wheel,rod,socket,cable])
    # Contacts are retained in the real chain channel. Ideal bearings avoid
    # redundant solid contact constraints between their mechanism bodies.
    mechanism = [slider,frame,motor,shaft,wheel,rod]
    cable.ext[KEY]["no_collision"] = [g.uid for g in mechanism]+[socket.uid]
    chain_members = [g.uid for g in scene.groups if g.name.startswith("Link ")]
    for group in mechanism:
        group.ext[KEY]["no_collision"] = list(set(group.ext[KEY].get("no_collision",[])+[g.uid for g in mechanism if g is not group]+chain_members))
    # Small assembly details are static and do not affect the drive constraints.
    details = []
    for x in (-2.15,1.45):
        for y in (-1.12,.62):
            details.append(cylinder("Mounting screw",[x,y,.04],[x,y,.055],.025,CHROME,6))
    details.extend([block("Trim strip",(-.35,-1.26,.044),(3.65,.02,.008),ORANGE),
                    block("Nameplate",(.92,-.95,.048),(.55,.22,.012),BLUE)])
    details.append(block("Anchor · Base plate",(-.8,0,.05),(.10,.36,.02),STEEL))
    for sign in (-1,1):
        details.append(block("Anchor · Bearing cheek",(-.8,sign*.145,.09),(.07,.025,.10),DARK))
        details.append(cylinder("Anchor · Bearing pin",[-.8,sign*.10,.14],[-.8,sign*.16,.14],.012,CHROME,20))
    decoration = body("Bed · Screws and details",details,mode="ignore")
    scene.groups.append(decoration)
    ensure_axis_layer(scene).visible = False
    return scene


def validate(scene,seconds=24):
    import numpy as np
    _,specs,_ = prepare(scene);world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=False))
    shaft = next(g for g in scene.groups if g.name=="Drive shaft")
    slider = next(g for g in scene.groups if g.name.startswith("Piston rod"))
    cable = next(g for g in scene.groups if g.name.startswith("Power cable"))
    cable_points = cable.ext[KEY]["flexible"]["points"]
    start = next(i for i,p in enumerate(cable_points) if math.dist(p,[-.8,0,.14])<1e-6)
    guide_points = cable_points[start:start+23]
    initial = {uid:np.array(p[0]) for uid,p in world.poses()["poses"].items()}
    frames = [next(g for g in scene.groups if g.name in (f"Link {i+1:02d} · Base",f"Link {i+1:02d} · Frame")) for i in range(22)]
    errors = [];worst_guide = 0.
    low,high = 1.,-1.
    for i in range(round(seconds*30)):
        result = world.step(8)
        x = result["joints"][slider.uid]["position"];low,high = min(low,x),max(high,x)
        angle = result["joints"][shaft.uid]["position"]
        expected = CRANK*math.sin(angle)+math.sqrt(ROD**2-(CRANK*math.cos(angle))**2)-math.sqrt(ROD**2-CRANK**2)
        errors.append(abs(x-expected))
        if i%30==29:
            lines = []
            for k,frame in enumerate(frames):
                bid = world.bodies[frame.uid];rot = world.data.xmat[bid].reshape(3,3)
                a = world.data.xpos[bid]+rot@(np.array(guide_points[k])-initial[frame.uid])
                b = a+rot@(np.array(guide_points[k+1])-guide_points[k]);lines.append((a,b))
            for k in range(22):
                p = world.data.xipos[world.bodies[segment_uid(cable.uid,start+k)]]
                distance = min(np.linalg.norm(p-(a+np.clip(np.dot(p-a,b-a)/np.dot(b-a,b-a),0,1)*(b-a))) for a,b in lines)
                worst_guide = max(worst_guide,distance)
        if i%120==119:
            print(f"t={result['time']:.1f}s Motor={result['joints'][shaft.uid]['position']:.2f}rad Hub={x:.3f}m vmax={np.max(np.abs(world.data.qvel)):.2f} eq={np.max(np.abs(world.data.efc_pos[world.data.efc_type==0]),initial=0):.4f}",flush=True)
    print(f"Stroke range {low:.4f} … {high:.4f} m, crank deviation {max(errors):.5f} m, cable distance {worst_guide:.4f} m, bodies {world.model.nbody-1}",flush=True)
    assert max(errors)<.01,"Crank/piston linkage does not follow the geometric stroke."
    assert worst_guide<.065,"Cable escaped the carrier channel."
    if seconds>=20:
        assert angle>2*math.pi,"Motor did not complete a full revolution."
        assert high-low>.28,"Piston did not complete its stroke."
    assert world.data.time>=seconds-.01,"Simulation reset unexpectedly."
    world.close()


def main():
    path = ROOT/"models/crank-drive-energy-chain.igz"
    if "--existing" in sys.argv:
        scene = Scene();igz.load_into(scene,path)
    else:
        if path.exists():raise FileExistsError(f"Existing model kept: {path}")
        scene = build()
    validate(scene,.5 if "--existing" in sys.argv else 24)
    if "--existing" not in sys.argv:igz.save_scene(scene,path)
    print(path,flush=True)
    if "--open" not in sys.argv:return
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    app = QApplication([]);app.setOrganizationName("NewtonPreview");app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat);QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    for key,value in dict(gravity_z=-9.81,floor=False,linear_damping=0,angular_damping=0).items():QSettings().setValue("newton/"+key,value)
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    folder = ROOT/".test-state/autosave";folder.mkdir(parents=True,exist_ok=True);autosave.autosave_dir = lambda:folder
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1550,980);assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds());win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable);panel.show_controls()
    app.exec()


if __name__=="__main__":main()
