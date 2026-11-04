from demo_support import seed_demo
import math
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox
from PySide6.QtCore import QEvent, QSettings, Qt
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
    fields = (panel.shape,panel.drive,panel.mass,panel.coupling_editor.ratio)
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
    assert all(panel.actions[k].isEnabled() for k in ("connect_ball","connect_hinge","connect_fixed"))
    before = len(vp.history.undo_stack);panel.actions["connect_hinge"].trigger()
    tool = vp.active_tool;assert type(tool).__name__=="ConnectionTool" and tool.kind=="hinge"
    monkeypatch.setattr(vp,"pick_group",lambda *args:b)
    ctx = SimpleNamespace(viewport=vp,screen=SimpleNamespace(x=lambda:100,y=lambda:100),world=QVector3D(0,0,2))
    tool.on_hover(ctx);assert tool.glow_group is None,"no target before the point is placed"
    tool.on_click(ctx);assert tool.claims_key(Qt.Key_Y,Qt.NoModifier)
    tool.on_key(vp,Qt.Key_Y,Qt.NoModifier);assert not a.ext[KEY].get("point_attachment")
    assert not tool.claims_key(Qt.Key_Y,Qt.NoModifier)
    tool.on_hover(ctx);assert tool.glow_group is b,"the final click's candidate is outlined"
    tool.on_click(ctx);qtapp.processEvents()
    assert a.ext[KEY]["point_attachment"]["target"]==b.uid
    assert a.ext[KEY]["point_attachment"]["axis"]==[0,1,0]
    assert len(vp.history.undo_stack)==before+1
    assert "reference" not in a.ext[KEY]
    panel.connection_editor.point[0].setValue(100)
    assert a.ext[KEY]["point_attachment"]["point"][0] == pytest.approx(.1)
    vp.history.undo();assert a.ext[KEY]["point_attachment"]["point"][0]==0


def test_connection_makes_the_body_movable_only_when_it_could_not_work_otherwise(panel):
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    vp = panel.app.viewport
    for source_mode,target_mode,expected in [("static","static","dynamic"),("ignore","static","dynamic"),
                                             ("static","dynamic","static"),("dynamic","static","dynamic")]:
        a,b = box("Link",(.5,0,2),(1,.1,.1),mode=source_mode),box("Anchor",(0,0,2),(.1,.1,.1),mode=target_mode)
        vp.history.execute(AddDemo([a,b]));vp.scene.select([a]);panel.refresh()
        before = len(vp.history.undo_stack)
        apply_connection(panel,a,dict(target=b.uid,point=[0,0,2],type="ball"),"Connection created.")
        assert a.ext[KEY]["mode"]==expected and a.ext[KEY]["point_attachment"]["type"]=="ball"
        message = panel.app.window.statusBar().currentMessage()
        assert message.startswith("Connection created.") and ("movable" in message)==(expected!=source_mode)
        assert len(vp.history.undo_stack)==before+1
        vp.history.undo()
        assert a.ext[KEY]["mode"]==source_mode and not a.ext[KEY].get("point_attachment")


def test_connection_to_an_excluded_body_is_refused(panel):
    from newton.model import box,AddDemo
    from newton.connections import connection_command
    a,b = box("Link",(.5,0,2),(1,.1,.1)),box("Anchor",(0,0,2),(.1,.1,.1),mode="ignore")
    panel.app.viewport.history.execute(AddDemo([a,b]))
    with pytest.raises(ValueError,match="participate"):
        connection_command(panel.app.scene,a,dict(target=b.uid,point=[0,0,2],type="ball"))


def test_connection_objects_mirror_connections_and_host_transforms_move_the_point(panel,qtapp):
    from core.history import MoveGroupCommand,RotateGroupCommand,DeleteGroupCommand
    from newton.model import box,AddDemo,AXES_LAYER,prepare
    from newton.connections import apply_connection
    from newton.axis_objects import CONNECTION,markers,owner_id,placement
    a,b = box("Link",(.5,0,2),(1,.1,.1)),box("Anchor",(0,0,2),(.1,.1,.1),mode="static")
    vp,scene = panel.app.viewport,panel.app.scene;history = vp.history
    history.execute(AddDemo([a,b]));panel.refresh()
    steps = len(history.undo_stack)
    apply_connection(panel,a,dict(target=b.uid,point=[0,0,2],type="ball"))
    assert len(history.undo_stack)==steps+1,"the connection and its object are one undo step"
    [marker] = markers(scene,CONNECTION)
    point = lambda:a.ext[KEY]["point_attachment"]["point"]
    assert owner_id(marker)==a.uid and marker.layer==AXES_LAYER and not marker.mesh.faces
    assert placement(marker)[0]==pytest.approx([0,0,2],abs=1e-5)
    assert all(s["uid"]!=marker.uid for s in prepare(scene)[1]),"connection objects never take part in the simulation"
    scene.select([marker])
    assert panel.selected()==[a],"a selected connection object stands for its body"
    history.execute(MoveGroupCommand(marker,QVector3D(.1,0,0)))
    assert len(history.undo_stack)==steps+2 and point()==pytest.approx([.1,0,2],abs=1e-5)
    history.undo()
    assert point()==pytest.approx([0,0,2]) and placement(marker)[0]==pytest.approx([0,0,2],abs=1e-5)
    # Moving the body carries the connection point and its object along.
    history.execute(MoveGroupCommand(a,QVector3D(0,1,0)))
    assert point()==pytest.approx([0,1,2],abs=1e-5) and placement(marker)[0]==pytest.approx([0,1,2],abs=1e-5)
    history.undo()
    # A pin connection carries its pin axis in the object frame.
    apply_connection(panel,a,dict(target=b.uid,point=[0,0,2],type="hinge",axis=[1,0,0]))
    [marker] = markers(scene,CONNECTION)
    assert placement(marker)[1]==pytest.approx([1,0,0],abs=1e-5)
    history.execute(RotateGroupCommand(marker,QVector3D(0,0,2),QVector3D(0,0,1),90))
    assert a.ext[KEY]["point_attachment"]["axis"]==pytest.approx([0,1,0],abs=1e-5)
    # Deleting the connection object deletes the connection, in one undo step.
    steps = len(history.undo_stack)
    history.execute(DeleteGroupCommand(marker))
    assert a.ext[KEY]["point_attachment"] is None and marker not in scene.groups and len(history.undo_stack)==steps+1
    history.undo()
    assert a.ext[KEY]["point_attachment"]["type"]=="hinge" and marker in scene.groups
    # Removing the connection removes its object.
    apply_connection(panel,a,None)
    assert not markers(scene,CONNECTION)


