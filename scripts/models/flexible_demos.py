"""Build independent rope/cable, articulated-chain and cable-carrier exhibits."""
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from PySide6.QtGui import QMatrix4x4,QQuaternion,QVector3D
from core.scene import Scene
from formats import igz
from newton.model import box,KEY,prepare
from newton.flexible import make,segment_uid
from newton.worker import World


def coloured(group,rgb):
    for face in group.mesh.faces:face.attrs["color"] = rgb
    return group


def rope_cable():
    scene = Scene()
    scene.groups.append(coloured(box("Support",(1,0,.025),(3.2,2.3,.05),mode="static"),(.22,.25,.29)))
    for kind,y,bend,colour in (("rope",-.55,2e4,(.88,.48,.15)),("cable",.55,2e6,(.18,.49,.86))):
        title = "Rope" if kind=="rope" else "Cable"
        anchor = coloured(box(title+" · Clamp",(0,y,2),(.12,.16,.16),mode="static"),(.5,.55,.6))
        pole = box(title+" · Post",(-.08,y,1),(.1,.16,2),mode="static")
        weight = coloured(box(title+" · Weight",(2,y,2),(.14,.14,.14),mass=.04,restitution=0),colour)
        cable = make(title,[[i/12,y,2] for i in range(25)],kind=kind,bend=bend,twist=bend/2,
            damping=.003,radius=.018,mass=.22,end_reference=weight.uid,colour=colour)
        cable.ext[KEY]["reference"] = anchor.uid
        scene.groups.extend([anchor,pole,weight,cable])
    return scene


def chain():
    scene = Scene()
    anchor = box("Chain holder",(0,0,2.5),(.16,.3,.16),mode="static")
    scene.groups.extend([box("Support",(.7,0,.025),(3,1.4,.05),mode="static"),anchor])
    parent = anchor.uid
    for i in range(12):
        start = [.13*i,0,2.5]
        group = coloured(box(f"Chain link {i+1:02d}",(.13*i+.065,0,2.5),(.12,.075,.045),mass=.055,shape="hull",
            joint=dict(type="hinge",drive="free",pivot=start,axis=[0,1,0],parent=parent,limited=False)),
            (.28,.53,.69) if i%2 else (.64,.70,.74))
        scene.groups.append(group);parent = group.uid
    return scene


def carrier():
    scene = Scene()
    scene.groups.append(coloured(box("Base plate",(.2,0,.025),(3.6,1.4,.05),mode="static",friction=.3),(.25,.28,.31)))
    pitch = .12
    angles = [0.]*8+[(i+.5)*math.pi/8 for i in range(8)]+[math.pi]*6
    points = [[-.8,0,.14]]
    for angle in angles:
        x,y,z = points[-1];points.append([x+pitch*math.cos(angle),y,z+pitch*math.sin(angle)])
    end = points[-1]
    carriage = coloured(box("Carriage",(end[0],.24,end[2]),(.22,.18,.2),mass=.3,friction=.2,restitution=0,
        joint=dict(type="slide",drive="position",name="Travel",pivot=end,axis=[1,0,0],
            limited=True,lower=-.15,upper=.25,target=0,max_speed=.12,acceleration=.3,force=40)),(.91,.55,.13))
    scene.groups.append(carriage)
    links = []
    parent = None
    for i,(a,b,theta) in enumerate(zip(points,points[1:],angles)):
        frame = QMatrix4x4();frame.translate(*a);frame.rotate(-math.degrees(theta),0,1,0)
        members = []
        for part,center,size in (("Base",(pitch/2,0,-.065),(pitch*1.5,.22,.025)),
                                 ("left",(pitch/2,-.105,0),(pitch*1.5,.025,.13)),
                                 ("right",(pitch/2,.105,0),(pitch*1.5,.025,.13)),
                                 ("Web",(pitch/2,0,.065),(pitch*1.5,.22,.025))):
            group = coloured(box(f"Link {i+1:02d} · {part}",center,size,mass=.012,shape="hull",friction=.2,restitution=0),(.17,.36,.53))
            if part!="Base":
                for face in group.mesh.faces:face.attrs["opacity"] = .28
            group.xform = frame*group.xform
            if not members:
                if i==0:group.ext[KEY]["mode"] = "static"
                else:
                    delta = theta-angles[i-1]
                    group.ext[KEY]["joint"] = dict(type="hinge",drive="free",pivot=a,axis=[0,1,0],parent=parent,
                        limited=True,lower=-math.pi/6+delta,upper=delta)
                parent = group.uid
            else:
                group.ext[KEY]["reference"] = parent
                if i==0:group.ext[KEY]["mode"] = "static"
            members.append(group);scene.groups.append(group)
        links.append(members)
    links[-1][0].ext[KEY]["point_attachment"] = dict(target=carriage.uid,point=end)
    for i,members in enumerate(links):
        nearby = [g.uid for near in links[max(0,i-1):i+2] for g in near]
        for group in members:group.ext[KEY]["no_collision"] = [uid for uid in nearby if uid!=group.uid]
    cable = make("Cable in the drag chain",points,kind="cable",radius=.012,bend=5e5,twist=2e5,
        damping=.001,mass=.08,end_reference=carriage.uid,colour=(.94,.55,.12))
    cable.ext[KEY]["reference"] = links[0][0].uid
    scene.groups.append(cable)
    return scene


BUILDERS = {"rope":("rope-and-cable",rope_cable),"chain":("joint-chain",chain),"carrier":("drag-chain-with-cable",carrier)}


def main():
    kind = next((s for s in sys.argv[1:] if s in BUILDERS),"rope")
    filename,builder = BUILDERS[kind];path = ROOT/"models"/(filename+".igz")
    if "--existing" in sys.argv:
        scene = Scene();igz.load_into(scene,path)
    else:
        if path.exists():raise FileExistsError(f"Existing model kept: {path}")
        scene = builder();igz.save_scene(scene,path)
    _,specs,_ = prepare(scene);world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=False))
    for _ in range(15):world.step(8)
    print(f"Checked: {filename}, {world.model.nbody-1} bodies, {world.model.nplugin} cable models.",flush=True);world.close()
    print(path,flush=True)
    if "--open" not in sys.argv:return
    from PySide6.QtCore import QSettings,QTimer
    from PySide6.QtWidgets import QApplication,QScrollArea
    app = QApplication([]);app.setOrganizationName("NewtonPreview");app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat);QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    st = QSettings()
    for key,value in dict(gravity_z=-9.81,floor=False,linear_damping=0,angular_damping=0).items():st.setValue("newton/"+key,value)
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    folder = ROOT/".test-state/autosave";folder.mkdir(parents=True,exist_ok=True);autosave.autosave_dir = lambda:folder
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1400,950);assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds());win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable)
    selected = next((g for g in win.viewport.scene.groups if (g.ext or {}).get(KEY,{}).get("flexible")),win.viewport.scene.groups[-1])
    win.viewport.scene.select([selected]);win.viewport.notify_scene_changed();panel.show_sidebar();panel.advanced_toggle.setChecked(True)
    QTimer.singleShot(500,lambda:panel.findChild(QScrollArea).ensureWidgetVisible(panel.flexible_section))
    if kind=="carrier":panel.show_controls()
    app.exec()


if __name__=="__main__":main()
