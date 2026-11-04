from .i18n import tr
"""Direct axis placement using IngeTrazo's native snapped tool events."""
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

    def __init__(self,finish,cancel):
        self.finish_callback,self.cancel_callback = finish,cancel
        self.anchor = self.hover = None
        self.work_plane = None
        self.done = False

    @property
    def start_point(self):return self.anchor

    @property
    def hover_point(self):return self.hover

    def on_activate(self,viewport):
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
        else:
            self.complete(ctx.world-self.anchor)

    def claims_key(self,key,modifiers):
        # Z must reach the axis tool before the built-in Zoom shortcut.
        return (not self.done and self.anchor is not None
                and key in (Qt.Key_X,Qt.Key_Y,Qt.Key_Z)
                and not modifiers & (Qt.ControlModifier|Qt.AltModifier))

    def on_key(self,viewport,key,modifiers):
        axes = {Qt.Key_X:(1,0,0),Qt.Key_Y:(0,1,0),Qt.Key_Z:(0,0,1)}
        if self.anchor is not None and key in axes:
            self.complete(QVector3D(*axes[key]))
            return True
        return False

    def complete(self,direction):
        if self.done or direction.lengthSquared()<1e-10:
            return
        self.done = True
        anchor,axis = list(self.anchor.toTuple()),list(direction.normalized().toTuple())
        QTimer.singleShot(0,lambda:self.finish_callback(anchor,axis))

    def on_cancel(self,viewport):
        if not self.done:
            self.done = True
            QTimer.singleShot(0,self.cancel_callback)

    def rubber_band_lines(self):
        return [(self.anchor,self.hover)] if self.anchor is not None and self.hover is not None else []