def test_context_menu_selects_only_the_physics_object_the_body_owns(panel,qtapp):
    from PySide6.QtWidgets import QMenu
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.axis_objects import AXIS,CONNECTION,markers,owner_id
    group = select_demo_axis(panel)
    scene = panel.app.scene
    anchor = box("Anchor",(9,9,2),(.1,.1,.1),mode="static");panel.app.viewport.history.execute(AddDemo([anchor]))
    menus = []  # Keeps each menu, and with it its actions, alive.
    def entries(selection):
        menus.append(QMenu());panel.context_menu(menus[-1],selection)
        return {a.text():a for a in menus[-1].actions()}
    actions = entries([group])
    assert actions["Select axis object"].isEnabled() and not actions["Select connection object"].isEnabled()
    actions["Select axis object"].trigger();qtapp.processEvents()
    [axis] = [m for m in markers(scene,AXIS) if owner_id(m)==group.uid]
    assert scene.selection=={axis},"the body is replaced by its axis object"
    apply_connection(panel,group,dict(target=anchor.uid,point=[0,0,2],type="ball"))
    actions = entries([group])
    assert actions["Select connection object"].isEnabled()
    actions["Select connection object"].trigger();qtapp.processEvents()
    assert scene.selection=={markers(scene,CONNECTION)[0]}
    actions = entries([anchor])
    assert not actions["Select axis object"].isEnabled() and not actions["Select connection object"].isEnabled()


def test_body_collision_shape_toggle_overrides_only_this_body(panel):
    from newton.model import box,AddDemo
    a,b = box("A",(0,0,1),(1,1,1)),box("B",(3,0,1),(1,1,1))
    panel.app.viewport.history.execute(AddDemo([a,b]))
    view = panel.collision_view
    panel.show_colliders.setChecked(False)
    try:
        panel.app.scene.select([a]);panel.refresh()
        assert not panel.show_collider.isChecked()
        panel.show_collider.setChecked(True)
        assert view.shown(a.uid) and not view.shown(b.uid) and view.active()
        assert not panel.show_colliders.isChecked(),"the global setting stays as it is"
        panel.show_colliders.setChecked(True)
        assert view.shown(b.uid) and panel.show_collider.isChecked()
        panel.show_collider.setChecked(False)
        assert not view.shown(a.uid) and view.shown(b.uid) and panel.show_colliders.isChecked()
        panel.app.scene.select([b]);panel.refresh()
        assert panel.show_collider.isChecked()
        panel.app.scene.select([a,b]);panel.refresh()
        assert not panel.show_collider.isEnabled()
    finally:
        panel.show_colliders.setChecked(False)
        view.overrides.clear()


def test_connection_object_wins_the_pick_over_the_body_around_it(panel,qtapp):
    from newton.model import box,AddDemo
    from newton.connections import apply_connection,HIT_PX
    from newton.axis_objects import CONNECTION,markers
    from PySide6.QtCore import QPointF
    a,b = box("Link",(.5,0,2),(1,.1,.1)),box("Anchor",(0,0,2),(.1,.1,.1),mode="static")
    vp = panel.app.viewport;vp.resize(1000,700);vp.camera.set_aspect(1000,700)
    vp.history.execute(AddDemo([a,b]));vp.camera.fit_to(*vp.scene.bounds());panel.refresh()
    apply_connection(panel,a,dict(target=b.uid,point=[0,0,2],type="ball"))
    [marker] = markers(vp.scene,CONNECTION);geometry = a.mesh
    xs,ys,_ = vp.world_to_pixels([[0,0,2]])
    near = QPointF(float(xs[0])+HIT_PX-2,float(ys[0]))
    panel.app.window._activate_tool("select");select = vp.active_tool
    ctx = SimpleNamespace(viewport=vp,screen=near,world=QVector3D(0,0,2),modifiers=Qt.NoModifier)
    select.on_hover(ctx)
    assert panel.hover_connection==marker.uid
    select.on_hover(SimpleNamespace(viewport=vp,screen=QPointF(near.x()+40,near.y()),world=QVector3D(),modifiers=Qt.NoModifier))
    assert panel.hover_connection is None
    select.on_click(ctx)
    assert vp.scene.selection=={marker},"clicking the point selects the connection object, not the body"
    panel.app.window._activate_tool("eraser");eraser = vp.active_tool
    eraser.on_click(ctx);eraser.on_release(vp)
    assert a in vp.scene.groups and a.mesh is geometry and marker not in vp.scene.groups
    assert a.ext[KEY]["point_attachment"] is None

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
    # A closed window stays alive; its palette watcher would repaint every later panel's icons too.
    win.deleteLater()
    QApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    set_language(old_language)


@pytest.mark.parametrize("kind,name,display_target,native_target,suffix",[
    ("Servo-Tür","Tür öffnen",60,math.pi/3,"°"),
    ("Linearschlitten","Schlittenposition",400,.4,"mm")])
