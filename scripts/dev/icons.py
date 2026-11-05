"""Export Newton's icons by name, as coloured SVG and PNG files and as an overview sheet.

    .venv/bin/python scripts/dev/icons.py                     # every icon to dist/icons/
    .venv/bin/python scripts/dev/icons.py rotate slide -s 64  # chosen icons, 64 px
    .venv/bin/python scripts/dev/icons.py --sheet             # dist/icons/overview.png only

The sheet shows each icon at 22 px (the dropdown size) and enlarged, on a light and a dark
background, so line weight, accent split and alignment can be compared side by side.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "ingetrazo-source")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from newton import icons

# (background, ink) close to IngeTrazo's light and dark palettes.
THEMES = (("#fafafa", "#30343a"), ("#2b2d31", "#e4e6ea"))


def image(name, ink, accent, size):
    pix = QPixmap()
    pix.loadFromData(icons.svg(name, ink, accent, size).encode(), "SVG")
    return pix


def sheet(names, accent, path):
    small, large, cell, columns = 22, 72, 132, 6
    rows = -(-len(names) // columns)
    width, height = columns * cell * len(THEMES), rows * (cell + 18)
    out = QImage(width, height, QImage.Format_ARGB32)
    painter = QPainter(out)
    font = QFont();font.setPixelSize(11);painter.setFont(font)
    for t, (background, ink) in enumerate(THEMES):
        left = t * columns * cell
        painter.fillRect(left, 0, columns * cell, height, QColor(background))
        for i, name in enumerate(names):
            x, y = left + (i % columns) * cell, (i // columns) * (cell + 18)
            painter.drawPixmap(x + 8, y + 8, image(name, ink, accent, small))
            painter.drawPixmap(x + cell - large - 8, y + 8, image(name, ink, accent, large))
            painter.setPen(QColor(ink))
            painter.drawText(QRect(x, y + large + 14, cell, 30), Qt.AlignHCenter | Qt.TextWordWrap, name)
    painter.end()
    out.save(str(path))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="icon names (default: all); see newton/icons/")
    parser.add_argument("-o", "--out", type=Path, default=ROOT / "dist" / "icons")
    parser.add_argument("-s", "--size", type=int, default=48, help="PNG size in pixels")
    parser.add_argument("--accent", default="#f37329", help="accent colour (IngeTrazo orange)")
    parser.add_argument("--ink", default=THEMES[0][1], help="shape colour")
    parser.add_argument("--sheet", action="store_true", help="write only the overview sheet")
    args = parser.parse_args()
    QApplication.instance() or QApplication([])
    names = args.names or icons.names()
    unknown = sorted(set(names) - set(icons.names()))
    if unknown:
        parser.error("unknown icon: " + ", ".join(unknown))
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.sheet:
        for name in names:
            (args.out / (name + ".svg")).write_text(icons.svg(name, args.ink, args.accent, args.size), encoding="utf-8")
            image(name, args.ink, args.accent, args.size).save(str(args.out / (name + ".png")))
    print(sheet(names, args.accent, args.out / "overview.png"))


if __name__ == "__main__":
    main()
