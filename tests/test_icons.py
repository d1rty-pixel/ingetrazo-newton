import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from newton import icons
from newton.toolbar import CHOICES

SOURCE = Path(icons.__file__).parent
NS = "{"+icons.NS+"}"


@pytest.mark.parametrize("name",icons.names())
def test_icon_file_follows_the_library_format(name):
    text = (icons.ROOT/(name+".svg")).read_text(encoding="utf-8")
    root = ET.fromstring(text)
    assert root.get("viewBox")=="0 0 24 24"
    groups = [child.get("id") for child in root if child.tag==NS+"g"]
    if name.startswith("status_"):
        assert groups==[] and icons.drawing(name) is None
        return
    assert text.startswith(icons.HEADER)
    assert groups==["ink","accent"] and len(root)==2
    ink,accent = icons.drawing(name)
    assert ink or accent
    assert re.fullmatch(r"[a-z]+(_[a-z]+)*",name)


def test_every_icon_file_is_used_and_every_choice_has_a_file():
    names = set(icons.names())
    referenced = {art for drawings in CHOICES.values() for art in drawings.values()}
    assert referenced<=names
    literals = set()
    for path in SOURCE.glob("*.py"):
        literals |= set(re.findall(r'"([a-z_]+)"',path.read_text(encoding="utf-8")))
    assert names-literals==set()


def test_icons_render_in_both_states(qtapp):
    from PySide6.QtGui import QIcon
    for name in icons.names():
        result = icons.icon(name)
        normal = result.pixmap(24,QIcon.Normal).toImage()
        assert not normal.isNull()
        if icons.drawing(name) is not None:
            assert result.pixmap(24,QIcon.Disabled).toImage()!=normal
