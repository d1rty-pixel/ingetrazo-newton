"""Newton: an isolated, reversible rigid-body simulation workspace."""
from .i18n import tr

__version__ = "0.15.0"


def setup(app):
    from .panel import NewtonPanel

    if app.api_version != 2 or not hasattr(app, "enter_workspace"):
        raise RuntimeError("Requires IngeTrazo 0.6.0 / Extension API 2")
    panel = NewtonPanel(app)
    dock = app.add_panel(tr("Newton"), panel)
    panel.dock = dock
    app.add_menu_action(tr("Newton…"), lambda: app.show_panel(dock),
                        tip=tr("Configure bodies and run Newton"))
    view = app.add_menu_action(tr("Show collision shapes"),lambda:panel.show_colliders.setChecked(not panel.show_colliders.isChecked()))
    if view is not None:
        panel.collision_action = view
        view.setObjectName("newton_show_colliders")
        view.setCheckable(True)
        view.setChecked(panel.show_colliders.isChecked())
        panel.show_colliders.toggled.connect(view.setChecked)
    app.on_document_changed(panel.refresh)
    app.window.destroyed.connect(panel.shutdown)
