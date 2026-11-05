import json
import math
import pytest
from PySide6.QtCore import QSettings
from newton import profiles
from newton.model import box,KEY


@pytest.fixture
def profile_store(qtapp):
    settings = QSettings()
    old = settings.value(profiles.STORE,None)
    settings.remove(profiles.STORE)
    yield
    if old is None:
        settings.remove(profiles.STORE)
    else:
        settings.setValue(profiles.STORE,old)


def test_builtins_cover_all_supported_axis_and_drive_combinations():
    values = profiles.builtins()
    combinations = {(p["joint"]["type"],p["joint"]["drive"]) for p in values if p["joint"]}
    assert combinations=={(kind,drive) for kind in ("hinge","slide") for drive in ("free","position","velocity")}
    assert len({p["id"] for p in values})==len(values)
    for p in values:
        assert profiles.validate(p)==p


def test_environment_override_survives_profile_and_model_save(profile_store,tmp_path):
    from core.scene import Scene
    from formats import igz
    override = dict(gravity=[2,0,0],linear_damping=1,angular_damping=2,floor=False)
    group = box("Local environment",(0,0,1),(1,1,1),simulation_override=override)
    profiles.save_custom(profiles.from_group(group,"Sideways"))
    assert profiles.custom_profiles()[0]["body"]["simulation_override"] == override
    scene = Scene();scene.groups = [group]
    path = tmp_path/"environment.igz"
    igz.save_scene(scene,path)
    loaded = Scene();igz.load_into(loaded,path)
    assert loaded.groups[0].ext[KEY]["simulation_override"] == override


def test_save_from_object_removes_identity_and_placement_then_rename_update_delete(profile_store):
    g = box("Private object",(123,456,789),(1,1,1),mass=4,reference="parent-id",
        joint=dict(type="hinge",drive="position",name="Private control",parent="parent-id",
                   pivot=[123,456,789],axis=[.6,0,.8],target=.4,force=50))
    p = profiles.save_custom(profiles.from_group(g,"My servo"))
    data = json.dumps(p)
    assert "parent-id" not in data and "Private" not in data and "pivot" not in data and "axis" not in p["joint"]
    assert p["body"]["mass"]==4
    assert profiles.custom_profiles()[0]["joint"]["target"]==.4
    p["name"] = "Renamed servo"
    p["body"]["mass"] = 2
    profiles.save_custom(p)
    assert len(profiles.custom_profiles())==1
    assert profiles.custom_profiles()[0]["name"]=="Renamed servo"
    profiles.delete_custom(p["id"])
    assert profiles.custom_profiles()==[]
    assert len(profiles.builtins())==8


def test_corrupt_custom_profiles_do_not_break_loading(profile_store):
    QSettings().setValue(profiles.STORE,json.dumps([{},dict(name="Bad",body=[]),dict(name="Bad",body={},joint=[])]))
    assert profiles.custom_profiles()==[]
    QSettings().setValue(profiles.STORE,"not json")
    assert profiles.custom_profiles()==[]


def test_translation_and_english_fallback_follow_host_language(qtapp):
    from core.i18n import current_language,set_language
    from newton.i18n import tr
    old = current_language()
    try:
        set_language("de")
        assert tr("Newton profiles")=="Newton-Profile"
        set_language("de-DE")
        assert tr("Quality")=="Qualität"
        set_language("fr")
        assert tr("Newton profiles")=="Newton profiles"
        assert tr("Actual: {value} {unit}",value="4.0",unit="mm")=="Actual: 4.0 mm"
    finally:
        set_language(old)


def test_limit_hardness_is_a_profile_value_and_keeps_older_signatures_valid(profile_store):
    import hashlib
    from newton.profile_sync import fingerprint,status
    g = box("Soft stop",(0,0,1),(1,1,1),joint=dict(type="hinge",drive="free",pivot=[0,0,1],axis=[0,0,1],
            limited=True,lower=-1,upper=1,limit_hardness=.3))
    p = profiles.save_custom(profiles.from_group(g,"Soft stop"))
    assert profiles.custom_profiles()[0]["joint"]["limit_hardness"]==.3
    # A signature stored before the setting existed, for a profile at the default hardness.
    hard = profiles.validate(dict(p,joint=dict(p["joint"],limit_hardness=1)))
    older = hashlib.sha256(json.dumps([hard["body"],{k:v for k,v in hard["joint"].items() if k!="limit_hardness"}],
                                      sort_keys=True).encode()).hexdigest()
    assert fingerprint(hard)==older
    assert fingerprint(p)!=fingerprint(hard)
    g.ext[KEY]["joint"]["limit_hardness"] = 1
    g.ext[KEY]["profile_link"] = dict(id=hard["id"],signature=older)
    assert status(g,hard)=="In sync"
