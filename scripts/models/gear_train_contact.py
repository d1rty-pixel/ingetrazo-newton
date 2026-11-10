"""Rebuild the gear train carousel so its gears drive each other through tooth contacts.

The original model (commit d14a6de) moved every shaft through axis couplings, and its gears only looked
as if they meshed. Here every toothed part becomes a body of child groups: the gear blank as one disc
(with the original lightening holes) and every tooth, ring segment or worm thread slice as its own convex
child, so the collision shape "Child components" gives MuJoCo one convex shape per tooth. The motor stays
on the crank; every other shaft of the drive (pinion, ring gear, carousel) becomes a free axis that only
its teeth drive. Hubs, shafts, the crank and the carousel keep their original geometry. The model's
contact solver is PGS (document data).

The worm is the exception: it keeps its axis coupling and does not collide with the worm wheel. Driven
backwards by the wheel, a worm with an 11° lead angle locks at a friction of 0.3, as a real one would;
at 0.05 it turned but the crank reached only half its speed, and even driven by its own motor the
segmented thread at 12 turns per second ran rough (±17 % speed ripple at 15 rad/s). Its thread and the
wheel, which is cut by that thread (hobbed), are still modelled so they visibly mesh.

Tooth phases are not computed by hand: for every meshing pair the follower is turned at the exact ratio
and the phase with the largest clearance is kept, which also settles the direction of rotation. The
result is compared with the ratios of the original couplings.

python scripts/models/gear_train_contact.py            # build and measure
python scripts/models/gear_train_contact.py --write    # replace models/gear-train-carousel.igz
"""
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
import numpy as np
from PySide6.QtGui import QVector3D
from core.mesh import Mesh
from core.group import Group
from core.scene import Scene
from formats import igz
from newton.model import KEY,prepare
from newton.worker import World

PATH = ROOT/"models/gear-train-carousel.igz"
SOURCE = "d14a6de"            # the coupled original
MODULE = .02
ALPHA = math.radians(20)
BACKLASH = .001               # along the pitch circle, per meshing pair
EMBED = .004                  # teeth reach this far into their blank, so the two overlap
BEVEL_FACE = .085             # bevel face width along the cone
WORM_RADIUS = .05
WORM_SLICE = math.radians(30)
BEVEL_TEETH = (36,11)        # ring gear shaft : carousel shaft, 3.27:1 (the original pair was 20:20)
CRANK_SPEED = math.radians(-15)  # the crank motor's start target, shown as −15 °/s (one turn in 24 s)


def involute(angle):
    return math.tan(angle)-angle


def tooth_half(radius,pitch,base,backlash=BACKLASH):
    """Half angle of an external involute tooth at ``radius``; below the base circle the flank is radial."""
    half = (math.pi*MODULE/2-backlash/2)/(2*pitch)+involute(ALPHA)
    return half-(involute(math.acos(base/radius)) if radius>base else 0)


def external_outline(pitch,steps=6):
    """One tooth centred on angle 0 as (radius, angle), counter-clockwise."""
    base = pitch*math.cos(ALPHA);tip,root = pitch+MODULE,pitch-1.25*MODULE
    start = max(root,base)
    radii = [root-EMBED]+([root] if root<base else [])+[start+(tip-start)*i/steps for i in range(steps+1)]
    return [(r,-tooth_half(r,pitch,base)) for r in radii]+[(r,tooth_half(r,pitch,base)) for r in reversed(radii)]


