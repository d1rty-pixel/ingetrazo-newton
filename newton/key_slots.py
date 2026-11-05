"""Key slots: shortcut actions the user maps to keys in IngeTrazo's own shortcut settings."""
from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QAction, QKeySequence

from .i18n import tr

DEFAULT_COUNT = 5
MAX_COUNT = 999
SETTING = "newton/key_slots"
LABEL_SETTING = "newton/key_slot_label_{n}"
MAX_LABEL = 40


def slot_count():
    try:
        count = int(QSettings().value(SETTING, DEFAULT_COUNT))
    except (TypeError, ValueError):
        return DEFAULT_COUNT
    return count if 0 <= count <= MAX_COUNT else DEFAULT_COUNT


def slot_label(n):
    return str(QSettings().value(LABEL_SETTING.format(n=n), "") or "").strip()


def action_text(n):
    label = slot_label(n)
    return tr("Newton: Key {n} – {label}", n=n, label=label) if label else tr("Newton: Key {n}", n=n)


def slot_name(n):
    """How every list shows a slot: "Key 1 – Gripper", or "Key 1" without a label."""
    label = slot_label(n)
    return tr("Key {n} – {label}", n=n, label=label) if label else tr("Key {n}", n=n)


class KeySlots(QObject):
    changed = Signal()    # a name or key of a slot changed, or a slot was added or removed

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
        action = QAction(action_text(n), window)
        action.setObjectName(f"newton_key_slot_{n}")
        action.setAutoRepeat(False)
        shown = [action.text(), action.shortcut().toString()]

        def follow():
            # QAction.changed also fires for enabling and checking, which must not rebuild the panel.
            now = [action.text(), action.shortcut().toString()]
            if now != shown:
                shown[:] = now
                self.changed.emit()
        action.changed.connect(follow)
        action.triggered.connect(lambda _checked=False, n=n: self.panel.session.press(n))
        window.addAction(action)
        self.panel.controls.addAction(action)   # a floating control panel is a window of its own and has the focus while driving
        self.actions.append(action)
        return action

    def set_label(self, n, text):
        """Store the label of slot ``n`` and show it in the action text; False when nothing changed."""
        text = " ".join(text.split())[:MAX_LABEL]
        if not 1 <= n <= len(self.actions) or text == slot_label(n):
            return False
        QSettings().setValue(LABEL_SETTING.format(n=n), text)
        self.actions[n-1].setText(action_text(n))
        return True

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
        self.changed.emit()
        return action

    def remove(self):
        if not self.actions:
            return False
        action = self.actions.pop()
        # A key left behind would clash with, or silently return to, a later slot with this number.
        from views.shortcuts import save_shortcut
        save_shortcut(action, [])
        QSettings().remove(LABEL_SETTING.format(n=len(self.actions)+1))   # a later slot with this number starts unlabelled
        action.setShortcuts([])
        self.panel.app.window.removeAction(action)
        self.panel.controls.removeAction(action)
        action.setParent(None)    # still a window child until deleteLater runs, so collect_actions would list it
        action.deleteLater()
        self._persist()
        self.changed.emit()
        return True

    def _persist(self):
        QSettings().setValue(SETTING, len(self.actions))
