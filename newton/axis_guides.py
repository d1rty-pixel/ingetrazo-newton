"""Small colour-coded guides, generated from the same frame as the axis glyph."""
import math
import time
from PySide6.QtCore import Qt,QRectF,QObject,QEvent,QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor,QPen,QVector3D,QFont,QFontMetrics,QBrush,QPainter
from .eraser import axis_frame,axis_geometry
from .model import axes_visible,with_zero,fit_limits
from .i18n import tr


COLOURS = {"axis":(160,150,130),"range":(50,175,140),"minimum":(70,155,240),
           "maximum":(235,110,75),"actual":(235,180,40),"target":(180,105,235),"zero":(150,150,150),
           "connected":(225,85,175),"exemption":(60,200,215)}


def place_caption(x,y,width,height,viewport_width,viewport_height,obstacles,occupied,near=4):
    """Prefer clear space outside every projected axis and its handles."""
    best = None
    seen = set()
    def consider(px,py):
        nonlocal best
        rect = QRectF(max(4,min(px,viewport_width-width-4)),max(4,min(py,viewport_height-height-4)),width,height)
        key = rect.x(),rect.y()
        if key in seen:return
        seen.add(key)
        limit = best[0][0] if best else None
        axis_hits = label_hits = 0
        for other in obstacles:
            if rect.intersects(other):axis_hits += 1
        if limit is not None and axis_hits>limit:return
        padded = rect.adjusted(-4,-4,4,4)
        for other in occupied:
            if padded.intersects(other):
                label_hits += 1
                if limit is not None and axis_hits+label_hits>limit:return
        score = (axis_hits+label_hits,axis_hits,(rect.center().x()-x)**2+(rect.center().y()-y)**2)
        if best is None or score<best[0]:best = score,rect
    xs = [x+28,x-width-28]
    ys = [y-height-20,y+24,y-height/2]
    def search():
        for px in xs:
            for py in ys:consider(px,py)
        return best and not best[0][0]
    # Nearest positions first: an early free spot at the viewport edge would otherwise win over a close one.
    if search():return best[1]
    # Every obstacle edge as a candidate is cubic in the selection size; only the neighbours are in the way.
    def distance(rect):return (rect.center().x()-x)**2+(rect.center().y()-y)**2
    for rect in sorted(obstacles,key=distance)[:near]:
        xs.extend((rect.right()+18,rect.left()-width-18))
        ys.extend((rect.bottom()+14,rect.top()-height-14))
    for rect in sorted(occupied,key=distance)[:near]:
        ys.extend((rect.bottom()+9,rect.top()-height-9))
    if search():return best[1]
    xs.extend((8,viewport_width-width-8))
    search()
    return best[1]


QUIET_AFTER_WHEEL = .25


class Quiet(QObject):
    """Tells the overlay that the view is being zoomed, and repaints once the wheel stops."""
    def __init__(self,panel,viewport):
        super().__init__(viewport)
        self.panel,self.viewport = panel,viewport
        viewport.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Wheel:
            self.panel.quiet_until = time.monotonic()+QUIET_AFTER_WHEEL
            QTimer.singleShot(int(QUIET_AFTER_WHEEL*1000)+20,self.viewport.update)
        elif event.type()==QEvent.MouseButtonRelease:
            QTimer.singleShot(0,self.viewport.update)
        return False


def quiet(panel,viewport):
    """Plates are placed from scratch every paint, so they wait while the view or an object is being dragged."""
    return (viewport.underMouse() and QApplication.mouseButtons()!=Qt.NoButton) or time.monotonic()<getattr(panel,"quiet_until",0)


def caption_font(viewport):
    """Bold caption font that follows the host's toolbar icon size, as IngeTrazo has no UI font size yet."""
    from views.icons import toolbar_icon_px,TOOLBAR_ICON_SIZES
    font = QFont(viewport.font())
    # Full size at the largest icons, never below the viewport's own text.
    largest = max(size for size,_ in TOOLBAR_ICON_SIZES)
    font.setPointSizeF(max(font.pointSizeF(),max(12,font.pointSizeF()+3)*toolbar_icon_px()/largest))
    font.setBold(True)
    return font