def internal_outlines(pitch,teeth,steps=4):
    """One internal tooth centred on angle 0, in two radial pieces: its flanks are concave, so one convex
    hull over the whole tooth would fill part of the tooth space."""
    # The tip is shortened by a fifth of the module, as usual for internal gears: the pinion's tip
    # corners would otherwise graze the internal teeth's tips.
    base = pitch*math.cos(ALPHA);tip,root = pitch-.8*MODULE,pitch+1.25*MODULE
    def half(r):
        space = (math.pi*MODULE/2+BACKLASH/2)/(2*pitch)+involute(ALPHA)-(involute(math.acos(base/r)) if r>base else 0)
        return math.pi/teeth-space
    middle = (tip+root)/2
    pieces = []
    for low,high in ((tip,middle),(middle,root+EMBED)):
        radii = [low+(high-low)*i/steps for i in range(steps+1)]
        pieces.append([(r,half(r)) for r in radii]+[(r,-half(r)) for r in reversed(radii)])
    return pieces


class Axis:
    """Cylindrical coordinates (radius, angle counter-clockwise about the axis, height along it)."""

    def __init__(self,pivot,axis):
        a = np.array(axis,float);a /= np.linalg.norm(a)
        ref = np.array([0.,0.,1.]) if abs(a[2])<.9 else np.array([1.,0.,0.])
        u = ref-a*(ref@a);u /= np.linalg.norm(u)
        self.p,self.a,self.u,self.v = np.array(pivot,float),a,u,np.cross(a,u)

    def point(self,r,angle,h):
        return self.p+self.a*h+r*(math.cos(angle)*self.u+math.sin(angle)*self.v)

    def local(self,point):
        d = np.array(point,float)-self.p;h = float(d@self.a);x,y = float(d@self.u),float(d@self.v)
        return math.hypot(x,y),math.atan2(y,x),h


def vec(p):
    return QVector3D(float(p[0]),float(p[1]),float(p[2]))


def key(p):
    return tuple(round(float(c),6) for c in p)


def finish(mesh,hard,colour):
    """Colour every face; only edges whose both ends lie on one cap stay hard (the outline of a tooth)."""
    for face in mesh.faces:face.attrs["color"] = colour
    for edge in mesh.edges:
        a,b = key(edge.v0.position.toTuple()),key(edge.v1.position.toTuple())
        edge.soft = not any(a in cap and b in cap for cap in hard)
    return mesh


def loft(name,sections,colour,closed=True):
    """A solid through cross-sections of equal size (each a loop of 3D points); caps at both ends."""
    mesh = Mesh()
    first,last = sections[0],sections[-1]
    mesh.add_face([vec(p) for p in reversed(first)])
    mesh.add_face([vec(p) for p in last])
    for s,t in zip(sections,sections[1:]):
        n = len(s)
        for i in range(n if closed else n-1):
            j = (i+1)%n
            quad = [s[i],s[j],t[j],t[i]]
            normal = np.cross(np.subtract(quad[1],quad[0]),np.subtract(quad[3],quad[0]))
            planar = abs(float(np.dot(normal/ (np.linalg.norm(normal) or 1),np.subtract(quad[2],quad[0]))))<1e-7
            if planar:mesh.add_face([vec(p) for p in quad])
            else:
                mesh.add_face([vec(quad[0]),vec(quad[1]),vec(quad[2])]);mesh.add_face([vec(quad[0]),vec(quad[2]),vec(quad[3])])
    group = Group(finish(mesh,[{key(p) for p in first},{key(p) for p in last}],colour),name)
    return group


def prism(name,frame,outline,h0,h1,colour,twist=0.,phase=0.):
    """An outline given as (radius, angle) swept along the axis from h0 to h1; ``twist`` turns it per metre
    (helical teeth). The loop must run counter-clockwise about the axis."""
    middle = (h0+h1)/2
    section = lambda h:[frame.point(r,phase+a+twist*(h-middle),h) for r,a in outline]
    return loft(name,[section(h0),section(h1)],colour)


