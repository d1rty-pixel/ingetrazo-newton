"""Undoable closed-loop attachments placed and edited in the model."""
import math
from PySide6.QtCore import Qt,QTimer,QPointF
from PySide6.QtGui import QVector3D,QColor,QPen,QBrush,QPainter,QFontMetrics
from tools.base import Tool
from .model import KEY,settings,Configure,axes_visible
from .worker import attachment_settings
from .i18n import tr

KINDS = {"ball":"Ball joint","hinge":"Pin joint","fixed":"Fixed connection"}


def editable(scene,group):
    return group in scene.groups and not group.hidden and not getattr(group,"locked",False) and not any(l.name==group.layer and (not l.visible or l.locked) for l in scene.layers)


def connection_command(scene,source,value):
    if not editable(scene,source):raise ValueError("The body is hidden or locked.")
    patch = dict(point_attachment=value)
    if value is not None:
        value = attachment_settings(value);patch["point_attachment"] = value
        target = next((g for g in scene.groups if g.uid==value["target"]),None)
        if target is source or target is None:raise ValueError("Choose another body.")
        if not editable(scene,target):raise ValueError("The body is hidden or locked.")
        if settings(source).get("flexible") or settings(target).get("flexible"):
            raise ValueError("Use the flexible material end attachments for ropes and cables.")
        if KEY in (target.ext or {}) and settings(target)["mode"]=="ignore":raise ValueError("Both bodies must participate in the simulation.")
        # A connection to a fixed target only works if this body moves; a fixed body may still anchor a movable target.
        mode = settings(source)["mode"] if KEY in (source.ext or {}) else None
        if mode in (None,"ignore") or (mode=="static" and (KEY not in (target.ext or {}) or settings(target)["mode"]=="static")):
            patch["mode"] = "dynamic"
    return Configure([source],patch,partial=True)


def apply_connection(panel,source,value,message=None):
    if panel.session.workspace:return
    command = connection_command(panel.app.scene,source,value)
    panel.app.viewport.history.execute(command)
    panel.app.viewport.notify_scene_changed()
    if message:
        made_movable = KEY in (source.ext or {}) and "mode" in command.values
        panel.status_message(tr("{message} The body is now movable.",message=tr(message)) if made_movable else tr(message))


class ConnectionTool(Tool):
    name = tr("Connect bodies")
    uses_snap = True
    magnetic_axis_deg = 3.;screen_axis_px = 9.

    """Point first, then the pin direction for a pin joint, and the other body with the final click."""

    def __init__(self,panel,source,kind):
        self.panel,self.source,self.kind = panel,source,kind
        self.scene = panel.app.scene;self.anchor = None;self.axis = None;self.hover = None;self.done = False;self.glow_group = None

    @property
    def start_point(self):return self.anchor

    @property
    def placed(self):return self.anchor is not None and (self.kind!="hinge" or self.axis is not None)

    def value(self,target):
        value = dict(target=target.uid,type=self.kind,point=list(self.anchor.toTuple()))
        if self.axis is not None:value["axis"] = list(self.axis.toTuple())
        return value

    def prompt(self,vp):
        text = ("Pick the connection point. Esc cancels." if self.anchor is None else
                "Pick the other body. Esc cancels." if self.placed else "Pick the pin direction or press X/Y/Z.")
        vp.flash_status(tr(text),15000)

    def on_activate(self,vp):self.prompt(vp)

    def on_hover(self,ctx):
        self.hover = QVector3D(ctx.world)
        group = None
        if self.placed:
            group = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
            try:
                if group is not None:connection_command(self.scene,self.source,self.value(group))
            except ValueError:group = None
        self.glow_group = group
        ctx.viewport.update()

    def on_click(self,ctx):
        if self.done:return
        try:
            if self.panel.app.scene is not self.scene:raise ValueError("Document changed.")
            if self.anchor is None:
                self.anchor = QVector3D(ctx.world);self.prompt(ctx.viewport)
            elif not self.placed:
                self.aim(ctx.viewport,QVector3D(ctx.world)-self.anchor)
            else:
                target = ctx.viewport.pick_group(ctx.screen.x(),ctx.screen.y())
                if target is not None:self.finish(target)
        except ValueError as exc:self.panel.status_message(str(exc))

    def aim(self,vp,axis):
        if axis.lengthSquared()<1e-10:return
        self.axis = axis.normalized();self.prompt(vp)

    def finish(self,target):
        if self.done:return
        apply_connection(self.panel,self.source,self.value(target),"Connection created.")
        self.done = True;self.glow_group = None;QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))

    def claims_key(self,key,modifiers):
        return self.anchor is not None and not self.placed and key in (Qt.Key_X,Qt.Key_Y,Qt.Key_Z) and not modifiers & (Qt.ControlModifier|Qt.AltModifier)

    def on_key(self,vp,key,modifiers):
        if self.claims_key(key,modifiers):
            self.aim(vp,QVector3D(*{Qt.Key_X:(1,0,0),Qt.Key_Y:(0,1,0),Qt.Key_Z:(0,0,1)}[key]));return True
        return False

    def on_cancel(self,vp):self.done = True;QTimer.singleShot(0,lambda:self.panel.app.window._activate_tool("select"))

    def on_deactivate(self,vp):self.done = True;self.glow_group = None

    def rubber_band_lines(self):return [(self.anchor,self.hover)] if self.anchor is not None and self.hover is not None else []


