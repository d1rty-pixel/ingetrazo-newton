import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence

from newton import key_slots
from test_interface import panel, seed_coupled_robot, wait  # noqa: F401 (fixture)


@pytest.fixture(autouse=True)
def clean_settings():
    st = QSettings()
    keys = [key_slots.SETTING] + [f"shortcuts/newton_key_slot_{n}" for n in range(1, 12)]
    old = {k: st.value(k) for k in keys}
    for k in keys:
        st.remove(k)
    yield
    for k, v in old.items():
        st.remove(k) if v is None else st.setValue(k, v)
    st.sync()


def slot_actions(window):
    from views.shortcuts import collect_actions
    return [a for a in collect_actions(window) if a.objectName().startswith("newton_key_slot_")]


def test_default_slots_are_empty_listed_and_not_repeating(panel):
    actions = panel.key_slots.actions
    assert [a.objectName() for a in actions] == [f"newton_key_slot_{n}" for n in range(1, 6)]
    assert [a.text() for a in actions] == [f"Newton: Key {n}" for n in range(1, 6)]
    assert all(not a.shortcuts() and not a.autoRepeat() for a in actions)
    assert set(slot_actions(panel.app.window)) == set(actions)
    assert all(a in panel.controls.actions() for a in actions)


def test_slots_are_enabled_only_while_a_simulation_runs(panel, qtapp, monkeypatch):
    seed_coupled_robot(panel)
    pressed = []
    monkeypatch.setattr(type(panel.session), "press", lambda self, n: pressed.append(n), raising=False)
    actions = panel.key_slots.actions
    assert not any(a.isEnabled() for a in actions)
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    assert all(a.isEnabled() for a in actions)
    actions[2].trigger()
    assert pressed == [3]
    panel.session.reset()
    wait(qtapp, lambda: not panel.session.workspace)
    assert not any(a.isEnabled() for a in actions)


def test_add_and_remove_persist_the_count_and_clear_the_removed_key(panel):
    from views.shortcuts import save_shortcut
    slots = panel.key_slots
    slots.add()
    assert QSettings().value(key_slots.SETTING, type=int) == 6
    last = slots.actions[-1]
    assert last.objectName() == "newton_key_slot_6" and last in panel.controls.actions()
    save_shortcut(last, [QKeySequence("F9")])
    last.setShortcut(QKeySequence("F9"))
    slots.remove()
    assert len(slots.actions) == 5
    assert QSettings().value(key_slots.SETTING, type=int) == 5
    assert not QSettings().contains("shortcuts/newton_key_slot_6")
    slots.add()
    assert not slots.actions[-1].shortcuts()


def test_a_saved_key_returns_to_a_slot_added_later(panel):
    from views.shortcuts import save_shortcut
    slots = panel.key_slots
    slots.add()
    save_shortcut(slots.actions[-1], [QKeySequence("F9")])
    slots.actions[-1].setShortcuts([])
    slots.remove()
    slots.add()
    assert not slots.actions[-1].shortcuts()


@pytest.mark.parametrize("stored", ["-1", "1000", "many", "2.5"])
def test_unreadable_counts_fall_back_to_five(stored):
    QSettings().setValue(key_slots.SETTING, stored)
    assert key_slots.slot_count() == 5


def test_zero_slots_are_allowed():
    QSettings().setValue(key_slots.SETTING, 0)
    assert key_slots.slot_count() == 0


def test_preferences_list_the_slots_and_add_one(panel):
    from views.preferences_dialog import PreferencesDialog
    dialog = PreferencesDialog(panel.app.window)
    page = dialog.newton_page
    assert page.slot_list.count() == 5
    page.add_slot_button.click()
    assert page.slot_list.count() == 6
    assert any(a.objectName() == "newton_key_slot_6" for a in dialog._shortcuts._actions)
    page.remove_slot_button.click()
    assert page.slot_list.count() == 5
    assert not any(a.objectName() == "newton_key_slot_6" for a in dialog._shortcuts._actions)
    dialog.deleteLater()
