from pathlib import Path

from formats import igz
from core.scene import Scene
from newton.model import ground_scrapers,prepare

MODEL = Path(__file__).parent.parent/"models/z0-contact-test.igz"


def load():
    scene = Scene();igz.load_into(scene,MODEL)
    return prepare(scene)


def test_test_model_reports_exactly_the_scraping_bodies():
    _,specs,movers = load()
    found = {movers[uid].name for uid in ground_scrapers(specs,True)}
    assert found
    for spec in specs:
        lowest = spec["center"][2]+min(v[2] for v in spec["vertices"])
        scraping = spec["mass"]>0 and lowest<-1e-6 and (spec.get("simulation_override") or {}).get("floor",True)
        assert (movers[spec["uid"]].name in found) == bool(scraping)


def test_global_ground_off_reports_only_bodies_with_own_ground():
    _,specs,_ = load()
    own = {s["uid"] for s in specs if (s.get("simulation_override") or {}).get("floor") is True}
    assert set(ground_scrapers(specs,False)) <= own


def test_resting_fixed_and_ground_free_bodies_are_not_reported():
    resting = dict(uid="a",mass=1,center=[0,0,.05],vertices=[[0,0,-.05]],simulation_override=None)
    assert ground_scrapers([resting],True) == []
    sunk = dict(resting,center=[0,0,.04])
    assert ground_scrapers([sunk],True) == ["a"]
    assert ground_scrapers([dict(sunk,mass=0)],True) == []
    assert ground_scrapers([dict(sunk,simulation_override=dict(floor=False))],True) == []
    assert ground_scrapers([sunk],False) == []