def disc(name,frame,radius,h0,h1,colour,holes=(),sides=96):
    """The gear blank: a disc with the original lightening holes (loops of (radius, angle))."""
    mesh = Mesh()
    ring = lambda h:[frame.point(radius,2*math.pi*i/sides,h) for i in range(sides)]
    hole = lambda loop,h:[frame.point(r,a,h) for r,a in loop]
    mesh.add_face([vec(p) for p in reversed(ring(h0))],[[vec(p) for p in hole(l,h0)] for l in holes])
    mesh.add_face([vec(p) for p in ring(h1)],[[vec(p) for p in reversed(hole(l,h1))] for l in holes])
    for loop,outward in [(ring(h0),True)]+[(hole(l,h0),False) for l in holes]:
        top = [p+frame.a*(h1-h0) for p in loop]
        for i in range(len(loop)):
            j = (i+1)%len(loop)
            quad = [loop[i],loop[j],top[j],top[i]] if outward else [loop[j],loop[i],top[i],top[j]]
            mesh.add_face([vec(p) for p in quad])
    caps = [{key(p) for p in ring(h)}|{key(p) for l in holes for p in hole(l,h)} for h in (h0,h1)]
    return Group(finish(mesh,caps,colour),name)


# ---- the gears --------------------------------------------------------------------------------------

def spur(prefix,frame,teeth,h0,h1,colour,phase,twist=0.):
    pitch = MODULE*teeth/2;outline = external_outline(pitch)
    return [prism(f"{prefix} tooth {i+1:02d}",frame,outline,h0,h1,colour,twist,phase+2*math.pi*i/teeth) for i in range(teeth)]


def ring_gear(prefix,frame,teeth,h0,h1,outer,colour,phase):
    pitch = MODULE*teeth/2;parts = []
    for i in range(teeth):
        for k,piece in enumerate(internal_outlines(pitch,teeth)):
            parts.append(prism(f"{prefix} tooth {i+1:02d}{'ab'[k]}",frame,piece,h0,h1,colour,phase=phase+2*math.pi*i/teeth))
    # The rim is an annulus, never convex as a whole: one segment per tooth pitch.
    inner,step = pitch+1.25*MODULE,2*math.pi/teeth
    for i in range(teeth):
        a0 = phase+step*(i+.5)
        arc = [a0+step*k/3 for k in range(4)]
        outline = [(outer,a) for a in arc]+[(inner,a) for a in reversed(arc)]
        parts.append(prism(f"{prefix} rim {i+1:02d}",frame,outline,h0,h1,colour))
    return parts


def bevel(prefix,frame,teeth,other,apex,direction,colour,phase,steps=5):
    """Teeth on the pitch cone of a bevel pair at 90° with ``other`` teeth on the partner (Tredgold's
    back-cone approximation) and the blank on the root cone. ``apex`` is the cone tip's height on the
    axis, ``direction`` +1/-1 the side the gear lies on. Returns the parts and the height of the back."""
    pitch = MODULE*teeth/2;delta = math.atan2(teeth,other)
    cone = pitch/math.sin(delta);scale = (cone-BEVEL_FACE)/cone
    virtual = cone*math.tan(delta);level = apex+direction*cone*math.cos(delta)
    apex_point = frame.point(0,0,apex)
    back = frame.point(0,0,apex+direction*cone/math.cos(delta))
    outline = external_outline(virtual,steps)
    def outer(angle):
        pitch_point = frame.point(pitch,angle,level)
        e = (pitch_point-back)/np.linalg.norm(pitch_point-back)
        t = np.cross(frame.a,(pitch_point-frame.point(0,0,level))/pitch)
        return lambda r,a:back+r*(math.cos(a)*e+math.sin(a)*t)
    inward = lambda p:apex_point+scale*(p-apex_point)
    parts = []
    for i in range(teeth):
        angle = phase+2*math.pi*i/teeth;place = outer(angle)
        ring = [place(r,a) for r,a in outline]
        # Counter-clockwise about the axis seen from the back: reverse when the gear lies below its apex.
        ring = ring if direction<0 else ring[::-1]
        parts.append(loft(f"{prefix} tooth {i+1:02d}",[ring,[inward(p) for p in ring]],colour))
    root = virtual-1.25*MODULE-EMBED
    circle = [outer(2*math.pi*k/60)(root,0) for k in range(60)]
    circle = circle if direction<0 else circle[::-1]
    parts.append(loft(f"{prefix} blank",[circle,[inward(p) for p in circle]],colour))
    return parts,frame.local(circle[0])[2]