def test_named_controls_drive_real_session_and_reset_without_saving_runtime_target(
        panel,qtapp,kind,name,display_target,native_target,suffix):
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
    assert tool.on_key(vp,Qt.Key_Return,Qt.NoModifier),"Enter keeps the 0° direction"
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
    assert panel.toolbar.objectName()=="newton_tools"
    assert len(panel.actions)==14
    assert all(not a.icon().isNull() for a in panel.actions.values())
    panel.actions["rotate"].trigger()
    assert panel.dialog is None
    assert panel.app.viewport.active_tool is panel.placement
    panel.placement.on_click(SimpleNamespace(world=QVector3D(2,0,2),viewport=panel.app.viewport))
    panel.placement.on_key(panel.app.viewport,Qt.Key_Z,Qt.NoModifier)
    panel.placement.on_key(panel.app.viewport,Qt.Key_Return,Qt.NoModifier)
    qtapp.processEvents();qtapp.processEvents()
    assert panel.app.window.statusBar().currentMessage()=="Axis placed.","the select tool hint must not hide the result"
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
    assert any("Türrahmen" in name for name in panel.reference_table.names())


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


def remove_button(table,row=0):
    from PySide6.QtWidgets import QToolButton
    return table.findChildren(QToolButton)[row]


def test_reference_table_rows_outline_their_body_on_hover_and_select_it_on_click(panel,qtapp):
    from PySide6.QtCore import Qt,QEvent,QPointF
    from PySide6.QtGui import QEnterEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from newton.model import reference_id
    door = select_demo_axis(panel)
    # The host loads the extension under its own module name.
    Row = sys.modules[type(panel.reference_table).__module__].Row
    parent = next(g for g in panel.app.scene.groups if g.uid==reference_id(door))
    row = next(c for c in panel.reference_table.children() if isinstance(c,Row))
    QApplication.sendEvent(row,QEnterEvent(QPointF(1,1),QPointF(1,1),QPointF(1,1)))
    assert panel.glow_candidate is parent
    QApplication.sendEvent(row,QEvent(QEvent.Leave))
    assert panel.glow_candidate is None
    QApplication.sendEvent(row,QEnterEvent(QPointF(1,1),QPointF(1,1),QPointF(1,1)))
    QTest.mouseClick(row,Qt.LeftButton)
    assert parent in panel.app.scene.selection
    assert door not in panel.app.scene.selection and panel.glow_candidate is None
    # The remove button keeps the selection.
    panel.app.scene.select([door]);panel.app.viewport.notify_scene_changed();panel.refresh()
    QTest.mouseClick(remove_button(panel.reference_table),Qt.LeftButton)
    assert not reference_id(door) and door in panel.app.scene.selection and parent not in panel.app.scene.selection


def test_reference_tables_show_a_picture_and_change_or_remove_the_link(panel,qtapp,monkeypatch):
    from PySide6.QtWidgets import QLabel
    from newton.model import box,AddDemo,reference_id
    from newton.connections import apply_connection
    from newton.flexible import make
    door = select_demo_axis(panel)
    vp = panel.app.viewport
    anchor,other = box("Anchor",(9,9,2),(.1,.1,.1),mode="static"),box("Other",(8,9,2),(.1,.1,.1),mode="static")
    rope = make("Rope",[[i*.1,3,2] for i in range(12)])
    vp.history.execute(AddDemo([anchor,other,rope]))
    apply_connection(panel,door,dict(target=anchor.uid,point=[0,0,2],type="hinge",axis=[0,0,1]))
    panel.app.scene.select([door]);vp.notify_scene_changed();panel.refresh()
    editor = panel.connection_editor
    assert editor.target.names()==["Anchor"] and editor.add.text()=="Set linked body…"
    assert any(not label.pixmap().isNull() for label in editor.target.findChildren(QLabel))
    # Setting the linked body keeps the placed point, type and pin axis.
    editor.add.click()
    monkeypatch.setattr(vp,"pick_group",lambda *a:other)
    vp.active_tool.on_click(SimpleNamespace(viewport=vp,screen=SimpleNamespace(x=lambda:1,y=lambda:1)))
    qtapp.processEvents()
    link = door.ext[KEY]["point_attachment"]
    assert link["target"]==other.uid and link["point"]==[0,0,2] and link["type"]=="hinge"
    assert editor.target.names()==["Other"]
    remove_button(editor.target).click()
    assert not door.ext[KEY].get("point_attachment") and editor.add.text()=="Connect…"
    assert reference_id(door) and panel.reference_table.names()
    remove_button(panel.reference_table).click()
    assert not reference_id(door) and panel.reference_table.names()==[]
    panel.app.scene.select([rope]);vp.notify_scene_changed();panel.refresh()
    flexible = panel.flexible_editor
    flexible.end.fill()
    action = next(a for a in flexible.end.menu.actions() if a.text()=="Anchor")
    offered = [a.text() for a in flexible.end.menu.actions()]
    assert "Rope" not in offered and any(g.billboard for g in panel.app.scene.groups)
    assert not any(g.billboard and g.name in offered for g in panel.app.scene.groups)
    action.trigger()
    assert rope.ext[KEY]["flexible"]["end_reference"]==anchor.uid and flexible.end_table.names()==["Anchor"]
    remove_button(flexible.end_table).click()
    assert rope.ext[KEY]["flexible"]["end_reference"] is None and flexible.end_table.names()==[]


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


def test_invalid_live_limits_keep_valid_model_and_can_be_corrected(panel,qtapp):
    group = select_demo_axis(panel)
    hist = panel.app.viewport.history
    before = len(hist.undo_stack)
    panel.upper.setValue(0)
    assert group.ext[KEY]["joint"]["upper"]==pytest.approx(math.pi/2)
    assert len(hist.undo_stack)==before
    qtapp.processEvents()
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
    from newton.axis_objects import owner_id
    assert source.groups==[g for g in old_groups if owner_id(g)!=group.uid],"only the axis object goes with the axis"
    assert group.mesh is geometry
    assert group.ext[KEY]["joint"] is None
    assert group.ext[KEY]["reference"]==parent
    assert len(vp.history.undo_stack)==before+1
    vp.history.undo()
    assert group.ext[KEY]["joint"]==original
    assert source.groups==old_groups


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
    assert panel.editor.header.text()==selection
    panel.show_profiles()
    assert panel.profile_manager.windowTitle()==profiles_title