def guide_geometry(panel,viewport,j,detail):
    a,d,u,v,r = axis_frame(panel,viewport,j)
    state = panel.session.joint_states.get(j["uid"],{}) if panel.session.workspace else {}
    actual = state.get("position",j.get("start",0))
    target = panel.session.targets.get(j["uid"],j["target"])
    if j.get("coupling"):
        c = j["coupling"]
        target = panel.session.targets.get(c["master"],0)*c["ratio"]
    lines,labels = [],[]
    def add(p,q,kind):
        lines.append((p,q,kind))
    def label(p,text,kind):
        labels.append((p,text,kind))
    if j["type"]=="hinge":
        def at(angle):
            return a+r*(u*math.cos(angle)+v*math.sin(angle))
        if detail and j["limited"]:
            count = max(8,min(180,math.ceil(abs(j["upper"]-j["lower"])*24)))
            points = [at(j["lower"]+(j["upper"]-j["lower"])*i/count) for i in range(count+1)]
            for p,q in zip(points[:-1],points[1:]): add(p,q,"range")
            for angle,kind in ((j["lower"],"minimum"),(j["upper"],"maximum")):
                p = at(angle)
                add(a+(p-a)*.85,a+(p-a)*1.15,kind)
                label(a+(p-a)*1.25,f"{math.degrees(angle):.1f}°",kind)
        add(a,at(actual),"actual")
        if detail:
            add(a,at(0),"zero")
            label(at(actual),f"{math.degrees(actual):.1f}°","actual")
            if j["drive"]=="position": add(a,at(target),"target")
    else:
        # Positions are real model distances, not a scaled schematic.
        track = a+u*r*.7
        if detail and j["limited"]:
            add(track+d*j["lower"],track+d*j["upper"],"range")
            for distance,kind in ((j["lower"],"minimum"),(j["upper"],"maximum")):
                p = track+d*distance
                add(p-u*r*.25,p+u*r*.25,kind)
                label(p,f"{distance*1000:.1f} mm",kind)
        p = track+d*actual
        add(p-u*r*.35,p+u*r*.35,"actual")
        if detail:
            label(p,f"{actual*1000:.1f} mm","actual")
            if j["drive"]=="position":
                p = track+d*target
                add(p-u*r*.3,p+u*r*.3,"target")
    return lines,labels


def axis_rows(panel):
    """Stored axes, with the one being placed replaced by its live preview."""
    rows = list(panel.axis_rows) if axes_visible(panel.app.scene) else []
    preview = panel.placement.preview_row() if panel.placement else None
    if preview:
        body = next((g for g in panel.app.scene.groups if g.uid==preview["uid"]),None)
        if body is not None and preview.get("zero"):
            preview = fit_limits(with_zero(body,preview))
        rows = [j for j in rows if j["uid"]!=preview["uid"]]+[preview]
    return rows


