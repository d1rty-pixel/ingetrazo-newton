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
    from scripts.models.solar_system import build,validate
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


def attraction_scene():
    attract = lambda mu,softening:dict(simulation_override=dict(attraction=mu,softening=softening))
    hinge = lambda pivot:dict(type="hinge",pivot=pivot,axis=[0,1,1])
    return [box("heavy",(0,0,10),(1,1,1),mass=5,**attract(3,.2)),
            box("light",(3,1,11),(.5,.5,.5),mass=.5,**attract(.4,.05)),
            box("coincident",(3,1,11),(.4,.4,.4),mass=2,**attract(1.5,0)),
            box("passive",(-2,4,9),(1,1,1),mass=3),
            box("hinged",(6,0,10),(2,.2,.2),mass=1.5,joint=hinge([5,0,10]),**attract(.7,.1))]


def test_attraction_matches_per_pair_jacobians():
    import numpy as np
    world = run(attraction_scene(),gravity=0,floor=False)
    try:
        world.data.qpos[-1] = .6
        world.mj.mj_fwdPosition(world.model,world.data)
        expected = np.zeros(world.model.nv)
        for source,mu,softening in world.attractors:
            for target in world.bodies.values():
                if target==source:continue
                delta = world.data.xipos[source]-world.data.xipos[target]
                distance2 = float(delta@delta)+softening**2
                if distance2<1e-18:continue
                jp = np.zeros((3,world.model.nv))
                world.mj.mj_jacBodyCom(world.model,world.data,jp,None,target)
                expected += jp.T@(world.model.body_mass[target]*mu*delta/distance2**1.5)
        world.data.qfrc_applied[:] = 0
        world.apply_attraction()
        assert expected[-1]!=0
        np.testing.assert_allclose(world.data.qfrc_applied,expected,rtol=1e-12,atol=1e-12*np.abs(expected).max())
    finally:world.close()


def test_mutual_attraction_conserves_linear_momentum():
    import numpy as np
    # Equal G and softening make every pair force reciprocal.
    bodies = [box(f"b{i}",(3*i,(-1)**i,10+i%3),(.5,.5,.5),mass=1+i,
                  simulation_override=dict(attraction=2*(1+i),softening=.1,initial_velocity=[0,.1*i,0]))
              for i in range(4)]
    world = run(bodies,gravity=0,floor=False)
    def momentum():
        world.mj.mj_subtreeVel(world.model,world.data)
        return world.model.body_subtreemass[0]*world.data.subtree_linvel[0].copy()
    try:
        before = momentum()
        advance(world,2)
        assert np.abs(world.data.qvel).max()>.5
        np.testing.assert_allclose(momentum(),before,atol=1e-9)
    finally:world.close()
