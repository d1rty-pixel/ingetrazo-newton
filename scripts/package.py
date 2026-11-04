"""Build a clean extension zip: exactly one folder, `newton/`, as the IngeTrazo catalog requires.

No caches, local paths, dependencies or per-machine files. The hash of the
result goes into the catalog entry, so build it once and upload that file.
"""
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

root = Path(__file__).resolve().parents[1]
version = re.search(r'__version__ = "([^"]+)"', (root / "newton" / "__init__.py").read_text(encoding="utf-8")).group(1)
out = root / "dist" / f"newton-{version}.zip"
out.parent.mkdir(exist_ok=True)
files = sorted([*(root / "newton").glob("*.py"), *(root / "newton").glob("*.txt"), *(root / "newton" / "i18n").glob("*.json"),
                *(root / "newton" / "icons").glob("*.svg")])
files.append(root / "LICENSE")
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for path in files:
        name = "newton/LICENSE" if path.name == "LICENSE" else path.relative_to(root).as_posix()
        # A fixed timestamp keeps the zip, and so its SHA-256, reproducible.
        info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type, info.external_attr = ZIP_DEFLATED, 0o644 << 16
        archive.writestr(info, path.read_bytes())
print(out)
