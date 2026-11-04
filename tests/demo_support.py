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