def thread_half(r):
    """Half the worm thread's axial thickness at radius ``r`` (a number or an array): a rack with straight 20° flanks."""
    return (math.pi*MODULE/2-BACKLASH)/2-(r-WORM_RADIUS)*math.tan(ALPHA)


def hobbed_wheel(prefix,frame,teeth,h0,h1,colour,worm_phase,slices=6,radii=12,turn=.35,samples=700):
    """Worm wheel teeth cut by the worm itself: in planes across the face width the worm's thread section
    rolls past the wheel at the exact ratio, and each tooth fills what the thread leaves between two
    gaps. A plain helical tooth fits a cylindrical worm only in the middle plane (6–8 mm interference at
    the faces); this is how a hob shapes real worm wheels. The worm lies below the wheel (angle π), its
    axis along the frame's v direction."""
    lead = math.pi*MODULE;pitch = MODULE*teeth/2;distance = pitch+WORM_RADIUS;step = 2*math.pi/teeth
    root,tip = WORM_RADIUS-1.25*MODULE-EMBED,WORM_RADIUS+MODULE
    rings = np.linspace(pitch-1.25*MODULE-EMBED,pitch+MODULE,radii)
    thetas = np.linspace(-turn,turn,samples)
    def profile(h):
        # Outline of the thread section in the plane at height h: flanks, tip and root edges.
        lo,hi = math.sqrt(max(root**2-h**2,0)),math.sqrt(tip**2-h**2)
        z = np.linspace(lo,hi,60);rho = np.hypot(h,z)
        centre = lead*(np.arctan2(-h,z)-worm_phase)/(2*math.pi)
        edge = np.concatenate([centre-thread_half(rho),centre+thread_half(rho)])
        height = np.concatenate([z,z])
        for zz,i in ((lo,0),(hi,-1)):
            across = np.linspace(edge[i],edge[60+i],20)
            edge,height = np.concatenate([edge,across]),np.concatenate([height,np.full(20,zz)])
        # Roll: the wheel turns θ, the worm 2π·pitch/lead·θ, so the thread moves by -pitch·θ.
        v = edge[None,:]-pitch*thetas[:,None];u = -distance+height[None,:]+0*v
        r = np.hypot(u,v).ravel();angle = (np.arctan2(v,u)-thetas[:,None]).ravel()
        d = (angle-math.pi+math.pi)%(2*math.pi)-math.pi
        near = np.abs(d)<step/2
        r,d = r[near],d[near]
        left,right = [],[]
        width = (rings[1]-rings[0])*.75
        for ring in rings:
            sel = np.abs(r-ring)<width
            left.append(d[sel].max() if sel.any() else None);right.append((-d[sel]).max() if sel.any() else None)
        # Where the thread never reaches (deep in the root) the gap keeps its deepest width.
        for side in (left,right):
            known = [i for i,x in enumerate(side) if x is not None]
            for i in range(len(side)):
                if side[i] is None:side[i] = side[min(known,key=lambda k:abs(k-i))]
        return [(ring,math.pi+l) for ring,l in zip(rings,left)]+[(ring,math.pi+step-g) for ring,g in reversed(list(zip(rings,right)))]
    heights = np.linspace(h0,h1,slices+1)
    outlines = [profile(h) for h in heights]
    parts = []
    for i in range(teeth):
        for k in range(slices):
            ends = [[frame.point(r,a+i*step,h) for r,a in outlines[j]] for j,h in ((k,heights[k]),(k+1,heights[k+1]))]
            parts.append(loft(f"{prefix} tooth {i+1:02d}{'abcdefgh'[k]}",ends,colour))
    return parts


