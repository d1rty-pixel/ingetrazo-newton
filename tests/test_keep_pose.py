import copy

import pytest
from PySide6.QtCore import QSettings

from newton import keep_pose
from test_interface import panel, seed_coupled_robot, wait  # noqa: F401 (fixture)


@pytest.fixture(autouse=True)
def clean_settings():
    st = QSettings()
    old = st.value(keep_pose.SETTING)
    st.remove(keep_pose.SETTING)
    yield
    st.remove(keep_pose.SETTING) if old is None else st.setValue(keep_pose.SETTING, old)
    st.sync()


def state(panel):
    return {g.uid: (None if g.xform is None else tuple(g.xform.data()), tuple(v.position.toTuple() for v in g.mesh.vertices),
                    copy.deepcopy(g.ext)) for g in panel.app.scene.groups}


def same(a, b):
    """Equal up to the float32 rounding of undoing a baked vertex move."""
    if a.keys() != b.keys():
        return False
    return all(a[k][0] == b[k][0] and a[k][2] == b[k][2]
               and all(abs(x - y) < 1e-5 for p, q in zip(a[k][1], b[k][1]) for x, y in zip(p, q)) for k in a)


def run(panel, qtapp, seconds=1.0):
    """Start and drive every limited joint to its upper limit, so bodies really move."""
    times = []
    panel.session.frame.connect(times.append)
    panel.start_or_pause()
    wait(qtapp, lambda: panel.session.ready)
    for row in panel.control_rows:
        if row["limited"] and row["uid"] in panel.session.targets:
            panel.session.set_target(row["uid"], row["upper"])
    start = len(times)
    wait(qtapp, lambda: len(times) > start and times[-1] - times[start] > seconds)


def run_and_reset(panel, qtapp, seconds=1.0):
    run(panel, qtapp, seconds)
    panel.session.reset()
    wait(qtapp, lambda: not panel.session.workspace)


def test_reset_restores_the_model_by_default(panel, qtapp):
    seed_coupled_robot(panel)
    before = state(panel)
    run_and_reset(panel, qtapp)
    assert state(panel) == before


def test_reset_writes_the_pose_as_one_undo_step_when_kept(panel, qtapp):
    seed_coupled_robot(panel)
    panel.controls.keep_pose.setChecked(True)
    before = state(panel)
    run_and_reset(panel, qtapp)
    after = state(panel)
    assert after != before
    assert any(a[0] != before[uid][0] or a[1] != before[uid][1] for uid, a in after.items())
    assert "written into the model" in panel.controls.hint.text()
    panel.app.viewport.history.undo()
    assert same(state(panel), before)
    panel.app.viewport.history.redo()
    assert same(state(panel), after)


def test_the_joint_frame_and_its_axis_object_move_with_the_body(panel, qtapp):
    from newton.axis_objects import markers, placement
    seed_coupled_robot(panel)
    panel.controls.keep_pose.setChecked(True)
    pivots = {g.uid: tuple(g.ext["newton"]["joint"]["pivot"]) for g in panel.app.scene.groups if (g.ext or {}).get("newton", {}).get("joint")}
    run_and_reset(panel, qtapp)
    moved = {g.uid: tuple(g.ext["newton"]["joint"]["pivot"]) for g in panel.app.scene.groups if (g.ext or {}).get("newton", {}).get("joint")}
    assert moved != pivots
    for marker in markers(panel.app.scene):
        owner = next((g for g in panel.app.scene.groups if g.uid == marker.ext["newton"].get("axis_of")), None)
        if owner is not None:
            assert all(abs(a - b) < 1e-4 for a, b in zip(placement(marker)[0], owner.ext["newton"]["joint"]["pivot"]))


def test_a_locked_body_keeps_nothing_and_says_why(panel, qtapp):
    seed_coupled_robot(panel)
    panel.controls.keep_pose.setChecked(True)
    before = state(panel)
    run(panel, qtapp)
    moving = next(row["uid"] for row in panel.control_rows if row["limited"] and row["uid"] in panel.session.targets)
    next(g for g in panel.app.window._parked["scene"].groups if g.uid == moving).locked = True
    panel.session.reset()
    wait(qtapp, lambda: not panel.session.workspace)
    text = panel.controls.banner_text.text() if not panel.controls.banner.isHidden() else panel.controls.hint.text()
    assert "was not kept" in text and "locked" in text
    assert state(panel) == before


def test_a_failure_never_keeps_the_pose(panel, qtapp):
    seed_coupled_robot(panel)
    panel.controls.keep_pose.setChecked(True)
    before = state(panel)
    run(panel, qtapp)
    panel.session.fail("boom")
    wait(qtapp, lambda: not panel.session.workspace)
    assert state(panel) == before
