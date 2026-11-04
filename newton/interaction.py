from .i18n import tr
"""Direct reference picking and force-based dragging in the simulation."""
from PySide6.QtGui import QVector3D
from PySide6.QtCore import Qt
from tools.base import Tool


class ReferencePickTool(Tool):
    name = tr("Assign reference body")
    uses_snap = False

    def __init__(self, choose, cancel, accepts=lambda group: True):
        self.choose, self.cancel, self.accepts = choose, cancel, accepts
        self.done = False
        self.glow_group = None

    def on_activate(self, vp):
        vp.flash_status(tr("Pick the reference body. Esc cancels."),15000)

    def on_hover(self, ctx):
        group = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
        group = group if group is not None and self.accepts(group) else None
        if group is not self.glow_group:
            self.glow_group = group
            ctx.viewport.update()

    def on_click(self, ctx):
        group = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
        if group is not None and not self.done:
            try:
                self.choose(group)
            except ValueError as exc:
                ctx.viewport.flash_status(str(exc),6000)

    def on_deactivate(self, vp):
        self.done = True
        self.glow_group = None

    def on_cancel(self, vp):
        self.cancel()


class DragTool(Tool):
    name = tr("Newton drag")
    uses_snap = False

    def __init__(self, session):
        self.session = session
        self.point = self.normal = None

    def on_activate(self, vp):
        vp.flash_status(tr("Drag passive bodies. Use controls for actuators."),10000)

    def on_deactivate(self, vp):
        self.release()

    def on_click(self, ctx):
        s = self.session
        if not s.ready or not s.running:
            s.message.emit(tr("Resume to drag a body."),"info")
            return
        group = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
        uid = next((uid for uid,g in s.movers.items() if g is group),None)
        if uid is None:
            return
        if not s.can_drag(uid):
            ctx.viewport.setCursor(Qt.ForbiddenCursor)
            s.message.emit(tr("Fixed or actuated body. Use the controls."),"info")
            return
        point = ctx.viewport._world_under_cursor(ctx.screen.x(),ctx.screen.y())
        if point is None:
            point = ctx.world
        self.point = QVector3D(point)
        self.normal = ctx.viewport.camera.forward().normalized()
        s.drag_serial += 1
        s.drag = dict(id=s.drag_serial,uid=uid,point=list(point.toTuple()),target=list(point.toTuple()))
        ctx.viewport.setCursor(Qt.ClosedHandCursor)
        ctx.viewport.scene.select([group])
        ctx.viewport.update()

    def on_hover(self,ctx):
        ctx.viewport.setCursor(Qt.ClosedHandCursor if self.session.drag else Qt.OpenHandCursor)
        if self.session.drag and self.point is not None:
            origin,direction = ctx.viewport._pixel_to_ray(ctx.screen.x(),ctx.screen.y())
            if origin is None or direction is None:
                return
            denom = QVector3D.dotProduct(direction,self.normal)
            if abs(denom)>1e-8:
                distance = QVector3D.dotProduct(self.point-origin,self.normal)/denom
                target = origin+distance*direction
                self.session.drag["target"] = list(target.toTuple())

    def drag_plane(self,vp):
        return (self.point,self.normal) if self.point is not None else None

    def release(self):
        self.session.drag = None
        self.point = self.normal = None

    def on_release(self,vp):
        self.release()
        vp.setCursor(Qt.OpenHandCursor)

    def on_cancel(self,vp):
        self.release()

    def claims_key(self,key,modifiers):
        return key in (Qt.Key_Delete,Qt.Key_Backspace)

    def on_key(self,vp,key,modifiers):
        if self.claims_key(key,modifiers):
            self.session.message.emit(tr("Reset before deleting model geometry."),"warning")
            return True
        return False