def worm_thread(frame,h0,h1,colour,phase,sections=3):
    """A right-handed single-start worm as slices along its helix; the axial section is a rack with
    straight 20° flanks. Slices whose section would leave the worm's length are left out."""
    lead = math.pi*MODULE
    root,tip = WORM_RADIUS-1.25*MODULE-EMBED,WORM_RADIUS+MODULE
    half = thread_half
    corners = [(root,-half(root)),(tip,-half(tip)),(tip,half(tip)),(root,half(root))]
    def section(psi):
        centre = lead*(psi-phase)/(2*math.pi)
        return [frame.point(r,psi,centre+dx) for r,dx in corners]
    parts = [];psi = phase+2*math.pi*math.floor((h0-lead)/lead)
    while lead*(psi-phase)/(2*math.pi)<h1+lead:
        ends = [psi+WORM_SLICE*k/(sections-1) for k in range(sections)]
        centres = [lead*(p-phase)/(2*math.pi) for p in ends]
        if min(centres)-half(root)>=h0 and max(centres)+half(root)<=h1:
            parts.append(loft(f"Worm thread {len(parts)+1:03d}",[section(p) for p in ends],colour))
        psi += WORM_SLICE
    return parts


# ---- splitting the original bodies ------------------------------------------------------------------

def shells(mesh):
    """The faces of each closed part; hole loops join their face's part."""
    faces = list(mesh.faces);parent = {}
    def find(a):
        parent.setdefault(a,a)
        while parent[a]!=a:parent[a] = parent[parent[a]];a = parent[a]
        return a
    for face in faces:
        keys = [key(v.toTuple()) for v in face.vertices]+[key(v.toTuple()) for h in face.holes for v in h]
        for k in keys[1:]:parent[find(k)] = find(keys[0])
    found = {}
    for face in faces:found.setdefault(find(key(face.vertices[0].toTuple())),[]).append(face)
    return list(found.values())


def copy(name,faces,soft):
    mesh = Mesh()
    for face in faces:
        new = mesh.add_face([QVector3D(v) for v in face.vertices],[[QVector3D(v) for v in h] for h in face.holes] or None)
        new.attrs.update(face.attrs)
    for edge in mesh.edges:
        edge.soft = frozenset((key(edge.v0.position.toTuple()),key(edge.v1.position.toTuple()))) in soft
    return Group(mesh,name)


def colour_of(faces):
    return faces[0].attrs.get("color",(.6,.6,.6,1.))


def holes_of(faces,frame,h):
    """The hole loops of the original face at height ``h``, as (radius, angle)."""
    face = next(f for f in faces if f.holes and abs(frame.local(f.vertices[0].toTuple())[2]-h)<1e-4)
    return [[frame.local(v.toTuple())[:2] for v in loop] for loop in face.holes]


def extent(faces,frame):
    pts = [frame.local(v.toTuple()) for f in faces for v in f.vertices]
    rs,hs = [p[0] for p in pts],[p[2] for p in pts]
    return min(rs),max(rs),min(hs),max(hs)


