import math

import pytest
from PySide6.QtWidgets import QDoubleSpinBox, QPushButton

from newton.key_bindings import check, next_value, resolve, stored, with_bindings
from newton.model import joint_rows
from newton.virtual_controls import with_controls
from test_interface import panel, seed_coupled_robot, wait  # noqa: F401 (fixture)


def toggle(uid="a", slot=1, value=1.0, rest=0.0, kind="joint"):
    return dict(target={kind: uid}, slot=slot, mode="toggle", value=value, rest=rest)


def step(uid="a", slot=1, size=.1, down=None, kind="joint"):
    b = dict(target={kind: uid}, slot=slot, mode="step", step=size)
    if down is not None:
        b["slot_down"] = down
    return b


def row(uid, **kw):
    return dict(dict(uid=uid, body=uid.upper(), drive="position", type="hinge", limited=True,
                     lower=-1.0, upper=2.0, max_speed=3.0), **kw)


def switch(joints=("a",), id="c1", states=((0,), (1,), (2,))):
    return dict(id=id, name="S", kind="switch", joints=list(joints), initial=0,
                states=[dict(name=f"S{i}", values=list(v)) for i, v in enumerate(states)])


@pytest.mark.parametrize("change", [
    lambda b: b.update(target={}),
    lambda b: b.update(target={"joint": "a", "control": "b"}),
    lambda b: b.update(target={"joint": ""}),
    lambda b: b.update(target={"body": "a"}),
    lambda b: b.update(slot=0),
    lambda b: b.update(slot=1000),
    lambda b: b.update(slot=True),
    lambda b: b.update(mode="hold"),
    lambda b: b.update(value=math.nan),
    lambda b: b.pop("rest"),
])
def test_damaged_toggle_is_refused(change):
    b = toggle()
    change(b)
    with pytest.raises(ValueError):
        check(b)


@pytest.mark.parametrize("change", [
    lambda b: b.update(step=0),
    lambda b: b.update(step=-1),
    lambda b: b.update(step=math.inf),
    lambda b: b.update(slot_down=0),
    lambda b: b.update(slot_down=1.5),
])
def test_damaged_step_is_refused(change):
    b = step()
    change(b)
    with pytest.raises(ValueError):
        check(b)


def test_valid_bindings_pass():
    assert check(step(down=2)) and check(step(down=None)) and check(toggle(kind="control"))


def test_document_data_round_trip_and_damage():
    assert stored(None) == [] and stored({"controls": []}) == []
    bindings = [toggle("a"), step("b", slot=2)]
    c = switch()
    data = with_bindings(with_controls(None, [c]), bindings)
    assert stored(data) == bindings and data["controls"] == [c]
    assert with_controls(data, [c])["bindings"] == bindings
    assert with_bindings(data, []) == {"controls": [c]}
    assert with_bindings({"bindings": bindings}, []) is None
    with pytest.raises(ValueError):
        stored({"bindings": "x"})
    with pytest.raises(ValueError):
        stored({"bindings": [toggle("a"), step("a", slot=2)]})
    with pytest.raises(ValueError):
        stored({"bindings": [toggle(slot=0)]})


def test_resolve_skips_invalid_targets_and_attaches_ranges():
    rows = [row("a"), row("free", drive="free"), row("fol", coupling={"master": "a"}), row("m"),
            row("u", limited=False), row("s", type="slide", limited=False),
            row("v", drive="velocity")]
    controls = [switch(("m",)), dict(switch((), id="c2", states=((), ())), kind="slider")]
    bindings = [toggle(x) for x in ("a", "free", "fol", "m", "u", "s", "v", "gone")]
    bindings += [toggle("c1", kind="control"), toggle("c2", kind="control"), toggle("nope", kind="control")]
    got = {next(iter(b["target"].values())): b["range"] for b in resolve(bindings, rows, controls)}
    assert got == {"a": (-1.0, 2.0), "u": (-math.pi, math.pi), "s": (-1.0, 1.0), "v": (-3.0, 3.0),
                   "c1": (0, 2), "c2": (0, 1)}


