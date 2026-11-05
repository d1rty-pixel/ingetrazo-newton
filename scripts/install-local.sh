#!/usr/bin/env bash
# Linux counterpart of install-local.ps1: copies the extension into the IngeTrazo
# plugin folder (Flatpak by default) and points runtime.json at the .venv interpreter.
set -euo pipefail

usage() {
    echo "Usage: $0 [--python PATH] [--destination PLUGINS_DIR] [--update]" >&2
    exit 2
}

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_root/.venv/bin/python"
destination="$HOME/.var/app/com.ingetrazo.IngeTrazo/data/ingetrazo/plugins"
update=0
while [ $# -gt 0 ]; do
    case "$1" in
        --python) [ $# -ge 2 ] || usage; python="$2"; shift 2 ;;
        --destination) [ $# -ge 2 ] || usage; destination="$2"; shift 2 ;;
        --update) update=1; shift ;;
        *) usage ;;
    esac
done

[ -f "$python" ] || { echo "Python with MuJoCo is missing. Create .venv (see README) or pass --python." >&2; exit 1; }
python="$(cd "$(dirname "$python")" && pwd)/$(basename "$python")"
"$python" -c 'import mujoco; print("MuJoCo", mujoco.__version__)' \
    || { echo "MuJoCo is not installed in this Python." >&2; exit 1; }

target="$destination/newton"
if [ -e "$target" ]; then
    [ "$update" -eq 1 ] || { echo "Target already exists: $target. Use --update to update it." >&2; exit 1; }
    grep -q 'Newton' "$target/__init__.py" 2>/dev/null \
        || { echo "Not a known Newton installation. Existing folder left unchanged." >&2; exit 1; }
    backup="$project_root/.backups/newton-$(date +%Y%m%d-%H%M%S)-$$"
    mkdir -p "$backup"
    cp -r "$target"/. "$backup"/
    echo "Backup: $backup"
fi

mkdir -p "$target"
cp "$project_root"/newton/*.py "$target"/
# Replace the folders so files removed from the extension do not linger.
rm -rf "$target/i18n" "$target/icons"
cp -r "$project_root/newton/i18n" "$project_root/newton/icons" "$target"/
"$python" -c 'import json, sys; print(json.dumps({"python": sys.argv[1]}))' "$python" > "$target/runtime.json"
echo "Installed: $target"
echo "Restart IngeTrazo. Open Extensions -> Newton."
