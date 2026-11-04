from demo_support import seed_demo
import math
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QVector3D
from PySide6.QtWidgets import QApplication
from types import SimpleNamespace
from newton.model import KEY, joint_rows


def test_child_component_collision_rejects_plain_mesh_without_changing_model(panel):
    from newton.model import box,AddDemo
    group = box("Plain solid",(0,0,1),(1,1,1))
    vp = panel.app.viewport;vp.history.execute(AddDemo([group]));vp.scene.select([group]);panel.refresh()
    before = len(vp.history.undo_stack)
    panel.shape.setCurrentIndex(panel.shape.findData("compound"))
    assert group.ext[KEY]["shape"]=="box"
    assert panel.shape.currentData()=="box" and len(vp.history.undo_stack)==before
    panel.apply_profile(dict(name="Open assembly",body=dict(group.ext[KEY],shape="compound"),joint=None))
    assert group.ext[KEY]["shape"]=="box" and len(vp.history.undo_stack)==before


def test_mouse_wheel_scrolls_sidebar_instead_of_changing_dropdowns_and_numbers(panel):
    from PySide6.QtCore import QPoint,QPointF
    from PySide6.QtGui import QWheelEvent
    fields = (panel.shape,panel.drive,panel.mass,panel.coupling_editor.master,panel.coupling_editor.ratio,
              panel.flexible_editor.end)
    for field in fields:
        before = field.currentIndex() if hasattr(field,"currentIndex") else field.value()
        event = QWheelEvent(QPointF(5,5),QPointF(5,5),QPoint(),QPoint(0,-120),Qt.NoButton,Qt.NoModifier,
                            Qt.NoScrollPhase,False)
        QApplication.sendEvent(field,event)
        assert not event.isAccepted()
        assert before==(field.currentIndex() if hasattr(field,"currentIndex") else field.value())


def test_connect_tool_places_a_pin_and_sidebar_edits_it_live(panel,qtapp,monkeypatch):
    from newton.model import box,AddDemo
    from newton.connections import ConnectionTool
    a,b = box("Link",(.5,0,2),(1,.1,.1)),box("Anchor",(0,0,2),(.1,.1,.1),mode="static")
    vp = panel.app.viewport;vp.history.execute(AddDemo([a,b]));vp.scene.select([a]);panel.refresh()
    panel.connection_editor.kind.setCurrentIndex(panel.connection_editor.kind.findData("hinge"))
    before = len(vp.history.undo_stack);panel.actions["connect"].trigger()
    tool = vp.active_tool;assert type(tool).__name__=="ConnectionTool"
    monkeypatch.setattr(vp,"pick_group",lambda *args:b)
    ctx = SimpleNamespace(viewport=vp,screen=SimpleNamespace(x=lambda:100,y=lambda:100),world=QVector3D(0,0,2))
    tool.on_click(ctx);assert not a.ext[KEY].get("point_attachment")
    tool.on_click(ctx);assert tool.claims_key(Qt.Key_Y,Qt.NoModifier)
    tool.on_key(vp,Qt.Key_Y,Qt.NoModifier);qtapp.processEvents()
    assert a.ext[KEY]["point_attachment"]["target"]==b.uid
    assert a.ext[KEY]["point_attachment"]["axis"]==[0,1,0]
    assert len(vp.history.undo_stack)==before+1
    assert "reference" not in a.ext[KEY]
    panel.connection_editor.point[0].setValue(100)
    assert a.ext[KEY]["point_attachment"]["point"][0] == pytest.approx(.1)
    vp.history.undo();assert a.ext[KEY]["point_attachment"]["point"][0]==0


def test_connection_marker_drags_with_one_undo_and_eraser_preserves_geometry(panel,qtapp):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from newton.model import box,AddDemo
    from newton.connections import apply_connection,MoveConnection
    a,b = box("Link",(.5,0,2),(1,.1,.1)),box("Anchor",(0,0,2),(.1,.1,.1),mode="static")
    vp = panel.app.viewport;vp.resize(1000,700);vp.camera.set_aspect(1000,700)
    vp.history.execute(AddDemo([a,b]));vp.scene.select([a]);vp.camera.fit_to(*vp.scene.bounds());panel.refresh()
    apply_connection(panel,a,dict(target=b.uid,point=[0,0,2],type="ball"));panel.app.window._activate_tool("select")
    before = len(vp.history.undo_stack);geometry = a.mesh
    xs,ys,_ = vp.world_to_pixels([[0,0,2]]);point = QPointF(float(xs[0]),float(ys[0]))
    event = QMouseEvent(QEvent.MouseButtonPress,point,point,Qt.LeftButton,Qt.LeftButton,Qt.NoModifier)
    QApplication.sendEvent(vp,event);assert type(vp.active_tool).__name__=="MoveConnection"
    vp.active_tool.on_hover(SimpleNamespace(viewport=vp,world=QVector3D(.1,0,2)))
    vp.active_tool.on_release(vp);qtapp.processEvents()
    assert len(vp.history.undo_stack)==before+1
    assert a.ext[KEY]["point_attachment"]["point"][0] == pytest.approx(.1)
    vp.history.undo();vp.notify_scene_changed()
    panel.app.window._activate_tool("eraser");eraser = vp.active_tool
    ctx = SimpleNamespace(viewport=vp,screen=point,modifiers=Qt.NoModifier)
    eraser.on_click(ctx);eraser.on_release(vp)
    assert a in vp.scene.groups and a.mesh is geometry
    assert a.ext[KEY]["point_attachment"] is None
    vp.history.undo();assert a.ext[KEY]["point_attachment"]["target"]==b.uid


def test_performance_is_visible_in_controls_and_pause_is_not_measured(panel,qtapp):
    seed_demo(panel,"Servo-Tür");panel.start_or_pause();wait(qtapp,lambda:panel.session.ready)
    wait(qtapp,lambda:panel.session.performance.get("speed") is not None)
    assert "real time" in panel.controls.performance_label.text()
    assert "Newton:" in panel.controls.performance_label.toolTip()
    panel.session.toggle();assert panel.controls.performance_label.text()=="Paused"
    panel.session.reset();assert panel.controls.performance_label.isHidden()


def test_flexible_sidebar_edits_and_external_session_reset(panel,qtapp):
    from newton.flexible import make
    from newton.model import AddDemo
    group = make("Test rope",[[i*.1,0,2] for i in range(12)])
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group]);panel.refresh()
    assert panel.browser_kind(group)["type"].endswith("Rope")
    panel.flexible_editor.bend.setValue(3e4)
    assert group.ext[KEY]["flexible"]["bend"] == 3e4
    panel.app.viewport.history.undo()
    assert group.ext[KEY]["flexible"]["bend"] == 2e4
    assert not panel.actions["rotate"].isEnabled()
    source = panel.app.scene
    assert not panel.controls.isVisible() and not hasattr(panel,"start_button")
    panel.start_or_pause();wait(qtapp,lambda:panel.session.ready)
    assert panel.controls.isVisible(),"the control panel opens even without actuators"
    assert len(panel.session.movers)==11
    wait(qtapp,lambda:panel.session.workspace.scene.version>5)
    panel.session.reset()
    assert panel.app.scene is source and group in source.groups


