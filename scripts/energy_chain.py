"""Open ladder-style energy chain: two side links, crossbars and hinge bosses."""
import math
from PySide6.QtGui import QVector3D,QMatrix4x4
from core.mesh import Mesh
from core.group import Group
from newton.model import KEY,DEFAULTS
from newton.flexible import make
from scripts.flexible_demos import carrier,coloured


def side_link(pitch,y,sign):
    from scripts.crank_carrier import cylinder
    radius = .045;thickness = .010;mesh = Mesh()
    outline = []
    for x,base in ((pitch,-math.pi/2),(0,math.pi/2)):
        for i in range(13):
            angle = base+math.pi*i/12
            outline.append((x+radius*math.cos(angle),radius*math.sin(angle)))
    rings = [[QVector3D(x,y+offset,z) for x,z in outline] for offset in (-thickness/2,thickness/2)]
    for points in (rings[0],list(reversed(rings[1]))):mesh.add_face(points).attrs["color"] = (.13,.19,.23)
    for i in range(len(outline)):
        j = (i+1)%len(outline)
        mesh.add_face([rings[0][i],rings[1][i],rings[1][j],rings[0][j]]).attrs["color"] = (.13,.19,.23)
    for edge in mesh.edges:edge.soft = True
    plate = Group(mesh,"Seitenlasche")
    pins = [cylinder("Gelenkbund",[x,y+sign*.005,0],[x,y+sign*.010,0],.015,(.50,.57,.61),20) for x in (0,pitch)]
    group = Group(name="Seitenlasche mit Gelenkbünden");group.adopt([plate,*pins])
    return group


def build():
    from newton.model import box
    scene = carrier();old_cable = scene.groups[-1]
    points = old_cable.ext[KEY]["flexible"]["points"]
    scene.groups = scene.groups[:2];carriage = scene.groups[1]
    parent = None;links = []
    for i,(a,b) in enumerate(zip(points,points[1:])):
        dx,dz = b[0]-a[0],b[2]-a[2];pitch = math.hypot(dx,dz);theta = math.atan2(dz,dx)
        stagger = .006 if i%2 else -.006
        parts = [side_link(pitch,-(.1+stagger),-1),side_link(pitch,.1+stagger,1)]
        for name,z in (("Unterer Quersteg",-.05),("Oberer Quersteg",.05)):
            parts.append(coloured(box(name,(pitch/2,0,z),(.024,.19,.012)),(.24,.31,.35)))
        link = Group(name=f"Glied {i+1:02d} · Rahmen");link.adopt(parts)
        link.xform = QMatrix4x4();link.xform.translate(*a);link.xform.rotate(-math.degrees(theta),0,1,0)
        link.ext = {KEY:dict(DEFAULTS,mode="static" if i==0 else "dynamic",mass=.048,
            shape="compound",friction=.2,restitution=0)}
        if i:
            previous = math.atan2(points[i][2]-points[i-1][2],points[i][0]-points[i-1][0])
            delta = theta-previous
            link.ext[KEY]["joint"] = dict(type="hinge",drive="free",pivot=a,axis=[0,1,0],parent=parent,
                limited=True,lower=-math.pi/6+delta,upper=delta)
        parent = link.uid;links.append(link);scene.groups.append(link)
    links[-1].ext[KEY]["point_attachment"] = dict(target=carriage.uid,point=points[-1])
    cable = make("Kabel in der Schleppkette",points,kind="cable",radius=.012,bend=5e5,twist=2e5,
        damping=.001,mass=.08,end_reference=carriage.uid,colour=(.94,.55,.12))
    cable.ext[KEY]["reference"] = links[0].uid;scene.groups.append(cable)
    return scene
