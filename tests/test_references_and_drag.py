import math
from types import SimpleNamespace
import pytest
from PySide6.QtGui import QVector3D,QMatrix4x4
from core.scene import Scene
from core.group import Group,world_mesh
from core.history import History,MoveGroupCommand,RotateGroupCommand,CompoundCommand
from newton.model import KEY,box,prepare,Configure
from newton.references import install,reference,validate_reference
from newton.worker import World


def center(g):
    pts = [v.position for v in world_mesh(g).vertices]
    return [sum(p.toTuple()[i] for p in pts)/len(pts) for i in range(3)]


def setup_chain(classic=False):
    scene = Scene()
    parent = box("Base",(0,0,3),(.3,.3,.3))
    child = box("Arm",(1,0,3),(.3,.3,.3))
    grandchild = box("Gripper",(2,0,3),(.3,.3,.3))
    if classic:
        parent = Group(world_mesh(parent),"Classic base")
    child.ext[KEY]["reference"] = parent.uid
    child.ext[KEY]["joint"] = dict(pivot=[.5,0,3],axis=[0,0,1],drive="free",parent=parent.uid)
    grandchild.ext[KEY]["reference"] = child.uid
    scene.groups = [parent,child,grandchild]
    hist = History(scene)
    previews = []
    vp = SimpleNamespace(scene=scene,history=hist,
        begin_groups_preview=lambda groups,external=False:previews.append((list(groups),external)),
        end_groups_preview=lambda:None)
    install(vp)
    return scene,hist,parent,child,grandchild,vp,previews


@pytest.mark.parametrize("classic",[False,True])
def test_native_parent_move_carries_descendants_and_joint_in_one_undo(classic):
    scene,hist,parent,child,grandchild,_,_ = setup_chain(classic)
    hist.execute(MoveGroupCommand(parent,QVector3D(3,4,0)))
    assert center(child)==pytest.approx([4,4,3])
    assert center(grandchild)==pytest.approx([5,4,3])
    assert child.ext[KEY]["joint"]["pivot"]==pytest.approx([3.5,4,3])
    assert len(hist.undo_stack)==1
    hist.undo()
    assert center(parent)==pytest.approx([0,0,3])
    assert center(child)==pytest.approx([1,0,3])
    assert child.ext[KEY]["joint"]["pivot"]==pytest.approx([.5,0,3])
    hist.redo()
    assert center(child)==pytest.approx([4,4,3])


def test_child_move_leaves_parent_and_reference_unchanged():
    scene,hist,parent,child,grandchild,_,_ = setup_chain()
    hist.execute(MoveGroupCommand(child,QVector3D(0,2,0)))
    assert center(parent)==pytest.approx([0,0,3])
    assert center(child)==pytest.approx([1,2,3])
    assert center(grandchild)==pytest.approx([2,2,3])
    assert reference(child)==parent.uid


def test_multiselection_does_not_double_move_dependents():
    scene,hist,parent,child,grandchild,_,_ = setup_chain()
    hist.execute(CompoundCommand([MoveGroupCommand(parent,QVector3D(2,0,0)),
                                 MoveGroupCommand(child,QVector3D(2,0,0))]))
    assert center(child)==pytest.approx([3,0,3])
    assert center(grandchild)==pytest.approx([4,0,3])
    hist.undo()
    assert center(child)==pytest.approx([1,0,3])


def test_reference_rotation_carries_geometry_and_axis():
    scene,hist,parent,child,grandchild,_,_ = setup_chain()
    hist.execute(RotateGroupCommand(parent,QVector3D(0,0,3),QVector3D(0,1,0),90))
    assert center(child)==pytest.approx([0,0,2],abs=1e-5)
    assert child.ext[KEY]["joint"]["axis"]==pytest.approx([1,0,0],abs=1e-5)
    hist.undo()
    assert center(child)==pytest.approx([1,0,3],abs=1e-5)


def test_preview_and_detach_match_native_move():
    scene,hist,parent,child,grandchild,vp,previews = setup_chain()
    vp.begin_groups_preview([parent])
    assert previews[-1][0]==[parent,child,grandchild]
    vp.begin_groups_preview([parent],external=True)
    assert previews[-1][0]==[parent]
    hist.execute(Configure([child],dict(reference=None),partial=True))
    hist.execute(MoveGroupCommand(parent,QVector3D(2,0,0)))
    assert center(child)==pytest.approx([1,0,3])
    hist.undo()
    hist.undo()
    assert reference(child)==parent.uid
    with pytest.raises(ValueError,match="cycle"):
        validate_reference(scene,parent,grandchild.uid)


def test_reference_survives_save_reload_and_native_move(tmp_path):
    from formats import igz
    scene,_,parent,child,_,_,_ = setup_chain()
    path = tmp_path/"reference.igz"
    igz.save_scene(scene,path)
    loaded = Scene()
    igz.load_into(loaded,path)
    p,c = loaded.groups[:2]
    hist = History(loaded)
    vp = SimpleNamespace(scene=loaded,history=hist,begin_groups_preview=lambda *a,**kw:None,end_groups_preview=lambda:None)
    install(vp)
    hist.execute(MoveGroupCommand(p,QVector3D(0,1,0)))
    assert reference(c)==p.uid
    assert center(c)==pytest.approx([1,1,3])


