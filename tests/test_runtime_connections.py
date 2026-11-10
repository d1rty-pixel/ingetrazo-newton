import json
import math
import pytest
from core.scene import Scene
from newton.model import box,prepare,KEY
from newton.worker import World,attachment_settings
from newton.performance import RealtimeMeter
from newton.connections import connection_command


def load(groups,**options):
    scene = Scene();scene.groups = groups;_,specs,_ = prepare(scene)
    world = World();world.load(dict(bodies=specs,floor=False,**options));return world


def advance(world,seconds):
    for _ in range(round(seconds*30)):result = world.step(8)
    return result


def motor(force=10):
    return box("loaded motor",(0,0,2),(.1,.1,.1),mass=1,
        joint=dict(type="slide",drive="velocity",pivot=[0,0,2],axis=[1,0,0],limited=False,
            target=.5,max_speed=1,acceleration=1,force=force),simulation_override=dict(gravity=[-2,0,0]))


def test_motor_tracks_velocity_under_load_and_reports_actual_effort():
    body = motor();world = load([body],gravity=0)
    try:
        result = advance(world,3);state = result["joints"][body.uid]
        assert state["velocity"] == pytest.approx(.5,abs=.005)
        assert state["effort"] == pytest.approx(2,abs=.03)
        assert state["load"] == pytest.approx(.2,abs=.005)
        assert not state["at_limit"]
        assert state["command"] == pytest.approx(.5)
        assert result["performance"]["newton_ms"]>=0
        json.dumps(result,allow_nan=False)  # Actual process protocol accepts all telemetry scalars.
    finally:world.close()


def test_motor_saturation_does_not_wind_up_when_load_is_removed():
    body = motor(.5);world = load([body],gravity=0)
    try:
        state = advance(world,1)["joints"][body.uid]
        assert state["at_limit"] and abs(state["effort"])<=.5
        assert abs(world.motors[body.uid]["integral"])<.01
        world.environments = []
        velocities = []
        for _ in range(180):velocities.append(world.step(8)["joints"][body.uid]["velocity"])
        assert max(velocities)<.6
        assert velocities[-1] == pytest.approx(.5,abs=.01)
    finally:world.close()


def test_realtime_meter_excludes_pause_and_restart():
    meter = RealtimeMeter()
    assert meter.observe(0,10) is None
    assert meter.observe(.5,11) == pytest.approx(.5)
    meter.reset()  # Pause/resume resets the measuring window.
    assert meter.observe(.5,100) is None
    assert meter.observe(1.5,101) == pytest.approx(1)
    assert meter.observe(0,102) is None


@pytest.mark.parametrize("kind",["ball","hinge","fixed"])
def test_connection_types_restrict_the_expected_motion(kind):
    anchor = box("anchor",(0,0,2),(.1,.1,.1),mode="static")
    arm = box("arm",(.5,0,2),(1,.05,.05),point_attachment=dict(type=kind,target=anchor.uid,point=[0,0,2],axis=[0,1,0]))
    world = load([anchor,arm])
    try:
        world.data.qvel[-1] = 2
        result = advance(world,.5)
        xyz = result["poses"][arm.uid][0]
        if kind=="fixed":assert xyz == pytest.approx([.5,0,2],abs=.003)
        elif kind=="hinge":
            assert abs(xyz[1])<.003
            assert xyz[2]<1.9
        else:assert abs(xyz[1])>.03
        assert result["poses"][anchor.uid][0] == pytest.approx([0,0,2])
    finally:world.close()


def test_connection_edit_is_single_undo_and_does_not_reparent():
    from core.history import History
    a,b = box("a",(0,0,2),(1,1,1)),box("b",(2,0,2),(1,1,1),mode="static")
    scene = Scene();scene.groups = [a,b];history = History(scene)
    history.execute(connection_command(scene,a,dict(target=b.uid,point=[1,0,2],type="ball")))
    assert "reference" not in a.ext[KEY]
    assert a.ext[KEY]["point_attachment"]["target"]==b.uid
    history.undo();assert not a.ext[KEY].get("point_attachment")
    history.redo();assert a.ext[KEY]["point_attachment"]["target"]==b.uid
    with pytest.raises(ValueError):connection_command(scene,a,dict(target=a.uid,point=[0,0,2]))


def test_native_rotation_carries_pin_axis_and_point_with_undo():
    from types import SimpleNamespace
    from PySide6.QtGui import QVector3D
    from core.history import History,RotateGroupCommand
    from newton.references import install
    a,b = box("a",(1,0,2),(1,1,1)),box("b",(0,0,2),(1,1,1),mode="static")
    scene = Scene();scene.groups = [a,b];history = History(scene)
    a.ext[KEY]["point_attachment"] = dict(type="hinge",target=b.uid,point=[1,0,2],axis=[0,1,0])
    vp = SimpleNamespace(scene=scene,history=history,begin_groups_preview=lambda *a,**k:None,end_groups_preview=lambda:None)
    install(vp);history.execute(RotateGroupCommand(a,QVector3D(0,0,2),QVector3D(0,0,1),90))
    assert a.ext[KEY]["point_attachment"]["point"] == pytest.approx([0,1,2],abs=1e-6)
    assert a.ext[KEY]["point_attachment"]["axis"] == pytest.approx([-1,0,0],abs=1e-6)
    history.undo()
    assert a.ext[KEY]["point_attachment"]["point"] == [1,0,2]
    assert a.ext[KEY]["point_attachment"]["axis"] == [0,1,0]


@pytest.mark.parametrize("quality",["quick","balanced","precise"])
def test_quality_preserves_geometry_and_elapsed_simulation_time(quality):
    body = box("drop",(0,0,3),(1,2,1));world = load([body],quality=quality)
    try:
        result = advance(world,.5)
        assert result["time"] == pytest.approx(.5)
        assert result["poses"][body.uid][0][2] == pytest.approx(3-.5*9.81*.5**2,abs=.02)
        assert result["performance"]["quality"]==quality
        assert world.model.geom_size[0] == pytest.approx([.5,1,.5])
    finally:world.close()


def test_contact_solver_option_selects_pgs_and_rejects_unknown_values():
    body = box("drop",(0,0,3),(1,2,1))
    world = load([body])
    try:
        assert world.model.opt.solver==world.mj.mjtSolver.mjSOL_NEWTON
        assert advance(world,.1)["performance"]["solver"]=="automatic"
    finally:world.close()
    world = load([body],solver="pgs")
    try:
        assert world.model.opt.solver==world.mj.mjtSolver.mjSOL_PGS
        result = advance(world,.5)
        assert result["performance"]["solver"]=="pgs"
        assert result["poses"][body.uid][0][2] == pytest.approx(3-.5*9.81*.5**2,abs=.02)
    finally:world.close()
    with pytest.raises(ValueError,match="contact solver"):
        load([body],solver="fast")


def test_hidden_connection_target_still_simulates():
    anchor = box("anchor",(0,0,2),(.1,.1,.1),mode="static")
    anchor.hidden = True
    arm = box("arm",(.5,0,2),(1,.05,.05),point_attachment=dict(type="fixed",target=anchor.uid,point=[0,0,2],axis=[0,1,0]))
    world = load([anchor,arm])
    try:
        assert advance(world,.3)["poses"][arm.uid][0] == pytest.approx([.5,0,2],abs=.003)
    finally:world.close()