def draw(panel,viewport,painter):
    rows = axis_rows(panel) if viewport is panel.app.viewport else []
    if not rows:
        return
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing,True)
    font = caption_font(viewport)
    painter.setFont(font)
    metrics = QFontMetrics(font)
    occupied = []
    still = quiet(panel,viewport)
    # Hidden plates stay pickable: the press that starts a drag may still be a click on one.
    if not still:panel.axis_label_hits = []
    eraser = panel.app.window._tools.get("eraser")
    marked = getattr(eraser,"axis_marked",set()) if viewport.active_tool is eraser else set()
    selected = {g.uid for g in panel.selected()}
    if panel.session.workspace and panel.detail_uid:
        selected.add(panel.detail_uid)
    obstacles = []
    order = {"zero":0,"range":1,"minimum":2,"maximum":2,"target":3,"actual":4}
    shown = []
    for j in rows:
        body = next((g for g in panel.app.scene.groups if g.uid==j["uid"]),None)
        if body is None or body.hidden or any(l.name==body.layer and not l.visible for l in panel.app.scene.layers):continue
        detail = j["uid"] in selected
        segments,anchor = axis_geometry(panel,viewport,j)
        lines,labels = guide_geometry(panel,viewport,j,detail)
        lines = sorted(lines,key=lambda item:order[item[2]])
        # One projection per axis: a call per segment dominated the paint time of large selections.
        points = [p for segment in segments for p in segment]+[p for start,end,_ in lines for p in (start,end)]
        outline = len(points)
        points += [anchor]+[p for p,_,_ in labels]
        xs,ys,front = viewport.world_to_pixels([list(p.toTuple()) for p in points])
        visible = [i for i in range(outline) if front[i]]
        if visible:
            left,right = min(float(xs[i]) for i in visible),max(float(xs[i]) for i in visible)
            top,bottom = min(float(ys[i]) for i in visible),max(float(ys[i]) for i in visible)
            obstacles.append(QRectF(left-20,top-20,right-left+40,bottom-top+40))
        shown.append((j,detail,segments,lines,labels,xs,ys,front))
    panel.axis_obstacles = obstacles
    def caption(x,y,rows,uid):
        limit = max(160,min(360,viewport.width()//2))
        rows = [(metrics.elidedText(text,Qt.ElideRight,limit),kind) for text,kind in rows]
        line = metrics.height()
        rect = place_caption(x,y,max(metrics.horizontalAdvance(text) for text,_ in rows)+14,line*len(rows)+10,
            viewport.width(),viewport.height(),obstacles,occupied)
        occupied.append(QRectF(rect))
        panel.axis_label_hits.append((QRectF(rect),uid))
        leader = QPen(QColor(*COLOURS[rows[0][1]]),1)
        leader.setStyle(Qt.DotLine);painter.setPen(leader)
        painter.drawLine(int(x),int(y),int(max(rect.left(),min(x,rect.right()))),int(max(rect.top(),min(y,rect.bottom()))))
        painter.setBrush(QBrush(QColor(24,28,34,235)))
        painter.drawRoundedRect(rect,5,5)
        for i,(text,kind) in enumerate(rows):
            painter.setPen(QColor(*COLOURS[kind]))
            painter.drawText(QRectF(rect.left()+7,rect.top()+5+i*line,rect.width()-14,line),Qt.AlignVCenter|Qt.AlignLeft,text)
    for j,detail,segments,lines,labels,xs,ys,front in shown:
        highlight = j["uid"] in marked or (viewport.active_tool is eraser and panel.hover_axis==j["uid"])
        def line(k,kind):
            if not (front[k] and front[k+1]):return
            width = 2 if kind in ("axis","zero") else 4 if kind in ("actual","range") else 3
            pen = QPen(QColor(235,65,45) if highlight and kind=="axis" else QColor(*COLOURS[kind]),width)
            pen.setCapStyle(Qt.RoundCap)
            if kind in ("target","zero"): pen.setStyle(Qt.DashLine if kind=="target" else Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(int(xs[k]),int(ys[k]),int(xs[k+1]),int(ys[k+1]))
        for i in range(len(segments)):line(2*i,"axis")
        base = 2*len(segments)
        for i,(_,_,kind) in enumerate(lines):line(base+2*i,kind)
        base += 2*len(lines)
        anchor = None
        if front[base]:
            painter.setPen(QPen(QColor(235,65,45) if highlight else QColor(*COLOURS["actual"]),3))
            painter.setBrush(QBrush(QColor(24,28,34,220)))
            x,y = int(xs[base]),int(ys[base])
            painter.drawEllipse(x-7,y-7,14,14)
            anchor = x,y
        rows_of = [(j["name"],"actual")] if (detail or highlight) and anchor else []
        for i,(_,text,kind) in enumerate(labels,base+1):
            prefix = tr("Min") if kind=="minimum" else tr("Max") if kind=="maximum" else tr("Actual")
            rows_of.append((prefix+" "+text,kind))
            if anchor is None and front[i]:anchor = int(xs[i]),int(ys[i])
        # One plate per axis keeps the free-space search linear in the number of selected axes.
        if rows_of and anchor and not still:caption(anchor[0],anchor[1],rows_of,j["uid"])
    painter.restore()
