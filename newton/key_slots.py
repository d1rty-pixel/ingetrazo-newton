"""Key slots: shortcut actions the user maps to keys in IngeTrazo's own shortcut settings."""
from PySide6.QtCore import QObject, QSettings
from PySide6.QtGui import QAction

from .i18n import tr

DEFAULT_COUNT = 5
MAX_COUNT = 999
SETTING = "newton/key_slots"


def slot_count():
    try:
        count = int(QSettings().value(SETTING, DEFAULT_COUNT))
    except (TypeError, ValueError):
        return DEFAULT_COUNT
    return count if 0 <= count <= MAX_COUNT else DEFAULT_COUNT


class KeySlots(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.actions = []
        for n in range(1, slot_count() + 1):
            self._create(n)
        panel.session.changed.connect(self.update_enabled)
        self.update_enabled()

    def _create(self, n):
        window = self.panel.app.window
        action = QAction(tr("Newton: Key {n}", n=n), window)
        action.setObjectName(f"newton_key_slot_{n}")
        action.setAutoRepeat(False)
        action.triggered.connect(lambda _checked=False, n=n: self.panel.session.press(n))
        window.addAction(action)
        self.panel.controls.addAction(action)   # the non-modal control panel window has the focus while driving
        self.actions.append(action)
        return action

    def update_enabled(self):
        session = self.panel.session
        running = bool(session.workspace and session.ready)
        for action in self.actions:
            action.setEnabled(running)

    def add(self):
        if len(self.actions) >= MAX_COUNT:
            return None
        action = self._create(len(self.actions) + 1)
        action.setEnabled(bool(self.panel.session.workspace and self.panel.session.ready))
        self._persist()
        from views.shortcuts import apply_user_shortcuts
        apply_user_shortcuts(self.panel.app.window)
        return action

    def remove(self):
        if not self.actions:
            return False
        action = self.actions.pop()
        # A key left behind would clash with, or silently return to, a later slot with this number.
        from views.shortcuts import save_shortcut
        save_shortcut(action, [])
        action.setShortcuts([])
        self.panel.app.window.removeAction(action)
        self.panel.controls.removeAction(action)
        action.setParent(None)    # still a window child until deleteLater runs, so collect_actions would list it
        action.deleteLater()
        self._persist()
        return True

    def _persist(self):
        QSettings().setValue(SETTING, len(self.actions))
