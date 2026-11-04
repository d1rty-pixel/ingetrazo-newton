import copy
import math
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D
from core.scene import Scene
from core.history import History
from newton.model import box, demo, prepare, KEY, Configure, joint_rows
from newton.worker import World
from newton.joints import PlacementTool


@pytest.fixture
def world():
    w = World()
    yield w
    w.close()


def load(world, groups, **kwargs):
    source = Scene()
    source.groups = groups
    _, specs, _ = prepare(source)
    return world.load(dict(bodies=specs, floor=False, **kwargs))


def advance(world, seconds, targets=None):
    for _ in range(round(seconds*240/8)):
        result = world.step(8, targets)
    return result


def test_servo_reaches_live_angle_and_holds_under_gravity(world):
    g = box("Arm", (.5,0,2), (1,.15,.15), joint=dict(
        pivot=[0,0,2], axis=[0,1,0], type="hinge", drive="position",
        target=0, force=100, limited=True, lower=-1.5, upper=1.5))
    load(world,[g])
    result = advance(world,2,{g.uid:.7})
    assert result["joints"][g.uid]["position"] == pytest.approx(.7,abs=.01)
    assert result["poses"][g.uid][0] == pytest.approx([0,0,2])
    result = advance(world,2,{g.uid:-.4})
    assert result["joints"][g.uid]["position"] == pytest.approx(-.4,abs=.01)


def test_linear_position_moves_to_target_and_clamps_to_limits(world):
    groups = demo("Linear carriage")
    uid = groups[1].uid
    load(world,groups)
    result = advance(world,2,{uid:.4})
    assert result["joints"][uid]["position"] == pytest.approx(.4,abs=.005)
    assert result["poses"][uid][0] == pytest.approx([.4,0,.55],abs=.005)
    result = advance(world,2,{uid:4})
    assert result["joints"][uid]["position"] == pytest.approx(.7,abs=.005)


def test_passive_linear_axis_falls_only_along_axis(world):
    g = box("Carriage", (1,2,3), (.2,.2,.2), joint=dict(
        type="slide", drive="free", pivot=[1,2,3], axis=[0,0,1],
        limited=True, lower=-1, upper=1))
    load(world,[g])
    result = advance(world,1)
    p = result["poses"][g.uid][0]
    assert p[:2] == pytest.approx([1,2])
    assert p[2] == pytest.approx(2,abs=.02)


def test_linear_velocity_motor_can_reverse(world):
    g = box("Feed", (0,0,3), (.2,.2,.2), joint=dict(
        type="slide", drive="velocity", pivot=[0,0,3], axis=[1,0,0],
        force=100, target=.2, limited=False))
    load(world,[g])
    result = advance(world,1)
    assert result["joints"][g.uid]["velocity"] == pytest.approx(.2,abs=.01)
    result = advance(world,1,{g.uid:-.3})
    assert result["joints"][g.uid]["velocity"] == pytest.approx(-.3,abs=.01)


def test_joint_to_moving_parent_follows_parent_and_preserves_relative_anchor(world):
    parent = box("Carrier", (0,0,5), (.3,.3,.3))
    child = box("Arm", (.6,0,5), (.8,.15,.15), joint=dict(
        parent=parent.uid, type="hinge", drive="position", name="Arm angle",
        pivot=[.2,0,5], axis=[0,0,1], target=.5, force=100))
    load(world,[child,parent])  # deliberately child before parent in source
    result = advance(world,1)
    a,b = result["poses"][parent.uid][0],result["poses"][child.uid][0]
    assert a[2] < 4
    assert math.dist(a,b) == pytest.approx(.2,abs=.005)
    assert result["joints"][child.uid]["position"] == pytest.approx(.5,abs=.04)


