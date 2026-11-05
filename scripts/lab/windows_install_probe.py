"""Probe plugin for scripts/lab/windows-install-test.ps1 (GUI phase).

The test suite copies this file as `zz_newton_probe.py` into a sandbox
plugins folder next to Newton and starts the real IngeTrazo with APPDATA
pointing there. The name sorts after `newton`, so Newton is set up first.
The probe reports what the installed host made of Newton to the JSON file in
NEWTON_PROBE_OUT: load errors, the loaded package, the runtime it resolves,
the runtime check, a runtime installation through the frozen host's Python
(the "Set up runtime" button path) and a short simulation of the opened model.
Never install this into a real plugins folder.
"""
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

OUT = os.environ.get("NEWTON_PROBE_OUT", "")
SETUP_ROOT = os.environ.get("NEWTON_PROBE_SETUP_ROOT", "")
KEEP_OPEN = os.environ.get("NEWTON_PROBE_KEEP_OPEN", "") == "1"
report = {"started": time.time(), "steps": [], "finished": False}


def write():
    if not OUT:
        return
    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    os.replace(tmp, OUT)


def step(name, **data):
    report["steps"].append(dict(name=name, t=round(time.time() - report["started"], 2), **data))
    write()


def setup(app):
    from PySide6.QtCore import QTimer
    window = app.window
    report["argv"] = sys.argv
    report["frozen"] = bool(getattr(sys, "frozen", False))
    report["host_python"] = sys.version
    write()
    state = {}

    def guarded(fn):
        def run():
            try:
                fn()
            except Exception:
                step("probe exception", error=traceback.format_exc())
                finish()
        return run

    def inspect_load():
        from PySide6.QtCore import QStandardPaths, QSettings
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QToolBar
        report["load_errors"] = getattr(window, "_extension_load_errors", None)
        module = sys.modules.get("ingetrazo_plugin_newton")
        report["newton_loaded"] = module is not None
        report["newton_file"] = getattr(module, "__file__", None)
        report["newton_version"] = getattr(module, "__version__", None)
        report["qt_appdata"] = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        report["env_appdata"] = os.environ.get("APPDATA")
        report["settings_newton_python"] = QSettings().value("newton/python", "")
        report["menu_actions"] = sorted({a.text() for a in window.findChildren(QAction) if "Newton" in a.text()})
        report["toolbars"] = sorted(t.windowTitle() for t in window.findChildren(QToolBar) if "Newton" in t.windowTitle())
        docks = [d for d in getattr(window, "_extension_docks", []) if d.objectName() == "extension_newton"]
        report["dock"] = bool(docks)
        if not module or not docks:
            step("newton not loaded")
            finish()
            return
        import importlib
        rs = importlib.import_module("ingetrazo_plugin_newton.runtime_setup")
        state["rs"], state["panel"] = rs, docks[0].widget()
        report["runtime_dir"] = str(rs.runtime_dir())
        report["resolve"] = rs.resolve()
        report["panel_python_initial"] = state["panel"].python.text()
        ok, message = rs.check(rs.resolve())
        report["check_resolved"] = dict(ok=ok, message=message)
        step("inspected")
        if SETUP_ROOT:
            threading.Thread(target=install_in_host, daemon=True).start()
            poll_install()
        else:
            wait_for_model()

    def install_in_host():
        rs = state["rs"]
        events = []
        started = time.time()
        try:
            python = rs.install(Path(SETUP_ROOT), progress=lambda e: events.append(e))
            state["install"] = dict(ok=True, python=python, check=rs.check(python))
        except Exception as exc:
            state["install"] = dict(ok=False, error=f"{type(exc).__name__}: {exc}")
        state["install"]["seconds"] = round(time.time() - started, 1)
        state["install"]["events"] = [e for e in events if e.get("step") != "mujoco"][-20:]

    def poll_install():
        if "install" not in state:
            QTimer.singleShot(500, guarded(poll_install))
            return
        report["install_in_host"] = state["install"]
        step("installed in host", ok=state["install"]["ok"])
        wait_for_model(deadline=time.time() + 30)

    def newton_groups():
        return [g for g in window.viewport.scene.groups if "newton" in (g.ext or {})]

    def wait_for_model(deadline=None):
        deadline = deadline or time.time() + 30
        if not newton_groups() and time.time() < deadline:
            QTimer.singleShot(500, guarded(lambda: wait_for_model(deadline)))
            return
        report["model_bodies"] = len(newton_groups())
        if not newton_groups():
            step("no Newton model open")
            finish()
            return
        simulate()

    def simulate():
        panel, rs = state["panel"], state["rs"]
        python = (report.get("install_in_host") or {}).get("python") or os.environ.get("NEWTON_PROBE_PYTHON") or rs.resolve()
        report["simulation_python"] = python
        panel.python.setText(python)       # in memory; Start saves it, the suite restores the registry
        frames = []
        panel.session.frame.connect(lambda t: frames.append((time.time(), t)))
        state["frames"] = frames
        state["start"] = time.time()
        panel.start_or_pause()
        report["start_message"] = panel.controls.hint.text() if hasattr(panel.controls, "hint") else None
        QTimer.singleShot(250, guarded(watch))

    def watch():
        panel, frames = state["panel"], state["frames"]
        elapsed = time.time() - state["start"]
        if elapsed < 20 and (len(frames) < 2 or frames[-1][0] - frames[0][0] < 3):
            if not panel.session.workspace and elapsed > 1:
                report["simulation"] = dict(ok=False, error="session ended", hint=panel.controls.hint.text())
                step("simulation failed")
                finish()
                return
            QTimer.singleShot(250, guarded(watch))
            return
        sim = dict(ok=len(frames) >= 2, frames=len(frames))
        if frames:
            sim["first_frame_after_s"] = round(frames[0][0] - state["start"], 2)
            wall = frames[-1][0] - frames[0][0]
            sim["sim_time"] = round(frames[-1][1], 3)
            sim["wall_s"] = round(wall, 2)
            sim["frames_per_s"] = round((len(frames) - 1) / wall, 1) if wall > 0 else None
        sim["hint"] = panel.controls.hint.text()
        sim["stderr"] = panel.session.stderr[-1500:]
        report["simulation"] = sim
        try:
            window.grab().save(str(Path(OUT).with_name("gui-running.png")))
        except Exception:
            pass
        panel.session.reset()
        report["reset_restored"] = panel.session.process is None
        step("simulated", ok=sim["ok"])
        finish()

    def finish():
        report["finished"] = True
        write()
        if not KEEP_OPEN:
            QTimer.singleShot(1000, window.close)

    QTimer.singleShot(3000, guarded(inspect_load))
