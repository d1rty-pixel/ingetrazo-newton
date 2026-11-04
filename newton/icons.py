"""Newton's icon library: one SVG file per drawing in ``icons/``, looked up by file name.

A drawing has two groups, like IngeTrazo's tool icons: ``ink`` (the shape, drawn in the palette's
text colour) and ``accent`` (the defining detail, drawn in the host accent colour). A file without
these groups, such as a status mark, keeps its own fixed colours. One concept has one drawing, so
the toolbar, the dropdowns and the forms cannot drift apart."""
import weakref
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path
import shiboken6
from PySide6.QtGui import QIcon,QPixmap,QPalette
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).with_name("icons")
NS = "http://www.w3.org/2000/svg"
# The header every file starts with; previews in a browser or editor use its fallback colours.
HEADER = ('<svg xmlns="'+NS+'" width="24" height="24" viewBox="0 0 24 24" fill="none" '
          'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">')
ET.register_namespace("",NS)


def names():
    return sorted(path.stem for path in ROOT.glob("*.svg"))


@cache
def drawing(name):
    """(ink, accent) markup of a two-colour drawing, or None for a file with fixed colours."""
    root = ET.parse(ROOT/(name+".svg")).getroot()
    groups = {group.get("id"):"".join(ET.tostring(child,encoding="unicode").strip() for child in group)
              for group in root.findall("{"+NS+"}g")}
    if "ink" not in groups and "accent" not in groups:
        return None
    return groups.get("ink",""),groups.get("accent","")


def svg(name,ink,accent,size=24):
    """The drawing as a standalone SVG document of ``size`` pixels in the given colours."""
    parts = drawing(name)
    if parts is None:
        text = (ROOT/(name+".svg")).read_text(encoding="utf-8")
        return text.replace('width="24" height="24"','width="'+str(size)+'" height="'+str(size)+'"',1)
    shape,detail = parts
    # Scaled slightly inside the frame so the icons sit lighter next to IngeTrazo's own.
    return ('<svg xmlns="'+NS+'" width="'+str(size)+'" height="'+str(size)+'" viewBox="0 0 24 24">'
            '<g fill="none" stroke="'+ink+'" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
            'transform="translate(12 12) scale(0.86) translate(-12 -12)">'
            +shape+'<g stroke="'+accent+'">'+detail+'</g></g></svg>')


def colours():
    """(ink, accent, disabled grey) of the current palette and host accent."""
    from views.theme import accent_color
    app = QApplication.instance()
    palette = app.palette() if app else None
    ink = palette.windowText().color().name() if palette else "#30343a"
    grey = palette.color(QPalette.Disabled,QPalette.WindowText).name() if palette else "#9a9da3"
    return ink,accent_color().name(),grey


def _pixmap(text,size):
    pix = QPixmap()
    pix.loadFromData(text.encode(),"SVG")
    pix.setDevicePixelRatio(pix.width()/size)
    return pix


def pixmap(name,size=20):
    """The drawing at ``size`` logical pixels, sharp on high-density screens."""
    ink,accent,_ = colours()
    return _pixmap(svg(name,ink,accent,size*2),size)


def icon(name):
    """An icon with a grey pixmap that Qt uses whenever the action or button is disabled."""
    ink,accent,grey = colours()
    result = QIcon()
    result.addPixmap(_pixmap(svg(name,ink,accent,48),24),QIcon.Normal)
    if drawing(name) is not None:
        result.addPixmap(_pixmap(svg(name,grey,grey,48),24),QIcon.Disabled)
    return result


_attached = weakref.WeakKeyDictionary()


def attach(widget,name,size=20):
    """Show the drawing on a button or label and repaint it with ``repaint()`` after a palette change."""
    _attached[widget] = (name,size)
    if hasattr(widget,"setIcon"):widget.setIcon(icon(name))
    else:widget.setPixmap(pixmap(name,size))
    return widget


def repaint():
    # A Python wrapper can outlive its deleted widget, so the weak registry keeps the entry.
    for widget,(name,size) in list(_attached.items()):
        if shiboken6.isValid(widget):attach(widget,name,size)
        else:del _attached[widget]
