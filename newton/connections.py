"""Undoable closed-loop attachments placed and edited in the model."""
import math
from PySide6.QtCore import Qt,QTimer,QObject,QEvent
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


def point_in_view(panel,group,value,vp=None):
    point = QVector3D(*value["point"])
    if panel.session.workspace:
        spec = panel.session.specs.get(group.uid);mover = panel.session.movers.get(group.uid)
        if spec and mover:
            origin = spec["joint"]["pivot"] if spec.get("joint") else spec["center"]
            return mover.xform.map(point-QVector3D(*origin))
    if getattr(panel,"connection_preview",None) and panel.connection_preview[0]==group.uid:return panel.connection_preview[1]
    vp = vp or panel.app.viewport
    if group.uid in getattr(vp,"_newton_preview_bodies",set()) and getattr(vp,"_preview_groups",None):
        return vp._groups_preview_transform().map(point)
    return point


# Screen pixels around a marker that count as a hit; the marker is an overlay, so it has no geometry to click.
HIT_PX = 16.


def pick(panel,vp,x,y):
    if panel.session.workspace or not axes_visible(panel.app.scene,picking=True):return None
    best,answer = HIT_PX,None
    for group in panel.app.scene.groups:
        value = settings(group).get("point_attachment")
        if not value or not editable(panel.app.scene,group):continue
        p = point_in_view(panel,group,value,vp);xs,ys,front = vp.world_to_pixels([list(p.toTuple())])
        if front[0]:
            distance = math.hypot(x-float(xs[0]),y-float(ys[0]))
            if distance<best:best,answer = distance,group
    return answer


def draw(panel,vp,painter):
    if not axes_visible(panel.app.scene):return
    scene = panel.app.scene
    for group in scene.groups:
        value = settings(group).get("point_attachment")
        if not value or group.hidden or any(l.name==group.layer and not l.visible for l in scene.layers):continue
        point = point_in_view(panel,group,value,vp);xs,ys,front = vp.world_to_pixels([list(point.toTuple())])
        if not front[0]:continue
        selected = group in scene.selection or any(g.uid==group.uid for g in getattr(panel,"_sidebar_groups",[]))
        x,y = int(xs[0]),int(ys[0]);r = 9 if selected else 7
        colour = QColor(235,65,45) if getattr(panel,"hover_connection",None)==group.uid else QColor(215,91,204)
        painter.setPen(QPen(colour,3 if selected else 2));painter.setBrush(QColor(25,29,35,220))
        painter.drawEllipse(x-r,y-r,r*2,r*2);painter.drawLine(x-r-3,y,x+r+3,y);painter.drawLine(x,y-r-3,x,y+r+3)


class MoveConnection(Tool):
    name = tr("Move connection point");uses_snap = True
    def __init__(self,panel,group):
        self.panel,self.group = panel,group;self.scene = panel.app.scene
        self.value = dict(settings(group)["point_attachment"]);self.point = QVector3D(*self.value["point"]);self.done = False;self.moved = False
        self.normal = panel.app.viewport.camera.forward().normalized()
    def on_activate(self,vp):vp.flash_status(tr("Drag the connection point. Esc cancels."),10000)
    def drag_plane(self,vp):return self.point,self.normal
    def on_hover(self,ctx):
        self.panel.connection_preview = (self.group.uid,QVector3D(ctx.world));self.moved = True;ctx.viewport.update()
    def on_click(self,ctx):pass
    def finish(self,commit):
        if self.done:return
        if commit and self.moved and self.panel.app.scene is self.scene:
            self.value["point"] = list(self.panel.connection_preview[1].toTuple())
            try:apply_connection(self.panel,self.group,self.value,"Connection point moved.")
            except ValueError as exc:self.panel.status_message(str(exc))
        self.done = True;self.panel.connection_preview = None;self.panel.app.viewport.update()
        QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))
    def on_release(self,vp):self.finish(True)
    def on_cancel(self,vp):self.finish(False)
    def on_deactivate(self,vp):self.done = True;self.panel.connection_preview = None;vp.update()


class ConnectionFilter(QObject):
    def __init__(self,panel):super().__init__(panel);self.panel = panel
    def eventFilter(self,vp,event):
        p = self.panel
        if event.type()==QEvent.MouseMove and event.buttons()==Qt.NoButton:
            self.hover(vp,event)
            return False
        if event.type()!=QEvent.MouseButtonPress or event.button()!=Qt.LeftButton or event.modifiers()!=Qt.NoModifier:return False
        if p.session.workspace or vp is not p.app.viewport or vp.nav_mode is not None or vp.active_tool is not p.app.window._tools["select"]:return False
        group = pick(p,vp,event.position().x(),event.position().y())
        if group is None:return False
        if group not in p.selected():p.app.scene.select([group]);vp.notify_scene_changed();p.show_sidebar()
        else:vp.set_active_tool(MoveConnection(p,group))
        return True

    def hover(self,vp,event):
        p = self.panel
        usable = not p.session.workspace and vp is p.app.viewport and vp.nav_mode is None and vp.active_tool is p.app.window._tools["select"]
        group = pick(p,vp,event.position().x(),event.position().y()) if usable else None
        uid = group.uid if group is not None else None
        if uid!=getattr(p,"hover_connection",None):
            p.hover_connection = uid;vp.update()


def install(panel):
    for vp in panel.app.window.all_viewports():
        if not getattr(vp,"_newton_connection_filter",None):
            vp._newton_connection_filter = ConnectionFilter(panel);vp.installEventFilter(vp._newton_connection_filter)
