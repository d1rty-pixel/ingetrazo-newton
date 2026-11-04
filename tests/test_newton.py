from demo_support import seed_demo
import copy
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtGui import QMatrix4x4, QVector3D
from core.scene import Scene
from core.group import Group, world_mesh
from core.history import History
from newton.model import KEY, Configure, AddDemo, box, demo, prepare
from newton.worker import World


@pytest.fixture
def world():
    w = World()
    yield w
    w.close()


def advance(world, seconds):
    for _ in range(round(seconds*240/8)):
        result = world.step(8)
    return result


def specs(groups):
    scene = Scene()
    scene.groups = groups
    return prepare(scene)


def test_falling_body_lands_on_floor_and_static_does_not_move(world):
    falling = box("fall", (0,0,3), (1,1,1), restitution=0)
    static = box("static", (4,0,3), (1,1,1), mode="static")
    _, bodies, _ = specs([falling, static])
    world.load(dict(bodies=bodies, floor=True))
    early = advance(world, .2)
    assert .1 < 3-early["poses"][falling.uid][0][2] < .3
    final = advance(world, 3)
    assert final["poses"][falling.uid][0][2] == pytest.approx(.5, abs=.02)
    assert final["poses"][static.uid][0] == pytest.approx([4,0,3])


def test_pendulum_rotates_but_anchor_stays_fixed(world):
    g = demo("Pendel")[0]
    _, bodies, _ = specs([g])
    world.load(dict(bodies=bodies, floor=False))
    poses = advance(world, .5)["poses"][g.uid]
    assert poses[0] == pytest.approx([0,0,3.2])
    assert abs(poses[1][1]) > .05


def test_motor_drives_wheel_and_reinit_resets(world):
    g = demo("Motorisiertes Rad")[0]
    _, bodies, _ = specs([g])
    initial = world.load(dict(bodies=bodies, floor=True))
    final = advance(world, .5)
    assert final["poses"][g.uid][0] == pytest.approx([0,0,1.5])
    assert abs(final["poses"][g.uid][1][1]) > .3
    reset = world.load(dict(bodies=bodies, floor=True))
    assert reset == initial


def test_body_body_contacts_keep_two_boxes_separate(world):
    groups = [box("lower", (0,0,.5), (1,1,1), restitution=0),
              box("upper", (0,0,2), (1,1,1), restitution=0)]
    _, bodies, _ = specs(groups)
    world.load(dict(bodies=bodies, floor=True))
    poses = advance(world, 3)["poses"]
    assert poses[groups[0].uid][0][2] == pytest.approx(.5, abs=.03)
    assert poses[groups[1].uid][0][2] == pytest.approx(1.5, abs=.03)


def test_rotated_cuboid_hull_uses_exact_box_contacts_without_inflating_it(world):
    import numpy as np
    g = box("rotated",(0,0,1),(.045,.16,.35),shape="hull")
    g.xform.rotate(27,0,0,1)
    _,bodies,_ = specs([g])
    world.load(dict(bodies=bodies))
    geom = next(i for i in range(world.model.ngeom) if world.model.geom_bodyid[i]==world.bodies[g.uid])
    assert world.model.geom_type[geom]==world.mj.mjtGeom.mjGEOM_BOX
    assert sorted(world.model.geom_size[geom])==pytest.approx([.0225,.08,.175],abs=1e-6)
    orientation = np.empty(9)
    world.mj.mju_quat2Mat(orientation,world.model.geom_quat[geom])
    rotation = orientation.reshape(3,3)
    actual = np.array(bodies[0]["vertices"])
    local = (actual-world.model.geom_pos[geom])@rotation
    assert np.abs(local)==pytest.approx(np.tile(world.model.geom_size[geom],(8,1)),abs=1e-6)


def test_non_rectangular_hull_is_not_replaced_with_a_box(world):
    import itertools
    vertices = [list(p) for p in itertools.product((-.1,.1),repeat=3)]
    vertices[0][0] += .03
    assert world.exact_box(vertices) is None


