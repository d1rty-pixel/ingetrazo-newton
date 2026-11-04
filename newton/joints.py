from .i18n import tr
"""Direct axis placement using IngeTrazo's native snapped tool events."""
import math
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QVector3D
from tools.base import Tool


class PlacementTool(Tool):
    name = tr("Place axis")
    uses_snap = True
    magnetic_axis_deg = 3.0
    screen_axis_px = 9.0
    axis_source = True
    axis_source_empty_only = True

    def __init__(self,finish,cancel,preview=None,zero=False):
        self.finish_callback,self.cancel_callback = finish,cancel
        self.preview = preview
        self.asks_zero = zero
        self.anchor = self.hover = self.axis = None
        self.work_plane = None
        self.done = False

    @property
    def start_point(self):return self.anchor

    def drag_plane(self,viewport):
        # The 0° direction is picked on the plane the hinge turns in.
        return (self.anchor,self.axis) if self.axis is not None and not self.done else None

    @property
    def hover_point(self):return self.hover

    status_viewport = None

    def on_activate(self,viewport):
        self.status_viewport = viewport
        viewport.flash_status(tr("Pick the origin. Esc cancels."),10000)

    def on_deactivate(self,viewport):
        if not self.done:
            self.done = True
            self.cancel_callback()

    def on_hover(self,ctx):
        self.hover = QVector3D(ctx.world)
        ctx.viewport.update()

    def on_click(self,ctx):
        if self.done:
            return
        if self.anchor is None:
            self.anchor = QVector3D(ctx.world)
            ctx.viewport.flash_status(tr("Pick the direction or press X/Y/Z."),15000)
        elif self.axis is None:
            self.complete(ctx.world-self.anchor)
        else:
            self.complete_zero(ctx.world-self.anchor)

    def claims_key(self,key,modifiers):
        # Z must reach the axis tool before the built-in Zoom shortcut.
        keys = (Qt.Key_X,Qt.Key_Y,Qt.Key_Z)+((Qt.Key_Return,Qt.Key_Enter) if self.axis is not None else ())
        return (not self.done and self.anchor is not None and key in keys
                and not modifiers & (Qt.ControlModifier|Qt.AltModifier))

    def on_key(self,viewport,key,modifiers):
        axes = {Qt.Key_X:(1,0,0),Qt.Key_Y:(0,1,0),Qt.Key_Z:(0,0,1)}
        if self.anchor is None:
            return False
        if self.axis is not None and key in (Qt.Key_Return,Qt.Key_Enter):
            self.complete_zero(None)
            return True
        if key in axes:
            (self.complete if self.axis is None else self.complete_zero)(QVector3D(*axes[key]))
            return True
        return False

    def complete(self,direction):
        if self.done or direction.lengthSquared()<1e-10:
            return
        self.axis = direction.normalized()
        if self.asks_zero:
            self.viewport_status(tr("Pick the 0° direction, X/Y/Z, or Enter to keep it."))
            return
        self.finish(None)

    def complete_zero(self,direction):
        """None keeps the 0° direction the axis had before."""
        if self.done:
            return
        if direction is None:
            zero = (self.preview or {}).get("zero")
        else:
            zero = self.perpendicular(direction)
            if zero is None:
                return
        self.finish(zero)

    def perpendicular(self,direction):
        d = QVector3D(direction)-self.axis*QVector3D.dotProduct(direction,self.axis)
        if d.length()<=1e-6:
            return None
        d.normalize()
        # World axes projected into the turning plane attract within magnetic_axis_deg.
        limit = math.cos(math.radians(self.magnetic_axis_deg))
        for world in ((1,0,0),(0,1,0),(0,0,1)):
            w = QVector3D(*world)
            w = w-self.axis*QVector3D.dotProduct(w,self.axis)
            if w.length()<.1:
                continue
            w.normalize()
            dot = QVector3D.dotProduct(d,w)
            if abs(dot)>=limit:
                d = w if dot>0 else -w
                break
        return list(d.toTuple())

    def finish(self,zero):
        self.done = True
        anchor,axis = list(self.anchor.toTuple()),list(self.axis.toTuple())
        QTimer.singleShot(0,lambda:self.finish_callback(anchor,axis,zero))

    def viewport_status(self,text):
        if self.status_viewport is not None:
            self.status_viewport.flash_status(text,15000)

    def on_cancel(self,viewport):
        if not self.done:
            self.done = True
            QTimer.singleShot(0,self.cancel_callback)

    def preview_row(self):
        """The axis as it would be committed now, for the overlay."""
        if self.done or self.preview is None or self.anchor is None or self.hover is None:
            return None
        if self.axis is not None:
            zero = self.perpendicular(self.hover-self.anchor) or self.preview.get("zero")
            return dict(self.preview,pivot=list(self.anchor.toTuple()),axis=list(self.axis.toTuple()),zero=zero)
        direction = self.hover-self.anchor
        if direction.lengthSquared()<1e-10:
            return None
        return dict(self.preview,pivot=list(self.anchor.toTuple()),axis=list(direction.normalized().toTuple()))

    def rubber_band_lines(self):
        if self.anchor is None or self.hover is None:
            return []
        if self.axis is None:
            return [(self.anchor,self.hover)]
        zero = self.perpendicular(self.hover-self.anchor)
        if zero is None:
            return []
        reach = max((self.hover-self.anchor).length(),1e-3)
        return [(self.anchor,self.anchor+QVector3D(*zero)*reach)]
