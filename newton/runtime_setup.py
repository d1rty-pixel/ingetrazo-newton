"""Create, check and locate the Newton runtime: a Python 3.12 environment with MuJoCo.

Standard library only (no Qt, no IngeTrazo imports), so it runs from the
command line with any Python 3.9+ and inside IngeTrazo's own process alike.
See docs/runtime-setup.md.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

# Code switches for maintainers. False hides the button and never starts a
# download or an installation; the manual guide remains.
RUNTIME_SETUP_ENABLED = True
# False never downloads a binary: only a uv from PATH (or --uv) is used.
DOWNLOAD_UV = True

PYTHON_VERSION = "3.12"
MUJOCO_VERSION = "3.3.7"
UV_VERSION = "0.13.7"
UV_URL = "https://github.com/astral-sh/uv/releases/download/{version}/{name}"
# (platform, machine) -> (archive, sha256, member inside the archive)
UV_ARCHIVES = {
    ("win32", "x86_64"): ("uv-x86_64-pc-windows-msvc.zip",
                          "0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021", "uv.exe"),
    ("linux", "x86_64"): ("uv-x86_64-unknown-linux-gnu.tar.gz",
                          "c5221ff41b7892bfc223543883600125f6a47fe845093e0f5bdff4f359196d83", "uv"),
    ("darwin", "arm64"): ("uv-aarch64-apple-darwin.tar.gz",
                          "81b811b57e4624df7ed3aac148e0359100d9962f3d9dce00aec533dc2e086731", "uv"),
}

MARKER = ".newton-runtime"
FLATPAK_ID = "com.ingetrazo.IngeTrazo"
REQUIREMENTS = Path(__file__).with_name("runtime-requirements.txt")
# Exit codes of the command line.
OK, FAILED, USAGE, UNSUPPORTED = 0, 1, 2, 3

Progress = Callable[[dict], None]


class SetupError(Exception):
    pass


def _windows() -> bool:
    return sys.platform == "win32"


def _machine() -> str:
    machine = platform.machine().lower()
    return "x86_64" if machine in ("amd64", "x86_64") else machine


def flatpak_data_dir() -> Path:
    return Path.home() / ".var" / "app" / FLATPAK_ID / "data" / "ingetrazo"


def runtime_dir(data_dir: Path | None = None) -> Path:
    """The runtime folder, outside the plugin folder so a Newton update keeps it."""
    if data_dir is not None:
        return Path(data_dir) / "newton-runtime"
    package = Path(__file__).resolve().parent
    if package.parent.name == "plugins":
        return package.parent.parent / "newton-runtime"
    return package.parent / ".newton-runtime"        # source checkout


def venv_python(root: Path) -> Path:
    return root / "venv" / ("Scripts/python.exe" if _windows() else "bin/python")


def _config_python(config: Path) -> str:
    try:
        return json.loads(config.read_text(encoding="utf-8-sig"))["python"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""


def resolve(root: Path | None = None) -> str:
    """The interpreter to use when the user chose none; "" when nothing exists."""
    root = root or runtime_dir()
    package = Path(__file__).resolve().parent
    for candidate in (_config_python(root / "runtime.json"),
                      _config_python(package / "runtime.json"),       # before 0.15, lost on updates
                      str(venv_python(root)),
                      str(package.parent / ".venv" / ("Scripts/python.exe" if _windows() else "bin/python"))):
        if candidate and Path(candidate).is_file():
            return candidate
    return ""


def clean_env(environ: dict | None = None) -> dict:
    """The environment for child processes: a PyInstaller bundle sets
    LD_LIBRARY_PATH to its own libraries, which break a foreign interpreter."""
    env = dict(os.environ if environ is None else environ)
    for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        original = env.pop(var + "_ORIG", None)
        if original is not None:
            env[var] = original
        elif getattr(sys, "frozen", False):
            env.pop(var, None)
    return env


def _run(args: list[str], env: dict | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if _windows() else 0
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          env=clean_env() if env is None else env, creationflags=flags)


_PROBE = ("import sys, mujoco, numpy\n"
          "m = mujoco.MjModel.from_xml_string('<mujoco/>'); d = mujoco.MjData(m); mujoco.mj_step(m, d)\n"
          "print('%d.%d' % sys.version_info[:2], mujoco.__version__)")


def check(python: str) -> tuple[bool, str]:
    """Whether the interpreter runs MuJoCo at the pinned version; a message for the user."""
    if not python or not Path(python).is_file():
        return False, "The Python interpreter does not exist."
    try:
        result = _run([python, "-E", "-c", _PROBE], timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"The interpreter cannot be started: {exc}"
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return False, "MuJoCo is not usable: " + (lines[-1] if lines else f"exit code {result.returncode}")
    try:
        python_version, mujoco_version = result.stdout.split()
    except ValueError:
        return False, "Unexpected output while testing the interpreter."
    if mujoco_version != MUJOCO_VERSION:
        return False, f"MuJoCo {mujoco_version} found, {MUJOCO_VERSION} is required."
    return True, f"Python {python_version} with MuJoCo {mujoco_version}."


def _emit(progress: Progress | None, step: str, message: str) -> None:
    if progress:
        progress(dict(step=step, message=message))


def _download(url: str, expected: str, cancel: Callable[[], bool]) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "newton-runtime-setup"})
    digest, chunks = hashlib.sha256(), []
    with urllib.request.urlopen(request, timeout=60) as response:
        while True:
            if cancel():
                raise SetupError("Cancelled.")
            chunk = response.read(1 << 16)
            if not chunk:
                break
            digest.update(chunk)
            chunks.append(chunk)
    if digest.hexdigest() != expected:
        raise SetupError("The downloaded uv does not match its pinned SHA-256; nothing was installed.")
    return b"".join(chunks)


def find_uv(root: Path, progress: Progress | None, cancel: Callable[[], bool],
            allow_download: bool, uv: str | None = None) -> str:
    """--uv, then PATH, then the pinned download; never executes an unverified file."""
    if uv:
        if not Path(uv).is_file():
            raise SetupError(f"uv not found: {uv}")
        return uv
    found = shutil.which("uv")
    if found:
        return found
    target = root / "tools" / ("uv.exe" if _windows() else "uv")
    if target.is_file():
        return str(target)
    if not allow_download:
        raise SetupError("uv is not installed and downloading it is disabled. See docs/runtime-setup.md for the manual setup.")
    entry = UV_ARCHIVES.get((sys.platform, _machine()))
    if entry is None:
        raise SetupError(f"No uv download for {sys.platform}/{_machine()}. Install uv yourself or follow docs/runtime-setup.md.")
    name, sha256, member = entry
    _emit(progress, "uv", f"Downloading uv {UV_VERSION}…")
    data = _download(UV_URL.format(version=UV_VERSION, name=name), sha256, cancel)
    target.parent.mkdir(parents=True, exist_ok=True)
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            blob = archive.read(next(n for n in archive.namelist() if Path(n).name == member))
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            blob = archive.extractfile(next(m for m in archive.getmembers() if m.isfile() and Path(m.name).name == member)).read()
    partial = target.with_suffix(".part")
    partial.write_bytes(blob)
    partial.chmod(0o755)
    partial.replace(target)
    return str(target)


def _stream(args: list[str], env: dict, progress: Progress | None, step: str, cancel: Callable[[], bool]) -> None:
    if cancel():
        raise SetupError("Cancelled.")
    flags = subprocess.CREATE_NO_WINDOW if _windows() else 0
    process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               creationflags=flags)
    tail = []
    for line in process.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-8:]
        _emit(progress, step, line)
        if cancel():
            process.terminate()
            process.wait()
            raise SetupError("Cancelled.")
    if process.wait() != 0:
        raise SetupError(f"{step} failed (exit code {process.returncode}): " + " | ".join(tail[-3:]))


def install(root: Path | None = None, progress: Progress | None = None,
            cancel: Callable[[], bool] = lambda: False, uv: str | None = None,
            find_links: str | None = None, allow_download: bool | None = None) -> str:
    """Create or repair the runtime and return its interpreter. Idempotent."""
    if not RUNTIME_SETUP_ENABLED:
        raise SetupError("Runtime setup is disabled in this build. See docs/runtime-setup.md.")
    root = root or runtime_dir()
    allow = DOWNLOAD_UV if allow_download is None else allow_download
    if root.exists() and not (root / MARKER).is_file() and any(root.iterdir()):
        raise SetupError(f"{root} exists and is not a Newton runtime folder.")
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text("Created by Newton. Safe to delete.\n", encoding="utf-8")
    tool = find_uv(root, progress, cancel, allow, uv)
    env = clean_env()
    env.update(UV_PYTHON_INSTALL_DIR=str(root / "python"), UV_CACHE_DIR=str(root / "cache"),
               UV_PYTHON_PREFERENCE="only-managed")       # a host Python is invisible inside a Flatpak
    python = venv_python(root)
    _emit(progress, "python", f"Preparing Python {PYTHON_VERSION}…")
    _stream([tool, "venv", "--python", PYTHON_VERSION, "--allow-existing", str(root / "venv")], env, progress, "python", cancel)
    _emit(progress, "mujoco", f"Installing MuJoCo {MUJOCO_VERSION}…")
    command = [tool, "pip", "install", "--python", str(python), "--only-binary", ":all:", "-r", str(REQUIREMENTS)]
    if find_links:
        command += ["--find-links", find_links]
    _stream(command, env, progress, "mujoco", cancel)
    _emit(progress, "check", "Testing the runtime…")
    ok, message = check(str(python))
    if not ok:
        raise SetupError(message)
    config = root / "runtime.json"
    partial = config.with_suffix(".part")
    partial.write_text(json.dumps(dict(python=str(python), mujoco=MUJOCO_VERSION, schema=1)) + "\n", encoding="utf-8")
    partial.replace(config)
    _emit(progress, "done", message)
    return str(python)


def uninstall(root: Path | None = None) -> None:
    root = root or runtime_dir()
    if not root.exists():
        return
    if not (root / MARKER).is_file():
        raise SetupError(f"{root} is not a Newton runtime folder; nothing was deleted.")
    shutil.rmtree(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set up the Newton runtime (Python + MuJoCo).")
    parser.add_argument("command", choices=("install", "check", "path", "uninstall"))
    parser.add_argument("--data-dir", help="IngeTrazo data folder (default: next to this plugin)")
    parser.add_argument("--flatpak", action="store_true", help=f"use the {FLATPAK_ID} data folder")
    parser.add_argument("--uv", help="use this uv instead of PATH or a download")
    parser.add_argument("--find-links", help="folder or URL with wheels (offline installation)")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--json", action="store_true", help="print one JSON object per progress line")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return USAGE if exc.code else OK
    if args.data_dir and args.flatpak:
        print("Use either --data-dir or --flatpak.", file=sys.stderr)
        return USAGE
    root = runtime_dir(Path(args.data_dir) if args.data_dir else flatpak_data_dir() if args.flatpak else None)

    def report(event: dict) -> None:
        print(json.dumps(event) if args.json else f"[{event['step']}] {event['message']}", flush=True)

    try:
        if args.command == "path":
            python = resolve(root)
            print(python)
            return OK if python else FAILED
        if args.command == "check":
            ok, message = check(resolve(root))
            print(message)
            return OK if ok else FAILED
        if args.command == "uninstall":
            if not args.yes and input(f"Delete {root}? [y/N] ").strip().lower() != "y":
                return FAILED
            uninstall(root)
            return OK
        if not RUNTIME_SETUP_ENABLED:
            raise SetupError("Runtime setup is disabled in this build. See docs/runtime-setup.md.")
        if (DOWNLOAD_UV and not args.uv and not shutil.which("uv")
                and (sys.platform, _machine()) not in UV_ARCHIVES):
            print(f"Unsupported platform {sys.platform}/{_machine()}; install uv yourself and use --uv.", file=sys.stderr)
            return UNSUPPORTED
        if not args.yes and input(f"Create the runtime in {root} (downloads Python {PYTHON_VERSION} "
                                  f"and MuJoCo {MUJOCO_VERSION})? [y/N] ").strip().lower() != "y":
            return FAILED
        install(root, report, uv=args.uv, find_links=args.find_links)
        return OK
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return FAILED


if __name__ == "__main__":
    sys.exit(main())