def test_thirty_dominoes_fall_then_settle_without_persistent_rocking(world):
    import numpy as np
    from scripts.domino import build
    _,bodies,_ = prepare(build())
    world.load(dict(bodies=bodies))
    positions,orientations = [],[]
    for i in range(150):
        world.step(24)
        if i>=100:
            positions.append(world.data.xpos[2:].copy())
            orientations.append(world.data.xmat[2:].copy())
    assert sum(abs(world.data.xmat[bid][8])<.55 for uid,bid in list(world.bodies.items())[1:])==30
    assert np.max(np.ptp(np.asarray(positions),axis=0))<.001
    assert np.max(np.ptp(np.asarray(orientations),axis=0))<.02


def test_collision_demo_pair_exceptions_and_restore_change_real_contacts(world):
    from scripts.collision_demo import build
    from newton.collision_ui import pair_command
    scene = build()
    _,bodies,_ = prepare(scene)
    initial = world.load(dict(bodies=bodies))
    assert all(c["points"] and c["edges"] for c in initial["colliders"].values())
    a,b = scene.groups[1],scene.groups[3]
    result = advance(world,3)
    assert result["poses"][a.uid][0][2]==pytest.approx(.74,abs=.02)
    assert result["poses"][b.uid][0][2]==pytest.approx(.21,abs=.02)
    command = pair_command(b,scene.groups[4],True)
    command.do(scene)
    world.load(dict(bodies=prepare(scene)[1]))
    result = advance(world,3)
    assert result["poses"][b.uid][0][2]==pytest.approx(.74,abs=.02)
    command.undo(scene)
    assert scene.groups[4].uid in b.ext[KEY]["no_collision"]


def test_collision_inspection_can_compile_a_fully_static_document(world):
    scene = Scene();g = box("static",(1,2,3),(.2,.3,.4),mode="static")
    scene.groups.append(g)
    _,bodies,_ = prepare(scene,require_movable=False)
    result = world.load(dict(bodies=bodies,floor=False))
    assert len(result["colliders"][g.uid]["edges"])==12
    assert result["poses"][g.uid][0]==pytest.approx([1,2,3])


