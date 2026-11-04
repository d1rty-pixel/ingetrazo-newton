"""Code-native vector icons for the newton toolbar."""
import weakref
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon,QPixmap,QPalette
from PySide6.QtWidgets import QToolBar,QApplication
from .i18n import tr


# (shape, detail): like IngeTrazo's tool icons, the shape is drawn in the text colour and the
# defining detail (pivot, direction, cut, handle) in the accent colour.
PATHS = {
 "connect": ('<path d="M5.5 7L9.83 9.5V14.5L5.5 17L1.17 14.5V9.5ZM1.17 9.5L5.5 12L9.83 9.5M5.5 12V17M18.5 7L22.83 9.5V14.5L18.5 17L14.17 14.5V9.5ZM14.17 9.5L18.5 12L22.83 9.5M18.5 12V17"/>', '<path d="M10 12h4"/><circle cx="12" cy="12" r="1.6"/>'),
 "rotate": ('<path d="M18.14 16.3A7.5 7.5 0 1 1 18.14 7.7"/>', '<path d="M18.42 4.51L18.14 7.7L15.05 6.87"/><circle cx="12" cy="12" r="1.8"/>'),
 "slide": ('<path d="M3 7h18M3 17h18"/><rect x="4" y="9.5" width="6" height="5" rx="1"/>', '<path d="M12 12h8M17 9l3 3-3 3"/>'),
 "link": ('<path d="M7 13 4 16a3 3 0 0 0 4 4l3-3M13 7l3-3a3 3 0 0 1 4 4l-3 3"/>', '<path d="m9 15 6-6"/>'),
 "unlink": ('<path d="m7 13-3 3a3 3 0 0 0 4 4l3-3M13 7l3-3a3 3 0 0 1 4 4l-3 3"/>', '<path d="M3 3l18 18"/>'),
 "free": ('<path d="M12 4.5c-4.5 3-4.5 5 0 7.5s4.5 4.5 0 7c-1.5.8-2.5 1.5-2.5 2.5"/>', '<path d="M7 3h10"/><circle cx="12" cy="4.5" r="1.4"/>'),
 "fixed": ('<path d="M5 18.5 3.5 13 6 8l5.5-2.5L17 7l3.5 5-1 6.5Z"/><path d="M6 8l4.5 4.5L17 7M10.5 12.5 9.5 18.5"/>', '<path d="M2 21h20"/>'),
 "drag": ('<path d="M8 12V5a2 2 0 0 1 4 0v6-8a2 2 0 0 1 4 0v8-5a2 2 0 0 1 4 0v10l-4 6H9l-6-8a2 2 0 0 1 3-2l2 2"/>', ''),
 "controls": ('<path d="M5 3v18M12 3v18M19 3v18"/>', '<path d="M2 8h6M9 16h6M16 6h6" stroke-width="4"/>'),
 "play": ('', '<path d="m7 3 14 9-14 9Z"/>'),
 "pause": ('', '<path d="M8 3v18M16 3v18" stroke-width="4"/>'),
 "reset": ('<path d="M4 9a8 8 0 1 1 0 7"/>', '<path d="M4 3v6h6"/>'),
 "panel": ('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M14 3v18"/>', '<path d="M17 8h1M17 12h1M17 16h1"/>'),
}


def icon(name):
    """One icon set; Qt picks the grey pixmap whenever the action or button is disabled."""
    return compose(*PATHS[name])


def compose(shape,detail):
    from views.theme import accent_color
    app = QApplication.instance()
    palette = app.palette() if app else None
    ink = palette.windowText().color().name() if palette else "#30343a"
    grey = palette.color(QPalette.Disabled,QPalette.WindowText).name() if palette else "#9a9da3"
    result = QIcon()
    for mode,body,accent in ((QIcon.Normal,ink,accent_color().name()),(QIcon.Disabled,grey,grey)):
        # Scaled slightly inside the frame so the icons sit lighter next to IngeTrazo's own.
        paths = ('<g transform="translate(12 12) scale(0.86) translate(-12 -12)" stroke-width="1.75">'
                 +shape+'<g stroke="'+accent+'">'+detail+'</g></g>')
        result.addPixmap(render(paths,body),mode)
    return result