def begin(panel,kind=None):
    """Connect the selected body; without ``kind`` the sidebar's connection type is used."""
    groups = panel.selected()
    if panel.session.workspace or len(groups)!=1:return
    if not editable(panel.app.scene,groups[0]):
        panel.status_message(tr("The body is hidden or locked."));return
    panel.app.viewport.set_active_tool(ConnectionTool(panel,groups[0],kind or panel.connection_editor.kind.currentData()))


def point_in_view(panel,group,value):
    """The connection point carried along by its simulated body."""
    point = QVector3D(*value["point"])
    spec = panel.session.specs.get(group.uid);mover = panel.session.movers.get(group.uid)
    if spec and mover:
        origin = spec["joint"]["pivot"] if spec.get("joint") else spec["center"]
        return mover.xform.map(point-QVector3D(*origin))
    return point


# Screen pixels around a connection object that count as a hit: the point mostly lies inside a body, whose faces would win the host's pick.
HIT_PX = 16.


def pick(panel,vp,x,y):
    """The connection object under the cursor, or None."""
    scene = panel.app.scene
    if panel.session.workspace or vp is not panel.app.viewport or not axes_visible(scene,picking=True):return None
    from .axis_objects import CONNECTION,markers,placement
    best,answer = HIT_PX,None
    for marker in markers(scene,CONNECTION):
        if not editable(scene,marker):continue
        xs,ys,front = vp.world_to_pixels([placement(marker)[0]])
        distance = math.hypot(x-float(xs[0]),y-float(ys[0]))
        if front[0] and distance<best:best,answer = distance,marker
    return answer


def ring(painter,x,y,colour):
    r = 7
    painter.setPen(QPen(colour,2));painter.setBrush(QColor(25,29,35,220))
    painter.drawEllipse(x-r,y-r,r*2,r*2);painter.drawLine(x-r-3,y,x+r+3,y);painter.drawLine(x,y-r-3,x,y+r+3)


RED,LOCKED = (235,65,45),(150,150,150)
# Glyph radius as a share of the body's gizmo size; the pin reaches PIN times further.
RADIUS,PIN = .35,2.2


def colours():
    """(glyph, point): a connection is a joint, so it is drawn in the axis colours; violet stays "target"."""
    from .axis_guides import COLOURS
    return COLOURS["axis"],COLOURS["actual"]


def circle(a,b,centre=(0,0,0),r=1.,n=24):
    return [tuple(centre[k]+(a[k]*math.cos(t)+b[k]*math.sin(t))*r for k in range(3)) for t in (2*math.pi*i/n for i in range(n+1))]


def glyph(kind):
    """Polylines in the object's own frame (z along the pin), drawn like the dropdown pictograms:
    a ball is a sphere (equator and meridian; the overlay adds its outline), a pin a rod through
    a ring, a rigid connection a plain cube."""
    x,y,z = (1,0,0),(0,1,0),(0,0,1)
    if kind=="ball":
        lines = [circle(x,y),circle(x,z)]
    elif kind=="hinge":
        lines = [[(0,0,-PIN),(0,0,PIN)],circle(x,y,r=.8)]
    else:
        corners = [(a*.6,b*.6,c*.6) for a in (-1,1) for b in (-1,1) for c in (-1,1)]
        lines = [[corners[i],corners[j]] for i in range(8) for j in range(i+1,8) if bin(i^j).count("1")==1]
    return [[tuple(c*RADIUS for c in p) for p in line] for line in lines]


def glyph_frame(value,size):
    from .axis_objects import CONNECTION,target_matrix
    m = target_matrix(CONNECTION,value)
    m.scale(size)
    return m


def size_of(panel,group):
    sizes = getattr(panel,"gizmo_sizes",{})
    if group.uid not in sizes:
        from .panel import gizmo_size
        sizes[group.uid] = gizmo_size(group)
    return sizes[group.uid]


# Smallest on-screen glyph radius: the glyph of a small body would otherwise vanish behind its handle.
MIN_RADIUS_PX = 18.


def screen_radius(vp,value,size):
    """On-screen glyph radius in pixels for a glyph of ``size``, or None when it is behind the camera."""
    point = QVector3D(*value["point"])
    ends = [point+QVector3D(*d)*size*RADIUS for d in ((1,0,0),(0,1,0),(0,0,1))]
    xs,ys,front = vp.world_to_pixels([list(p.toTuple()) for p in [point]+ends])
    if not all(front):return None
    return max(math.hypot(float(xs[i])-float(xs[0]),float(ys[i])-float(ys[0])) for i in (1,2,3))