class Body:
    """One original body: its toothed parts are replaced, every other part is kept as a child."""

    def __init__(self,group):
        self.group = group
        joint = group.ext[KEY]["joint"]
        self.frame = Axis(joint["pivot"],joint["axis"])
        self.parts = shells(group.mesh)
        self.soft = {frozenset((key(e.v0.position.toTuple()),key(e.v1.position.toTuple()))) for e in group.mesh.edges if e.soft}

    def take(self,radial_max,tolerance=.002):
        """Remove and return the part whose outer radius is ``radial_max`` (a toothed part)."""
        found = [p for p in self.parts if abs(extent(p,self.frame)[1]-radial_max)<tolerance and len(p)>20]
        if len(found)!=1:raise ValueError(f"{self.group.name}: {len(found)} parts with radius {radial_max}")
        self.parts.remove(found[0])
        return found[0]

    def rebuild(self,generated,merged=None,merge_from=None,coupled=False):
        """Every kept part becomes its own child: a common hull can reach a partner (the worm's core and
        coupling make a cone that hits the wheel's tips). ``merged`` names one child for the parts from
        height ``merge_from`` on: the carousel above its platform, whose flat pennants MuJoCo cannot hull
        on their own; below it hub and shaft stay apart, or their hull with the platform would swallow
        the large bevel gear."""
        high = [p for p in self.parts if merged and extent(p,self.frame)[2]>=merge_from]
        kept = [copy(f"Part {i+1:02d}",faces,self.soft) for i,faces in enumerate(p for p in self.parts if p not in high)]
        if high:kept.append(copy(merged,[f for faces in high for f in faces],self.soft))
        children = kept+generated
        for child in children:child.layer = self.group.layer
        self.group.mesh = Mesh()
        self.group.adopt(children)
        cfg = self.group.ext[KEY]
        cfg["shape"] = "compound"
        joint = cfg["joint"]
        if joint.get("coupling") and not coupled:
            joint.pop("coupling")
            joint.update(drive="free",force=0.)
        return len(children)


def load_source():
    data = subprocess.run(["git","-C",str(ROOT),"show",f"{SOURCE}:models/gear-train-carousel.igz"],
                          capture_output=True,check=True).stdout
    with tempfile.NamedTemporaryFile(suffix=".igz",delete=False) as handle:
        handle.write(data)
    scene = Scene();igz.load_into(scene,Path(handle.name));Path(handle.name).unlink()
    return scene


def named(scene,name):
    return next(g for g in scene.groups if g.name==name)


def build(scene,phase,worm_hull=True):
    """Rebuild every gear body with the given tooth phases; returns the bodies by role."""
    crank,pinion,ring,carousel,worm = (named(scene,n) for n in
        ("Worm wheel + spur gear","Pinion","Ring gear + bevel gear","Bevel gear + carousel","Worm"))
    # Spur gear 40 and worm wheel 30 on the crank shaft.
    body = Body(crank);f = body.frame
    spur_faces,wheel_faces = body.take(.42),body.take(.32)
    _,_,s0,s1 = extent(spur_faces,f);_,_,w0,w1 = extent(wheel_faces,f)
    parts = [disc("Spur gear 40 blank",f,.375,s0,s1,colour_of(spur_faces),holes_of(spur_faces,f,s1)),
             disc("Worm wheel 30 blank",f,.275,w0,w1,colour_of(wheel_faces),holes_of(wheel_faces,f,w1))]
    parts += spur("Spur gear 40",f,40,s0,s1,colour_of(spur_faces),phase["spur"])
    parts += hobbed_wheel("Worm wheel 30",f,30,w0,w1,colour_of(wheel_faces),phase["worm"])
    counts = {crank.name:body.rebuild(parts)}
    # Long pinion 16: meshes with the spur gear and inside the ring gear.
    body = Body(pinion);f = body.frame;faces = body.take(.18)
    _,_,p0,p1 = extent(faces,f)
    counts[pinion.name] = body.rebuild([disc("Pinion 16 blank",f,.135,p0,p1,colour_of(faces))]+
                                       spur("Pinion 16",f,16,p0,p1,colour_of(faces),phase["pinion"]))
    # Ring gear 48 (internal) with its web, and bevel gear 20 on the same shaft.
    body = Body(ring);f = body.frame
    ring_faces = body.take(.54);bevel_faces = body.take(.22)
    web = [fc for fc in ring_faces if extent([fc],f)[2]>=-.165-1e-4]
    _,_,r0,_ = extent(ring_faces,f)
    parts = [disc("Ring gear web",f,.54,-.165,-.145,colour_of(web),holes_of(ring_faces,f,-.145))]
    parts += ring_gear("Ring gear 48",f,48,r0,-.165,.54,colour_of(ring_faces),phase["ring"])
    # The two bevel axes cross at y 1.3, z 1.29. With 36:11 instead of the original 20:20 the large
    # gear moves towards the apex; a spacer joins it to the hub at the end of the ring gear's shaft.
    apex = 1.3-.8;big,small = BEVEL_TEETH
    gear,back = bevel(f"Bevel gear {big}",f,big,small,apex,-1,colour_of(bevel_faces),phase["ring_bevel"])
    parts += gear
    if back>.30:parts.append(disc("Bevel gear spacer",f,.06,.30,back+.005,colour_of(bevel_faces),sides=32))
    counts[ring.name] = body.rebuild(parts)
    body = Body(carousel);f = body.frame;faces = body.take(.22)
    gear,_ = bevel(f"Carousel bevel gear {small}",f,small,big,1.29-1.49,1,colour_of(faces),phase["carousel"])
    counts[carousel.name] = body.rebuild(gear,"Carousel",merge_from=.49)
    # The worm: thread slices on its own core (kept).
    body = Body(worm);f = body.frame;faces = body.take(.07)
    _,_,h0,h1 = extent(faces,f)
    # The worm keeps its axis coupling (see the module text) and collides as one hull with nothing.
    counts[worm.name] = body.rebuild(worm_thread(f,h0,h1,colour_of(faces),phase["worm"]),coupled=True)
    if worm_hull:worm.ext[KEY]["shape"] = "hull"
    return dict(crank=crank,pinion=pinion,ring=ring,carousel=carousel,worm=worm),counts