_BOX = '<rect x="8" y="5" width="8" height="8" rx="1"/>'
_BARS = '<path d="M3 19l6.5-5.5M21 19l-6.5-5.5"/>'
_PART = '<path d="M6 7h7v5h5v6H6Z"/>'
_STRAND = '<path d="M6 12c5 0 9 2 15 6"/>'
# Choice values drawn as interactions (ink: the bodies involved, accent: how they interact).
CHOICES = {
 "mode": {
  "dynamic": (_BOX+'<path d="M3 21h18"/>', '<path d="M12 14.5v4M10 16.5l2 2 2-2"/>'),
  "static": ('<rect x="7" y="8" width="10" height="9" rx="1"/><path d="M3 17h18"/>', '<path d="M6 17l-2 3.5M11 17l-2 3.5M16 17l-2 3.5M21 17l-2 3.5"/>'),
  "ignore": ('<rect x="7" y="7" width="10" height="10" rx="1" stroke-dasharray="2 2"/><path d="M3 15h18"/>', '<path d="M4 20 20 4"/>')},
 "shape": {
  "box": (_PART, '<rect x="3.5" y="4.5" width="17" height="16" rx="1" stroke-dasharray="2 1.5"/>'),
  "sphere": (_PART, '<circle cx="12" cy="12.5" r="9.5" stroke-dasharray="2 1.5"/>'),
  "hull": (_PART, '<path d="M4.5 5.5h9.2l5.8 5.8v8.2h-15Z" stroke-dasharray="2 1.5"/>'),
  "compound": ('<rect x="5" y="6" width="6" height="5" rx="1"/><rect x="13" y="13" width="6" height="6" rx="1"/>',
               '<rect x="3.5" y="4.5" width="9" height="8" stroke-dasharray="2 1.5"/><rect x="11.5" y="11.5" width="9" height="9" stroke-dasharray="2 1.5"/>')},
 "drive": {
  "free": ('<circle cx="14" cy="12" r="6"/><path d="M14 6v12"/>', '<path d="M2 18h5M5 16l2 2-2 2"/>'),
  "position": ('<path d="M3.5 17a8.5 8.5 0 0 1 17 0"/><circle cx="12" cy="17" r="1.2"/>', '<path d="M12 17l4.5-6"/><circle cx="17.5" cy="9.7" r="1.4"/>'),
  "velocity": ('<circle cx="12" cy="12" r="5"/><path d="M12 7v10"/>', '<path d="M19.5 9a8 8 0 1 1-3-4"/><path d="M16 2v3.5h3.5"/>')},
 "connection": {
  "ball": (_BARS, '<circle cx="12" cy="11.5" r="2.8"/>'),
  "hinge": (_BARS, '<path d="M12 3v17" stroke-dasharray="2 1.5"/><circle cx="12" cy="12" r="2"/>'),
  "fixed": (_BARS, '<rect x="8.5" y="9" width="7" height="6" rx="1"/><path d="M10.5 12h0M13.5 12h0" stroke-width="2.5"/>')},
 "flexible": {
  "rigid": ('<rect x="3" y="10" width="18" height="4" rx="1"/>', ''),
  "rope": ('<path d="M3 6c2 12 12 15 18 4"/>', '<circle cx="3" cy="5" r="1.5"/><circle cx="21" cy="9" r="1.5"/>'),
  "cable": ('<path d="M3 9c6 0 10 6 15 6M3 12c6 0 10 6 15 6"/>', '<rect x="18" y="13.5" width="3.5" height="6" rx="1"/>')},
 "attachment": {
  "fixed": ('<path d="M4 4v16"/>'+_STRAND, '<rect x="3" y="9.5" width="4.5" height="5" rx="1"/>'),
  "pinned": ('<path d="M4 4v16"/><path d="M8 12c4 0 8 2 13 6"/>', '<circle cx="6" cy="12" r="2"/>'),
  "free": ('<path d="M4 9c5 0 9 6 16 7"/>', '<path d="M3 5l2 2M2 9h2.5"/>')},
 "direction": {
  1: ('<path d="M3 8h14M14 5l3 3-3 3"/>', '<path d="M3 16h14M14 13l3 3-3 3"/>'),
  -1: ('<path d="M3 8h14M14 5l3 3-3 3"/>', '<path d="M21 16H7M10 13l-3 3 3 3"/>')},
 "axis": {
  None: ('<path d="m12 4 7 4v8l-7 4-7-4V8Z"/>', ''),
  "hinge": PATHS["rotate"], "slide": PATHS["slide"]},
}
_decorated = weakref.WeakKeyDictionary()


def decorate(combo,kind):
    """Give each fixed choice of a dropdown its interaction pictogram; dynamic entries stay plain."""
    _decorated[combo] = kind
    combo.setIconSize(QSize(22,22))
    compact(combo)
    drawings = CHOICES[kind]
    for index in range(combo.count()):
        key = combo.itemData(index)
        if key in drawings:combo.setItemIcon(index,compose(*drawings[key]))


def compact(combo):
    """Let a dropdown shrink with a narrow sidebar instead of sizing itself to its longest entry."""
    from PySide6.QtWidgets import QComboBox
    combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(6)
    return combo


def redecorate():
    for combo,kind in list(_decorated.items()):decorate(combo,kind)
    repaint_pictograms()


def render(paths,colour,size=48):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="'+str(size)+'" height="'+str(size)+'" viewBox="0 0 24 24">'
           '<g fill="none" stroke="'+colour+'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
           +paths+'</g></svg>')
    pix = QPixmap()
    pix.loadFromData(svg.encode(),"SVG")
    return pix