def screen_size(vp,value,size):
    """The body's glyph size, enlarged so the glyph keeps MIN_RADIUS_PX on screen."""
    radius = screen_radius(vp,value,size)
    return size*max(1.,MIN_RADIUS_PX/radius) if radius and radius>1e-6 else size


def point_mark(painter,x,y,kind,colour):
    """The attachment point, shaped like the accent of the type's pictogram: a ring, or for a rigid connection a plate with two screws."""
    painter.setPen(QPen(colour,3));painter.setBrush(QBrush(QColor(24,28,34,220)))
    if kind!="fixed":
        painter.drawEllipse(x-6,y-6,12,12)
        return
    painter.drawRoundedRect(x-7,y-6,14,12,2,2)
    painter.setPen(Qt.NoPen);painter.setBrush(colour)
    for dx in (-3,3):painter.drawEllipse(QPointF(x+dx,y),1.6,1.6)


def caption(panel,vp,painter,x,y,text,colour):
    """A name plate like the axes' own, placed clear of the axis guides."""
    from .axis_guides import place_caption,caption_font
    font = caption_font(vp)
    painter.setFont(font);metrics = QFontMetrics(font)
    text = metrics.elidedText(text,Qt.ElideRight,max(160,min(360,vp.width()//2)))
    rect = place_caption(x,y,metrics.horizontalAdvance(text)+14,metrics.height()+10,vp.width(),vp.height(),
                         getattr(panel,"axis_obstacles",[]),[])
    leader = QPen(colour,1);leader.setStyle(Qt.DotLine);painter.setPen(leader)
    painter.drawLine(x,y,int(max(rect.left(),min(x,rect.right()))),int(max(rect.top(),min(y,rect.bottom()))))
    painter.setBrush(QBrush(QColor(24,28,34,235)));painter.drawRoundedRect(rect,5,5)
    painter.setPen(colour);painter.drawText(rect.adjusted(7,4,-7,-4),Qt.AlignVCenter|Qt.AlignLeft,text)


def draw(panel,vp,painter):
    scene = panel.app.scene
    if not axes_visible(scene):return
    if panel.session.workspace:
        # The simulated scene has no connection objects, so the point is drawn here.
        for group in scene.groups:
            value = settings(group).get("point_attachment")
            if not value or group.hidden or any(l.name==group.layer and not l.visible for l in scene.layers):continue
            point = point_in_view(panel,group,value);xs,ys,front = vp.world_to_pixels([list(point.toTuple())])
            if front[0]:ring(painter,int(xs[0]),int(ys[0]),QColor(*colours()[1]))
        return
    if vp is not panel.app.viewport:return
    from .axis_objects import CONNECTION,markers,owner_id
    bodies = {g.uid:g for g in scene.groups}
    selected = {g.uid for g in panel.selected()}
    shape_colour,point_colour = colours()
    painter.save();painter.setRenderHint(QPainter.Antialiasing,True)
    for marker in markers(scene,CONNECTION):
        body = bodies.get(owner_id(marker))
        if body is None or marker.hidden or any(l.name==body.layer and not l.visible for l in scene.layers):continue
        value = settings(body).get("point_attachment")
        if not value:continue
        locked = bool(getattr(marker,"locked",False))
        hover = marker.uid==getattr(panel,"hover_connection",None)
        colour = QColor(*(RED if hover else LOCKED if locked else shape_colour))
        size = screen_size(vp,value,size_of(panel,body));m = glyph_frame(value,size)
        kind = value.get("type","ball")
        xs,ys,front = vp.world_to_pixels([value["point"]])
        centre = (int(xs[0]),int(ys[0])) if front[0] else None
        radius = screen_radius(vp,value,size)
        if kind=="ball" and centre and radius:
            # The outline of a sphere is a circle from every side.
            painter.setPen(QPen(colour,2));painter.setBrush(QColor(24,28,34,70))
            painter.drawEllipse(QPointF(*centre),radius,radius)
        pen = QPen(colour,2);pen.setCapStyle(Qt.RoundCap);painter.setPen(pen);painter.setBrush(Qt.NoBrush)
        for index,line in enumerate(glyph(kind)):
            pen.setStyle(Qt.DashLine if kind=="hinge" and index==0 else Qt.SolidLine);painter.setPen(pen)
            xs,ys,front = vp.world_to_pixels([list(m.map(QVector3D(*p)).toTuple()) for p in line])
            for i in range(len(line)-1):
                if front[i] and front[i+1]:painter.drawLine(int(xs[i]),int(ys[i]),int(xs[i+1]),int(ys[i+1]))
        if centre:
            point_mark(painter,*centre,kind,QColor(*(RED if hover else LOCKED if locked else point_colour)))
            target = bodies.get(value.get("target"))
            if body.uid in selected and target is not None:
                caption(panel,vp,painter,*centre,"→ "+target.name,QColor(*point_colour))
    painter.restore()


def set_hover(panel,vp,marker):
    uid = marker.uid if marker is not None else None
    if uid!=getattr(panel,"hover_connection",None):
        panel.hover_connection = uid;vp.update()
