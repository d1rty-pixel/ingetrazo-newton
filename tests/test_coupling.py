import copy
import math
import pytest
from scripts.models.robot_arm import build
from newton.model import KEY,prepare,box,ensure_axis_layer,AXES_LAYER
from newton.worker import World,joint_settings,resolve_couplings


def robot_world(contact=False):
    scene = build(True)
    jaws = [g for g in scene.groups if "jaw" in g.name]
    if contact:
        # Held in place to apply a deliberately asymmetric contact load.
        scene.groups.append(box("Stop",(1.32,-.004,1.52),(.06,.04,.06),mode="static",friction=1.2))
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=0,floor=False))
    return scene,jaws,world


@pytest.mark.parametrize("contact",[False,True])
def test_gripper_equality_keeps_center_under_contact_and_reopens(contact):
    scene,jaws,world = robot_world(contact)
    try:
        for target in (.05,0):
            for _ in range(160):
                result = world.step(8,{jaws[0].uid:target})
            positions = [result["joints"][g.uid]["position"] for g in jaws]
            assert positions[0]==pytest.approx(positions[1],abs=2e-4)
            if not contact or target==0:
                assert positions[0]==pytest.approx(target,abs=.001)
            else:
                assert .01<positions[0]<.049
                assert world.data.ncon>=2
                pairs = [{int(world.model.geom_bodyid[c.geom1]),int(world.model.geom_bodyid[c.geom2])}
                         for c in world.data.contact]
                stop = world.bodies[scene.groups[-1].uid]
                assert all({stop,world.bodies[g.uid]} in pairs for g in jaws)
        with pytest.raises(ValueError,match="shared"):
            world.step(8,{jaws[1].uid:.02})
        with pytest.raises(ValueError,match="Actuated"):
            world.step(8,drag=dict(uid=jaws[1].uid,id=1,point=[0,0,0],target=[0,0,1]))
    finally:
        world.close()


def test_negative_ratio_transmits_opposite_travel_in_the_newton_solver():
    from core.scene import Scene
    a = box("Master",(0,0,1),(.1,.1,.1),joint=dict(type="slide",drive="position",pivot=[0,0,1],
            axis=[1,0,0],force=50,lower=-.1,upper=.1))
    b = box("Follower",(0,1,1),(.1,.1,.1),joint=dict(type="slide",drive="free",pivot=[0,1,1],
            axis=[1,0,0],force=0,lower=-.2,upper=.2,coupling=dict(master=a.uid,ratio=-2)))
    scene = Scene();scene.groups.extend([a,b])
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=0,floor=False))
    for _ in range(120):
        result = world.step(8,{a.uid:.07})
    assert result["joints"][a.uid]["position"]==pytest.approx(.07,abs=.001)
    assert result["joints"][b.uid]["position"]==pytest.approx(-.14,abs=.001)
    world.close()


def test_coupling_intersects_limits_speed_and_rejects_invalid_links():
    def j(**kw):
        return joint_settings(dict(type="slide",drive="position",pivot=[0,0,0],axis=[1,0,0],
                                   force=30,lower=-.2,upper=.3,max_speed=.2,acceleration=1,**kw))
    master = j()
    follower = j(coupling=dict(master="a",ratio=-2))
    follower.update(lower=-.1,upper=.2,max_speed=.1,acceleration=.5)
    result = resolve_couplings(dict(a=master,b=follower))
    assert result["a"]["lower"]==pytest.approx(-.1)
    assert result["a"]["upper"]==pytest.approx(.05)
    assert result["a"]["max_speed"]==pytest.approx(.05)
    assert result["a"]["acceleration"]==pytest.approx(.25)
    for link in ("missing","b"):
        with pytest.raises(ValueError):
            resolve_couplings(dict(a=j(),b=j(coupling=dict(master=link,ratio=1))))
    with pytest.raises(ValueError,match="cycles"):
        resolve_couplings(dict(a=j(coupling=dict(master="b",ratio=1)),b=j(coupling=dict(master="a",ratio=1))))
    with pytest.raises(ValueError,match="Invalid"):
        j(coupling=dict(master="a",ratio=0))


def test_coupling_and_reserved_layer_survive_native_file_roundtrip(tmp_path):
    from formats import igz
    from core.scene import Scene
    scene = build(True)
    layer = ensure_axis_layer(scene)
    layer.visible = False
    assert ensure_axis_layer(scene) is layer
    assert len([l for l in scene.layers if l.name==AXES_LAYER])==1
    assert all(g.layer!=AXES_LAYER for g in scene.groups)
    path = tmp_path/"coupled.igz"
    igz.save_scene(scene,path)
    loaded = Scene()
    igz.load_into(loaded,path)
    assert not next(l for l in loaded.layers if l.name==AXES_LAYER).visible
    assert [g.ext for g in loaded.groups]==[g.ext for g in scene.groups]
    _,specs,_ = prepare(loaded)
    world = World()
    world.load(dict(bodies=specs))
    assert len(world.motors)==6 and world.model.neq==1
    world.close()


def test_motor_leader_turns_follower_continuously_with_ratio():
    from core.scene import Scene
    a = box("Crank",(0,0,1),(.1,.1,.1),joint=dict(type="hinge",drive="velocity",pivot=[.05,.05,1.05],
            axis=[0,1,0],force=20,target=3,max_speed=3,acceleration=6))
    b = box("Wheel",(0,1,1),(.1,.1,.1),joint=dict(type="hinge",drive="free",pivot=[.05,1.05,1.05],
            axis=[0,1,0],force=0,limited=False,max_speed=50,acceleration=100,
            coupling=dict(master=a.uid,ratio=-2.5)))
    scene = Scene();scene.groups.extend([a,b])
    _,specs,_ = prepare(scene)
    world = World()
    world.load(dict(bodies=specs,gravity=0,floor=False))
    try:
        for _ in range(90):
            result = world.step(8)
        crank,wheel = (result["joints"][g.uid] for g in (a,b))
        # Past one turn: a motor leader is not held at a position like a servo.
        assert crank["position"]>2*math.pi
        assert crank["velocity"]==pytest.approx(3,abs=.05)
        assert wheel["position"]==pytest.approx(-2.5*crank["position"],abs=.01)
        with pytest.raises(ValueError,match="shared"):
            world.step(8,{b.uid:1})
    finally:
        world.close()


def test_motor_leader_keeps_its_speed_target_and_free_leaders_stay_rejected():
    def j(**kw):
        return joint_settings(dict(dict(type="hinge",pivot=[0,0,0],axis=[0,1,0],force=10),**kw))
    follower = j(drive="free",limited=True,lower=-1,upper=1,max_speed=4,coupling=dict(master="a",ratio=2))
    motor = j(drive="velocity",target=3,max_speed=3)
    result = resolve_couplings(dict(a=motor,b=follower))["a"]
    assert result["limited"] and (result["lower"],result["upper"])==pytest.approx((-.5,.5))
    assert result["target"]==3 and result["max_speed"]==pytest.approx(2)
    with pytest.raises(ValueError,match="servo or motor"):
        resolve_couplings(dict(a=j(drive="free"),b=j(drive="free",coupling=dict(master="a",ratio=1))))
