import pytest
import numpy as np
from core.scene import Scene
from core.group import Group,world_mesh
from newton.model import KEY,DEFAULTS,box,prepare
from newton.worker import World


@pytest.mark.parametrize("shape,expected_z",[("compound",.05),("hull",1.1)])
def test_compound_opening_is_a_real_collision_opening(shape,expected_z):
    frame = Group(name="open frame")
    frame.adopt([box("left",(-.45,0,1),(.1,1,.1)),box("right",(.45,0,1),(.1,1,.1)),
                 box("front",(0,-.45,1),(.8,.1,.1)),box("back",(0,.45,1),(.8,.1,.1))])
    frame.ext = {KEY:dict(DEFAULTS,mode="static",shape=shape)}
    falling = box("probe",(0,0,2),(.1,.1,.1),restitution=0)
    scene = Scene();scene.groups = [frame,falling];_,specs,_ = prepare(scene)
    world = World();world.load(dict(bodies=specs,floor=True))
    try:
        for _ in range(75):result = world.step(8)
        assert result["poses"][falling.uid][0][2] == pytest.approx(expected_z,abs=.015)
        if shape=="compound":
            assert world.model.body_geomnum[world.bodies[frame.uid]]==4
            overlay = world.collider_lines()[frame.uid]
            assert overlay["kind"]=="Compound" and len(overlay["points"])==32
            assert world.model.body_mass[world.bodies[frame.uid]] == pytest.approx(1)
    finally:world.close()


def test_energy_chain_links_are_single_rigid_open_frames():
    from scripts.energy_chain import build
    scene = build();_,specs,_ = prepare(scene);world = World();world.load(dict(bodies=specs,floor=False))
    links = [g for g in scene.groups if g.name.startswith("Glied ")]
    try:
        assert len(links)==22 and all(len(g.children)==4 for g in links)
        assert all(world.model.body_geomnum[world.bodies[g.uid]]==4 for g in links)
        assert all(world.collider_lines()[g.uid]["kind"]=="Compound" for g in links)
        assert sum(world.model.body_mass[world.bodies[g.uid]] for g in links) == pytest.approx(22*.048)
        # No artificial collision exemptions between non-neighbouring links.
        assert all(not g.ext[KEY].get("no_collision") for g in links)
        for _ in range(60):world.step(8)
        chain_ids = {world.bodies[g.uid] for g in links}
        assert not any(int(world.model.geom_bodyid[c.geom1]) in chain_ids and int(world.model.geom_bodyid[c.geom2]) in chain_ids for c in world.data.contact[:world.data.ncon])
    finally:world.close()


def test_crank_rod_is_outside_wheel_plane_and_motor_still_drives_it():
    from scripts.crank_carrier import build
    scene = build()
    wheel = next(g for g in scene.groups if g.name.startswith("Speichenrad"))
    rod = next(g for g in scene.groups if g.name=="Pleuelstange")
    wheel_y = max(v.position.y() for part in wheel.children if part.name not in ("Kurbelzapfen","Bolzensicherung") for v in world_mesh(part).vertices)
    rod_y = min(v.position.y() for v in world_mesh(rod).vertices)
    assert rod_y-wheel_y>=.0399
    _,specs,_ = prepare(scene);world = World();world.load(dict(bodies=specs,floor=False))
    shaft = next(g for g in scene.groups if g.name=="Antriebswelle")
    slider = next(g for g in scene.groups if g.name.startswith("Kolbenstange"))
    try:
        for _ in range(120):result = world.step(8)
        assert result["joints"][shaft.uid]["position"]>1.9
        assert result["joints"][slider.uid]["position"]>.1
        assert not any({int(world.model.geom_bodyid[c.geom1]),int(world.model.geom_bodyid[c.geom2])}=={world.bodies[wheel.uid],world.bodies[rod.uid]} for c in world.data.contact[:world.data.ncon])
    finally:world.close()
