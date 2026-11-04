import copy
import math
import numpy as np
import pytest
from core.scene import Scene
from formats import igz
from newton.model import KEY,prepare
from newton.flexible import make,segment_uid
from newton.worker import World
from scripts.flexible_demos import rope_cable,chain,carrier


def loaded(scene):
    _,specs,movers = prepare(scene)
    world = World();world.load(dict(bodies=specs,gravity=-9.81,floor=False))
    return world,movers


def advance(world,seconds,targets=None):
    for _ in range(round(seconds*30)):result = world.step(8,targets)
    return result


def test_native_elasticity_has_independent_bodies_and_preserves_source(tmp_path):
    source = rope_cable()
    before = [copy.deepcopy(g.ext) for g in source.groups]
    path = tmp_path/"flexible.igz";igz.save_scene(source,path)
    restored = Scene();igz.load_into(restored,path)
    assert [g.ext for g in restored.groups] == before
    world,movers = loaded(restored)
    try:
        assert world.model.nplugin == 2
        assert set(world.poses()["poses"]) == set(movers)
        assert world.substeps>1
        advance(world,5)
        assert world.data.time == pytest.approx(5)
        assert [g.ext for g in source.groups] == before
        assert all(c["kind"]=="Capsule" for uid,c in world.collider_lines().items() if ":flex:" in uid)
        weights = {g.name:world.data.xpos[world.bodies[g.uid]][2] for g in restored.groups if "Gewicht" in g.name}
        assert weights["Kabel · Gewicht"]>weights["Seil · Gewicht"]+.05
        # End attachments remain within 1 cm despite the load and ground contacts.
        eq = world.data.efc_pos[world.data.efc_type==0]
        assert np.max(np.abs(eq))<.01
    finally:world.close()


def test_rope_segments_are_inextensible_and_start_stays_clamped():
    scene = Scene();body = make("rope",[[i*.1,0,2] for i in range(21)],mass=.2)
    scene.groups = [body]
    world,_ = loaded(scene)
    try:
        advance(world,2)
        for i in range(19):
            a,b = [world.data.xpos[world.bodies[segment_uid(body.uid,k)]] for k in (i,i+1)]
            assert np.linalg.norm(a-b) == pytest.approx(.1,abs=1e-6)
        assert world.data.xpos[world.bodies[segment_uid(body.uid,0)]] == pytest.approx([0,0,2])
        assert world.data.xpos[world.bodies[segment_uid(body.uid,19)]][2]<1.5
    finally:world.close()


def test_articulated_chain_swings_without_links_separating():
    scene = chain();world,_ = loaded(scene)
    initial = world.poses()["poses"]
    try:
        final = advance(world,4)["poses"]
        links = [g for g in scene.groups if g.name.startswith("Kettenglied")]
        assert final[links[0].uid][0] == pytest.approx(initial[links[0].uid][0])
        assert final[links[-1].uid][0][2]<1.5
        for a,b in zip(links,links[1:]):
            assert math.dist(final[a.uid][0],final[b.uid][0]) == pytest.approx(.13,abs=2e-6)
    finally:world.close()


def test_carrier_keeps_cable_inside_while_carriage_moves_both_ways():
    scene = carrier();world,_ = loaded(scene)
    cable = scene.groups[-1];points = cable.ext[KEY]["flexible"]["points"]
    carriage = next(g for g in scene.groups if g.name=="Schlitten")
    initial = {uid:np.array(p[0]) for uid,p in world.poses()["poses"].items()}
    parts = [world.bodies[segment_uid(cable.uid,i)] for i in range(len(points)-1)]
    frames = [next(g for g in scene.groups if g.name==f"Glied {i+1:02d} · Boden") for i in range(len(points)-1)]
    try:
        for target in (.18,-.10,.20):
            result = advance(world,4,{carriage.uid:target})
            assert abs(result["joints"][carriage.uid]["position"]-target)<.04
            assert np.max(np.abs(world.data.efc_pos[world.data.efc_type==0]))<.005
            lines = []
            for i,frame in enumerate(frames):
                bid = world.bodies[frame.uid];rot = world.data.xmat[bid].reshape(3,3)
                a = world.data.xpos[bid]+rot@(np.array(points[i])-initial[frame.uid])
                b = a+rot@(np.array(points[i+1])-points[i]);lines.append((a,b))
            for bid in parts:
                p = world.data.xipos[bid]
                distance = min(np.linalg.norm(p-(a+np.clip(np.dot(p-a,b-a)/np.dot(b-a,b-a),0,1)*(b-a))) for a,b in lines)
                assert distance<.06
        assert world.data.time == pytest.approx(12)
    finally:world.close()


def test_overly_stiff_cable_fails_with_actionable_message():
    scene = Scene();scene.groups = [make("too stiff",[[i*.01,0,2] for i in range(5)],bend=1e10)]
    _,specs,_ = prepare(scene);world = World()
    try:
        with pytest.raises(ValueError,match="too stiff"):world.load(dict(bodies=specs))
    finally:world.close()


@pytest.mark.parametrize("start",["fixed","pinned","free"])
def test_cable_start_modes(start):
    scene = Scene();body = make("start",[[i*.1,0,3] for i in range(8)],start=start)
    scene.groups = [body];world,_ = loaded(scene)
    try:
        result = advance(world,.5)
        position = result["poses"][segment_uid(body.uid,0)][0]
        if start=="free":assert position[2]<2.5
        else:assert position == pytest.approx([0,0,3],abs=1e-6)
    finally:world.close()


def test_collision_exemption_applies_to_every_segment_of_flexible_body():
    from newton.model import box
    obstacle = box("enclosure",(.3,0,2),(1,1,1),mode="static")
    cable = make("lead",[[i*.1,0,2] for i in range(7)])
    source = Scene();source.groups = [obstacle,cable]
    world = World()
    try:
        _,specs,_ = prepare(source)
        world.load(dict(bodies=specs,gravity=0,floor=False))
        assert world.data.ncon>0
        cable.ext[KEY]["no_collision"] = [obstacle.uid]
        _,specs,_ = prepare(source)
        world.load(dict(bodies=specs,gravity=0,floor=False))
        assert world.data.ncon==0
        advance(world,.2)
        assert world.data.ncon==0
        assert np.max(np.abs(world.data.qvel))<1e-5
    finally:world.close()