def test_toolbar_groups_and_icons_follow_palette_and_state(panel):
    from PySide6.QtGui import QPalette,QColor,QIcon
    from PySide6.QtWidgets import QApplication
    palette = QApplication.palette()
    from PySide6.QtWidgets import QWidgetAction
    def keys(bar):return [a.objectName().removeprefix("newton_") for a in bar.actions() if not isinstance(a,QWidgetAction)]
    assert keys(panel.toolbar)==["rotate","slide","connect_ball","connect_hinge","connect_fixed","link","unlink","free","fixed","panel","controls"]
    assert keys(panel.simulation_bar)==["play","reset","drag"]
    # Categories are set apart by space, not by separator lines.
    assert len([a for a in panel.toolbar.actions() if isinstance(a,QWidgetAction)])==5
    assert not [a for a in panel.toolbar.actions()+panel.simulation_bar.actions() if a.isSeparator()]
    assert "profiles" not in panel.actions and "settings" not in panel.actions
    assert len(panel.actions)==14
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


def test_toolbar_actions_survive_an_invalidated_wrapper(panel,qtapp):
    # PySide 6.11 drops live QAction wrappers when other code walks menus; the sidebar must keep working.
    import shiboken6
    group = select_demo_axis(panel)
    shiboken6.invalidate(panel.actions._actions["rotate"])
    panel.selection_signature = None
    panel.refresh_widgets()
    rotate = panel.actions["rotate"]
    assert shiboken6.isValid(rotate) and rotate.objectName()=="newton_rotate"
    assert rotate in panel.toolbar.actions() and rotate.isEnabled()
    assert panel.heading.text().endswith(group.name)


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
    assert editor.leader==left.uid and editor.table.names()==[left.name]
    assert editor.direction.currentData()==-1  # physical direction; axes point inward
    remove_button(editor.table).click()
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
    assert pairs.table.names()==[b.name]
    remove_button(pairs.table).click()
    assert not excludes(a,b)
    panel.app.viewport.history.undo();panel.app.viewport.notify_scene_changed()
    assert excludes(a,b)
    # A previously unconfigured model group remains static after adding a pair.
    groups[2].ext = None
    panel.app.viewport.history.execute(pair_command(groups[1],groups[2],False))
    assert groups[2].ext[KEY]["mode"]=="static"
    path = tmp_path/"exemptions.igz";igz.save_scene(panel.app.scene,path)
    loaded = Scene();igz.load_into(loaded,path)
    assert excludes(next(g for g in loaded.groups if g.uid==groups[1].uid),next(g for g in loaded.groups if g.uid==groups[2].uid))
    assert len(prepare(loaded)[1])==6


def test_pressing_an_axis_or_connection_point_selects_its_object_without_dragging(panel,qtapp):
    import copy
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QPoint
    from newton.eraser import axis_frame
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.axis_objects import AXIS,CONNECTION,marker_of
    group = select_demo_axis(panel)
    scene,vp = panel.app.scene,panel.app.viewport
    anchor = box("Anchor",(9,9,2),(.1,.1,.1),mode="static");vp.history.execute(AddDemo([anchor]))
    panel.app.window.show();vp.resize(800,600);qtapp.processEvents()
    vp.camera.fit_to(*vp.scene.bounds())
    panel.app.window._activate_tool("select")
    select = vp.active_tool
    j = next(j for j in panel.axis_rows if j["uid"]==group.uid)
    anchor_point,*_ = axis_frame(panel,vp,j)
    before = copy.deepcopy(group.ext)
    xs,ys,_ = vp.world_to_pixels([list(anchor_point.toTuple())])
    point = QPoint(round(xs[0]),round(ys[0]))
    QTest.mousePress(vp,Qt.LeftButton,Qt.NoModifier,point)
    QTest.mouseMove(vp,point+QPoint(35,20))
    QTest.mouseRelease(vp,Qt.LeftButton,Qt.NoModifier,point+QPoint(35,20));qtapp.processEvents()
    assert group.ext==before,"no Newton drag handle edits the axis; the host tools do"
    QTest.mouseClick(vp,Qt.LeftButton,Qt.NoModifier,point);qtapp.processEvents()
    assert vp.active_tool is select and scene.selection=={marker_of(scene,group,AXIS)}
    apply_connection(panel,group,dict(target=anchor.uid,point=list(anchor_point.toTuple()),type="ball"))
    xs,ys,_ = vp.world_to_pixels([list(anchor_point.toTuple())])
    QTest.mouseClick(vp,Qt.LeftButton,Qt.NoModifier,QPoint(round(xs[0]),round(ys[0])));qtapp.processEvents()
    assert vp.active_tool is select and scene.selection=={marker_of(scene,group,CONNECTION)}


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


def test_axis_labels_follow_the_toolbar_icon_size(panel):
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QImage,QPainter
    select_demo_axis(panel)
    vp = panel.app.viewport
    heights = {}
    try:
        for px in (20,24,40):
            QSettings().setValue("ui/toolbar_icon_px",px)
            image = QImage(1200,900,QImage.Format_ARGB32);image.fill(Qt.white)
            painter = QPainter(image);panel.draw_joints(vp,painter);painter.end()
            heights[px] = max(r.height() for r,uid in panel.axis_label_hits)
    finally:
        QSettings().remove("ui/toolbar_icon_px")
    assert heights[20]<=heights[24]<heights[40]


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
    assert panel.editor.header.text()=="Generic"
    assert panel.editor.parentWidget().layout().itemAt(0).widget() is panel.editor
    panel.body_section.set_open(True)
    panel.start_or_pause();wait(qtapp,lambda:panel.session.ready)
    assert all(not w.isHidden() for w in panel.selection_widgets)
    assert all(not fold.body.isEnabled() and fold.header.isEnabled() for fold in panel.sections)
    assert panel.heading.text().endswith(group.name)
    panel.body_section.set_open(False);panel.body_section.set_open(True)
    panel.session.reset()
    assert panel.editor.body.isEnabled() and panel.joint_box.body.isEnabled()
    assert not panel.body_section.body.isHidden()


