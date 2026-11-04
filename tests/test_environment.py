import pytest
from core.scene import Scene
from newton.model import box,prepare
from newton.worker import World,environment_override


def run(groups,**options):
    scene = Scene();scene.groups = groups
    _,bodies,_ = prepare(scene)
    world = World();world.load(dict(bodies=bodies,**options))
    return world


def advance(world,seconds=1):
    for _ in range(round(seconds*30)):result = world.step(8)
    return result["poses"]


def test_local_gravity_changes_only_its_body():
    bodies = [box("normal",(0,0,10),(1,1,1)),
              box("weightless",(4,0,10),(1,1,1),simulation_override=dict(gravity=[0,0,0])),
              box("sideways",(8,0,10),(1,1,1),simulation_override=dict(gravity=[2,0,0]))]
    world = run(bodies,floor=False)
    try:
        poses = advance(world)
        assert poses[bodies[0].uid][0][2] == pytest.approx(10-9.81/2,abs=.03)
        assert poses[bodies[1].uid][0] == pytest.approx([4,0,10],abs=1e-5)
        assert poses[bodies[2].uid][0] == pytest.approx([9,0,10],abs=.01)
    finally:world.close()


@pytest.mark.parametrize("global_floor",[True,False])
def test_ground_override_is_independent_of_global_ground(global_floor):
    supported = box("ground",(0,0,2),(1,1,1),simulation_override=dict(floor=True))
    falling = box("no ground",(4,0,2),(1,1,1),simulation_override=dict(floor=False))
    upper = box("stack",(0,0,4),(1,1,1),simulation_override=dict(floor=False))
    world = run([supported,falling,upper],floor=global_floor)
    try:
        poses = advance(world,2)
        assert poses[supported.uid][0][2] == pytest.approx(.5,abs=.03)
        assert poses[upper.uid][0][2] == pytest.approx(1.5,abs=.03)
        assert poses[falling.uid][0][2] < -10
    finally:world.close()


@pytest.mark.parametrize("local",[False,True])
def test_damping_reduces_translation_and_rotation(local):
    damping = dict(linear_damping=2,angular_damping=2)
    body = box("damped",(0,0,10),(1,1,1),**(dict(simulation_override=damping) if local else {}))
    world = run([body],floor=False,gravity=0,**({} if local else damping))
    try:
        world.data.qvel[:] = [1,0,0,0,0,1]
        advance(world)
        assert world.data.qvel[0] == pytest.approx(.135,abs=.01)
        assert world.data.qvel[5] == pytest.approx(.135,abs=.01)
    finally:world.close()


@pytest.mark.parametrize("raw",[False,dict(gravity=[0,0,float("nan")]),dict(linear_damping=-1),dict(angular_damping=101),dict(floor="yes")])
def test_invalid_environment_override_rejected(raw):
    with pytest.raises(ValueError):environment_override(raw)


def test_sun_and_planet_orbit_around_shared_centre():
    from scripts.solar_system import build,validate
    validate(build())


def test_attraction_is_finite_at_coincident_centres():
    import numpy as np
    a = box("source",(0,0,10),(1,1,1),simulation_override=dict(attraction=10,softening=.1))
    b = box("target",(0,0,10),(1,1,1))
    world = run([a,b],gravity=0,floor=False)
    try:
        advance(world,.1)
        assert np.isfinite(world.data.qvel).all()
    finally:world.close()


def test_initial_velocity_restored_on_reload():
    body = box("moving",(0,0,10),(1,1,1),simulation_override=dict(initial_velocity=[0,2,0]))
    world = run([body],gravity=0,floor=False)
    try:
        assert advance(world)[body.uid][0] == pytest.approx([0,2,10],abs=.001)
        scene = Scene();scene.groups = [body]
        _,bodies,_ = prepare(scene)
        world.load(dict(bodies=bodies,gravity=0,floor=False))
        assert advance(world)[body.uid][0] == pytest.approx([0,2,10],abs=.001)
    finally:world.close()