# ---- checks -----------------------------------------------------------------------------------------

def world_of(scene,groups):
    everything = list(scene.groups)
    frame = named(scene,"Frame")
    scene.groups[:] = [frame]+list(groups)
    try:
        _,specs,_ = prepare(scene,require_movable=False)
    finally:
        scene.groups[:] = everything
    for spec in specs:spec["no_collision"] = []
    world = World();world.load(dict(bodies=specs,gravity=0,floor=False,solver="pgs"))
    return world


def clearance_search(scene,driver,follower,teeth_driver,teeth_follower,signs=(1,-1),samples=48,turns=10):
    """Turn the driver over one tooth pitch at ratio ±zd/zf and the follower at every phase offset; the
    offset and sign with the largest smallest distance between the two bodies."""
    import mujoco
    world = world_of(scene,[driver,follower]);m,d = world.model,world.data
    m.geom_margin[:] = .02
    joint = lambda g:m.joint(int(m.body_jntadr[world.bodies[g.uid]]))
    qa,qb = joint(driver).qposadr[0],joint(follower).qposadr[0]
    ba,bb = world.bodies[driver.uid],world.bodies[follower.uid]
    best = (-1.,0.,0)
    for sign in signs:
        ratio = sign*teeth_driver/teeth_follower
        for k in range(samples):
            offset = 2*math.pi/teeth_follower*k/samples;worst = .02
            for step in range(turns):
                alpha = 2*math.pi/teeth_driver*step/turns
                d.qpos[qa],d.qpos[qb] = alpha,offset+ratio*alpha
                mujoco.mj_forward(m,d)
                for c in d.contact[:d.ncon]:
                    pair = {int(m.geom_bodyid[c.geom1]),int(m.geom_bodyid[c.geom2])}
                    if pair=={ba,bb}:worst = min(worst,float(c.dist))
            if worst>best[0]:best = (worst,offset,sign)
    world.close()
    return best