def test_grouped_open_line_becomes_rope_and_move_undo_keeps_path_aligned(panel):
    from core.mesh import Mesh
    from core.group import Group
    from core.history import MoveGroupCommand
    from newton.model import AddDemo,prepare
    mesh = Mesh();mesh.add_edge(QVector3D(0,0,2),QVector3D(2,0,2))
    group = Group(mesh,"Centre line")
    vp = panel.app.viewport;vp.history.execute(AddDemo([group]))
    vp.scene.select([group]);panel.refresh()
    editor = panel.flexible_editor
    editor.kind.setCurrentIndex(editor.kind.findData("rope"))
    assert len(group.ext[KEY]["flexible"]["points"])==21
    vp.history.execute(MoveGroupCommand(group,QVector3D(0,1,0)))
    _,specs,_ = prepare(vp.scene)
    assert specs[0]["flexible"]["points"][0] == pytest.approx([0,1,2])
    vp.history.undo()
    assert group.ext[KEY]["flexible"]["points"][0] == pytest.approx([0,0,2])
    endpoint = max(group.mesh.vertices,key=lambda v:v.position.x())
    group.mesh.move_vertex(endpoint,QVector3D(1,0,0))
    _,specs,_ = prepare(vp.scene)
    assert specs[0]["flexible"]["points"][-1] == pytest.approx([3,0,2])