def test_fifty_independent_bodies_remain_finite_and_land(world):
    groups = [box(str(i), (2*(i%10), 2*(i//10), 2+i*.02), (.5,.5,.5), restitution=0)
              for i in range(50)]
    _, bodies, _ = specs(groups)
    world.load(dict(bodies=bodies, floor=True))
    poses = advance(world, 3)["poses"]
    assert len(poses) == 50
    for g in groups:
        assert all(math.isfinite(v) for v in poses[g.uid][0] + poses[g.uid][1])
        assert poses[g.uid][0][2] == pytest.approx(.25, abs=.02)


def test_adapter_bakes_nested_mirrored_scaled_geometry_without_mutation():
    child = box("child", (1,2,3), (1,2,3))
    child.xform.scale(-2, .5, 1.3)
    parent = Group(name="parent")
    parent.adopt([child])
    parent.xform.translate(10,20,30)
    parent.ext = {KEY: dict(mode="dynamic", shape="hull", mass=2)}
    before = [tuple(v.position.toTuple()) for v in world_mesh(parent).vertices]
    source = Scene()
    source.groups = [parent]
    scene, bodies, movers = prepare(source)
    after = [tuple(v.position.toTuple()) for v in world_mesh(parent).vertices]
    cloned = [tuple(v.position.toTuple()) for v in world_mesh(movers[parent.uid]).vertices]
    assert after == before
    for a, b in zip(cloned, before):
        assert a == pytest.approx(b, abs=1e-4)
    assert movers[parent.uid].mesh is not child.mesh
    assert bodies[0]["mass"] == 2


def test_config_and_demo_are_undoable_and_settings_survive_igz(tmp_path):
    from formats import igz
    scene = Scene()
    hist = History(scene)
    groups = demo("Pendel")
    hist.execute(AddDemo(groups))
    original = copy.deepcopy(groups[0].ext)
    hist.execute(Configure(groups, dict(mode="static", mass=3)))
    assert groups[0].ext[KEY]["mode"] == "static"
    hist.undo()
    assert groups[0].ext == original
    path = tmp_path / "newton.igz"
    igz.save_scene(scene, path)
    loaded = Scene()
    igz.load_into(loaded, path)
    assert loaded.groups[0].ext == original
    hist.undo()
    assert scene.groups == []
    hist.redo()
    assert len(scene.groups) == 1


def test_unconfigured_groups_are_static_ignored_and_hidden_omitted():
    dynamic = box("dynamic", (0,0,2), (1,1,1))
    unconfigured = box("static", (3,0,2), (1,1,1))
    unconfigured.ext = None
    ignored = box("ignored", (6,0,2), (1,1,1), mode="ignore")
    hidden = box("hidden", (9,0,2), (1,1,1))
    hidden.hidden = True
    scene, bodies, movers = specs([dynamic, unconfigured, ignored, hidden])
    assert len(scene.groups) == 3
    assert len(bodies) == 2
    assert bodies[1]["mass"] == 0
    assert ignored.uid not in movers


def test_worker_protocol_recovers_from_invalid_command():
    worker = Path(__file__).resolve().parents[1]/"newton"/"worker.py"
    _, bodies, _ = specs([box("fall", (0,0,3), (1,1,1))])
    payload = "\n".join(json.dumps(r) for r in [dict(op="init", bodies=bodies),
        dict(op="nonsense"), dict(op="step", count=8), dict(op="quit")]) + "\n"
    result = subprocess.run([sys.executable, "-u", str(worker)], input=payload,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    replies = [json.loads(s.split(":",1)[1]) for s in result.stdout.splitlines()
               if s.startswith("IGPHYSICS:")]
    assert [r["ok"] for r in replies] == [True, False, True]
    assert replies[2]["time"] == pytest.approx(8/240)


def test_real_extension_loader_and_mainwindow_session(qtapp, monkeypatch):
    from core import extensions
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [root])
    from views.main_window import MainWindow
    win = MainWindow()
    try:
        dock = next(d for d in win._extension_docks if d.objectName() == "extension_newton")
        panel = dock.widget()
        panel.python.setText(sys.executable)
        seed_demo(panel,"Pendel")
        original = win.viewport.scene
        pendulum = next(g for g in original.groups if KEY in (g.ext or {}))
        original_matrix = list(pendulum.xform.data())
        old_history = win.viewport.history
        panel.start_or_pause()
        deadline = time.monotonic()+15
        while not panel.session.ready and time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        assert panel.session.ready, panel.status.text()
        deadline = time.monotonic()+.3
        while time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        assert win.viewport.scene is not original
        assert list(pendulum.xform.data()) == original_matrix
        panel.session.toggle()
        assert not panel.session.running
        # Drain the single outstanding step, then verify paused time stays put.
        deadline = time.monotonic()+.1
        while time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        clock = panel.clock.text()
        deadline = time.monotonic()+.1
        while time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        assert panel.clock.text() == clock
        panel.session.reset()
        assert panel.session.process is None
        assert win.viewport.scene is original
        assert win.viewport.history is old_history
        assert list(pendulum.xform.data()) == original_matrix
        # An unexpected external-engine crash must also restore the model.
        panel.start_or_pause()
        deadline = time.monotonic()+15
        while not panel.session.ready and time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        assert panel.session.ready, panel.status.text()
        panel.session.process.kill()
        deadline = time.monotonic()+3
        while panel.session.workspace and time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        assert panel.session.workspace is None
        assert win.viewport.scene is original
        assert list(pendulum.xform.data()) == original_matrix
    finally:
        if win.workspace():
            win.leave_workspace()
        win._saved_version = win.viewport.scene.version
        win.close()
