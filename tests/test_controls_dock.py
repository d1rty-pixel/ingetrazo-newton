from PySide6.QtWidgets import QLabel, QToolButton

from newton.virtual_controls import with_controls
from test_interface import panel, seed_coupled_robot  # noqa: F401 (fixture)
from test_virtual_controls import control, eligible_rows


def texts(panel):
    return [label.text() for label in panel.controls.scroll.widget().findChildren(QLabel)]


def arrow(panel, tip):
    return next(b for b in panel.controls.scroll.widget().findChildren(QToolButton) if b.toolTip() == tip)


def test_virtual_controls_come_first_and_every_row_shows_name_actual_target_and_key(panel):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.show_controls()
    controls = panel.controls
    shown = texts(panel)
    assert shown.index("VIRTUAL CONTROLS") < shown.index("Flap") < shown.index("AXES")
    assert set(controls.virtual_inputs) == {"c1"} and first["uid"] not in controls.rows
    assert controls.rows and all(label.text() == "—" for label, _, _ in controls.rows.values())
    assert "No key" in shown
    assert controls.virtual_state_labels["c1"].text() == "S0"
    assert not controls.start_button.isHidden() and controls.time_label.text() == "Time: 0.00 s"


def test_a_row_expands_in_place_for_its_key_binding_and_collapses_again(panel):
    seed_coupled_robot(panel)
    uid = next(iter(eligible_rows(panel)))["uid"]
    panel.show_controls()
    controls = panel.controls
    arrow(panel, "Key binding").click()
    assert ("joint", uid) in controls.expanded and "KEY BINDING" in texts(panel)
    arrow(panel, "Key binding").click()
    assert not controls.expanded and "KEY BINDING" not in texts(panel)


def test_a_virtual_row_expands_with_its_states_above_the_key_binding(panel):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.show_controls()
    arrow(panel, "Key binding and states").click()
    shown = texts(panel)
    assert shown.index("STATES") < shown.index("KEY BINDING")


def test_open_control_shows_the_dock_and_expands_the_row(panel):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.controls.dock.hide()
    panel.edit_virtual_controls("c1")
    assert not panel.controls.dock.isHidden() and ("control", "c1") in panel.controls.expanded


def test_the_banner_lists_bodies_above_the_rows_and_clears_with_a_notice(panel):
    controls = panel.controls
    controls.message("Careful.", "warning", [(None, "Body", "3 mm below")])
    assert not controls.banner.isHidden() and not controls.bodies.isHidden() and controls.hint.text() == ""
    assert controls.banner_text.text() == "Careful."
    controls.message("All fine.")
    assert controls.banner.isHidden() and controls.bodies.isHidden() and controls.hint.text() == "All fine."


def test_the_header_carries_the_transport_and_the_two_keep_options(panel):
    controls = panel.controls
    assert controls.keep.isCheckable() and controls.keep_pose.isCheckable()
    assert controls.dock.titleBarWidget() is controls.header
    assert controls.header.isAncestorOf(controls.start_button) and controls.header.isAncestorOf(controls.reset_button)
    assert controls.header.isAncestorOf(controls.time_label) and controls.header.isAncestorOf(controls.options_button)


def test_the_pressed_switch_button_takes_the_accent_colour(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.show_controls()
    button = panel.controls.virtual_inputs["c1"][1].buttons()[0]
    assert "palette(highlight)" in button.styleSheet() and "checked" in button.styleSheet()


def test_the_dock_is_remembered_by_the_host_window_state(panel, monkeypatch):
    from views.main_window import MainWindow
    first = panel.app.window
    panel.show_controls()
    panel.controls.dock.setFloating(True)
    first._saved_version = first.viewport.scene.version
    first.close()
    second = MainWindow()
    try:
        remembered = next(d for d in second._extension_docks if d.objectName() == "extension_newton").widget().controls.dock
        assert not remembered.isHidden() and remembered.isFloating()
    finally:
        second._saved_version = second.viewport.scene.version
        second.close()
        second.deleteLater()