def test_cycle_and_missing_parent_are_explicit_errors(world):
    a = box("A", (0,0,2), (.2,.2,.2))
    b = box("B", (1,0,2), (.2,.2,.2))
    a.ext[KEY]["joint"] = dict(parent=b.uid, pivot=[0,0,2], axis=[0,1,0])
    b.ext[KEY]["joint"] = dict(parent=a.uid, pivot=[1,0,2], axis=[0,1,0])
    with pytest.raises(ValueError,match="cycle"):
        load(world,[a,b])
    a.ext[KEY]["joint"]["parent"] = "missing"
    with pytest.raises(ValueError,match="missing"):
        load(world,[a])


def test_passive_hinge_has_no_drive_and_legacy_motor_migrates(world):
    g = demo("Pendulum")[0]
    load(world,[g])
    assert world.motors[g.uid]["drive"] == "free"
    g = demo("Motorised wheel")[0]
    load(world,[g])
    assert world.motors[g.uid]["drive"] == "velocity"
    assert world.motors[g.uid]["target"] == 3


def test_partial_body_changes_preserve_joint_name_parent_and_other_properties():
    scene = Scene()
    scene.groups = demo("Servo door")
    g = scene.groups[1]
    old = copy.deepcopy(g.ext[KEY]["joint"])
    hist = History(scene)
    hist.execute(Configure([g],dict(mass=3),partial=True))
    assert g.ext[KEY]["joint"] == old
    assert joint_rows(scene)[0]["name"] == "Open door"
    hist.undo()
    assert g.ext[KEY]["mass"] == 1


def test_placement_uses_two_snapped_points_and_axis_shortcut(qtapp):
    finished, cancelled = [], []
    viewport = SimpleNamespace(flash_status=lambda *a:None, update=lambda:None)
    ctx = lambda p: SimpleNamespace(world=QVector3D(*p),viewport=viewport)
    tool = PlacementTool(lambda a,b,z:finished.append((a,b)), lambda:cancelled.append(True))
    tool.on_click(ctx((1,2,3)))
    tool.on_click(ctx((1,4,3)))
    qtapp.processEvents()
    assert finished == [([1,2,3],[0,1,0])]
    assert not cancelled
    finished.clear()
    tool = PlacementTool(lambda a,b,z:finished.append((a,b)),lambda:cancelled.append(True))
    tool.on_click(ctx((2,3,4)))
    assert tool.on_key(viewport,Qt.Key_Z,Qt.NoModifier)
    qtapp.processEvents()
    assert finished == [([2,3,4],[0,0,1])]
    tool = PlacementTool(lambda *a:None,lambda:cancelled.append(True))
    tool.on_cancel(viewport)
    qtapp.processEvents()
    assert cancelled == [True]


def test_zero_direction_lies_in_the_turning_plane_and_snaps_to_projected_world_axes(qtapp):
    finished = []
    viewport = SimpleNamespace(flash_status=lambda *a:None,update=lambda:None)
    tool = PlacementTool(lambda a,b,z:finished.append(z),lambda:None,preview={},zero=True)
    tool.on_click(SimpleNamespace(world=QVector3D(0,0,0),viewport=viewport))
    tool.on_click(SimpleNamespace(world=QVector3D(1,0,1),viewport=viewport))  # tilted 45° axis
    plane = tool.drag_plane(viewport)
    assert plane[0]==QVector3D(0,0,0) and plane[1].toTuple()==pytest.approx((.7071,0,.7071),abs=1e-4)
    near_y = QVector3D(math.sin(math.radians(2)),math.cos(math.radians(2)),0)
    assert tool.perpendicular(near_y)==pytest.approx([0,1,0],abs=1e-6)
    # World X projected into the tilted plane is (1,0,-1)/√2.
    assert tool.perpendicular(QVector3D(1,0.03,-1))==pytest.approx([.7071,0,-.7071],abs=1e-4)
    assert tool.perpendicular(QVector3D(1,.3,-1))[1]>.1,"far from an axis the direction stays free"
    tool.on_key(viewport,Qt.Key_Y,Qt.NoModifier)
    qtapp.processEvents()
    assert finished[0]==pytest.approx([0,1,0])
    assert tool.drag_plane(viewport) is None