def test_sidebar_sections_fold_and_remember_their_state(panel):
    from views.fold_section import FoldSection
    folds = panel.findChildren(FoldSection)
    assert set(folds)==set(panel.sections)
    assert not any(isinstance(w,QCheckBox) and w.text()=="More settings" for w in panel.findChildren(QCheckBox))
    panel.coupling_section.set_open(True)
    assert not panel.coupling_section.body.isHidden()
    assert QSettings().value("newton/open_coupling")=="1"
    panel.coupling_section.set_open(False)
    assert panel.coupling_section.body.isHidden()
    assert QSettings().value("newton/open_coupling")=="0"


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


def test_axis_placement_previews_the_axis_along_the_hover_direction(panel,qtapp):
    from newton.model import box,AddDemo
    from newton.axis_guides import axis_rows
    group = box("Klappe",(2,0,2),(.5,.5,.5))
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group])
    panel.refresh()
    panel.actions["rotate"].trigger()
    tool,vp = panel.placement,panel.app.viewport
    tool.on_hover(SimpleNamespace(world=QVector3D(2,0,2),viewport=vp))
    assert axis_rows(panel)==[],"no preview before the origin is picked"
    tool.on_click(SimpleNamespace(world=QVector3D(2,0,2),viewport=vp))
    tool.on_hover(SimpleNamespace(world=QVector3D(2,3,2),viewport=vp))
    [row] = axis_rows(panel)
    assert row["uid"]==group.uid and row["type"]=="hinge"
    assert row["pivot"]==pytest.approx([2,0,2]) and row["axis"]==pytest.approx([0,1,0])
    assert panel.gizmo_sizes[group.uid]==pytest.approx(.1)
    from PySide6.QtGui import QImage,QPainter
    image = QImage(400,300,QImage.Format_ARGB32);image.fill(Qt.white)
    painter = QPainter(image);panel.draw_joints(vp,painter);painter.end()
    tool.on_key(vp,Qt.Key_X,Qt.NoModifier)
    tool.on_key(vp,Qt.Key_Return,Qt.NoModifier)
    qtapp.processEvents()
    assert group.ext[KEY]["joint"]["axis"]==[1,0,0]
    panel.refresh()
    panel.actions["rotate"].trigger()  # re-placing must not draw the old axis next to the preview
    panel.placement.on_click(SimpleNamespace(world=QVector3D(2,0,2.2),viewport=vp))
    panel.placement.on_hover(SimpleNamespace(world=QVector3D(2,0,3),viewport=vp))
    rows = axis_rows(panel)
    assert [r["uid"] for r in rows]==[group.uid] and rows[0]["axis"]==pytest.approx([0,0,1])


def test_axis_objects_mirror_joints_and_host_transforms_move_the_axis(panel,qtapp):
    from core.history import MoveGroupCommand,RotateGroupCommand,DeleteGroupCommand,InsertGroupCommand
    from core.group import copy_group
    from newton.axis_objects import markers,owner_id,placement
    from newton.model import AXES_LAYER,prepare
    group = select_demo_axis(panel)
    scene,history = panel.app.scene,panel.app.viewport.history
    [marker] = [m for m in markers(scene) if owner_id(m)==group.uid]
    joint = lambda:group.ext[KEY]["joint"]
    assert marker.layer==AXES_LAYER and not marker.mesh.faces
    assert placement(marker)[0]==pytest.approx(joint()["pivot"],abs=1e-5)
    assert all(s["uid"]!=marker.uid for s in prepare(scene)[1]),"axis objects never take part in the simulation"
    scene.select([marker])
    assert panel.selected()==[group],"a selected axis object stands for its body"
    steps = len(history.undo_stack)
    original = dict(joint())
    history.execute(MoveGroupCommand(marker,QVector3D(0,.5,0)))
    assert len(history.undo_stack)==steps+1,"moving the axis and writing the joint is one undo step"
    assert joint()["pivot"]==pytest.approx([original["pivot"][0],original["pivot"][1]+.5,original["pivot"][2]],abs=1e-5)
    history.execute(RotateGroupCommand(marker,QVector3D(*joint()["pivot"]),QVector3D(1,0,0),90))
    assert joint()["axis"]==pytest.approx([0,-1,0],abs=1e-5)
    history.undo();history.undo()
    assert joint()["pivot"]==pytest.approx(original["pivot"]) and joint()["axis"]==pytest.approx(original["axis"])
    assert placement(marker)[0]==pytest.approx(original["pivot"],abs=1e-5)
    history.redo()
    assert placement(marker)[0]==pytest.approx(joint()["pivot"],abs=1e-5)
    history.undo()
    # Moving the body carries joint and axis object along.
    history.execute(MoveGroupCommand(group,QVector3D(1,0,0)))
    assert placement(marker)[0]==pytest.approx([original["pivot"][0]+1,*original["pivot"][1:]],abs=1e-5)
    history.undo()
    # A pasted copy of the axis object is dropped; a copy of the body gets its own.
    history.execute(InsertGroupCommand(copy_group(marker)))
    assert [m for m in markers(scene) if owner_id(m)==group.uid]==[marker]
    twin = copy_group(group)
    history.execute(InsertGroupCommand(twin))
    assert len([m for m in markers(scene) if owner_id(m)==twin.uid])==1
    history.undo()
    assert not any(owner_id(m)==twin.uid for m in markers(scene))
    # Deleting the axis object deletes the axis, in one undo step.
    history.execute(DeleteGroupCommand(marker))
    assert joint() is None and marker not in scene.groups
    history.undo()
    assert joint()==original and marker in scene.groups


