"""Native selection picks axis glyphs; two handles edit origin and direction."""
import math
from PySide6.QtCore import Qt,QTimer,QObject,QEvent
from PySide6.QtGui import QVector3D
from tools.base import Tool
from .eraser import pick_axis,axis_frame
from .connections import pick as pick_connection,set_hover as set_connection_hover,handle_at as connection_handle,ConnectionEditTool
from .model import settings,axes_visible
from .i18n import tr


def handle_at(panel,viewport,j,x,y):
    if not axes_visible(panel.app.scene,picking=True):return None
    a,d,_,_,r = axis_frame(panel,viewport,j)
    xs,ys,front = viewport.world_to_pixels([list(a.toTuple()),list((a+d*r*2).toTuple())])
    for i,key in ((0,"origin"),(1,"direction")):
        if front[i] and math.hypot(x-xs[i],y-ys[i])<=10:return key
    return None


class AxisEditTool(Tool):
    name = tr("Edit axis")
    uses_snap = True
    magnetic_axis_deg = 3.0
    screen_axis_px = 9.0

    @property
    def start_point(self):return self.anchor if self.handle=="direction" else None

    def __init__(self,panel,group,joint,handle):
        self.panel,self.group = panel,group
        self.original,self.values = dict(joint),dict(joint)
        self.handle = handle
        self.done = self.moved = False
        self.scene = panel.app.scene
        self.anchor = QVector3D(*joint["pivot"])
        self.normal = panel.app.viewport.camera.forward().normalized()
        a,d,_,_,radius = axis_frame(panel,panel.app.viewport,dict(uid=group.uid,**joint))
        self.plane_point = a if handle=="origin" else a+d*radius*2

    def drag_plane(self,viewport):return self.plane_point,self.normal

    def on_activate(self,viewport):
        viewport.flash_status(tr("Drag the handle. X/Y/Z sets direction; Esc cancels."),10000)

    def on_hover(self,ctx):
        if self.done:return
        p = QVector3D(ctx.world)
        if self.handle=="origin":self.values["pivot"] = list(p.toTuple())
        else:
            d = p-self.anchor
            if d.lengthSquared()<1e-10:return
            self.values["axis"] = list(d.normalized().toTuple())
        self.moved = True
        self.panel.axis_preview = dict(uid=self.group.uid,**self.values)
        ctx.viewport.update()

    def on_click(self,ctx):pass

    def finish(self,commit):
        if self.done:return
        self.done = True
        self.panel.axis_preview = None
        if commit and self.moved:
            try:self.panel.commit_joint(self.scene,self.group,self.values)
            except ValueError as exc:self.panel.status_message(str(exc))
        elif commit:
            # A click without a drag selects the axis object, as on an unselected axis.
            from .axis_objects import AXIS,marker_of
            marker = marker_of(self.scene,self.group,AXIS)
            if marker is not None and not getattr(marker,"locked",False):
                self.scene.select([marker]);self.panel.app.viewport.notify_scene_changed()
        self.panel.app.viewport.update()
        QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))

    def on_release(self,viewport):self.finish(True)
    def on_cancel(self,viewport):self.finish(False)
    def on_deactivate(self,viewport):
        self.done = True
        self.panel.axis_preview = None
        viewport.update()

    def claims_key(self,key,modifiers):
        return self.handle=="direction" and key in (Qt.Key_X,Qt.Key_Y,Qt.Key_Z) and not modifiers & (Qt.ControlModifier|Qt.AltModifier)

    def on_key(self,viewport,key,modifiers):
        if self.claims_key(key,modifiers):
            self.values["axis"] = {Qt.Key_X:[1,0,0],Qt.Key_Y:[0,1,0],Qt.Key_Z:[0,0,1]}[key]
            self.moved = True
            self.finish(True)
            return True
        return False


def install(panel):
    for vp in panel.app.window.all_viewports():
        if not getattr(vp,"_newton_axis_filter",None):
            vp._newton_axis_filter = HandleFilter(panel)
            vp.installEventFilter(vp._newton_axis_filter)
    tool = panel.app.window._tools["select"]
    if getattr(tool,"_newton_axis_edit",False):return
    tool._newton_axis_edit = True
    click,hover = tool.on_click,tool.on_hover

    def on_click(ctx):
        if not panel.session.workspace and ctx.viewport is panel.app.viewport and ctx.modifiers==Qt.NoModifier:
            connection = pick_connection(panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
            if connection is not None:
                panel.app.scene.select([connection]);ctx.viewport.notify_scene_changed();panel.show_sidebar()
                return
            uid = pick_axis(panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
            group = next((g for g in panel.app.scene.groups if g.uid==uid),None)
            if group:
                # Selecting the axis object lets the host's Move/Rotate act on the axis.
                from .axis_objects import AXIS,markers,owner_id
                marker = next((g for g in markers(panel.app.scene,AXIS) if owner_id(g)==uid),group)
                panel.app.scene.select([marker]);ctx.viewport.notify_scene_changed();panel.show_sidebar()
                return
        click(ctx)

    def on_hover(ctx):
        hover(ctx)
        connection = pick_connection(panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
        set_connection_hover(panel,ctx.viewport,connection)
        if connection is not None:
            ctx.viewport.set_hover(None)
        if not panel.session.workspace and ctx.viewport is panel.app.viewport:
            for j in panel.axis_rows:
                if any(g.uid==j["uid"] for g in panel.selected()) and handle_at(panel,ctx.viewport,j,ctx.screen.x(),ctx.screen.y()):
                    ctx.viewport.setCursor(Qt.SizeAllCursor)
                    break
            else:
                if any(connection_handle(panel,ctx.viewport,g,ctx.screen.x(),ctx.screen.y()) for g in editable_connections(panel)):
                    ctx.viewport.setCursor(Qt.SizeAllCursor)
    tool.on_click,tool.on_hover = on_click,on_hover


class HandleFilter(QObject):
    def __init__(self,panel):
        super().__init__(panel)
        self.panel = panel

    def eventFilter(self,viewport,event):
        p = self.panel
        if (event.type()!=QEvent.MouseButtonPress or event.button()!=Qt.LeftButton or event.modifiers()!=Qt.NoModifier
            or p.session.workspace or viewport is not p.app.viewport or viewport.nav_mode is not None
            or viewport.active_tool is not p.app.window._tools["select"]):return False
        for j in p.axis_rows:
            group = next((g for g in p.selected() if g.uid==j["uid"]),None)
            if group is None or group.hidden or getattr(group,"locked",False):continue
            if any(l.name==group.layer and (not l.visible or l.locked) for l in p.app.scene.layers):continue
            handle = handle_at(p,viewport,j,event.position().x(),event.position().y())
            if handle:
                viewport.set_active_tool(AxisEditTool(p,group,settings(group)["joint"],handle))
                return True
        for group in editable_connections(p):
            handle = connection_handle(p,viewport,group,event.position().x(),event.position().y())
            if handle:
                viewport.set_active_tool(ConnectionEditTool(p,group,handle))
                return True
        return False


def editable_connections(panel):
    """Selected bodies whose connection object the handles may move: not hidden, not locked."""
    from .axis_objects import CONNECTION,marker_of
    from .connections import editable
    scene = panel.app.scene
    result = []
    for group in panel.selected():
        marker = marker_of(scene,group,CONNECTION) if settings(group).get("point_attachment") else None
        if marker is not None and editable(scene,group) and editable(scene,marker):
            result.append(group)
    return result
