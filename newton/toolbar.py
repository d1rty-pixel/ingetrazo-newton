"""Code-native vector icons for the newton toolbar."""
from PySide6.QtCore import QSize,QSettings
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import QToolBar,QApplication
from .i18n import tr


PATHS = {
 "connect": '<path d="M3 9h6v6H3M21 9h-6v6h6M9 12h6"/><circle cx="12" cy="12" r="4"/>',
 "rotate": '<path d="M19 8a8 8 0 1 0 1 7"/><path d="M15 8h5V3"/><circle cx="12" cy="12" r="2"/>',
 "slide": '<path d="M3 8h18M3 16h18M4 5 1 8l3 3M20 13l3 3-3 3"/><rect x="9" y="5" width="6" height="14" rx="1"/>',
 "link": '<path d="m9 15 6-6M7 13 4 16a3 3 0 0 0 4 4l3-3M13 7l3-3a3 3 0 0 1 4 4l-3 3"/>',
 "unlink": '<path d="m7 13-3 3a3 3 0 0 0 4 4l3-3M13 7l3-3a3 3 0 0 1 4 4l-3 3M3 3l18 18"/>',
 "free": '<path d="m12 3 8 5v9l-8 5-8-5V8Zm-8 5 8 5 8-5M12 13v9"/>',
 "fixed": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4"/><circle cx="12" cy="15" r="1"/>',
 "drag": '<path d="M8 12V5a2 2 0 0 1 4 0v6-8a2 2 0 0 1 4 0v8-5a2 2 0 0 1 4 0v10l-4 6H9l-6-8a2 2 0 0 1 3-2l2 2"/>',
 "controls": '<path d="M5 3v18M12 3v18M19 3v18"/><path d="M2 8h6M9 16h6M16 6h6" stroke-width="4"/>',
 "play": '<path d="m7 3 14 9-14 9Z"/>',
 "pause": '<path d="M8 3v18M16 3v18" stroke-width="4"/>',
 "reset": '<path d="M4 9a8 8 0 1 1 0 7M4 3v6h6"/>',
 "panel": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M14 3v18M17 8h1M17 12h1M17 16h1"/>',
 "profiles": '<path d="M6 3h9l4 4v14H6Z M15 3v5h4 M9 12h7 M9 16h7"/>',
 "settings": '<circle cx="12" cy="12" r="4"/><path d="M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2"/>',
}


def icon(name):
    style = QSettings().value("newton/icon_set","native")
    if style=="native":
        from views.icons import tool_icon
        native = {"rotate":"rotate","drag":"pan","free":"view_iso","fixed":"layers_lock",
                  "reset":"refresh","panel":"layers_panel"}.get(name)
        if native:
            return tool_icon(native)
    app = QApplication.instance()
    ink = app.palette().windowText().color().name() if app else "#30343a"
    from views.theme import accent_color
    accent = accent_color().name()
    colour = accent if style=="accent" else ink
    dot = '<circle cx="12" cy="12" r="1.2" fill="'+accent+'" stroke="none"/>' if style=="native" and name in ("slide","link","unlink") else ""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">'
           '<g fill="none" stroke="'+colour+'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
           +PATHS[name]+dot+'</g></svg>')
    pix = QPixmap()
    pix.loadFromData(svg.encode(),"SVG")
    return QIcon(pix)


def build(panel):
    from .connections import begin as begin_connection
    bar = QToolBar(tr("Newton"),panel.app.window)
    bar.setObjectName("newton_toolbar")
    from views.icons import toolbar_icon_px
    size = toolbar_icon_px()
    bar.setIconSize(QSize(size,size))
    actions = {}
    def add(key,label,callback,tip):
        action = bar.addAction(icon(key),tr(label))
        action.setObjectName("newton_"+key)
        action.setToolTip(tr(label)+" — "+tr(tip))
        action.triggered.connect(callback)
        actions[key] = action
    groups = [
        ("Axes",[("rotate","Place rotation axis",lambda:panel.edit_joint("hinge"),"Pick the pivot and direction"),
            ("slide","Place linear axis",lambda:panel.edit_joint("slide"),"Pick the origin and direction"),
            ("connect","Connect bodies",lambda:begin_connection(panel),"Pick another body and place the connection")]),
        ("Bodies",[("free","Movable",lambda:panel.mark("dynamic"),"Make the selection movable"),
            ("fixed","Fixed",lambda:panel.mark("static"),"Fix the selection")]),
        ("References",[("link","Assign reference body",panel.pick_reference,"Pick a reference body"),
            ("unlink","Detach reference body",panel.detach_reference,"Keep the current placement")]),
        ("Simulation",[("play","Start / pause",panel.start_or_pause,"Run or pause the simulation"),
            ("reset","Reset",panel.session.reset,"Return to the original model"),
            ("drag","Drag body",panel.activate_drag,"Drag passive bodies"),
            ("controls","Controls",panel.show_controls,"Open named actuator controls")]),
        ("Extension",[("panel","Newton properties",panel.show_sidebar,"Show properties of the selection")])]
    for index,(title,entries) in enumerate(groups):
        if index:
            separator = bar.addSeparator()
            separator.setObjectName("newton_separator_"+str(index))
            separator.setToolTip(tr(title))
        for entry in entries:
            add(*entry)
    panel.app.window.addToolBar(bar)
    panel.app.restore_toolbar_layout()
    return bar,actions
