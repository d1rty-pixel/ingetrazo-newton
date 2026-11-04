"""Coloured rims around bodies: the body a pick would take, and the bodies linked to the selection."""
import math
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QColor,QPen,QPainter,QPolygonF
from .model import KEY,settings,reference_id,axes_visible

# Large meshes are thinned so a hover stays fluid; the outline only needs the extreme points.
MAX_POINTS = 4000
_points = {}


def links(group):
    """Uids this body points to: reference body, connection target, rope end, coupling leader."""
    if KEY not in (group.ext or {}):
        return set()
    cfg = settings(group)
    found = {reference_id(group),(cfg.get("point_attachment") or {}).get("target"),
             (cfg.get("flexible") or {}).get("end_reference"),
             ((cfg.get("joint") or {}).get("coupling") or {}).get("master")}
    return found-{None,group.uid}


def linked(scene,selection):
    """Bodies linked to the selection in either direction, without the selection itself."""
    chosen = {g.uid for g in selection}
    found = set()
    for group in scene.groups:
        own = links(group)
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


def rim(vp,painter,scene,group,colour):
    world = points(scene,group)
    if not world:return
    xs,ys,front = vp.world_to_pixels(world)
    outline = hull([(round(float(xs[i]),1),round(float(ys[i]),1)) for i in range(len(world)) if front[i]])
    if len(outline)<3:return
    polygon = QPolygonF([QPointF(x,y) for x,y in outline])
    halo = QColor(colour);halo.setAlpha(70)
    fill = QColor(colour);fill.setAlpha(30)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(halo,9,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPolygon(polygon)
    painter.setBrush(fill)
    painter.setPen(QPen(colour,2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPolygon(polygon)


def draw(panel,vp,painter):
    """The pick candidate in the accent colour, the bodies linked to the selection in the connection colour."""
    if panel.session.workspace or vp is not panel.app.viewport:return
    from views.theme import accent_color
    from .axis_guides import COLOURS
    scene = panel.app.scene
    candidate = getattr(panel,"glow_candidate",None) or getattr(vp.active_tool,"glow_group",None)
    if candidate not in scene.groups:candidate = None
    # The linked rims are guides like the axes and hide with their layer; a pick always shows its candidate.
    others = [g for g in linked(scene,panel.selected()) if g is not candidate] if axes_visible(scene) else []
    if not others and candidate is None:return
    painter.save();painter.setRenderHint(QPainter.Antialiasing,True)
    for group in others:rim(vp,painter,scene,group,QColor(*COLOURS["actual"]))
    if candidate is not None:rim(vp,painter,scene,candidate,accent_color())
    painter.restore()


def offer(panel,group):
    """Show (or with None clear) the rim of a body offered in a menu."""
    if getattr(panel,"glow_candidate",None) is not group:
        panel.glow_candidate = group
        panel.app.viewport.update()
