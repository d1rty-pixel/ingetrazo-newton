import math

import pytest

from newton.model import joint_rows
from newton.virtual_controls import (check, eligible, managed, new_control, resolve, stored, targets,
                                     with_controls)
from test_interface import panel, seed_coupled_robot, wait  # noqa: F401 (fixture)


def control(kind="switch", joints=("a", "b"), states=((0, 0), (1, 2)), initial=0, name="Flap", id="c1"):
    return dict(id=id, name=name, kind=kind, joints=list(joints),
                states=[dict(name=f"S{i}", values=list(v)) for i, v in enumerate(states)], initial=initial)


def rows(*uids, drive="position"):
    return [dict(uid=u, body=u.upper(), drive=drive) for u in uids]


def test_switch_sets_the_values_of_its_state_and_clamps_the_index():
    c = control(states=((0, 0), (1, 2), (3, 4)))
    assert targets(c, 1) == {"a": 1, "b": 2}
    assert targets(c, 9) == {"a": 3, "b": 4}
    assert targets(c, -1) == {"a": 0, "b": 0}


def test_slider_interpolates_between_neighbouring_states():
    c = control("slider", states=((0, 0), (1, 2), (3, 2)))
    assert targets(c, 0) == {"a": 0, "b": 0}
    assert targets(c, .25) == pytest.approx({"a": .5, "b": 1})
    assert targets(c, .75) == pytest.approx({"a": 2, "b": 2})
    assert targets(c, 1) == {"a": 3, "b": 2}
    assert targets(c, 7) == {"a": 3, "b": 2}


@pytest.mark.parametrize("change", [
    lambda c: c.update(kind="knob"),
    lambda c: c.update(name=""),
    lambda c: c.update(joints=["a", "a"]),
    lambda c: c["states"].pop(),
    lambda c: c["states"][0]["values"].pop(),
    lambda c: c["states"][1]["values"].__setitem__(0, math.nan),
    lambda c: c["states"][1]["values"].__setitem__(0, True),
    lambda c: c.update(initial=2),
    lambda c: c.update(initial=.5),
    lambda c: c.update(kind="slider", initial=1.5),
])
def test_damaged_controls_are_refused(change):
    c = control()
    change(c)
    with pytest.raises(ValueError):
        check(c)


def test_document_data_round_trip_and_damage():
    assert stored(None) == []
    assert stored({"other": 1}) == []
    c = control()
    data = with_controls({"other": 1}, [c])
    assert stored(data) == [c] and data["other"] == 1
    assert with_controls(data, []) == {"other": 1}
    assert with_controls({"controls": [c]}, []) is None
    with pytest.raises(ValueError):
        stored({"controls": [c, dict(c)]})
    with pytest.raises(ValueError):
        stored({"controls": "x"})


def test_new_controls_are_valid_once_they_have_joints():
    for kind in ("switch", "slider"):
        assert check(new_control(kind, "New"))["joints"] == []


def test_resolve_drops_missing_or_passive_joints_with_their_values():
    c = control(joints=("a", "gone", "b"), states=((0, 9, 0), (1, 9, 2)))
    available = rows("a") + rows("b", drive="free")
    (result,) = resolve([c], available)
    assert result["joints"] == ["a"]
    assert [s["values"] for s in result["states"]] == [[0], [1]]
    assert c["joints"] == ["a", "gone", "b"]
    assert set(eligible(rows("a") + [dict(uid="f", body="F", drive="position", coupling={"master": "a"})])) == {"a"}


def test_a_joint_in_two_controls_is_refused():
    first, second = control(), control(id="c2", name="Other", joints=("b",), states=((0,), (1,)))
    with pytest.raises(ValueError, match="Other"):
        resolve([first, second], rows("a", "b"))
    assert set(managed(resolve([first], rows("a", "b")))) == {"a", "b"}


def eligible_rows(panel):
    return [r for r in joint_rows(panel.app.scene) if r["drive"] != "free" and not r.get("coupling")]