def test_next_value_toggle_and_step():
    t = dict(toggle(), range=(-5, 5))
    assert next_value(t, 0) == 1.0
    assert next_value(t, 1.0 + 1e-10) == 0.0
    assert next_value(t, 3) == 1.0
    s = dict(step(size=.4), range=(-1, 1))
    assert next_value(s, 0) == pytest.approx(.4)
    assert next_value(s, .8) == 1
    assert next_value(s, -.8, down=True) == -1
    k = dict(step(size=1), range=(0, 2), integer=True)
    assert next_value(k, 1) == 2 and next_value(k, 2) == 2 and next_value(k, 0, down=True) == 0
    assert isinstance(next_value(k, 1), int)


def eligible_rows(panel):
    return [r for r in joint_rows(panel.app.scene) if r["drive"] != "free" and not r.get("coupling")]


def start(panel, qtapp, data):
    panel.app.set_document_data(data)
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)


def test_press_toggles_a_joint_target_and_the_panel_follows_exactly(panel, qtapp):
    seed_coupled_robot(panel)
    first = next(r for r in eligible_rows(panel) if r["drive"] == "position" and r["limited"])
    uid = first["uid"]
    value = (first["lower"]+first["upper"])/2+1e-4
    start(panel, qtapp, with_bindings(None, [toggle(uid, 3, value, first["lower"])]))
    spin = panel.controls.joint_inputs[uid][0]
    panel.session.press(3)
    assert panel.session.targets[uid] == value
    assert spin.value() == pytest.approx(math.degrees(value), abs=.06)
    panel.session.press(3)
    assert panel.session.targets[uid] == first["lower"]
    panel.session.press(4)
    assert panel.session.targets[uid] == first["lower"]


def test_step_with_second_slot_clamps_at_the_range(panel, qtapp):
    seed_coupled_robot(panel)
    first = next(r for r in eligible_rows(panel) if r["drive"] == "position" and r["limited"])
    uid = first["uid"]
    start(panel, qtapp, with_bindings(None, [step(uid, 1, 10, down=2)]))
    panel.session.press(1)
    assert panel.session.targets[uid] == first["upper"]
    panel.session.press(2)
    assert panel.session.targets[uid] == first["lower"]


def test_press_steps_a_virtual_switch_and_the_card_follows(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    c = switch((first["uid"],), states=((0,), (.1,), (.2,)))
    start(panel, qtapp, with_bindings(with_controls(None, [c]), [step("c1", 1, 1, down=2, kind="control")]))
    panel.session.press(1)
    panel.session.press(1)
    panel.session.press(1)
    assert panel.session.virtual_values == {"c1": 2}
    assert panel.session.targets[first["uid"]] == pytest.approx(.2)
    buttons = panel.controls.virtual_cards["c1"].findChildren(QPushButton)
    assert [b.isChecked() for b in buttons] == [False, False, True]
    panel.session.press(2)
    assert [b.isChecked() for b in buttons] == [False, True, False]
    assert panel.session.targets[first["uid"]] == pytest.approx(.1)


def test_press_moves_a_slider_card(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    c = dict(switch((first["uid"],), states=((0,), (.4,))), kind="slider")
    start(panel, qtapp, with_bindings(with_controls(None, [c]), [step("c1", 1, .25, kind="control")]))
    panel.session.press(1)
    assert panel.controls.virtual_cards["c1"].findChild(QDoubleSpinBox).value() == 25
    assert panel.session.virtual_values["c1"] == .25
    assert panel.session.targets[first["uid"]] == pytest.approx(.1)


def test_binding_on_a_managed_joint_is_skipped(panel, qtapp):
    seed_coupled_robot(panel)
    first = eligible_rows(panel)[0]
    c = switch((first["uid"],))
    start(panel, qtapp, with_bindings(with_controls(None, [c]), [toggle(first["uid"], 1, .5, 0)]))
    assert panel.session.bindings == []


def test_damaged_bindings_refuse_start(panel):
    seed_coupled_robot(panel)
    panel.app.set_document_data({"bindings": [toggle(slot=0)]})
    panel.start_or_pause()
    assert panel.session.workspace is None
    assert "key bindings" in panel.controls.hint.text()


def test_press_does_nothing_when_not_running(panel):
    seed_coupled_robot(panel)
    uid = eligible_rows(panel)[0]["uid"]
    panel.session.bindings = [dict(toggle(uid), range=(-5, 5))]
    seen = []
    panel.session.targets_changed.connect(lambda: seen.append(1))
    panel.session.press(1)
    assert seen == [] and panel.session.targets == {}
