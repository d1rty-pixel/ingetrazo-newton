"""Native selection picks axis glyphs and connection points; the host's Move/Rotate/Scale edit the selected object."""
from PySide6.QtCore import Qt
from .eraser import pick_axis
from .connections import pick as pick_connection,set_hover as set_connection_hover


def install(panel):
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
                if not getattr(marker,"locked",False):
                    panel.app.scene.select([marker]);ctx.viewport.notify_scene_changed();panel.show_sidebar()
                    return
        click(ctx)

    def on_hover(ctx):
        hover(ctx)
        connection = pick_connection(panel,ctx.viewport,ctx.screen.x(),ctx.screen.y())
        set_connection_hover(panel,ctx.viewport,connection)
        if connection is not None:
            ctx.viewport.set_hover(None)
    tool.on_click,tool.on_hover = on_click,on_hover