def test_switch_drives_its_joints_hides_their_cards_and_is_undoable(panel, qtapp):
    seed_coupled_robot(panel)
    first, second = eligible_rows(panel)[:2]
    c = control(joints=(first["uid"], second["uid"]), states=((0, 0), (.3, -.2)), initial=1)
    panel.app.set_document_data(with_controls(None, [c]))
    panel.refresh()
    assert set(panel.controls.virtual_inputs) == {"c1"}
    assert first["uid"] not in panel.controls.rows and second["uid"] not in panel.controls.rows
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    assert panel.session.targets[first["uid"]] == pytest.approx(.3)
    assert panel.session.targets[second["uid"]] == pytest.approx(-.2)
    off = next(b for b in panel.controls.virtual_inputs["c1"][1].buttons() if b.text() == "S0")
    off.click()
    assert panel.session.virtual_values == {"c1": 0}
    assert panel.session.targets[first["uid"]] == 0 and panel.session.targets[second["uid"]] == 0
    panel.session.reset()
    assert panel.session.virtual == {}
    assert panel.app.document_data() == {"controls": [c]}
    panel.app.viewport.history.undo()
    panel.refresh()
    assert panel.app.document_data() is None
    assert panel.controls.virtual_inputs == {}
    assert first["uid"] in panel.controls.rows