def test_environment_overrides_edit_and_undo_without_changing_motion(panel):
    seed_demo(panel,"Servo-Tür")
    group = next(g for g in panel.app.scene.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    panel.app.scene.select([group]);panel.refresh()
    editor = panel.environment
    original = dict(group.ext[KEY]["joint"])
    editor.enabled.setChecked(True)
    editor.gravity[0].setValue(3)
    assert group.ext[KEY]["simulation_override"]["gravity"][0] == 3
    assert group.ext[KEY]["joint"] == original
    editor.enabled.setChecked(False)
    assert group.ext[KEY]["simulation_override"] is None
    panel.app.viewport.history.undo()
    assert group.ext[KEY]["simulation_override"]["gravity"][0] == 3


def test_preferences_organize_and_stage_global_simulation(panel):
    from PySide6.QtCore import QSettings
    from newton.preferences import NewtonPreferences
    st = QSettings()
    keys = ["gravity_z","floor","linear_damping","angular_damping","python"]
    saved = {key:st.value("newton/"+key) for key in keys}
    try:
        page = NewtonPreferences(panel)
        assert page.tabs.count() == 4
        explained = [page.colliders,page.shortcuts_button,page.quality,page.gravity.parentWidget(),
                     page.floor,page.linear,page.angular,page.python.parentWidget()]
        texts = [w.toolTip() for w in explained]
        assert all(texts) and len(set(texts)) == len(texts)
        assert panel.gravity.isHidden() and panel.floor.isHidden() and panel.python.isHidden()
        old = panel.gravity.value()
        page.gravity.setValue(-3);page.linear.setValue(1.5)
        assert panel.gravity.value() == old
        page.commit()
        assert panel.gravity.value() == -3
        assert float(st.value("newton/linear_damping")) == 1.5
        page.deleteLater()
    finally:
        for key,value in saved.items():
            name = "newton/"+key
            if value is None:st.remove(name)
            else:st.setValue(name,value)
        st.sync()


def wait(qtapp, condition, seconds=10):
    deadline = time.monotonic()+seconds
    while not condition() and time.monotonic() < deadline:
        qtapp.processEvents()
        time.sleep(.005)
    assert condition()


@pytest.fixture
def panel(qtapp, monkeypatch,request):
    from core import extensions
    from core.i18n import current_language,set_language
    old_language = current_language()
    if getattr(request,"param",None):
        set_language(request.param)
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(extensions, "plugin_dirs", lambda:[root])
    from views.main_window import MainWindow
    win = MainWindow()
    dock = next(d for d in win._extension_docks if d.objectName() == "extension_newton")
    p = dock.widget()
    p.python.setText(sys.executable)
    yield p
    if win.workspace():
        win.leave_workspace()
    p.controls.close()
    if p.dialog:
        p.dialog.close()
    if p.profile_manager:
        p.profile_manager.close()
    win._saved_version = win.viewport.scene.version
    win.close()
    set_language(old_language)


@pytest.mark.parametrize("kind,name,display_target,native_target,suffix",[
    ("Servo-Tür","Tür öffnen",60,math.pi/3,"°"),
    ("Linearschlitten","Schlittenposition",400,.4,"mm")])
def test_named_controls_drive_real_session_and_reset_without_saving_runtime_target(
        panel,qtapp,kind,name,display_target,native_target,suffix):
    assert panel.advanced.isHidden()
    seed_demo(panel,kind)
    source = panel.app.scene
    row = next(j for j in joint_rows(source) if j["name"] == name)
    panel.start_or_pause()
    wait(qtapp,lambda:panel.session.ready)
    assert panel.controls.isVisible()
    value = panel.controls.findChild(QDoubleSpinBox)
    assert suffix in value.suffix()
    value.setValue(display_target)
    assert panel.session.targets[row["uid"]] == pytest.approx(native_target)
    wait(qtapp,lambda:float(panel.controls.time_label.text().split(":")[1].split()[0]) > 1.5,5)
    label = panel.controls.rows[row["uid"]][0].text()
    actual = float(label.split(":")[1].split()[0])
    assert actual == pytest.approx(display_target,abs=2)
    panel.session.reset()
    assert panel.app.scene is source
    assert next(j for j in joint_rows(source) if j["name"] == name)["target"] == 0


def test_sidebar_joint_edit_preserves_arbitrary_axis_and_can_be_undone(panel):
    seed_demo(panel,"Servo-Tür")
    group = next(g for g in panel.app.scene.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    group.ext[KEY]["joint"]["axis"] = [-.6,0,.8]
    panel.app.scene.select([group])
    panel.refresh()
    panel.name_edit.setText("Meine Tür")
    panel.configure_joint()
    assert group.ext[KEY]["joint"]["axis"] == pytest.approx([-.6,0,.8])
    assert group.ext[KEY]["joint"]["name"] == "Meine Tür"
    panel.app.viewport.history.undo()
    assert group.ext[KEY]["joint"]["name"] == "Tür öffnen"


def test_ui_rejects_cyclic_parent_before_modifying_document(panel):
    seed_demo(panel,"Servo-Tür")
    source = panel.app.scene
    door = next(g for g in source.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    frame = next(g for g in source.groups if g.uid == door.ext[KEY]["joint"]["parent"])
    values = dict(door.ext[KEY]["joint"],parent=door.uid)
    before = len(panel.app.viewport.history.undo_stack)
    with pytest.raises(ValueError,match="cycle"):
        panel.commit_joint(source,frame,values)
    assert len(panel.app.viewport.history.undo_stack) == before


def test_viewport_claims_z_before_zoom_shortcut_and_places_joint(panel,qtapp):
    seed_demo(panel,"Servo-Tür")
    source = panel.app.scene
    group = next(g for g in source.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    cfg = dict(group.ext[KEY]["joint"])
    panel.begin_placement(source,group,cfg)
    tool = panel.placement
    vp = panel.app.viewport
    tool.on_click(SimpleNamespace(world=QVector3D(0,0,1.2),viewport=vp))
    event = QKeyEvent(QEvent.ShortcutOverride,Qt.Key_Z,Qt.NoModifier)
    event.setAccepted(False)
    QApplication.sendEvent(vp,event)
    assert event.isAccepted()
    QApplication.sendEvent(vp,QKeyEvent(QEvent.KeyPress,Qt.Key_Z,Qt.NoModifier))
    qtapp.processEvents()
    assert panel.placement is None
    assert group.ext[KEY]["joint"]["pivot"] == pytest.approx([0,0,1.2])
    assert group.ext[KEY]["joint"]["axis"] == [0,0,1]


def test_toolbar_places_axis_without_dialog_and_sidebar_sets_drive(panel,qtapp):
    from newton.model import box,AddDemo
    from newton.joints import PlacementTool
    group = box("Greifer",(2,0,2),(.5,.5,.5))
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group])
    panel.refresh()
    assert panel.toolbar.objectName()=="newton_toolbar"
    assert len(panel.actions)==12
    assert all(not a.icon().isNull() for a in panel.actions.values())
    panel.actions["rotate"].trigger()
    assert panel.dialog is None
    assert panel.app.viewport.active_tool is panel.placement
    panel.placement.on_click(SimpleNamespace(world=QVector3D(2,0,2),viewport=panel.app.viewport))
    panel.placement.on_key(panel.app.viewport,Qt.Key_Z,Qt.NoModifier)
    qtapp.processEvents()
    panel.name_edit.setText("Greifer schließen")
    panel.name_edit.editingFinished.emit()
    panel.drive.setCurrentIndex(panel.drive.findData("position"))
    panel.target.setValue(30)
    panel.max_speed.setValue(45)
    panel.acceleration.setValue(90)
    panel.configure_joint()
    j = group.ext[KEY]["joint"]
    assert j["name"]=="Greifer schließen"
    assert j["target"]==pytest.approx(math.pi/6)
    assert j["max_speed"]==pytest.approx(math.pi/4)
    assert j["acceleration"]==pytest.approx(math.pi/2)


def test_reference_is_picked_in_viewport_and_detached_without_removing_axis(panel,qtapp,monkeypatch):
    from newton.model import demo,AddDemo
    from newton.references import reference
    parent,child = demo("Servo-Tür")
    panel.app.viewport.history.execute(AddDemo([parent,child]))
    panel.app.scene.select([child])
    panel.refresh()
    panel.detach_reference()
    assert reference(child) is None
    assert child.ext[KEY]["joint"]
    panel.pick_reference()
    tool = panel.app.viewport.active_tool
    monkeypatch.setattr(panel.app.viewport,"pick_group",lambda *a:parent)
    tool.on_click(SimpleNamespace(viewport=panel.app.viewport,
        screen=SimpleNamespace(x=lambda:100,y=lambda:100)))
    qtapp.processEvents()
    assert reference(child)==parent.uid
    assert "Türrahmen" in panel.reference_label.text()


def test_simulation_select_tool_stays_drag_tool_and_driven_body_cannot_drag(panel,qtapp):
    from newton.interaction import DragTool
    seed_demo(panel,"Servo-Tür")
    uid = panel.control_rows[0]["uid"]
    panel.start_or_pause()
    wait(qtapp,lambda:panel.session.ready)
    assert not panel.session.can_drag(uid)
    assert panel.app.viewport.active_tool is panel.session.drag_tool
    panel.app.window._activate_tool("select")
    assert panel.app.viewport.active_tool is panel.session.drag_tool
    panel.session.reset()
    assert type(panel.app.viewport.active_tool).__name__=="SelectTool"


def test_enabling_servo_on_legacy_passive_hinge_gets_useful_default_force(panel):
    seed_demo(panel,"Pendel")
    panel.drive.setCurrentIndex(panel.drive.findData("position"))
    panel.target.setValue(30)
    panel.configure_joint()
    group = next(g for g in panel.app.scene.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    assert group.ext[KEY]["joint"]["force"]==100


def select_demo_axis(panel,kind="Servo-Tür"):
    seed_demo(panel,kind)
    group = next(g for g in panel.app.scene.groups if (g.ext or {}).get(KEY,{}).get("joint"))
    panel.app.scene.select([group])
    panel.app.viewport.notify_scene_changed()
    panel.refresh()
    return group


def test_sidebar_edits_apply_without_buttons_and_refresh_does_not_write(panel,qtapp):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton
    from newton.worker import joint_settings
    group = select_demo_axis(panel)
    hist = panel.app.viewport.history
    before = len(hist.undo_stack)
    for _ in range(3):
        panel.refresh()
    assert len(hist.undo_stack)==before
    assert not any("übernehmen" in b.text().lower() for b in panel.findChildren(QPushButton))
    panel.max_speed.selectAll()
    QTest.keyClicks(panel.max_speed,"45")
    assert joint_settings(group.ext[KEY]["joint"])["max_speed"]==pytest.approx(math.pi)
    QTest.keyClick(panel.max_speed,Qt.Key_Return)
    assert group.ext[KEY]["joint"]["max_speed"]==pytest.approx(math.pi/4)
    assert len(hist.undo_stack)==before+1
    hist.undo()
    panel.app.viewport.notify_scene_changed()
    assert panel.max_speed.value()==pytest.approx(180)
    assert len(hist.undo_stack)==before
    panel.acceleration.setValue(60)
    assert group.ext[KEY]["joint"]["acceleration"]==pytest.approx(math.pi/3)
    panel.name_edit.setText("Tür links")
    panel.name_edit.editingFinished.emit()
    assert group.ext[KEY]["joint"]["name"]=="Tür links"


def test_changing_one_field_preserves_other_fields_full_precision(panel):
    group = select_demo_axis(panel)
    group.ext[KEY]["joint"]["acceleration"] = 1.234567891
    panel.refresh()
    panel.max_speed.setValue(40)
    assert group.ext[KEY]["joint"]["acceleration"]==1.234567891
    panel.mode.setCurrentIndex(panel.mode.findData("static"))
    assert group.ext[KEY]["mode"]=="static"
    panel.mass.setValue(2.5)
    assert group.ext[KEY]["mass"]==2.5


def test_invalid_live_limits_keep_valid_model_and_can_be_corrected(panel):
    group = select_demo_axis(panel)
    hist = panel.app.viewport.history
    before = len(hist.undo_stack)
    panel.upper.setValue(0)
    assert group.ext[KEY]["joint"]["upper"]==pytest.approx(math.pi/2)
    assert len(hist.undo_stack)==before
    assert "Invalid" in panel.app.window.statusBar().currentMessage()
    panel.upper.setValue(45)
    assert group.ext[KEY]["joint"]["upper"]==pytest.approx(math.pi/4)


@pytest.mark.parametrize("kind",["Servo-Tür","Linearschlitten"])
def test_native_eraser_removes_axis_over_geometry_without_deleting_body(panel,monkeypatch,kind):
    from PySide6.QtCore import QPointF
    group = select_demo_axis(panel,kind)
    source = panel.app.scene
    vp = panel.app.viewport
    parent = group.ext[KEY]["joint"]["parent"]
    old_groups = list(source.groups)
    geometry = group.mesh
    original = dict(group.ext[KEY]["joint"])
    xs,ys,front = vp.world_to_pixels([original["pivot"]])
    assert front[0]
    monkeypatch.setattr(vp,"pick_group",lambda *a:group)
    panel.app.window._activate_tool("eraser")
    eraser = vp.active_tool
    ctx = SimpleNamespace(viewport=vp,screen=QPointF(float(xs[0]),float(ys[0])),
                          world=QVector3D(*original["pivot"]),modifiers=Qt.NoModifier)
    before = len(vp.history.undo_stack)
    eraser.on_hover(ctx)
    assert panel.hover_axis==group.uid
    eraser.on_click(ctx)
    eraser.on_release(vp)
    assert source.groups==old_groups
    assert group.mesh is geometry
    assert group.ext[KEY]["joint"] is None
    assert group.ext[KEY]["reference"]==parent
    assert len(vp.history.undo_stack)==before+1
    vp.history.undo()
    assert group.ext[KEY]["joint"]==original


def test_axis_eraser_stroke_never_erases_body_when_pointer_leaves_symbol(panel,monkeypatch):
    from PySide6.QtCore import QPointF
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    xs,ys,_ = vp.world_to_pixels([group.ext[KEY]["joint"]["pivot"]])
    panel.app.window._activate_tool("eraser")
    eraser = vp.active_tool
    ctx = SimpleNamespace(viewport=vp,screen=QPointF(float(xs[0]),float(ys[0])),modifiers=Qt.NoModifier)
    eraser.on_click(ctx)
    assert eraser.axis_marked=={group.uid}
    def geometry_pick(*args):
        raise AssertionError("Axis-only stroke must not pick model geometry")
    monkeypatch.setattr(vp,"pick_group",geometry_pick)
    eraser.on_hover(SimpleNamespace(viewport=vp,screen=QPointF(20,20)))
    eraser.on_release(vp)
    assert group in vp.scene.groups
    assert group.ext[KEY]["joint"] is None


def test_erasing_multiple_axes_is_one_undo_stroke(panel):
    from newton.model import box,AddDemo
    from PySide6.QtCore import QPointF
    groups = [box(str(i),(i*3,0,2),(.3,.3,.3),joint=dict(
        pivot=[i*3,0,2],axis=[0,0,1],drive="free")) for i in range(2)]
    vp = panel.app.viewport
    vp.history.execute(AddDemo(groups))
    vp.notify_scene_changed()
    lo,hi = vp.scene.bounds()
    vp.camera.fit_to(lo,hi)
    panel.app.window._activate_tool("eraser")
    eraser = vp.active_tool
    xs,ys,front = vp.world_to_pixels([[i*3,0,2] for i in range(2)])
    assert all(front)
    contexts = [SimpleNamespace(viewport=vp,screen=QPointF(float(x),float(y)),
                                modifiers=Qt.NoModifier) for x,y in zip(xs,ys)]
    before = len(vp.history.undo_stack)
    eraser.on_click(contexts[0])
    eraser.on_hover(contexts[1])
    eraser.on_release(vp)
    assert all(g.ext[KEY]["joint"] is None for g in groups)
    assert all(g in vp.scene.groups for g in groups)
    assert len(vp.history.undo_stack)==before+1
    vp.history.undo()
    assert all(g.ext[KEY]["joint"] for g in groups)


def test_fixed_body_axis_remains_visible_and_erasable(panel):
    from PySide6.QtCore import QPointF
    group = select_demo_axis(panel)
    panel.mode.setCurrentIndex(panel.mode.findData("static"))
    assert not panel.control_rows
    assert any(j["uid"]==group.uid for j in panel.axis_rows)
    vp = panel.app.viewport
    xs,ys,_ = vp.world_to_pixels([group.ext[KEY]["joint"]["pivot"]])
    panel.app.window._activate_tool("eraser")
    eraser = vp.active_tool
    eraser.on_click(SimpleNamespace(viewport=vp,screen=QPointF(float(xs[0]),float(ys[0])),modifiers=Qt.NoModifier))
    eraser.on_release(vp)
    assert group in vp.scene.groups
    assert group.ext[KEY]["mode"]=="static" and group.ext[KEY]["joint"] is None


def test_control_window_start_pause_resume_reset_buttons_work_without_sidebar_selection(panel,qtapp):
    group = select_demo_axis(panel)
    original = panel.app.scene
    panel.app.scene.select([])
    panel.app.viewport.notify_scene_changed()
    assert all(w.isHidden() for w in panel.selection_widgets)
    panel.show_controls()
    panel.controls.start_button.click()
    wait(qtapp,lambda:panel.session.ready)
    panel.controls.start_button.click()
    assert not panel.session.running
    assert panel.controls.start_button.text()=="Resume"
    panel.controls.start_button.click()
    assert panel.session.running
    panel.controls.reset_button.click()
    assert panel.app.scene is original and not panel.session.workspace
    assert panel.controls.start_button.text()=="Start"
    assert not panel.controls.reset_button.isEnabled()


def test_browser_exposes_axes_and_control_names_while_newton_sidebar_is_empty(panel):
    from views.outliner import COL_TYPE
    group = select_demo_axis(panel)
    panel.app.scene.select([])
    panel.app.viewport.notify_scene_changed()
    assert all(w.isHidden() for w in panel.selection_widgets)
    assert not hasattr(panel,"joint_list") and not hasattr(panel,"demo_kind")
    outliner = panel.app.window.project_browser.outliner
    outliner.refresh()
    row = outliner._items[id(group)]
    assert "Rotary servo" in row.text(COL_TYPE)
    assert "Tür öffnen" in row.text(COL_TYPE)


def test_profile_overwrites_parameters_as_one_undo_but_preserves_spatial_identity(panel):
    from newton.profiles import builtins
    import copy
    group = select_demo_axis(panel)
    original = copy.deepcopy(group.ext)
    matrix,uid = list(group.xform.data()),group.uid
    before = len(panel.app.viewport.history.undo_stack)
    profile = next(p for p in builtins() if p["id"]=="builtin_slide_velocity")
    panel.apply_profile(profile)
    cfg = group.ext[KEY]
    assert cfg["joint"]["type"]=="slide" and cfg["joint"]["drive"]=="velocity"
    assert cfg["joint"]["pivot"]==original[KEY]["joint"]["pivot"]
    assert cfg["joint"]["parent"]==original[KEY]["joint"]["parent"]
    assert cfg["joint"]["name"]==original[KEY]["joint"]["name"]
    assert group.uid==uid and list(group.xform.data())==matrix
    assert len(panel.app.viewport.history.undo_stack)==before+1
    panel.app.viewport.history.undo()
    assert group.ext==original


def test_profile_without_existing_axis_starts_placement_and_cancel_is_a_noop(panel,qtapp):
    from newton.profiles import builtins
    from newton.model import box,AddDemo
    group = box("Body",(2,0,2),(.5,.5,.5))
    group.ext = None
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group])
    panel.refresh()
    profile = next(p for p in builtins() if p["id"]=="builtin_hinge_position")
    before = len(panel.app.viewport.history.undo_stack)
    panel.apply_profile(profile)
    assert panel.placement and group.ext is None
    panel.placement.on_cancel(panel.app.viewport)
    qtapp.processEvents()
    assert group.ext is None and len(panel.app.viewport.history.undo_stack)==before
    panel.apply_profile(next(p for p in builtins() if p["id"]=="builtin_dynamic"))
    assert group.ext[KEY]["mode"]=="dynamic"


def test_profile_manager_can_save_rename_replace_delete_custom_profile(panel,monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QInputDialog
    from newton import profiles
    settings = QSettings()
    old = settings.value(profiles.STORE,None)
    settings.remove(profiles.STORE)
    try:
        group = select_demo_axis(panel)
        panel.show_profiles()
        manager = panel.profile_manager
        monkeypatch.setattr(QInputDialog,"getText",lambda *a,**kw:("Custom door",True))
        manager.save_selection()
        assert len(profiles.custom_profiles())==1
        manager.list.setCurrentRow(len(manager.values)-1)
        monkeypatch.setattr(QInputDialog,"getText",lambda *a,**kw:("Renamed door",True))
        manager.rename()
        assert profiles.custom_profiles()[0]["name"]=="Renamed door"
        manager.list.setCurrentRow(len(manager.values)-1)
        panel.mass.setValue(7)
        manager.replace()
        assert profiles.custom_profiles()[0]["body"]["mass"]==7
        manager.list.setCurrentRow(len(manager.values)-1)
        manager.delete()
        assert profiles.custom_profiles()==[]
    finally:
        if old is None:
            settings.remove(profiles.STORE)
        else:
            settings.setValue(profiles.STORE,old)


@pytest.mark.parametrize("panel,selection,profiles_title",[("de","Allgemein","Newton-Profile"),("fr","Generic","Newton profiles")],indirect=["panel"])
def test_extension_ui_uses_host_language_and_english_fallback(panel,selection,profiles_title):
    assert panel.editor.title()==selection
    panel.show_profiles()
    assert panel.profile_manager.windowTitle()==profiles_title


def test_toolbar_groups_and_icons_follow_palette_and_state(panel):
    from PySide6.QtGui import QPalette,QColor,QIcon
    from PySide6.QtWidgets import QApplication
    palette = QApplication.palette()
    assert len([a for a in panel.toolbar.actions() if a.isSeparator()])==4
    assert "profiles" not in panel.actions and "settings" not in panel.actions
    assert len(panel.actions)==12
    try:
        assert all(not a.icon().isNull() for a in panel.actions.values())
        rotate = panel.actions["rotate"].icon()
        assert rotate.pixmap(24,QIcon.Disabled).toImage()!=rotate.pixmap(24,QIcon.Normal).toImage()
        dark = QPalette(palette)
        dark.setColor(QPalette.WindowText,QColor("white"))
        QApplication.setPalette(dark)
        panel.refresh_icons()
        white = panel.actions["rotate"].icon().cacheKey()
        light = QPalette(palette)
        light.setColor(QPalette.WindowText,QColor("black"))
        QApplication.setPalette(light)
        panel.refresh_icons()
        assert panel.actions["rotate"].icon().cacheKey()!=white
    finally:
        QApplication.setPalette(palette)


def test_native_preferences_stage_icons_and_profiles_until_ok(panel,monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QInputDialog
    from views.preferences_dialog import PreferencesDialog
    from newton import profiles
    st = QSettings()
    key = "newton/show_colliders_by_default"
    old_profiles,old_colliders = st.value(profiles.STORE),st.value(key)
    st.remove(profiles.STORE)
    st.setValue(key,False)
    group = select_demo_axis(panel)
    try:
        dialog = PreferencesDialog(panel.app.window)
        page = dialog.newton_page
        assert dialog._tabs.tabText(dialog._tabs.indexOf(page))=="Newton"
        assert page.profiles.apply_button.isHidden()
        page.colliders.setChecked(True)
        monkeypatch.setattr(QInputDialog,"getText",lambda *a,**kw:("Draft profile",True))
        page.profiles.save_selection()
        assert profiles.custom_profiles()==[]
        assert str(st.value(key)).lower()=="false"
        dialog.reject()
        dialog.deleteLater()
        assert profiles.custom_profiles()==[]
        assert str(st.value(key)).lower()=="false"

        dialog = PreferencesDialog(panel.app.window)
        page = dialog.newton_page
        assert len(page.profiles.values)==8
        page.colliders.setChecked(True)
        page.profiles.save_selection()
        page.profiles.list.setCurrentRow(8)
        monkeypatch.setattr(QInputDialog,"getText",lambda *a,**kw:("Saved profile",True))
        page.profiles.rename()
        page.profiles.replace()
        dialog.accept()
        assert str(st.value(key)).lower()=="true"
        assert profiles.custom_profiles()[0]["name"]=="Saved profile"
        assert profiles.custom_profiles()[0]["body"]["mass"]==group.ext[KEY]["mass"]
        assert panel.profile_combo.findText("Saved profile")>=0
        dialog.deleteLater()

        dialog = PreferencesDialog(panel.app.window)
        dialog.newton_page.profiles.list.setCurrentRow(8)
        dialog.newton_page.profiles.delete()
        assert len(profiles.custom_profiles())==1
        dialog.accept()
        assert profiles.custom_profiles()==[]
        dialog.deleteLater()
    finally:
        if old_colliders is None:st.remove(key)
        else:st.setValue(key,old_colliders)
        if old_profiles is None:
            st.remove(profiles.STORE)
        else:
            st.setValue(profiles.STORE,old_profiles)


def test_window_preferences_entry_uses_adapter_without_duplicate_pages(panel,monkeypatch):
    from views.preferences_dialog import PreferencesDialog
    from newton.preferences import install_preferences
    install_preferences(panel)
    opened = []
    def inspect(dialog):
        opened.append(dialog)
        assert sum(dialog._tabs.widget(i).objectName()=="newton_preferences"
                   for i in range(dialog._tabs.count()))==1
        assert dialog._tabs.currentWidget() is dialog._units_page
        dialog.reject()
        return 0
    monkeypatch.setattr(PreferencesDialog,"exec",inspect)
    panel.app.window.open_preferences(page="units")
    assert len(opened)==1


def seed_coupled_robot(panel):
    from scripts.robot_arm import build
    from newton.model import AddDemo
    groups = build(True).groups
    panel.app.viewport.history.execute(AddDemo(groups))
    panel.app.scene.select([groups[-2]])
    panel.app.viewport.notify_scene_changed()
    return groups


def test_shared_opening_control_maps_mm_to_both_jaws_and_resets(panel,qtapp):
    groups = seed_coupled_robot(panel)
    left,right = groups[-2:]
    assert len(panel.controls.rows)==5
    assert left.uid in panel.controls.rows and right.uid not in panel.controls.rows
    panel.start_or_pause()
    wait(qtapp,lambda:panel.session.ready)
    values = panel.controls.findChildren(QDoubleSpinBox)
    opening = next(v for v in values if v.suffix().strip()=="mm")
    assert opening.minimum()==pytest.approx(5)
    assert opening.maximum()==pytest.approx(105)
    opening.setValue(25)
    assert panel.session.targets[left.uid]==pytest.approx(.04)
    assert right.uid not in panel.session.targets
    assert not panel.session.can_drag(right.uid)
    wait(qtapp,lambda:panel.session.joint_states.get(left.uid,{}).get("position",0)>.035)
    panel.session.toggle()
    assert panel.session.joint_states[left.uid]["position"]==pytest.approx(panel.session.joint_states[right.uid]["position"],abs=.0002)
    panel.session.reset()
    assert panel.session.joint_states=={}
    assert left.ext[KEY]["joint"]["target"]==0


def test_coupling_picker_direction_and_erase_master_are_undoable(panel):
    groups = seed_coupled_robot(panel)
    left,right = groups[-2:]
    panel.app.scene.select([right])
    panel.app.viewport.notify_scene_changed()
    editor = panel.coupling_editor
    assert editor.master.currentData()==left.uid
    assert editor.direction.currentData()==-1  # physical direction; axes point inward
    editor.master.setCurrentIndex(0)
    editor.change()
    assert not right.ext[KEY]["joint"].get("coupling")
    panel.app.viewport.history.undo()
    panel.app.viewport.notify_scene_changed()
    assert right.ext[KEY]["joint"]["coupling"]["master"]==left.uid
    panel.app.scene.select([left])
    panel.app.viewport.notify_scene_changed()
    panel.remove_axes()
    assert left.ext[KEY]["joint"] is None
    assert not right.ext[KEY]["joint"].get("coupling")
    panel.app.viewport.history.undo()
    assert left.ext[KEY]["joint"]
    assert right.ext[KEY]["joint"]["coupling"]["master"]==left.uid


def test_axis_layer_hides_only_guides_and_disables_eraser_picking(panel):
    from newton.model import AXES_LAYER,ensure_axis_layer
    from newton.eraser import pick_axis
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    layer = ensure_axis_layer(panel.app.scene)
    assert len([l for l in panel.app.scene.layers if l.name==AXES_LAYER])==1
    assert group.layer!=AXES_LAYER
    xs,ys,_ = vp.world_to_pixels([group.ext[KEY]["joint"]["pivot"]])
    assert pick_axis(panel,vp,float(xs[0]),float(ys[0]))==group.uid
    class Painter:
        def __init__(self): self.calls=[]
        def __getattr__(self,key): return lambda *a:self.calls.append((key,a))
    painter = Painter()
    panel.draw_joints(vp,painter)
    assert painter.calls
    layer.visible = False
    painter = Painter()
    panel.draw_joints(vp,painter)
    assert not painter.calls
    assert pick_axis(panel,vp,float(xs[0]),float(ys[0])) is None
    assert not group.hidden and group.ext[KEY]["joint"]


def test_axis_guides_show_limits_and_live_parent_frame(panel,qtapp):
    from newton.axis_guides import guide_geometry
    from newton.eraser import axis_frame
    groups = seed_coupled_robot(panel)
    panel.app.scene.select([groups[2]])
    panel.app.viewport.notify_scene_changed()
    j = next(j for j in panel.axis_rows if j["uid"]==groups[2].uid)
    lines,labels = guide_geometry(panel,panel.app.viewport,j,True)
    assert {kind for p,q,kind in lines}>={"range","minimum","maximum","actual","target","zero"}
    assert len(labels)==3
    panel.start_or_pause()
    wait(qtapp,lambda:panel.session.ready)
    parent = panel.session.movers[groups[1].uid]
    parent.xform.translate(1,2,3)
    anchor,*_ = axis_frame(panel,panel.app.viewport,j)
    assert anchor.x()==pytest.approx(1,abs=.001)
    assert anchor.y()==pytest.approx(2,abs=.001)
    assert anchor.z()==pytest.approx(3.65,abs=.001)
    panel.session.joint_states[j["uid"]] = dict(position=math.pi/6,velocity=0)
    lines,labels = guide_geometry(panel,panel.app.viewport,j,True)
    assert any(text=="30.0°" and kind=="actual" for p,text,kind in labels)
    panel.session.reset()


def test_collision_inspection_uses_compiled_shapes_and_refreshes_after_edits(panel,qtapp):
    from scripts.collision_demo import build
    from newton.model import AddDemo
    groups = build().groups
    panel.app.viewport.history.execute(AddDemo(groups))
    panel.app.scene.select([groups[1]]);panel.app.viewport.notify_scene_changed()
    try:
        panel.show_colliders.setChecked(True)
        wait(qtapp,lambda:len(panel.collision_view.colliders)==6)
        assert panel.collision_view.colliders[groups[-1].uid]["kind"]=="Convex hull"
        assert panel.collision_view.colliders[groups[-1].uid]["edges"]
        from PySide6.QtGui import QImage,QPainter
        image = QImage(1000,800,QImage.Format_ARGB32);image.fill(Qt.white)
        painter = QPainter(image);panel.draw_joints(panel.app.viewport,painter);painter.end()
        old_key = panel.collision_view.key
        panel.shape.setCurrentIndex(panel.shape.findData("sphere"))
        wait(qtapp,lambda:panel.collision_view.colliders.get(groups[1].uid,{}).get("kind")=="Sphere")
        assert panel.collision_view.key!=old_key
        panel.start_or_pause();wait(qtapp,lambda:panel.session.ready)
        assert panel.session.colliders[groups[1].uid]["kind"]=="Sphere"
        assert panel.collision_view.process is None
        panel.session.reset()
    finally:panel.show_colliders.setChecked(False)


def test_collision_pairs_restore_and_undo_preserve_body_mode_and_native_file(panel,tmp_path):
    from scripts.collision_demo import build
    from newton.model import AddDemo,prepare
    from newton.collision_ui import pair_command,excludes
    from formats import igz
    from core.scene import Scene
    groups = build().groups
    panel.app.viewport.history.execute(AddDemo(groups))
    a,b = groups[3:5]
    panel.app.scene.select([a]);panel.app.viewport.notify_scene_changed()
    pairs = panel.collision_pairs
    assert pairs.list.count()==1
    pairs.list.setCurrentRow(0);pairs.restore()
    assert not excludes(a,b)
    panel.app.viewport.history.undo();panel.app.viewport.notify_scene_changed()
    assert excludes(a,b)
    # A previously unconfigured model group remains static after adding a pair.
    groups[2].ext = None
    panel.app.viewport.history.execute(pair_command(groups[1],groups[2],False))
    assert groups[2].ext[KEY]["mode"]=="static"
    path = tmp_path/"exceptions.igz";igz.save_scene(panel.app.scene,path)
    loaded = Scene();igz.load_into(loaded,path)
    assert excludes(next(g for g in loaded.groups if g.uid==groups[1].uid),next(g for g in loaded.groups if g.uid==groups[2].uid))
    assert len(prepare(loaded)[1])==6


def test_axis_handles_drag_with_native_mouse_events_cancel_and_undo(panel,qtapp):
    import copy
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint
    from newton.eraser import axis_frame
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    panel.app.window.show();vp.resize(800,600);qtapp.processEvents()
    vp.camera.fit_to(*vp.scene.bounds())
    panel.app.window._activate_tool("select")
    before = copy.deepcopy(group.ext)
    matrix = list(group.xform.data())
    j = next(j for j in panel.axis_rows if j["uid"]==group.uid)
    anchor,*_ = axis_frame(panel,vp,j)
    xs,ys,front = vp.world_to_pixels([list(anchor.toTuple())])
    point = QPoint(round(xs[0]),round(ys[0]))
    QTest.mousePress(vp,Qt.LeftButton,Qt.NoModifier,point)
    assert vp.active_tool.__class__.__name__=="AxisEditTool"
    QTest.mouseMove(vp,point+QPoint(35,20));qtapp.processEvents()
    assert panel.axis_preview and group.ext==before
    QTest.mouseRelease(vp,Qt.LeftButton,Qt.NoModifier,point+QPoint(35,20));qtapp.processEvents()
    assert group.ext[KEY]["joint"]["pivot"]!=before[KEY]["joint"]["pivot"]
    assert list(group.xform.data())==matrix
    vp.history.undo();vp.notify_scene_changed()
    assert group.ext==before
    # Cancelling a direction edit keeps the complete original configuration.
    from newton.axis_edit import AxisEditTool
    tool = AxisEditTool(panel,group,group.ext[KEY]["joint"],"direction")
    assert (tool.drag_plane(vp)[0]-anchor).length()>.01
    vp.set_active_tool(tool)
    tool.on_hover(SimpleNamespace(world=anchor+QVector3D(1,1,0),viewport=vp))
    tool.on_cancel(vp);qtapp.processEvents()
    assert group.ext==before and panel.axis_preview is None


def test_axis_labels_are_larger_separated_and_pickable(panel):
    from PySide6.QtGui import QImage,QPainter,QFontMetrics
    from newton.eraser import pick_axis
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    image = QImage(1200,900,QImage.Format_ARGB32);image.fill(Qt.white)
    painter = QPainter(image)
    panel.draw_joints(vp,painter);painter.end()
    hits = panel.axis_label_hits
    assert len(hits)>=4
    assert all(r.height()>=QFontMetrics(vp.font()).height()+10 for r,uid in hits)
    assert all(not a.intersects(b) for i,(a,_) in enumerate(hits) for b,_ in hits[i+1:])
    assert all(not rect.intersects(axis) for rect,uid in hits for axis in panel.axis_obstacles)
    rect,uid = hits[0]
    assert pick_axis(panel,vp,rect.center().x(),rect.center().y())==uid==group.uid


def test_axis_placement_uses_the_native_line_geometry_and_world_axis_snaps(panel):
    from tools.line import LineTool
    from newton.joints import PlacementTool
    from newton.model import box,AddDemo
    from core.group import world_mesh
    group = box("Snap reference",(2,0,1),(1,1,1))
    vp = panel.app.viewport
    vp.history.execute(AddDemo([group]))
    vp.resize(1000,700);vp.camera.set_aspect(1000,700)
    vp.camera.fit_to(*vp.scene.bounds())
    line = LineTool()
    placement = PlacementTool(lambda *a:None,lambda:None)
    points = [v.position for v in world_mesh(group).vertices]
    answers = []
    for point in points:
        xs,ys,front = vp.world_to_pixels([list(point.toTuple())])
        if not front[0]:continue
        x,y = float(xs[0])+1,float(ys[0])+1
        vp.set_active_tool(line);expected = vp._snap_at(x,y,Qt.NoModifier)
        # Fresh placement tool: the previous one was deactivated by the line.
        placement = PlacementTool(lambda *a:None,lambda:None)
        vp.set_active_tool(placement);actual = vp._snap_at(x,y,Qt.NoModifier)
        if expected and expected.kind in ("endpoint","midpoint","vertex"):
            assert actual.kind==expected.kind
            assert (actual.point-expected.point).length()<1e-5
            answers.append(actual)
    assert len(answers)>=2
    start = QVector3D(3,3,2)
    vp.camera.target = start
    vp.camera.distance = 8
    vp.camera.pitch = math.radians(30)
    vp.camera.yaw = math.radians(-45)
    for axis in (QVector3D(1,0,0),QVector3D(0,1,0),QVector3D(0,0,1)):
        point = start+axis
        xs,ys,front = vp.world_to_pixels([list(point.toTuple())])
        line = LineTool();vp.set_active_tool(line);line.start_point = start
        expected = vp._snap_at(float(xs[0])+1,float(ys[0])+1,Qt.NoModifier)
        placement = PlacementTool(lambda *a:None,lambda:None)
        vp.set_active_tool(placement);placement.anchor = start
        actual = vp._snap_at(float(xs[0])+1,float(ys[0])+1,Qt.NoModifier)
        assert expected is not None and expected.kind in ("axis","axis_inference")
        assert actual.kind==expected.kind and actual.axis==expected.axis
        assert (actual.point-expected.point).length()<1e-5


def test_sidebar_position_slider_uses_linear_limits_and_one_undo_per_drag(panel):
    group = select_demo_axis(panel,"Linearschlitten")
    control = panel.ranges["target"]
    assert (control.a,control.b)==pytest.approx((-700,700))
    assert (panel.target.minimum(),panel.target.maximum())==pytest.approx((-700,700))
    hist = panel.app.viewport.history
    before = len(hist.undo_stack)
    control.slider.sliderPressed.emit()
    control.slider.setValue(7500)
    assert group.ext[KEY]["joint"]["target"]==pytest.approx(.35)
    control.slider.setValue(8500)
    control.slider.sliderReleased.emit()
    assert group.ext[KEY]["joint"]["target"]==pytest.approx(.49)
    assert len(hist.undo_stack)==before+1
    hist.undo();panel.app.viewport.notify_scene_changed()
    assert group.ext[KEY]["joint"]["target"]==0
    hist.redo();panel.app.viewport.notify_scene_changed()
    assert group.ext[KEY]["joint"]["target"]==pytest.approx(.49)
    panel.upper.setValue(300)
    assert control.b==300 and panel.target.maximum()==300
    assert group.ext[KEY]["joint"]["target"]==pytest.approx(.3)
    panel.lower.setValue(-100)
    assert control.a==-100 and panel.target.minimum()==-100


def test_sidebar_angle_slider_keeps_precise_multi_turn_input_and_passive_state(panel):
    group = select_demo_axis(panel)
    panel.upper.setValue(360)
    assert panel.ranges["upper"].b==360
    panel.target.setValue(270)
    assert panel.ranges["target"].slider.value()==7500
    assert group.ext[KEY]["joint"]["target"]==pytest.approx(1.5*math.pi)
    before = len(panel.app.viewport.history.undo_stack)
    panel.refresh()
    assert len(panel.app.viewport.history.undo_stack)==before
    panel.drive.setCurrentIndex(panel.drive.findData("free"))
    assert panel.ranges["target"].isHidden()
    panel.limited.setChecked(False)
    assert not panel.ranges["lower"].slider.isEnabled()
    assert not panel.ranges["upper"].slider.isEnabled()


def test_sidebar_keeps_selected_configuration_visible_but_disabled_in_simulation(panel,qtapp):
    group = select_demo_axis(panel)
    assert panel.heading.text().endswith(group.name)
    assert panel.editor.title()=="Generic"
    assert panel.editor.parentWidget().layout().itemAt(0).widget() is panel.editor
    panel.advanced_toggle.setChecked(True)
    panel.start_or_pause();wait(qtapp,lambda:panel.session.ready)
    assert all(not w.isHidden() for w in panel.selection_widgets)
    assert not panel.editor.isEnabled() and not panel.joint_box.isEnabled()
    assert not panel.advanced.isEnabled() and not panel.advanced_toggle.isEnabled()
    assert panel.heading.text().endswith(group.name)
    panel.session.reset()
    assert panel.editor.isEnabled() and panel.advanced_toggle.isEnabled()
    assert panel.advanced_toggle.isChecked() and not panel.advanced.isHidden()


def test_deceleration_sync_custom_value_undo_and_native_save(panel,tmp_path):
    from formats import igz
    from core.scene import Scene
    group = select_demo_axis(panel)
    panel.acceleration.setValue(80)
    assert panel.deceleration.value()==80 and not panel.deceleration.isEnabled()
    assert group.ext[KEY]["joint"]["deceleration"]==pytest.approx(math.radians(80))
    panel.deceleration_sync.setChecked(False);panel.deceleration.setValue(20)
    panel.acceleration.setValue(120)
    assert panel.deceleration.value()==20
    panel.deceleration_sync.setChecked(True)
    assert panel.deceleration.value()==120
    panel.app.viewport.history.undo();panel.app.viewport.notify_scene_changed()
    assert not panel.deceleration_sync.isChecked() and panel.deceleration.value()==20
    path = tmp_path/"braking.igz";igz.save_scene(panel.app.scene,path)
    loaded = Scene();igz.load_into(loaded,path)
    j = next(g for g in loaded.groups if g.uid==group.uid).ext[KEY]["joint"]
    assert j["deceleration"]==pytest.approx(math.radians(20)) and not j["deceleration_sync"]


def test_collision_preferences_default_off_and_use_native_shortcuts(panel):
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QKeySequence
    from views.preferences_dialog import PreferencesDialog
    from views.shortcuts import save_shortcut,apply_user_shortcuts
    st = QSettings();key="newton/show_colliders_by_default"
    old=st.value(key,None);old_keys=panel.collision_action.shortcuts()
    try:
        st.remove(key)
        panel.show_colliders.setChecked(False)
        assert panel.show_colliders.isHidden()
        dialog = PreferencesDialog(panel.app.window)
        page = dialog.newton_page
        assert not page.colliders.isChecked()
        page.configure_shortcut()
        assert dialog._tabs.currentWidget() is dialog._shortcuts
        page.colliders.setChecked(True)
        dialog.reject();dialog.deleteLater()
        assert not panel.collision_view.enabled
        save_shortcut(panel.collision_action,[QKeySequence("Ctrl+Alt+F12")])
        apply_user_shortcuts(panel.app.window)
        assert panel.collision_action.shortcut().toString()=="Ctrl+Alt+F12"
        panel.collision_action.trigger()
        assert panel.collision_view.enabled
        assert st.value(key,None) is None  # temporary toggle is not a startup preference
        panel.show_colliders.setChecked(False)
    finally:
        save_shortcut(panel.collision_action,old_keys)
        apply_user_shortcuts(panel.app.window)
        if old is None:st.remove(key)
        else:st.setValue(key,old)


def test_eraser_cancel_and_shift_preserve_axis_and_normal_geometry_erase_still_works(panel,monkeypatch):
    from PySide6.QtCore import QPointF
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    xs,ys,_ = vp.world_to_pixels([group.ext[KEY]["joint"]["pivot"]])
    panel.app.window._activate_tool("eraser")
    eraser = vp.active_tool
    ctx = SimpleNamespace(viewport=vp,screen=QPointF(float(xs[0]),float(ys[0])),modifiers=Qt.NoModifier)
    before = len(vp.history.undo_stack)
    eraser.on_click(ctx)
    eraser.on_cancel(vp)
    eraser.on_release(vp)
    assert group.ext[KEY]["joint"]
    assert len(vp.history.undo_stack)==before
    ctx.modifiers = Qt.ShiftModifier
    eraser.on_click(ctx)
    eraser.on_release(vp)
    assert group.ext[KEY]["joint"]
    assert group in vp.scene.groups and not group.hidden
    monkeypatch.setattr(vp,"pick_text_label",lambda *a,**kw:None)
    monkeypatch.setattr(vp,"pick_visible_edge",lambda *a:None)
    monkeypatch.setattr(vp,"pick_group",lambda *a:group)
    ctx.screen,ctx.modifiers = QPointF(20,20),Qt.NoModifier
    eraser.on_click(ctx)
    eraser.on_release(vp)
    assert group not in vp.scene.groups
    vp.history.undo()
    assert group in vp.scene.groups

def test_profile_values_inspect_builtin_and_edit_custom_without_precision_loss(panel,monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QInputDialog
    from newton import profiles
    st = QSettings();old = st.value(profiles.STORE);st.remove(profiles.STORE)
    try:
        group = select_demo_axis(panel)
        panel.show_profiles();editor = panel.profile_manager.editor
        assert editor.parameters.name.isReadOnly()
        assert editor.parameters.mass.isReadOnly()
        assert editor.parameters.motion['force'].value()==100
        monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('Editable',True))
        editor.duplicate();assert len(profiles.custom_profiles())==1
        p = editor.parameters
        assert not p.mass.isReadOnly()
        original_speed = profiles.custom_profiles()[0]['joint']['max_speed']
        p.mass.setValue(4.25)
        assert profiles.custom_profiles()[0]['body']['mass']==4.25
        assert profiles.custom_profiles()[0]['joint']['max_speed']==original_speed
        p.own.setChecked(True);p.gravity[2].setValue(0)
        assert profiles.custom_profiles()[0]['body']['simulation_override']['gravity']==[0,0,0]
        assert profiles.builtins()[0]['body']['mass']==1
    finally:
        if old is None:st.remove(profiles.STORE)
        else:st.setValue(profiles.STORE,old)


def test_profile_sync_tracks_local_and_profile_changes_and_undo(panel,tmp_path):
    import copy
    from PySide6.QtCore import QSettings
    from newton import profiles,profile_sync
    from newton.model import settings
    st = QSettings();old = st.value(profiles.STORE)
    try:
        group = select_demo_axis(panel)
        p = profiles.save_custom(profiles.from_group(group,'Tracked'))
        panel.apply_profile(p)
        assert profile_sync.status(group,p)=='In sync'
        assert group.uid in panel.controls.rows
        panel.mass.setValue(3)
        assert profile_sync.status(group,p)=='Local changes'
        p['body']['mass']=5;p=profiles.save_custom(p)
        panel.refresh_profiles()
        assert profile_sync.status(group,p)=='Profile changed'
        original = copy.deepcopy(group.ext);mesh = group.mesh
        xform = list(group.xform.data());axis = copy.deepcopy(settings(group)['joint'])
        count = len(panel.app.viewport.history.undo_stack)
        panel.sync_profile()
        assert settings(group)['mass']==5
        assert settings(group)['joint']==axis
        assert group.mesh is mesh and list(group.xform.data())==xform
        assert profile_sync.status(group,p)=='In sync'
        assert len(panel.app.viewport.history.undo_stack)==count+1
        from formats import igz
        path = tmp_path/'linked-profile.igz';igz.save_scene(panel.app.scene,path)
        from core.scene import Scene
        loaded = Scene();igz.load_into(loaded,path)
        restored = next(g for g in loaded.groups if g.uid==group.uid)
        assert settings(restored)['profile_link']==settings(group)['profile_link']
        panel.app.viewport.history.undo();assert group.ext==original
        profiles.delete_custom(p['id']);panel.refresh_profiles()
        assert not panel.profile_sync.isEnabled()
        assert profile_sync.status(group,None)=='Missing profile'
    finally:
        if old is None:st.remove(profiles.STORE)
        else:st.setValue(profiles.STORE,old)


def test_preferences_bulk_sync_is_staged_cancel_safe_and_one_undo(panel):
    import copy
    from PySide6.QtCore import QSettings
    from views.preferences_dialog import PreferencesDialog
    from newton import profiles
    from newton.model import box,AddDemo,settings
    st = QSettings();old = st.value(profiles.STORE);st.remove(profiles.STORE)
    try:
        a,b = box('A',(0,0,1),(.1,.1,.1)),box('B',(1,0,1),(.1,.1,.1))
        panel.app.viewport.history.execute(AddDemo([a,b]))
        p = profiles.save_custom(profiles.from_group(a,'Shared'))
        for g in (a,b):
            panel.app.scene.select([g]);panel.refresh()
            panel.apply_profile(p)
        original = [copy.deepcopy(g.ext) for g in (a,b)]
        for accept in (False,True):
            dialog = PreferencesDialog(panel.app.window);editor = dialog.newton_page.profiles
            editor.list.setCurrentRow(8)
            editor.parameters.mass.setValue(6)
            editor.sync_linked()
            assert [g.ext for g in (a,b)]==original
            assert profiles.custom_profiles()[0]['body']['mass']==1
            before = len(panel.app.viewport.history.undo_stack)
            if accept:
                dialog.accept();assert len(panel.app.viewport.history.undo_stack)==before+1
                assert all(settings(g)['mass']==6 for g in (a,b))
                assert profiles.custom_profiles()[0]['body']['mass']==6
                panel.app.viewport.history.undo();assert [g.ext for g in (a,b)]==original
            else:dialog.reject();assert len(panel.app.viewport.history.undo_stack)==before
            dialog.deleteLater()
        # Legacy bodies can be associated without changing parameters, then synced.
        panel.app.scene.select([a,b]);panel.refresh()
        dialog = PreferencesDialog(panel.app.window);editor = dialog.newton_page.profiles
        editor.list.setCurrentRow(6);editor.link_selection();editor.sync_linked()
        assert settings(a)['mode']=='dynamic'
        dialog.accept();assert all(settings(g)['mode']=='static' for g in (a,b))
        panel.app.viewport.history.undo();assert [g.ext for g in (a,b)]==original
        dialog.deleteLater()
    finally:
        if old is None:st.remove(profiles.STORE)
        else:st.setValue(profiles.STORE,old)


def test_bulk_profile_sync_preflights_all_bodies_without_partial_changes(panel):
    import copy
    from newton import profiles,profile_sync
    from newton.model import box,AddDemo
    a = select_demo_axis(panel);b = box('No axis',(2,0,1),(.1,.1,.1))
    panel.app.viewport.history.execute(AddDemo([b]))
    original = [copy.deepcopy(g.ext) for g in (a,b)]
    with pytest.raises(ValueError,match='Place an axis'):
        profile_sync.command(panel.app.scene,{a.uid:profiles.builtins()[0],b.uid:profiles.builtins()[0]})
    assert [g.ext for g in (a,b)]==original

def test_link_legacy_body_keeps_implicit_static_behaviour_and_undo(panel):
    from newton.model import box,AddDemo,settings
    group = box('Legacy',(0,0,1),(.1,.1,.1));group.ext = None
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group]);panel.refresh();panel.show_profiles()
    editor = panel.profile_manager.editor;editor.list.setCurrentRow(7)
    editor.link_selection()
    assert settings(group)['mode']=='static' and settings(group)['profile_link']
    panel.app.viewport.history.undo();assert group.ext is None