def test_documents_without_axis_objects_get_them_on_load_without_an_undo_step(panel):
    from newton.axis_objects import markers
    group = select_demo_axis(panel)
    scene,history = panel.app.scene,panel.app.viewport.history
    for m in markers(scene):scene.groups.remove(m)
    history.clear()
    panel.selection_signature = None
    panel.refresh()
    assert [m.ext[KEY]["axis_of"] for m in markers(scene)]==[g.uid for g in scene.groups if (g.ext or {}).get(KEY,{}).get("joint")]
    assert not history.undo_stack


def test_dragging_a_body_previews_its_axis_object_and_dragging_the_axis_object_its_glyph(panel):
    from newton.axis_objects import markers,owner_id
    group = select_demo_axis(panel)
    vp = panel.app.viewport
    [marker] = [m for m in markers(panel.app.scene) if owner_id(m)==group.uid]
    vp.begin_groups_preview([group])
    assert id(marker) in vp._preview_groups and group.uid in vp._newton_preview_axes
    vp.end_groups_preview()
    vp.begin_groups_preview([marker])
    assert group.uid in vp._newton_preview_axes and group.uid not in vp._newton_preview_bodies
    vp.end_groups_preview()


def test_hinge_placement_sets_the_zero_direction_and_start_angle(panel,qtapp):
    from newton.model import box,AddDemo
    from newton.axis_guides import axis_rows
    from newton.axis_objects import markers,owner_id,placement
    from core.history import RotateGroupCommand
    group = box("Klappe",(2.5,0,2),(1,.1,.5))
    panel.app.viewport.history.execute(AddDemo([group]))
    panel.app.scene.select([group]);panel.refresh()
    panel.actions["rotate"].trigger()
    tool,vp = panel.placement,panel.app.viewport
    tool.on_click(SimpleNamespace(world=QVector3D(2,0,2),viewport=vp))
    tool.on_key(vp,Qt.Key_Z,Qt.NoModifier)
    assert panel.placement is tool,"a hinge asks for its 0° direction"
    tool.on_hover(SimpleNamespace(world=QVector3D(2,1,2.4),viewport=vp))
    [row] = axis_rows(panel)
    assert row["zero"]==pytest.approx([0,1,0]) and row["start"]==pytest.approx(-math.pi/2)
    tool.on_click(SimpleNamespace(world=QVector3D(2,1,2.4),viewport=vp))
    qtapp.processEvents()
    joint = group.ext[KEY]["joint"]
    assert joint["zero"]==pytest.approx([0,1,0]) and joint["start"]==pytest.approx(-math.pi/2)
    [marker] = [m for m in markers(panel.app.scene) if owner_id(m)==group.uid]
    assert placement(marker)[2]==pytest.approx([0,1,0],abs=1e-5),"the axis object carries the 0° direction"
    # Turning the axis object about its own axis turns the 0° direction and the start angle.
    vp.history.execute(RotateGroupCommand(marker,QVector3D(2,0,2),QVector3D(0,0,1),90))
    joint = group.ext[KEY]["joint"]
    assert joint["zero"]==pytest.approx([-1,0,0],abs=1e-5) and joint["start"]==pytest.approx(math.pi,abs=1e-5)
    # Turning the body turns the 0° direction with it; the start angle stays.
    vp.history.execute(RotateGroupCommand(group,QVector3D(2,0,2),QVector3D(0,0,1),90))
    joint = group.ext[KEY]["joint"]
    assert joint["zero"]==pytest.approx([0,-1,0],abs=1e-5) and joint["start"]==pytest.approx(math.pi,abs=1e-5)


def test_control_panel_marks_errors_and_warnings_but_not_hints(panel):
    controls = panel.controls
    panel.session.message.emit("Newton process timed out (15 seconds).","error")
    assert not controls.hint_row.isHidden() and not controls.hint_mark.isHidden()
    assert controls.hint_mark.accessibleName()=="Error"
    panel.session.message.emit("Reset before saving the model.","warning")
    assert not controls.hint_mark.isHidden() and controls.hint_mark.accessibleName()=="Warning"
    controls.message("Original model restored.")
    assert controls.hint_mark.isHidden() and controls.hint.text()=="Original model restored."


def test_control_panel_opens_at_the_view_corner_and_fits_its_cards(panel):
    from PySide6.QtCore import QPoint
    controls = panel.controls
    vp = panel.app.viewport
    panel.show_controls()
    corner = vp.mapToGlobal(QPoint(vp.width(),0))
    frame = controls.frameGeometry()
    assert abs(frame.right()+1+controls.MARGIN-corner.x())<=1 and abs(frame.top()-controls.MARGIN-corner.y())<=1
    empty = controls.height()
    assert empty<260
    controls.close()
    controls.refresh([dict(uid=str(i),body="Body",name="Axis",type="hinge",drive="position",lower=-1,upper=1,
        limited=True,target=0,max_speed=1) for i in range(40)],False)
    assert empty<controls.height()<=controls.height_limit
    assert controls.scroll.verticalScrollBar().maximum()>0 or not controls.isVisible()


def test_control_panel_opens_tall_enough_for_its_cards(qtapp,panel):
    seed_demo(panel,"Servo-Tür")
    panel.show_controls()
    qtapp.processEvents()
    scroll = panel.controls.scroll
    assert scroll.height()>=scroll.widget().sizeHint().height()


def squashed_widgets(root):
    """Visible controls the layout gave less height than they need; a spin box's inner line edit is always smaller."""
    from PySide6.QtWidgets import QWidget,QAbstractSpinBox,QComboBox,QPushButton,QCheckBox,QLabel,QLineEdit
    kinds = (QAbstractSpinBox,QComboBox,QPushButton,QCheckBox,QLabel,QLineEdit)
    return [(type(w).__name__,w.height(),w.minimumSizeHint().height()) for w in root.findChildren(QWidget)
        if isinstance(w,kinds) and w.isVisible() and not isinstance(w.parentWidget(),QAbstractSpinBox)
        and w.height()<w.minimumSizeHint().height()-1]