def test_slider_sets_interpolated_targets(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    c = control("slider", joints=(first["uid"],), states=((0,), (.4,)), initial=0)
    panel.app.set_document_data(with_controls(None, [c]))
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    number = panel.controls.virtual_inputs["c1"][1]
    assert number.suffix() == " %" and number.isEnabled()
    number.setValue(25)
    assert panel.session.targets[first["uid"]] == pytest.approx(.1)


def test_start_refuses_a_joint_in_two_controls(panel):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    one = control(joints=(first["uid"],), states=((0,), (1,)))
    two = control(id="c2", name="Second", joints=(first["uid"],), states=((0,), (1,)))
    panel.app.set_document_data(with_controls(None, [one, two]))
    panel.start_or_pause()
    assert panel.session.workspace is None
    assert "Second" in panel.controls.banner_text.text()


def inline_editor(panel, control_id):
    """The editor in the expanded row of a control; the host loads the extension under its own package name, so the class differs from newton.virtual_editor's."""
    from PySide6.QtWidgets import QFrame
    controls = panel.controls
    controls.expanded.add(("control", control_id))
    panel.show_controls()
    return next(w for w in controls.scroll.widget().findChildren(QFrame) if type(w).__name__ == "VirtualControlEditor" and w.id == control_id)


def test_new_control_opens_its_row_and_is_created_in_one_undo_step(panel, qtapp):
    seed_coupled_robot(panel)
    first, second = eligible_rows(panel)[:2]
    panel.show_controls()
    panel.controls.add_control("switch")
    (created,) = panel.app.document_data()["controls"]
    assert ("control", created["id"]) in panel.controls.expanded
    editor = inline_editor(panel, created["id"])
    editor.name.setText("Gripper")
    editor.name.textEdited.emit("Gripper")
    assert panel.controls.name_labels[created["id"]].text() == "Gripper"
    for row in (first, second):
        editor = inline_editor(panel, created["id"])
        editor.choice.setCurrentIndex(editor.choice.findData(row["uid"]))
        editor.add_joint()
    editor = inline_editor(panel, created["id"])
    assert editor.choice.findData(first["uid"]) == -1
    box = editor.values[0, 1]
    box.setValue(box.value()+30)
    editor.state_names[1].setText("Closed")
    editor.state_names[1].textEdited.emit("Closed")
    editor.add_state()
    editor = inline_editor(panel, created["id"])
    editor.start.setCurrentIndex(1)
    editor.start.activated.emit(1)
    (control,) = panel.app.document_data()["controls"]
    assert control["name"] == "Gripper" and control["joints"] == [first["uid"], second["uid"]]
    assert [s["name"] for s in control["states"]][1] == "Closed" and len(control["states"]) == 3
    assert control["states"][1]["values"][0]-control["states"][0]["values"][0] == pytest.approx(math.radians(30))
    assert control["initial"] == 1
    assert set(panel.controls.virtual_inputs) == {control["id"]}


def test_a_state_an_axis_and_the_control_have_their_own_remove_button(panel):
    seed_coupled_robot(panel)
    first, second = eligible_rows(panel)[:2]
    c = control(joints=(first["uid"], second["uid"]), states=((0, 0), (.1, .1), (.2, .2)), initial=2)
    panel.app.set_document_data(with_controls(None, [c]))
    panel.refresh()
    editor = inline_editor(panel, "c1")
    assert all(b.isEnabled() for b in editor.state_removes) and len(editor.axis_removes) == 2
    editor.state_removes[1].click()
    (stored_control,) = panel.app.document_data()["controls"]
    assert [s["name"] for s in stored_control["states"]] == ["S0", "S2"] and stored_control["initial"] == 1
    assert [s["values"] for s in stored_control["states"]] == [[0, 0], [.2, .2]]
    editor = inline_editor(panel, "c1")
    assert not any(b.isEnabled() for b in editor.state_removes), "a control keeps two states"
    editor.axis_removes[0].click()
    (stored_control,) = panel.app.document_data()["controls"]
    assert stored_control["joints"] == [second["uid"]] and [s["values"] for s in stored_control["states"]] == [[0], [.2]]
    panel.app.viewport.history.undo()
    assert panel.app.document_data()["controls"][0]["joints"] == [first["uid"], second["uid"]]
    inline_editor(panel, "c1")
    delete = next(b for b in panel.controls.scroll.widget().findChildren(type(panel.controls.new_button)) if b.text() == "Delete control")
    delete.click()
    assert panel.app.document_data() is None
    assert ("control", "c1") not in panel.controls.expanded


def test_the_virtual_control_editor_is_disabled_and_new_control_unavailable_during_simulation(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.show_controls()
    assert panel.controls.new_button.isEnabled()
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    assert not panel.controls.new_button.isEnabled()
    assert not inline_editor(panel, "c1").isEnabled()


def test_one_by_one_switch_starts_each_axis_after_the_previous_ramp(panel, qtapp):
    seed_coupled_robot(panel)
    first, second = eligible_rows(panel)[1:3]
    c = control(joints=(first["uid"], second["uid"]), states=((0, 0), (.3, -.3)))
    c["sequential"] = True
    panel.app.set_document_data(with_controls(None, [c]))
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    panel.session.set_virtual("c1", 1)
    assert panel.session.targets[first["uid"]] == pytest.approx(.3)
    assert panel.session.targets[second["uid"]] == 0
    wait(qtapp, lambda: panel.session.targets[second["uid"]] != 0)
    state = panel.session.joint_states[first["uid"]]
    assert state["command"] == pytest.approx(.3)
    assert panel.session.joint_states[second["uid"]]["command"] == pytest.approx(0, abs=1e-9)
    wait(qtapp, lambda: "c1" not in panel.session.sequences)
    # Switching back mid-way drops the rest of the old order.
    panel.session.set_virtual("c1", 0)
    panel.session.set_virtual("c1", 1)
    assert panel.session.sequences["c1"]["rest"] == [(second["uid"], -.3)]


def test_one_by_one_is_refused_unless_true_or_false():
    c = control()
    c["sequential"] = "yes"
    with pytest.raises(ValueError):
        check(c)


def test_editor_stores_one_by_one_only_for_switches_when_on(panel):
    seed_coupled_robot(panel)
    panel.show_controls()
    panel.controls.add_control("switch")
    (created,) = panel.app.document_data()["controls"]
    editor = inline_editor(panel, created["id"])
    editor.sequential.setChecked(True)
    assert panel.app.document_data()["controls"][0]["sequential"] is True
    editor.sequential.setChecked(False)
    assert "sequential" not in panel.app.document_data()["controls"][0]
    panel.controls.add_control("slider")
    slider = next(c for c in panel.app.document_data()["controls"] if c["kind"] == "slider")
    assert inline_editor(panel, slider["id"]).sequential is None


def test_sidebar_notes_the_managing_control_and_opens_its_editor(panel, monkeypatch):
    seed_coupled_robot(panel)
    first, second = eligible_rows(panel)[:2]
    by_uid = {g.uid: g for g in panel.app.scene.groups}
    panel.app.set_document_data(with_controls(None, [control(joints=(first["uid"],), states=((0,), (1,)))]))
    panel.app.scene.select([by_uid[second["uid"]]])
    panel.refresh()
    assert panel.managed_note.isHidden()
    panel.app.scene.select([by_uid[first["uid"]]])
    panel.refresh()
    assert not panel.managed_note.isHidden() and "Flap" in panel.managed_label.text()
    opened = []
    monkeypatch.setattr(panel, "edit_virtual_controls", lambda select=None: opened.append(select))
    panel.managed_button.click()
    assert opened == ["c1"]
    panel.app.set_document_data(None)
    panel.refresh()
    assert panel.managed_note.isHidden()
