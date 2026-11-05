"""Development fixtures, deliberately absent from the extension UI."""
from newton.model import demo,AddDemo


def seed_demo(panel,kind):
    groups = demo(kind)
    panel.app.viewport.history.execute(AddDemo(groups))
    panel.app.scene.select(groups)
    panel.app.viewport.notify_scene_changed()
    lo,hi = panel.app.scene.bounds()
    if lo is not None:
        panel.app.viewport.camera.fit_to(lo,hi)
    panel.refresh()
    return groups


def set_units(panel,unit):
    """Window -> Units, as the host's preferences dialog applies it."""
    from core import units
    scene = panel.app.scene
    units.apply_units(scene,{"length":unit,"precision":2})
    scene.version += 1
    panel.app.viewport.notify_scene_changed()
