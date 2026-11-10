"""Coloured rims around bodies: the body a pick would take, and the bodies linked to the selection."""
import math
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QColor,QPen,QPainter,QPolygonF
from .model import KEY,settings,reference_id,axes_visible

# Large meshes are thinned so a hover stays fluid; the outline only needs the extreme points.
MAX_POINTS = 4000
_points = {}


# Rim colour per kind of link, in drawing order (axis_guides.COLOURS).
KINDS = {"connection":"connected","reference":"actual","exemption":"exemption"}


def links(group,kind="reference"):
    """Uids this body points to by kind: reference body and coupling leader, connection target and
    rope end, or collision exemptions."""
    if KEY not in (group.ext or {}):
        return set()
    cfg = settings(group)
    found = {"reference":{reference_id(group),((cfg.get("joint") or {}).get("coupling") or {}).get("master")},
             "connection":{(cfg.get("point_attachment") or {}).get("target"),(cfg.get("flexible") or {}).get("end_reference")},
             "exemption":set(cfg.get("no_collision",[]))}[kind]
    return found-{None,group.uid}


def linked(scene,selection,kind="reference"):
    """Bodies linked to the selection in either direction by one kind of link, without the selection itself."""
    chosen = {g.uid for g in selection}
    found = set()
    for group in scene.groups:
        own = links(group,kind)
        if group.uid in chosen:found |= own
        elif own & chosen:found.add(group.uid)
    hidden = {l.name for l in scene.layers if not l.visible}
    return [g for g in scene.groups if g.uid in found-chosen and not g.hidden and g.layer not in hidden]


def points(scene,group):
    from core.group import world_mesh
    key = (group.uid,scene.version)
    if key not in _points:
        if len(_points)>64:_points.clear()
        vertices = list(world_mesh(group).vertices)
        step = max(1,math.ceil(len(vertices)/MAX_POINTS))
        _points[key] = [list(v.position.toTuple()) for v in vertices[::step]]
    return _points[key]


def hull(xy):
    """Convex hull of screen points (monotone chain), counter-clockwise."""
    xy = sorted(set(xy))
    if len(xy)<3:return xy
    def half(seq):
        out = []
        for p in seq:
            while len(out)>=2 and (out[-1][0]-out[-2][0])*(p[1]-out[-2][1])-(out[-1][1]-out[-2][1])*(p[0]-out[-2][0])<=0:out.pop()
            out.append(p)
        return out[:-1]
    return half(xy)+half(reversed(xy))


def rim(vp,painter,scene,group,colour,dashed=False,filled=False):
    world = points(scene,group)
    if not world:return
    xs,ys,front = vp.world_to_pixels(world)
    outline = hull([(round(float(xs[i]),1),round(float(ys[i]),1)) for i in range(len(world)) if front[i]])
    if len(outline)<3:return
    polygon = QPolygonF([QPointF(x,y) for x,y in outline])
    painter.setBrush(Qt.NoBrush)
    if filled:
        halo = QColor(colour);halo.setAlpha(70)
        fill = QColor(colour);fill.setAlpha(30)
        painter.setPen(QPen(halo,9,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPolygon(polygon)
        painter.setBrush(fill)
    pen = QPen(colour,3 if dashed else 2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin)
    if dashed:pen.setStyle(Qt.DashLine);pen.setCapStyle(Qt.FlatCap)
    painter.setPen(pen);painter.drawPolygon(polygon)


def exemptions_shown(panel,vp):
    """Exemptions often pair every moving part with every other, so their rims would mark nearly the whole model;
    they show only while the pointer is over the exemption block or an "Exempt body…" pick runs."""
    box,pairs = getattr(panel,"collision_box",None),getattr(panel,"collision_pairs",None)
    return bool(box is not None and box.hovered) or (pairs is not None and pairs.picker is not None and vp.active_tool is pairs.picker)


def draw(panel,vp,painter):
    """The pick candidate in the accent colour, the bodies linked to the selection in their link's colour."""
    if panel.session.workspace or vp is not panel.app.viewport:return
    from views.theme import accent_color
    from .axis_guides import COLOURS
    scene = panel.app.scene
    candidate = getattr(panel,"glow_candidate",None) or getattr(vp.active_tool,"glow_group",None)
    if candidate not in scene.groups:candidate = None
    # The linked rims are guides like the axes and hide with their layer; a pick always shows its candidate.
    selection = panel.selected()
    kinds = [kind for kind in KINDS if kind!="exemption" or exemptions_shown(panel,vp)] if axes_visible(scene) else []
    others = {kind:[g for g in linked(scene,selection,kind) if g is not candidate] for kind in kinds}
    if not any(others.values()) and candidate is None:return
    painter.save();painter.setRenderHint(QPainter.Antialiasing,True)
    drawn = set()
    for kind in kinds:
        for group in others[kind]:
            # A connection wins over a reference; an exemption stays visible as a dashed rim over either.
            if kind=="exemption" or group.uid not in drawn:
                rim(vp,painter,scene,group,QColor(*COLOURS[KINDS[kind]]),dashed=kind=="exemption")
                drawn.add(group.uid)
    # Only the body a click would take gets a fill and a halo: linked rims are plain lines, so a large
    # reference body such as a frame does not wash over the bodies in front of it.
    if candidate is not None:rim(vp,painter,scene,candidate,accent_color(),filled=True)
    painter.restore()


def offer(panel,group):
    """Show (or with None clear) the rim of a body offered in a menu."""
    if getattr(panel,"glow_candidate",None) is not group:
        panel.glow_candidate = group
        panel.app.viewport.update()