@pytest.mark.parametrize("width",[600,400,300,280])
def test_sidebar_rows_keep_their_height_at_every_width(panel,qtapp,width):
    from newton.model import box,AddDemo,Configure
    from newton.connections import apply_connection
    from newton.flexible import make
    door = select_demo_axis(panel)
    vp = panel.app.viewport
    anchor = box("Anchor",(9,9,2),(.1,.1,.1),mode="static")
    rope = make("Rope",[[i*.1,3,2] for i in range(12)])
    vp.history.execute(AddDemo([anchor,rope]))
    apply_connection(panel,door,dict(target=anchor.uid,point=[0,0,2],type="hinge",axis=[0,0,1]))
    vp.history.execute(Configure([door],dict(simulation_override=dict(gravity=[0,0,-1])),partial=True))
    panel.app.window.resize(1500,1100);panel.app.window.show();panel.show_sidebar()
    panel.setFixedWidth(width)
    # Switching from a body without a connection to one with it changes which rows show.
    for body in (anchor,door,rope,door):
        panel.app.scene.select([body]);vp.notify_scene_changed();panel.refresh()
        for fold in panel.sections:fold.set_open(True)
        for _ in range(4):qtapp.processEvents()
        assert not squashed_widgets(panel),(body.name,squashed_widgets(panel))
        scroll = panel.sections[0].parentWidget().parentWidget().parentWidget()
        assert scroll.horizontalScrollBar().maximum()==0,"no sideways scrolling"


def test_folded_sidebar_sections_stack_instead_of_sharing_the_spare_height(panel,qtapp):
    select_demo_axis(panel)
    panel.app.window.resize(1500,1100);panel.app.window.show();panel.show_sidebar()
    for fold in panel.sections:fold.set_open(False)
    for _ in range(4):qtapp.processEvents()
    shown = [f for f in panel.sections if f.isVisible()]
    layout = shown[0].parentWidget().layout()
    assert len(shown)>3 and layout.spacing()>=12
    for upper,lower in zip(shown,shown[1:]):
        assert lower.y()-(upper.y()+upper.height())==layout.spacing(),(upper.header.text(),lower.header.text())


def test_collision_exemptions_live_in_the_body_and_contact_section(panel):
    assert panel.body_section.isAncestorOf(panel.collision_pairs)
    assert not hasattr(panel,"collision_section")


def test_fixed_and_excluded_bodies_disable_settings_without_effect(panel):
    group = select_demo_axis(panel)
    def mode(value):
        panel.mode.setCurrentIndex(panel.mode.findData(value))
        panel.refresh()
        return {fold:fold.body.isEnabled() for fold in panel.sections}
    enabled = mode("dynamic")
    assert all(enabled.values()) and panel.mass.isEnabled()
    enabled = mode("static")
    assert group.ext[KEY]["mode"]=="static"
    assert not enabled[panel.joint_box] and not enabled[panel.coupling_section] and not enabled[panel.flexible_section]
    assert enabled[panel.body_section] and enabled[panel.connection_section] and enabled[panel.editor]
    from newton.model import reference_id
    assert panel.mass.isEnabled()==bool(reference_id(group))
    enabled = mode("ignore")
    assert not enabled[panel.body_section] and not enabled[panel.connection_section] and not enabled[panel.environment_section]
    assert enabled[panel.editor] and enabled[panel.profile_box] and panel.mode.isEnabled()
    assert not any(b.isEnabled() for b in panel.reference_buttons)


def test_locked_axis_and_connection_objects_follow_their_body_only(panel,qtapp):
    from PySide6.QtWidgets import QMenu
    from core.history import MoveGroupCommand
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.axis_objects import AXIS,CONNECTION,marker_of,placement
    group = select_demo_axis(panel)
    scene,history = panel.app.scene,panel.app.viewport.history
    anchor = box("Anchor",(9,9,2),(.1,.1,.1),mode="static");history.execute(AddDemo([anchor]))
    apply_connection(panel,group,dict(target=anchor.uid,point=[0,0,2],type="ball"))
    scene.select([group]);panel.app.viewport.notify_scene_changed();panel.refresh()
    axis,connection = marker_of(scene,group,AXIS),marker_of(scene,group,CONNECTION)
    assert panel.axis_lock.isEnabled() and not panel.axis_lock.isChecked()
    steps = len(history.undo_stack)
    panel.axis_lock.setChecked(True);panel.connection_editor.lock.setChecked(True)
    assert axis.locked and connection.locked and len(history.undo_stack)==steps+2
    panel.refresh()
    assert not panel.connection_editor.fields.isEnabled()
    menu = QMenu();panel.context_menu(menu,[group])
    assert not any(a.isEnabled() for a in menu.actions() if a.text() in ("Select axis object","Select connection object"))
    pivot = placement(axis)[0]
    history.execute(MoveGroupCommand(group,QVector3D(0,.5,0)))
    assert placement(axis)[0]==pytest.approx([pivot[0],pivot[1]+.5,pivot[2]],abs=1e-5),"a locked object still follows its body"
    history.undo();history.undo()
    assert axis.locked and not connection.locked
    history.undo()
    assert not axis.locked


def test_connection_glyph_follows_its_type_in_the_same_undo_step(panel):
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.axis_objects import CONNECTION,marker_of,glyph_name
    scene,history = panel.app.scene,panel.app.viewport.history
    a,b = box("a",(0,0,2),(1,1,1)),box("b",(2,0,2),(1,1,1),mode="static")
    history.execute(AddDemo([a,b]))
    apply_connection(panel,a,dict(target=b.uid,point=[1,0,2],type="ball"))
    marker = marker_of(scene,a,CONNECTION)
    ball = len(marker.mesh.edges)
    assert marker.ext[KEY]["glyph"].startswith("ball/") and ball>40,"equator and meridian"
    steps = len(history.undo_stack)
    apply_connection(panel,a,dict(target=b.uid,point=[1,0,2],type="fixed"))
    assert len(history.undo_stack)==steps+1 and marker_of(scene,a,CONNECTION) is marker
    assert marker.ext[KEY]["glyph"].startswith("fixed/") and len(marker.mesh.edges)==12,"a plain cube"
    history.undo()
    assert marker.ext[KEY]["glyph"].startswith("ball/") and len(marker.mesh.edges)==ball
    # A wire saved with an older drawing is rebuilt on the next sync.
    marker.ext[KEY]["glyph"] = "ball/1"
    history.execute(AddDemo([box("c",(5,5,2),(1,1,1))]))
    assert marker.ext[KEY]["glyph"]==glyph_name(a.ext[KEY]["point_attachment"])


