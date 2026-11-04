"""Build a collision inspection exhibit without changing other test models."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"ingetrazo-source")]
from core.scene import Scene
from core.group import Group
from formats import igz
from newton.model import box,KEY,DEFAULTS,prepare
from newton.worker import World


def colour(group,rgb):
    for face in group.mesh.faces:face.attrs["color"] = rgb
    return group


def build():
    scene = Scene()
    base = colour(box("Support",(0,.65,.03),(3.3,2.5,.06),mode="static",restitution=0),(.18,.22,.27))
    a = colour(box("A · Collision on",(-.85,0,1.3),(.3,.3,.3),restitution=0),(.15,.65,.86))
    pa = colour(box("A · Catch plate",(-.85,0,.55),(.7,.7,.08),mode="static",restitution=0),(.55,.6,.65))
    b = colour(box("B · Collision off",(.85,0,1.3),(.3,.3,.3),restitution=0),(.95,.35,.12))
    pb = colour(box("B · Pass-through plate",(.85,0,.55),(.7,.7,.08),mode="static",restitution=0),(.55,.6,.65))
    b.ext[KEY]["no_collision"] = [pb.uid]
    pb.ext[KEY]["no_collision"] = [b.uid]
    arch = Group(name="C · Opening and convex hull")
    arch.adopt([colour(box("Left post",(-.4,1.45,.41),(.16,.24,.70)),(.85,.66,.15)),
                colour(box("Right post",(.4,1.45,.41),(.16,.24,.70)),(.85,.66,.15)),
                colour(box("Crossbeam",(0,1.45,.81),(.96,.24,.10)),(.85,.66,.15))])
    arch.ext = {KEY:dict(DEFAULTS,mode="static",shape="hull")}
    scene.groups.extend([base,a,pa,b,pb,arch])
    return scene


def validate(scene):
    _,specs,_ = prepare(scene)
    w = World();result = w.load(dict(bodies=specs))
    a,b,arch = scene.groups[1],scene.groups[3],scene.groups[5]
    assert result["colliders"][arch.uid]["kind"]=="Convex hull"
    assert result["colliders"][arch.uid]["edges"]
    for _ in range(80):result = w.step(8)
    assert abs(result["poses"][a.uid][0][2]-.74)<.02
    assert abs(result["poses"][b.uid][0][2]-.21)<.02
    w.close()
    print("Checked: blue lands on the plate, orange falls through its plate; convex hull visible.",flush=True)


def main():
    path = ROOT/"models/collision-test.igz"
    if "--existing" in sys.argv:
        scene = Scene();igz.load_into(scene,path)
    else:
        if path.exists():raise FileExistsError(f"Existing model kept: {path}")
        scene = build()
    validate(scene)
    if "--existing" not in sys.argv:igz.save_scene(scene,path)
    print(path,flush=True)
    if "--open" not in sys.argv:return
    from PySide6.QtCore import QSettings,QTimer
    from PySide6.QtWidgets import QApplication,QScrollArea
    app = QApplication([]);app.setOrganizationName("NewtonPreview");app.setApplicationName("NewtonPreview")
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(ROOT/".test-state"))
    from core import extensions,autosave
    extensions.plugin_dirs = lambda:[ROOT]
    autosave_dir = ROOT/".test-state/autosave";autosave_dir.mkdir(parents=True,exist_ok=True)
    autosave.autosave_dir = lambda:autosave_dir
    from views.main_window import MainWindow
    win = MainWindow();win.resize(1400,950);assert win.open_path(path)
    win.viewport.camera.fit_to(*win.viewport.scene.bounds());win.show()
    panel = next(d.widget() for d in win._extension_docks if d.objectName()=="extension_newton")
    panel.python.setText(sys.executable)
    selected = next(g for g in win.viewport.scene.groups if g.name.startswith("C ·"))
    win.viewport.scene.select([selected]);win.viewport.notify_scene_changed()
    panel.show_sidebar();panel.advanced_toggle.setChecked(True);panel.show_colliders.setChecked(True)
    QTimer.singleShot(400,lambda:panel.findChild(QScrollArea).ensureWidgetVisible(panel.body_section))
    panel.show_controls();app.exec()


if __name__=="__main__":main()