# (ink, accent): like IngeTrazo's tool icons, the accent marks the quantity the setting changes.
PICTOGRAMS = {
 "gravity": ('<circle cx="12" cy="5.5" r="3"/><path d="M4 21h16"/>', '<path d="M12 10.5v7M9 14.5l3 3 3-3"/>'),
 "ground": ('<circle cx="12" cy="9.5" r="4"/>', '<path d="M2 14h20M5 14l-3 5M10 14l-3 5M15 14l-3 5M20 14l-3 5"/>'),
 "linear_damping": ('<circle cx="5" cy="12" r="3"/><path d="M9 12h7M13.5 9l3 3-3 3"/>', '<path d="M19.5 6v12M22.5 8.5v7"/>'),
 "angular_damping": ('<path d="M16.5 5.5a8 8 0 1 0 2.8 9"/><path d="M12.5 5.5h4v-4"/><circle cx="11" cy="12" r="1.5"/>', '<path d="M21 17v5M23.5 18.5v2"/>'),
 "mass": ('<path d="M7 9h10l3 11H4Z"/>', '<circle cx="12" cy="6" r="2.2"/>'),
 "friction": ('<rect x="6" y="7" width="10" height="8" rx="1"/><path d="M2 15h20M11 4h7M16 2l2 2-2 2"/>', '<path d="M15 18.5H6M8.5 16.5 6 18.5l2.5 2"/>'),
 "bounce": ('<circle cx="18" cy="7" r="3"/><path d="M2 21h20"/>', '<path d="M3 5c2 0 3 15 5.5 15S12 11 15 9" stroke-dasharray="2 1.5"/>'),
 "limit_min": ('<path d="M3 12h18"/><circle cx="12" cy="12" r="2"/>', '<path d="M4 6v12"/>'),
 "limit_max": ('<path d="M3 12h18"/><circle cx="12" cy="12" r="2"/>', '<path d="M20 6v12"/>'),
 "target": ('<path d="M3 12h18"/>', '<path d="M15 5v14" stroke-dasharray="2 1.5"/><circle cx="15" cy="12" r="2.2"/>'),
 "speed": ('<path d="M4 3v17h17"/>', '<path d="M5 10h15"/>'),
 "acceleration": ('<path d="M4 3v17h17"/>', '<path d="M5 19C11 19 15 13 19 4"/>'),
 "deceleration": ('<path d="M4 3v17h17"/>', '<path d="M5 5c4 9 8 13 15 14"/>'),
 "force": ('<rect x="12" y="7" width="9" height="10" rx="1"/>', '<path d="M2 12h8M7 8.5l3.5 3.5L7 15.5" stroke-width="2.5"/>'),
 "ratio": ('<circle cx="8" cy="12" r="5.5"/><circle cx="18.5" cy="12" r="3"/>', '<circle cx="13.5" cy="12" r="1.3"/><path d="M8 6.5v2M18.5 9v1.5"/>'),
 "attraction": ('<circle cx="7" cy="12" r="4"/><circle cx="20" cy="12" r="2"/>', '<path d="M17 12h-5M13.5 10.5 12 12l1.5 1.5"/>'),
 "softening": ('<circle cx="12" cy="12" r="2.5"/>', '<circle cx="12" cy="12" r="8.5" stroke-dasharray="2 1.5"/><path d="M14.5 12h6"/>'),
 "velocity": ('<circle cx="6" cy="15" r="3"/>', '<path d="M9.5 12.5 19 6M15 5.5h4v4"/>'),
 "radius": ('<circle cx="12" cy="12" r="8"/>', '<path d="M12 12h8"/><circle cx="12" cy="12" r="1.3"/>'),
 "bending": ('<path d="M3 20c7 0 12-5 15-15"/>', '<path d="M20.5 12a8 8 0 0 1-5 6.5M15 15.5l.5 3 3-.5"/>'),
 "torsion": ('<path d="M3 12h18"/>', '<path d="M8 6c2.5 0 2.5 12 4 12s1.5-12 4-12"/>'),
}


def pictogram(name,size=40):
    """Drawing of the physical quantity a preference changes, in the current text and accent colours."""
    from views.theme import accent_color
    app = QApplication.instance()
    ink = app.palette().windowText().color().name() if app else "#30343a"
    shape,detail = PICTOGRAMS[name]
    accent = '<g stroke="'+accent_color().name()+'" stroke-width="2">'+detail+'</g>'
    pix = render(shape+accent,ink,size*2)
    pix.setDevicePixelRatio(2)
    return pix


_labelled = weakref.WeakKeyDictionary()


def physical_label(text,art):
    """Form label with a small drawing of the physical quantity at its right end, so label texts stay aligned."""
    from PySide6.QtWidgets import QWidget,QLabel,QHBoxLayout
    widget = QWidget();row = QHBoxLayout(widget);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
    row.addWidget(QLabel(text));row.addStretch()
    image = QLabel();image.setPixmap(pictogram(art,20));row.addWidget(image)
    _labelled[image] = art
    return widget


def physical_check(checkbox,art):
    checkbox.setIcon(compose(*PICTOGRAMS[art]));checkbox.setIconSize(QSize(20,20))
    _labelled[checkbox] = art
    return checkbox


def repaint_pictograms():
    for widget,art in list(_labelled.items()):
        if hasattr(widget,"setIcon"):widget.setIcon(compose(*PICTOGRAMS[art]))
        else:widget.setPixmap(pictogram(art,20))


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
