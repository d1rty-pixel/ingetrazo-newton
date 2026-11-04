"""Let the native eraser delete axis overlays as undoable stroke targets."""
import math
from PySide6.QtGui import QVector3D,QFontMetrics
from tools.eraser import EraserTool
from core.history import CompoundCommand
from .model import settings,remove_axes_command,axes_visible


def axis_frame(panel,viewport,j):
    preview = getattr(panel,"axis_preview",None)
    if preview and preview["uid"]==j["uid"]:j = preview
    a = QVector3D(*j["pivot"])
    direction = QVector3D(*j["axis"]).normalized()
    if panel.session.workspace:
        parent = j.get("parent")
        mover = panel.session.movers.get(parent)
        spec = panel.session.specs.get(parent)
        if mover is not None and spec:
            origin = spec["joint"]["pivot"] if spec.get("joint") else spec["center"]
            a = mover.xform.map(a-QVector3D(*origin))
            direction = mover.xform.mapVector(direction).normalized()
    if j["uid"] in getattr(viewport,"_newton_preview_bodies",set()) and getattr(viewport,"_preview_groups",None):
        m = viewport._groups_preview_transform()
        a,direction = m.map(a),m.mapVector(direction).normalized()
    radius = panel.gizmo_sizes.get(j["uid"],.2)
    ref = QVector3D(0,0,1) if abs(direction.z())<.9 else QVector3D(0,1,0)
    u = QVector3D.crossProduct(direction,ref).normalized()
    v = QVector3D.crossProduct(direction,u).normalized()
    return a,direction,u,v,radius


def axis_geometry(panel,viewport,j):
    a,direction,u,v,radius = axis_frame(panel,viewport,j)
    segments = [(a,a+direction*radius*2)]
    if j["type"]=="hinge":
        ring = [a+radius*(u*math.cos(i*2*math.pi/32)+v*math.sin(i*2*math.pi/32)) for i in range(33)]
        segments.extend(zip(ring[:-1],ring[1:]))
        segments.extend([(ring[0],ring[0]-.25*radius*v+.2*radius*u),
                         (ring[0],ring[0]-.25*radius*v-.2*radius*u)])
    else:
        tip = a+direction*radius*2
        segments.extend([(tip,tip-direction*radius*.4+u*radius*.25),
                         (tip,tip-direction*radius*.4-u*radius*.25),
                         (a-u*radius*.3,a+u*radius*.3)])
    return segments,a


def segment_distance(px,py,ax,ay,bx,by):
    dx,dy = bx-ax,by-ay
    denominator = dx*dx+dy*dy
    t = max(0,min(1,((px-ax)*dx+(py-ay)*dy)/denominator)) if denominator>1e-12 else 0
    return math.hypot(px-ax-t*dx,py-ay-t*dy)


def pick_axis(panel,viewport,x,y):
    if panel.session.workspace or viewport is not panel.app.viewport or not axes_visible(panel.app.scene,picking=True):
        return None
    best,answer = 8.,None
    for rect,uid in getattr(panel,"axis_label_hits",[]):
        if rect.contains(x,y):
            body = next((g for g in panel.app.scene.groups if g.uid==uid),None)
            if body and not body.hidden and not any(l.name==body.layer and not l.visible for l in panel.app.scene.layers):
                return uid
    metrics = QFontMetrics(viewport.font())
    for joint in panel.axis_rows:
        body = next((g for g in panel.app.scene.groups if g.uid==joint["uid"]),None)
        if body is None or body.hidden or any(l.name==body.layer and not l.visible for l in panel.app.scene.layers):
            continue
        segments,anchor = axis_geometry(panel,viewport,joint)
        if body in panel.app.scene.selection:
            from .axis_guides import guide_geometry
            guides,_ = guide_geometry(panel,viewport,joint,True)
            segments.extend((p,q) for p,q,kind in guides)
        # Use the exact geometry used for drawing, projected in one batch.
        points = [list(anchor.toTuple())]
        points.extend(list(p.toTuple()) for seg in segments for p in seg)
        xs,ys,front = viewport.world_to_pixels(points)
        if front[0]:
            distance = max(0,math.hypot(x-xs[0],y-ys[0])-5)
            if distance<best:
                best,answer = distance,joint["uid"]
            if xs[0]+9<=x<=xs[0]+9+metrics.horizontalAdvance(joint["name"]) and ys[0]-9-metrics.ascent()<=y<=ys[0]-9+metrics.descent():
                best,answer = 0,joint["uid"]
        for i in range(1,len(points),2):
            if front[i] and front[i+1]:
                distance = segment_distance(x,y,xs[i],ys[i],xs[i+1],ys[i+1])
                if distance<best:
                    best,answer = distance,joint["uid"]
    return answer


class NewtonEraser(EraserTool):
    """Preserve the built-in E tool; prioritize newton symbols over geometry.

    A stroke beginning on an axis stays axis-only until release. Rubbing across
    a ring must never start deleting the component behind its empty interior.
    """
    def __init__(self,panel):
        super().__init__()
        self.panel = panel
        self.axis_marked = set()
        self.connection_marked = set()
        self.axis_only = None
        self.stroke_scene = None

    def _reset(self):
        super()._reset()
        self.axis_marked = set()
        self.connection_marked = set()
        self.axis_only = None
        self.stroke_scene = None
        self.panel.hover_axis = None
        self.panel.hover_connection = None

    def on_click(self,ctx):
        self.axis_marked = set()
        self.connection_marked = set()
        self.axis_only = None
        self.stroke_scene = ctx.viewport.scene
        super().on_click(ctx)

    def _mark(self,viewport,x,y):
        from .connections import pick as pick_connection
        connection = pick_connection(self.panel,viewport,x,y)
        if connection is not None:
            if self.axis_only is None:self.axis_only = True
            if not self._hide:self.connection_marked.add(connection.uid)
            viewport.set_hover(None);return
        uid = pick_axis(self.panel,viewport,x,y)
        if self.axis_only is None:
            self.axis_only = uid is not None
        if uid is not None:
            if not self._hide:
                self.axis_marked.add(uid)
            viewport.set_hover(None)
            return
        if self.axis_only:
            return
        super()._mark(viewport,x,y)

    def on_hover(self,ctx):
        from .connections import pick as pick_connection
        connection = pick_connection(self.panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
        self.panel.hover_connection = connection.uid if connection else None
        self.panel.hover_axis = pick_axis(self.panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
        if not self._stroke and (self.panel.hover_axis or connection):
            ctx.viewport.set_hover(None)
            ctx.viewport.update()
        else:
            super().on_hover(ctx)

    def on_release(self,viewport):
        if not self._stroke:
            return
        uids = set(self.axis_marked)
        connection_uids = set(self.connection_marked)
        commands = []
        execute = viewport.history.execute
        try:
            viewport.history.execute = commands.append
            super().on_release(viewport)
        finally:
            viewport.history.execute = execute
        if not self._hide and viewport.scene is self.stroke_scene:
            groups = [g for g in viewport.scene.groups if g.uid in uids and settings(g).get("joint")]
            if groups:
                commands.append(remove_axes_command(groups,viewport.scene))
            from .model import Configure
            connected = [g for g in viewport.scene.groups if g.uid in connection_uids and settings(g).get("point_attachment")]
            if connected:commands.append(Configure(connected,dict(point_attachment=None),partial=True))
        self.axis_marked = set()
        self.panel.hover_axis = None
        if commands:
            execute(commands[0] if len(commands)==1 else CompoundCommand(commands))
            viewport.notify_scene_changed()
        viewport.update()
