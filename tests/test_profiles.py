import json
import math
from pathlib import Path
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


def test_english_master_and_fallback_follow_host_language(qtapp):
    from core.i18n import current_language,set_language
    from newton.i18n import tr
    root = Path(__file__).resolve().parents[1]/"newton"/"i18n"
    master = json.loads((root/"en.json").read_text(encoding="utf-8"))
    german = json.loads((root/"de.json").read_text(encoding="utf-8"))
    assert master and all(key==value for key,value in master.items())
    assert set(german)<=set(master)
    old = current_language()
    try:
        set_language("de")
        assert tr("Newton profiles")=="Newton-Profile"
        set_language("de-DE")
        assert tr("Icon set")=="Icon-Set"
        set_language("fr")
        assert tr("Newton profiles")=="Newton profiles"
        assert tr("Actual: {value:.1f} {unit}",value=4,unit="mm")=="Actual: 4.0 mm"
    finally:
        set_language(old)
