import locale
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ingetrazo-source"))

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

@pytest.fixture(scope="session")
def qtapp():
    app = QApplication.instance() or QApplication([])
    # Do not overwrite the user's saved app settings in tests.
    app.setOrganizationName("NewtonTests")
    app.setApplicationName("NewtonTests")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(ROOT / ".test-state"))
    return app


@pytest.fixture(autouse=True)
def c_numeric_locale():
    # QApplication adopts the system's LC_NUMERIC; MuJoCo's cable plugin then cannot parse "0.5" in a comma locale.
    locale.setlocale(locale.LC_NUMERIC, "C")


@pytest.fixture(autouse=True)
def isolated_autosave(monkeypatch):
    from core import autosave
    folder = ROOT / ".test-state" / "autosave"
    folder.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(autosave, "autosave_dir", lambda: folder)