def measure(scene,bodies,seconds=12.):
    _,specs,_ = prepare(scene)
    world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=True,solver="pgs"))
    m,d = world.model,world.data
    dof = {k:m.joint(int(m.body_jntadr[world.bodies[g.uid]])).dofadr[0] for k,g in bodies.items()}
    names = {bid:next(g.name for g in scene.groups if g.uid==uid) for uid,bid in world.bodies.items()}
    speeds = {k:[] for k in dof};pairs = {};depth = 0.;started = time.perf_counter()
    try:
        while d.time<seconds:
            world.step(8)
            if d.time>3:
                for k,i in dof.items():speeds[k].append(float(d.qvel[i]))
                for c in d.contact[:d.ncon]:
                    pair = tuple(sorted(names.get(int(m.geom_bodyid[g]),"world") for g in (c.geom1,c.geom2)))
                    pairs[pair] = pairs.get(pair,0)+1;depth = max(depth,-float(c.dist))
    except ValueError as error:
        return dict(failed=f"{error} at {d.time:.2f} s")
    finally:
        wall = time.perf_counter()-started;world.close()
    return dict(speeds={k:(round(float(np.mean(v)),3),round(float(np.std(v)),3)) for k,v in speeds.items()},
                contact_pairs=pairs,max_penetration_mm=round(depth*1000,2),realtime=round(seconds/wall,1))


def main():
    phase = dict(spur=0.,pinion=0.,ring=0.,ring_bevel=0.,carousel=0.,worm=0.)
    found = {}
    # Each pair on a fresh copy of the original, the driver's phase fixed by the pairs before it.
    for name,(driver,follower,zd,zf,key_name) in {
            "spur 40 → pinion 16":("crank","pinion",40,16,"pinion"),
            "pinion 16 → ring gear 48":("pinion","ring",16,48,"ring"),
            f"bevel {BEVEL_TEETH[0]} → carousel bevel {BEVEL_TEETH[1]}":("ring","carousel",*BEVEL_TEETH,"carousel")}.items():
        scene = load_source();bodies,_ = build(scene,phase)
        clearance,offset,sign = clearance_search(scene,bodies[driver],bodies[follower],zd,zf)
        phase[key_name] += offset;found[name] = (sign,clearance)
        print(f"{name}: ratio {sign*zd/zf:+.3f}, phase {math.degrees(offset):.2f}°, smallest clearance {clearance*1000:.2f} mm",flush=True)
    # The wheel is cut by the worm, so their phases agree by construction; the search only confirms that
    # they visibly mesh (the worm itself turns through its coupling), so its thread collides here.
    scene = load_source();bodies,_ = build(scene,phase,worm_hull=False)
    clearance,offset,sign = clearance_search(scene,bodies["crank"],bodies["worm"],30,1,signs=(1,),samples=36,turns=6)
    print(f"worm wheel 30 → worm: ratio {sign*30:+.0f}, best worm phase {math.degrees(offset):.0f}°, smallest clearance {clearance*1000:.2f} mm",flush=True)
    scene = load_source();bodies,counts = build(scene,phase)
    print("children per body:",counts,flush=True)
    for group in scene.groups:
        cfg = (group.ext or {}).get(KEY)
        if cfg and "no_collision" in cfg:
            cfg["no_collision"] = []
    # The man stands where the crank shaft and its bearing pass; nothing else overlaps.
    man,crank = named(scene,"Man"),bodies["crank"]
    worm = bodies["worm"]
    man.ext[KEY]["no_collision"] = [crank.uid];worm.ext[KEY]["no_collision"] = [crank.uid]
    crank.ext[KEY]["no_collision"] = [man.uid,worm.uid]
    scene.plugin_data["newton"] = dict(scene.plugin_data.get("newton") or {},solver="pgs")
    # The original −2.5 rad/s turned the worm at 12 turns per second; this pace is calmer to watch and
    # keeps the simulation rate steady. The motor's speed limit stays, so the control can go faster.
    crank.ext[KEY]["joint"]["target"] = CRANK_SPEED
    report = measure(scene,{k:bodies[k] for k in ("crank","pinion","ring","carousel","worm")})
    print(report,flush=True)
    if "--write" in sys.argv:
        igz.save_scene(scene,PATH);print(PATH)


if __name__=="__main__":
    main()
