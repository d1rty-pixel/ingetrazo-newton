"""Undoable closed-loop attachments placed and edited in the model."""
import math
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QVector3D,QColor,QPen
from tools.base import Tool
from .model import KEY,settings,Configure,axes_visible
from .worker import attachment_settings
from .i18n import tr

KINDS = {"ball":"Ball joint","hinge":"Pin joint","fixed":"Fixed connection"}


def editable(scene,group):
    return group in scene.groups and not group.hidden and not getattr(group,"locked",False) and not any(l.name==group.layer and (not l.visible or l.locked) for l in scene.layers)


def connection_command(scene,source,value):
    if not editable(scene,source):raise ValueError("The body is hidden or locked.")
    patch = dict(point_attachment=value)
    if value is not None:
        value = attachment_settings(value);patch["point_attachment"] = value
        target = next((g for g in scene.groups if g.uid==value["target"]),None)
        if target is source or target is None:raise ValueError("Choose another body.")
        if not editable(scene,target):raise ValueError("The body is hidden or locked.")
        if settings(source).get("flexible") or settings(target).get("flexible"):
            raise ValueError("Use the flexible material end attachments for ropes and cables.")
        if KEY in (target.ext or {}) and settings(target)["mode"]=="ignore":raise ValueError("Both bodies must participate in the simulation.")
        # A connection to a fixed target only works if this body moves; a fixed body may still anchor a movable target.
        mode = settings(source)["mode"] if KEY in (source.ext or {}) else None
        if mode in (None,"ignore") or (mode=="static" and (KEY not in (target.ext or {}) or settings(target)["mode"]=="static")):
            patch["mode"] = "dynamic"
    return Configure([source],patch,partial=True)


def apply_connection(panel,source,value,message=None):
    if panel.session.workspace:return
    command = connection_command(panel.app.scene,source,value)
    panel.app.viewport.history.execute(command)
    panel.app.viewport.notify_scene_changed()
    if message:
        made_movable = KEY in (source.ext or {}) and "mode" in command.values
        panel.status_message(tr("{message} The body is now movable.",message=tr(message)) if made_movable else tr(message))


class ConnectionTool(Tool):
    name = tr("Connect bodies")
    uses_snap = True
    magnetic_axis_deg = 3.;screen_axis_px = 9.

    def __init__(self,panel,source,kind):
        self.panel,self.source,self.kind = panel,source,kind
        self.scene = panel.app.scene;self.target = None;self.anchor = None;self.hover = None;self.done = False

    @property
    def start_point(self):return self.anchor

    def on_activate(self,vp):vp.flash_status(tr("Pick the other body. Esc cancels."),15000)

    def on_hover(self,ctx):self.hover = QVector3D(ctx.world);ctx.viewport.update()

    def on_click(self,ctx):
        if self.done:return
        try:
            if self.panel.app.scene is not self.scene:raise ValueError("Document changed.")
            if self.target is None:
                target = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
                if target is None:return
                connection_command(self.scene,self.source,dict(target=target.uid,point=list(ctx.world.toTuple()),type=self.kind))
                self.target = target;ctx.viewport.flash_status(tr("Pick the connection point. Esc cancels."),15000);return
            if self.anchor is None:
                self.anchor = QVector3D(ctx.world)
                if self.kind!="hinge":self.finish()
                else:ctx.viewport.flash_status(tr("Pick the pin direction or press X/Y/Z."),15000)
            else:self.finish(QVector3D(ctx.world)-self.anchor)
        except ValueError as exc:self.panel.status_message(str(exc))

    def finish(self,axis=None):
        if self.done:return
        value = dict(target=self.target.uid,type=self.kind,point=list(self.anchor.toTuple()))
        if self.kind=="hinge":
            if axis is None or axis.lengthSquared()<1e-10:return
            value["axis"] = list(axis.normalized().toTuple())
        apply_connection(self.panel,self.source,value,"Connection created.")
        self.done = True;QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))

    def claims_key(self,key,modifiers):return self.anchor is not None and key in (Qt.Key_X,Qt.Key_Y,Qt.Key_Z) and not modifiers & (Qt.ControlModifier|Qt.AltModifier)

    def on_key(self,vp,key,modifiers):
        if self.claims_key(key,modifiers):
            self.finish(QVector3D(*{Qt.Key_X:(1,0,0),Qt.Key_Y:(0,1,0),Qt.Key_Z:(0,0,1)}[key]));return True
        return False

    def on_cancel(self,vp):self.done = True;QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))

    def on_deactivate(self,vp):self.done = True

    def rubber_band_lines(self):return [(self.anchor,self.hover)] if self.anchor is not None and self.hover is not None else []


def begin(panel):
    groups = panel.selected()
    if panel.session.workspace or len(groups)!=1:return
    panel.app.viewport.set_active_tool(ConnectionTool(panel,groups[0],panel.connection_editor.kind.currentData()))


def point_in_view(panel,group,value):
    """The connection point carried along by its simulated body."""
    point = QVector3D(*value["point"])
    spec = panel.session.specs.get(group.uid);mover = panel.session.movers.get(group.uid)
    if spec and mover:
        origin = spec["joint"]["pivot"] if spec.get("joint") else spec["center"]
        return mover.xform.map(point-QVector3D(*origin))
    return point


# Screen pixels around a connection object that count as a hit: the point mostly lies inside a body, whose faces would win the host's pick.
HIT_PX = 16.


def pick(panel,vp,x,y):
    """The connection object under the cursor, or None."""
    scene = panel.app.scene
    if panel.session.workspace or vp is not panel.app.viewport or not axes_visible(scene,picking=True):return None
    from .axis_objects import CONNECTION,markers,placement
    best,answer = HIT_PX,None
    for marker in markers(scene,CONNECTION):
        if not editable(scene,marker):continue
        xs,ys,front = vp.world_to_pixels([placement(marker)[0]])
        distance = math.hypot(x-float(xs[0]),y-float(ys[0]))
        if front[0] and distance<best:best,answer = distance,marker
    return answer


def ring(painter,x,y,colour):
    r = 7
    painter.setPen(QPen(colour,2));painter.setBrush(QColor(25,29,35,220))
    painter.drawEllipse(x-r,y-r,r*2,r*2);painter.drawLine(x-r-3,y,x+r+3,y);painter.drawLine(x,y-r-3,x,y+r+3)


def draw(panel,vp,painter):
    scene = panel.app.scene
    if not axes_visible(scene):return
    if not panel.session.workspace:
        hover = next((g for g in scene.groups if g.uid==getattr(panel,"hover_connection",None)),None)
        if hover is not None:
            from .axis_objects import placement
            xs,ys,front = vp.world_to_pixels([placement(hover)[0]])
            if front[0]:ring(painter,int(xs[0]),int(ys[0]),QColor(235,65,45))
        return
    # The simulated scene has no connection objects, so the point is drawn here.
    for group in scene.groups:
        value = settings(group).get("point_attachment")
        if not value or group.hidden or any(l.name==group.layer and not l.visible for l in scene.layers):continue
        point = point_in_view(panel,group,value);xs,ys,front = vp.world_to_pixels([list(point.toTuple())])
        if front[0]:ring(painter,int(xs[0]),int(ys[0]),QColor(215,91,204))


def set_hover(panel,vp,marker):
    uid = marker.uid if marker is not None else None
    if uid!=getattr(panel,"hover_connection",None):
        panel.hover_connection = uid;vp.update()