def test_small_connection_glyphs_keep_a_readable_size_on_screen(panel,qtapp):
    from newton.connections import screen_size,RADIUS,MIN_RADIUS_PX
    vp = panel.app.viewport
    panel.app.window.show();vp.resize(800,600);qtapp.processEvents()
    vp.camera.fit_to(QVector3D(-5,-5,0),QVector3D(5,5,4))
    value = dict(point=[0,0,1],type="ball")
    size = screen_size(vp,value,.001)
    xs,ys,_ = vp.world_to_pixels([[0,0,1],[size*RADIUS,0,1],[0,size*RADIUS,1],[0,0,1+size*RADIUS]])
    import math
    assert max(math.hypot(xs[i]-xs[0],ys[i]-ys[0]) for i in (1,2,3))==pytest.approx(MIN_RADIUS_PX,rel=.05)
    assert screen_size(vp,value,2.)==2.,"large glyphs keep the body's size"


def test_collision_exemptions_and_connections_get_their_own_rim_colours(panel):
    from PySide6.QtGui import QImage,QPainter,QColor
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.collision_ui import pair_command
    from newton.axis_guides import COLOURS
    from newton import glow
    scene,vp = panel.app.scene,panel.app.viewport
    a,b,c = box("a",(0,0,2),(1,1,1)),box("b",(3,0,2),(1,1,1),mode="static"),box("c",(-3,0,2),(1,1,1))
    vp.history.execute(AddDemo([a,b,c]))
    apply_connection(panel,a,dict(target=b.uid,point=[1,0,2],type="ball"))
    vp.history.execute(pair_command(a,c,False))
    assert [g.name for g in glow.linked(scene,[c],"exemption")]==["a"]
    scene.select([a])
    image = QImage(vp.width(),vp.height(),QImage.Format_ARGB32);image.fill(QColor(0,0,0,0))
    painter = QPainter(image);glow.draw(panel,vp,painter);painter.end()
    colours = {image.pixelColor(x,y).rgb()&0xffffff for x in range(image.width()) for y in range(image.height()) if image.pixelColor(x,y).alpha()==255}
    assert QColor(*COLOURS["connected"]).rgb()&0xffffff in colours
    assert QColor(*COLOURS["exemption"]).rgb()&0xffffff in colours
    assert QColor(*COLOURS["actual"]).rgb()&0xffffff not in colours


def test_selection_outlines_linked_bodies_and_picks_outline_their_candidate(panel):
    from PySide6.QtGui import QImage,QPainter,QColor
    from newton.model import box,AddDemo
    from newton.connections import apply_connection
    from newton.interaction import ReferencePickTool
    from newton.reference_table import ChooseButton
    from newton import glow
    scene,vp = panel.app.scene,panel.app.viewport
    a,b,c,d = box("a",(0,0,2),(1,1,1)),box("b",(2,0,2),(1,1,1),mode="static"),box("c",(0,3,2),(1,1,1)),box("d",(5,5,2),(1,1,1))
    c.ext[KEY]["reference"] = a.uid
    vp.history.execute(AddDemo([a,b,c,d]))
    apply_connection(panel,a,dict(target=b.uid,point=[1,0,2],type="ball"))
    assert [g.name for g in glow.linked(scene,[a])]==["c"],"dependent body"
    assert [g.name for g in glow.linked(scene,[a],"connection")]==["b"],"connection target"
    assert [g.name for g in glow.linked(scene,[b],"connection")]==["a"],"links count in both directions"
    assert glow.linked(scene,[d])==[] and glow.linked(scene,[d],"connection")==[]
    scene.select([a])
    def painted():
        image = QImage(vp.width(),vp.height(),QImage.Format_ARGB32);image.fill(QColor(0,0,0,0))
        painter = QPainter(image);glow.draw(panel,vp,painter);painter.end()
        return sum(image.pixelColor(x,y).alpha()>0 for x in range(0,image.width(),4) for y in range(0,image.height(),4))
    linked_only = painted()
    assert linked_only>0
    tool = ReferencePickTool(lambda g:None,lambda:None,lambda g:g is not d)
    class Context:
        viewport,screen = vp,type("P",(),{"x":lambda s:0,"y":lambda s:0})()
    for picked,expected in ((d,None),(b,b),(None,None)):
        vp.pick_group = lambda x,y,g=picked:g
        tool.on_hover(Context())
        assert tool.glow_group is expected,"only a body the click would accept gets a rim"
    tool.glow_group = d
    vp.active_tool = tool
    try:
        assert painted()>linked_only
    finally:
        vp.active_tool = None
    offered = []
    button = ChooseButton("Choose…",lambda:[("b",b,"b")],lambda k:None,"none",offered.append)
    button.fill()
    button.hover(button.menu.actions()[0])
    button.menu.aboutToHide.emit()
    assert offered==[b,None]
    glow.offer(panel,b)
    assert panel.glow_candidate is b
    glow.offer(panel,None)


def test_control_panel_grows_when_the_speed_line_appears(qtapp,panel):
    seed_demo(panel,"Servo-Tür")
    panel.show_controls()
    controls = panel.controls
    controls.message("Drag passive bodies. Use controls for actuators.")
    qtapp.processEvents()
    room = controls.scroll.height()
    controls.show_performance(dict(speed=1.0))
    qtapp.processEvents()
    assert controls.scroll.height()>=room
