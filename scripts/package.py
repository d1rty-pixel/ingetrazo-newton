"""Build a clean extension zip without caches, local paths or dependencies."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
out = root / "dist" / "newton-0.14.0.zip"
out.parent.mkdir(exist_ok=True)
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for path in sorted((root / "newton").glob("*.py")):
        archive.write(path, path.relative_to(root))
    for path in sorted((root / "newton" / "i18n").glob("*.json")):
        archive.write(path,path.relative_to(root))
    for name in ("README.md", "LICENSE", "docs/handbuch.md"):
        archive.write(root / name, name)
    for path in sorted((root / "scripts").glob("*.ps1")):
        archive.write(path, path.relative_to(root))
print(out)