@pytest.fixture
def world():
    w = World()
    yield w
    w.close()


def load(world,groups,gravity=0):
    scene = Scene()
    scene.groups = groups
    _,specs,_ = prepare(scene)
    world.load(dict(bodies=specs,floor=False,gravity=gravity))


def test_drag_applies_force_to_passive_body_without_teleporting(world):
    g = box("Cubes",(0,0,3),(.4,.4,.4))
    load(world,[g])
    drag = dict(id=1,uid=g.uid,point=[0,0,3],target=[1,0,3])
    first = world.step(1,drag=drag)["poses"][g.uid][0]
    assert 0<first[0]<.05
    for _ in range(60):
        result = world.step(8,drag=drag)
    assert result["poses"][g.uid][0][0]==pytest.approx(1,abs=.03)
    world.step(8,drag=None)
    assert world.drag is None


def test_drag_drives_passive_hinge_chain(world):
    g = box("Arm",(.5,0,3),(1,.1,.1),joint=dict(
        pivot=[0,0,3],axis=[0,0,1],drive="free"))
    load(world,[g])
    drag = dict(id=1,uid=g.uid,point=[1,0,3],target=[.7,.7,3])
    for _ in range(45):
        result = world.step(8,drag=drag)
    assert result["joints"][g.uid]["position"]>.5
    assert result["poses"][g.uid][0]==pytest.approx([0,0,3])


@pytest.mark.parametrize("mode",["position","velocity"])
def test_engine_rejects_manual_drag_of_driven_bodies(world,mode):
    g = box("Drive",(0,0,3),(.4,.4,.4),joint=dict(
        pivot=[0,0,3],axis=[0,0,1],drive=mode,force=20))
    load(world,[g])
    with pytest.raises(ValueError,match="Actuated"):
        world.step(8,drag=dict(id=1,uid=g.uid,point=[0,0,3],target=[1,0,3]))


def test_reference_without_axis_is_rigid_relative_to_parent_in_simulation(world):
    parent = box("Base",(0,0,3),(.3,.3,.3))
    child = box("Part",(1,0,3),(.3,.3,.3),reference=parent.uid)
    load(world,[parent,child])
    drag = dict(id=1,uid=parent.uid,point=[0,0,3],target=[0,1,3])
    for _ in range(45):
        result = world.step(8,drag=drag)
    a,b = result["poses"][parent.uid][0],result["poses"][child.uid][0]
    assert math.dist(a,b)==pytest.approx(1,abs=.01)
    assert a[1]>.5


def test_fixed_dependent_follows_parent_but_cannot_be_grabbed_itself(world):
    parent = box("Base",(0,0,3),(.3,.3,.3))
    child = box("Bolted fixed",(1,0,3),(.3,.3,.3),reference=parent.uid,mode="static",mass=.5)
    load(world,[parent,child])
    drag = dict(id=1,uid=parent.uid,point=[0,0,3],target=[0,1,3])
    for _ in range(45):
        result = world.step(8,drag=drag)
    a,b = result["poses"][parent.uid][0],result["poses"][child.uid][0]
    assert math.dist(a,b)==pytest.approx(1,abs=.01)
    assert a[1]>.5
    with pytest.raises(ValueError,match="Fixed"):
        world.step(8,drag=dict(id=2,uid=child.uid,point=b,target=[1,1,3]))


def test_motor_reference_respects_acceleration_and_speed_settings(world):
    g = box("Feed",(0,0,3),(.2,.2,.2),joint=dict(
        type="slide",pivot=[0,0,3],axis=[1,0,0],drive="velocity",target=2,
        force=100,max_speed=.5,acceleration=.2,limited=False))
    load(world,[g])
    for _ in range(6):
        world.step(8)
    assert world.motors[g.uid]["command_vel"]==pytest.approx(.04)
    for _ in range(90):
        result = world.step(8)
    assert world.motors[g.uid]["command_vel"]==pytest.approx(.5)
    assert result["joints"][g.uid]["velocity"]<=.51


def test_motor_uses_separate_braking_rate_before_reversing(world):
    g = box("Brake test",(0,0,3),(.2,.2,.2),joint=dict(
        type="slide",pivot=[0,0,3],axis=[1,0,0],drive="velocity",target=0,
        force=100,max_speed=1,acceleration=.4,deceleration=.1,deceleration_sync=False,limited=False))
    load(world,[g])
    for _ in range(30):world.step(8,{g.uid:1})
    assert world.motors[g.uid]["command_vel"]==pytest.approx(.4)
    for _ in range(30):world.step(8,{g.uid:0})
    assert world.motors[g.uid]["command_vel"]==pytest.approx(.3)
    for _ in range(90):world.step(8,{g.uid:-1})
    assert world.motors[g.uid]["command_vel"]==pytest.approx(0,abs=.001)
    for _ in range(30):world.step(8,{g.uid:-1})
    assert world.motors[g.uid]["command_vel"]==pytest.approx(-.4,abs=.002)
