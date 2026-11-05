"""Standalone MuJoCo JSON-lines worker; no IngeTrazo or Qt dependency."""
from __future__ import annotations

import json
import math
import time
import sys
import xml.etree.ElementTree as ET

PREFIX = "NEWTON:"
DT = 1.0 / 240.0
# Integral gain per inertia: 300 rings in the drag-chain demo, 600 oscillates; kp=100, kd=20.
KI_POSITION = 100.
# Share of the drive force the integral may hold; a blocked servo otherwise winds up and releases slowly.
INTEGRAL_SHARE = .15


def vector(value, name):
    if len(value) != 3 or not all(math.isfinite(float(v)) for v in value):
        raise ValueError(f"Invalid vector: {name}")
    return [float(v) for v in value]


def numbers(values):
    return " ".join(str(float(v)) for v in values)


def limit_solver(hardness):
    """MuJoCo solref/solimp of a joint limit: 0 is MuJoCo's default softness, 1 a hard stop.

    The soft default gives way by tens of degrees in chains of light links, because the load of the whole chain acts
    on each small link. 2*DT is the stiffest time constant MuJoCo accepts without clamping it."""
    h = float(hardness)
    timeconst = .02+(2*DT-.02)*h
    return numbers([timeconst,1]),numbers([.9+.09*h,.95+.049*h,.001,.5,2])


def attachment_settings(raw):
    if not isinstance(raw,dict) or not isinstance(raw.get("target"),str) or not raw["target"]:
        raise ValueError("Invalid mechanical connection.")
    kind = raw.get("type","ball")
    if kind not in ("ball","hinge","fixed"):raise ValueError("Invalid mechanical connection.")
    result = dict(raw,type=kind,point=vector(raw["point"],"connection"))
    if kind=="hinge":
        axis = vector(raw.get("axis",[0,1,0]),"connection axis")
        length = math.sqrt(sum(v*v for v in axis))
        if length<1e-9:raise ValueError("The connection axis must not be zero.")
        result["axis"] = [v/length for v in axis]
        span = float(raw.get("span",.1))
        if not math.isfinite(span) or not 1e-4<=span<=1000:raise ValueError("Invalid mechanical connection.")
        result["span"] = span
    return result


def environment_override(raw):
    if raw is None:return None
    if not isinstance(raw,dict):raise ValueError("Invalid simulation override.")
    result = {}
    if "gravity" in raw:result["gravity"] = vector(raw["gravity"],"gravity")
    if "initial_velocity" in raw:result["initial_velocity"] = vector(raw["initial_velocity"],"initial_velocity")
    for key in ("attraction","softening"):
        if key in raw:
            value = float(raw[key])
            if not math.isfinite(value) or value<0:raise ValueError("Invalid attraction.")
            result[key] = value
    for key in ("linear_damping","angular_damping"):
        if key in raw:
            value = float(raw[key])
            if not math.isfinite(value) or not 0<=value<=100:raise ValueError("Invalid damping.")
            result[key] = value
    if "floor" in raw:
        if not isinstance(raw["floor"],bool):raise ValueError("Invalid ground contact override.")
        result["floor"] = raw["floor"]
    return result


def joint_settings(raw):
    """Normalize Newton joint parameters; native units are radians and metres."""
    j = dict(raw)
    j.setdefault("type", "hinge")
    j.setdefault("drive", "velocity" if j.get("force", 0) > 0 else "free")
    j.setdefault("name", "Rotation axis" if j["type"] == "hinge" else "Linear axis")
    j.setdefault("parent", None)
    j.setdefault("target", j.get("speed", 0))
    j.setdefault("force", 20 if j["type"] == "hinge" else 100)
    j.setdefault("limited", j["type"] == "slide" or j["drive"] == "position")
    j.setdefault("lower", -math.pi/2 if j["type"] == "hinge" else -.5)
    j.setdefault("upper", math.pi/2 if j["type"] == "hinge" else .5)
    j.setdefault("limit_hardness", 1.0)
    j.setdefault("max_speed", max(abs(float(j["target"])) if j["drive"] == "velocity" else 0,
                                  math.pi if j["type"] == "hinge" else 1))
    j.setdefault("acceleration", 2*math.pi if j["type"] == "hinge" else 2)
    j.setdefault("deceleration_sync",True)
    j.setdefault("deceleration",j["acceleration"])
    if j["deceleration_sync"]:j["deceleration"] = j["acceleration"]
    if j["type"] not in ("hinge", "slide") or j["drive"] not in ("free", "velocity", "position"):
        raise ValueError("Unknown joint type or actuator.")
    j["pivot"], j["axis"] = vector(j["pivot"], "Origin"), vector(j["axis"], "Axis")
    # Angle of the modelled pose, measured from the user's 0° direction ("zero").
    j["start"] = float(j.get("start",0)) if j["type"]=="hinge" else 0.
    if j.get("zero") is not None:
        j["zero"] = vector(j["zero"],"Zero")
    length = math.sqrt(sum(v*v for v in j["axis"]))
    if length < 1e-9:
        raise ValueError("The joint axis must not be zero.")
    j["axis"] = [v/length for v in j["axis"]]
    for key in ("target", "force", "lower", "upper", "limit_hardness", "max_speed", "acceleration","deceleration","start"):
        j[key] = float(j[key])
        if not math.isfinite(j[key]):
            raise ValueError("Invalid joint parameter.")
    if j["force"] < 0 or (j["limited"] and not j["lower"] < j["upper"]):
        raise ValueError("Invalid joint limits or force.")
    if not 0 <= j["limit_hardness"] <= 1:
        raise ValueError("Limit hardness must be between 0 and 100 %.")
    if j["max_speed"] <= 0 or j["acceleration"] <= 0 or j["deceleration"]<=0:
        raise ValueError("Speed and acceleration must be positive.")
    if j["limited"] and not j["lower"] <= j["start"] <= j["upper"]:
        raise ValueError("Joint limits must include the initial position.")
    if j["drive"] == "position" and j["limited"]:
        j["target"] = max(j["lower"], min(j["upper"], j["target"]))
    if j.get("coupling"):
        c = j["coupling"]
        ratio = float(c.get("ratio",1))
        if not c.get("master") or not math.isfinite(ratio) or abs(ratio)<1e-6:
            raise ValueError("Invalid axis coupling.")
        j["coupling"] = dict(master=str(c["master"]),ratio=ratio)
    if j.get("display"):
        d = j["display"]
        scale,offset = float(d.get("scale",1)),float(d.get("offset",0))
        if not math.isfinite(scale) or abs(scale)<1e-6 or not math.isfinite(offset) or j["drive"]!="position":
            raise ValueError("Invalid control display.")
        j["display"] = dict(scale=scale,offset=offset)
    j["visual_layer"] = "Newton Axes"
    return j


def resolve_couplings(joints):
    """Validate direct master/follower pairs and intersect their travel limits."""
    for uid,j in joints.items():
        if not j or not j.get("coupling"):
            continue
        c = j["coupling"]
        master = joints.get(c["master"])
        if c["master"]==uid or not master:
            raise ValueError("Coupled axis is missing or refers to itself.")
        if master.get("coupling"):
            raise ValueError("Coupling chains and cycles are not supported.")
        if master["type"]!=j["type"] or master["drive"]!="position":
            raise ValueError("Choose a matching position actuator.")
        if j["limited"]:
            # Couplings relate motion from the start poses (MuJoCo's qpos0).
            low,high = sorted((master["start"]+(j["lower"]-j["start"])/c["ratio"],
                               master["start"]+(j["upper"]-j["start"])/c["ratio"]))
            if master["limited"]:
                low,high = max(low,master["lower"]),min(high,master["upper"])
            if high-low<1e-8:
                raise ValueError("Coupled axes have no shared travel.")
            master.update(limited=True,lower=low,upper=high,
                          target=max(low,min(high,master["target"])))
        master["max_speed"] = min(master["max_speed"],j["max_speed"]/abs(c["ratio"]))
        master["acceleration"] = min(master["acceleration"],j["acceleration"]/abs(c["ratio"]))
        master["deceleration"] = min(master["deceleration"],j["deceleration"]/abs(c["ratio"]))
    return joints


class World:
    def __init__(self):
        import mujoco
        import numpy
        self.mj = mujoco
        self.np = numpy
        self.model = self.data = None
        self.bodies = {}
        self.motors = {}
        self.drag = None
        self.specs = {}
        self.environments = []

    def close(self):
        self.model = self.data = None

    def exact_box(self,vertices):
        """Use analytic face contacts only when a hull is an actual cuboid.

        Principal axes are a candidate, not an approximation: all eight
        vertices must match the fitted orthogonal box's eight corners.
        """
        points = self.np.unique(self.np.asarray(vertices,dtype=float),axis=0)
        if len(points)!=8:
            return None
        center = points.mean(axis=0)
        centered = points-center
        _,rotation = self.np.linalg.eigh(centered.T@centered)
        if self.np.linalg.det(rotation)<0:
            rotation[:,0] *= -1
        local = centered@rotation
        half = self.np.max(self.np.abs(local),axis=0)
        tolerance = max(float(half.max())*1e-5,1e-8)
        if half.min()<1e-6 or self.np.max(self.np.abs(self.np.abs(local)-half))>tolerance:
            return None
        if len(self.np.unique(self.np.sign(local),axis=0))!=8:
            return None
        quat = self.np.empty(4)
        self.mj.mju_mat2Quat(quat,rotation.ravel())
        return center.tolist(),half.tolist(),quat.tolist()

    def load(self, data):
        flexible = [s for s in data["bodies"] if s.get("flexible")]
        self.substeps = 1
        segment_specs = {s["uid"]:s for s in data["bodies"] if s.get("flex_segment")}
        data = dict(data,bodies=[s for s in data["bodies"] if not s.get("flexible") and not s.get("flex_segment")])
        self.bodies.clear()
        self.motors.clear()
        self.drag = None
        root = ET.Element("mujoco", model="Newton")
        ET.SubElement(root, "compiler", angle="radian", inertiafromgeom="true")
        gravity = float(data.get("gravity", -9.81))
        if not math.isfinite(gravity):
            raise ValueError("Invalid gravity.")
        self.global_gravity = self.np.array([0.,0.,gravity])
        self.global_damping = [float(data.get("linear_damping",0)),float(data.get("angular_damping",0))]
        if any(not math.isfinite(d) or not 0<=d<=100 for d in self.global_damping):raise ValueError("Invalid damping.")
        global_floor = bool(data.get("floor",True))
        environments = {}
        for spec in data["bodies"]:
            raw = environment_override(spec.get("simulation_override")) or {}
            g = vector(raw.get("gravity",self.global_gravity),"gravity")
            linear,angular = float(raw.get("linear_damping",self.global_damping[0])),float(raw.get("angular_damping",self.global_damping[1]))
            if any(not math.isfinite(d) or d<0 for d in (linear,angular)):raise ValueError("Invalid damping.")
            floor = raw.get("floor",global_floor)
            if not isinstance(floor,bool):raise ValueError("Invalid ground contact override.")
            environments[spec["uid"]] = dict(gravity=g,linear=linear,angular=angular,floor=floor,
                attraction=raw.get("attraction",0),softening=raw.get("softening",.01),
                initial_velocity=raw.get("initial_velocity",[0,0,0]))
        option = ET.SubElement(root, "option", timestep=str(DT), gravity=f"0 0 {gravity}",
                      iterations="80", integrator="implicitfast",cone="elliptic",impratio="10")
        ET.SubElement(option,"flag",multiccd="enable")
        assets = ET.SubElement(root, "asset")
        world = ET.SubElement(root, "worldbody")
        if global_floor or any(e["floor"] for e in environments.values()):
            ET.SubElement(world, "geom", type="plane", size="0 0 .1", friction=".6 .005 .0001",contype="1",conaffinity="0")
        pending = []
        specs = {}
        origins, joints, names, references = {}, {}, {}, {}
        for i, spec in enumerate(data["bodies"]):
            uid = spec["uid"]
            if uid in specs:
                raise ValueError("Duplicate body ID.")
            specs[uid] = spec
            j = joint_settings(spec["joint"]) if spec.get("joint") and spec.get("mass", 1) > 0 else None
            joints[uid] = j
            references[uid] = spec.get("reference",j.get("parent") if j else None)
            origins[uid] = j["pivot"] if j else vector(spec["center"], "center")
            names[uid] = f"body{i}"
        resolve_couplings(joints)
        elements, visiting = {}, set()

        def build(uid):
            if uid in elements:
                return elements[uid]
            if uid in visiting:
                raise ValueError("Joint cycle detected. Closed chains are not supported.")
            visiting.add(uid)
            spec, joint = specs[uid], joints[uid]
            parent = references[uid]
            if parent and parent not in specs:
                raise ValueError("The reference body is missing, hidden or excluded from the simulation.")
            parent_element = build(parent) if parent else world
            base = origins[parent] if parent else [0, 0, 0]
            name = names[uid]
            element = ET.SubElement(parent_element, "body", name=name,
                                    pos=numbers([a-b for a,b in zip(origins[uid], base)]))
            elements[uid] = element
            visiting.remove(uid)
            return element

        for uid, spec in specs.items():
            center, half = vector(spec["center"], "center"), vector(spec["half"], "half")
            mass = float(spec.get("mass", 1))
            if min(half) <= 0 or mass < 0 or not math.isfinite(mass):
                raise ValueError("Invalid body mass or size.")
            joint = joints[uid]
            origin = origins[uid]
            offset = [a-b for a,b in zip(center, origin)]
            name = names[uid]
            body = build(uid)
            if joint:
                args = dict(name=f"joint_{name}", type=joint["type"],
                            axis=numbers(joint["axis"]), damping=".02",
                            limited="true" if joint["limited"] else "false")
                if joint["limited"]:
                    args["range"] = numbers([joint["lower"], joint["upper"]])
                    args["solreflimit"],args["solimplimit"] = limit_solver(joint["limit_hardness"])
                if joint["start"]:
                    args["ref"] = numbers([joint["start"]])
                ET.SubElement(body, "joint", **args)
                pending.append((uid, f"joint_{name}", joint))
            elif mass > 0 and not references[uid]:
                ET.SubElement(body, "freejoint")
            e = float(spec.get("restitution", .1))
            friction = float(spec.get("friction", .5))
            if not 0 <= e <= 1 or not math.isfinite(friction) or friction < 0:
                raise ValueError("Invalid contact properties.")
            # MuJoCo has compliant contacts: bounce maps approximately to damping.
            damping = 1.0 if e < .001 else max(.05, -math.log(e) / math.sqrt(math.pi**2 + math.log(e)**2))
            inertia_mass = float(spec.get("inertia_mass",mass if mass else 1))
            if not math.isfinite(inertia_mass) or inertia_mass<=0:
                raise ValueError("Invalid body mass.")
            args = dict(pos=numbers(offset), friction=f"{friction} .005 .0001",
                        solref=f".02 {damping}", mass=str(inertia_mass),contype="2",
                        conaffinity="3" if environments[uid]["floor"] else "2")
            kind = spec.get("shape", "box")
            if kind=="compound":
                parts = spec.get("parts",[])
                if not 1<=len(parts)<=256:raise ValueError("Invalid compound collision shape.")
                for index,part in enumerate(parts):
                    verts = [vector(v,"compound vertex") for v in part]
                    part_args = dict(args,mass=str(inertia_mass/len(parts)))
                    fitted = self.exact_box(verts)
                    if fitted:
                        local_center,size,quaternion = fitted
                        part_args.update(type="box",size=numbers(size),quat=numbers(quaternion),pos=numbers([a+b for a,b in zip(offset,local_center)]))
                    else:
                        mesh_name = f"mesh_{name}_{index}"
                        ET.SubElement(assets,"mesh",name=mesh_name,vertex=" ".join(numbers(v) for v in verts))
                        part_args.update(type="mesh",mesh=mesh_name)
                    ET.SubElement(body,"geom",**part_args)
                self.bodies[uid] = name
                continue
            elif kind == "box":
                args.update(type="box", size=numbers(half))
            elif kind == "sphere":
                args.update(type="sphere", size=str(max(half)))
            elif kind == "hull":
                verts = [vector(v, "vertex") for v in spec["vertices"]]
                fitted = self.exact_box(verts)
                if fitted:
                    local_center,size,quaternion = fitted
                    args.update(type="box",size=numbers(size),quat=numbers(quaternion),
                                pos=numbers([a+b for a,b in zip(offset,local_center)]))
                else:
                    ET.SubElement(assets, "mesh", name=f"mesh_{name}",
                                  vertex=" ".join(numbers(v) for v in verts))
                    args.update(type="mesh", mesh=f"mesh_{name}")
            else:
                raise ValueError("Unknown collision shape.")
            ET.SubElement(body, "geom", **args)
            self.bodies[uid] = name
        # Directly connected bodies often meet/overlap at the bearing. Their
        # contact must not lock the joint; other body pairs still collide.
        contacts = ET.SubElement(root, "contact")
        excluded = set()
        for uid,parent in references.items():
            if parent:
                excluded.add(tuple(sorted((uid,parent))))
        for uid,spec in specs.items():
            for other in spec.get("no_collision",[]):
                if other in names and other!=uid:
                    excluded.add(tuple(sorted((uid,other))))
        for a,b in sorted(excluded):
            ET.SubElement(contacts,"exclude",body1=names[a],body2=names[b])
        equality = ET.SubElement(root,"equality")
        for uid,spec in specs.items():
            attach = spec.get("point_attachment")
            if attach:
                attach = attachment_settings(attach)
                target = attach["target"]
                if target not in names or target==uid:raise ValueError("Attachment body is missing or refers to itself.")
                point = vector(attach["point"],"attachment")
                if attach["type"]=="fixed":ET.SubElement(equality,"weld",body1=names[uid],body2=names[target],solref=".01 1",solimp=".99 .9999 .001")
                else:
                    ET.SubElement(equality,"connect",body1=names[uid],body2=names[target],
                        anchor=numbers([a-b for a,b in zip(point,origins[uid])]),solref=".01 1")
                    if attach["type"]=="hinge":
                        second = [point[k]+attach["axis"][k]*attach["span"]-origins[uid][k] for k in range(3)]
                        ET.SubElement(equality,"connect",body1=names[uid],body2=names[target],anchor=numbers(second),solref=".01 1")
                ET.SubElement(contacts,"exclude",body1=names[uid],body2=names[target])
        for uid,j in joints.items():
            if j and j.get("coupling"):
                c = j["coupling"]
                ET.SubElement(equality,"joint",joint1="joint_"+names[uid],
                    joint2="joint_"+names[c["master"]],polycoef=numbers([0,c["ratio"],0,0,0]),
                    solref=".01 1",solimp=".99 .9999 .001")
        if flexible:
            ET.SubElement(ET.SubElement(root,"extension"),"plugin",plugin="mujoco.elasticity.cable")
        for index,spec in enumerate(flexible):
            from_flex = spec["flexible"]
            points = [vector(p,"centre line") for p in from_flex["points"]]
            if not 3<=len(points)<=201 or any(math.dist(a,b)<1e-5 for a,b in zip(points,points[1:])):
                raise ValueError("Invalid cable centre line.")
            radius = float(from_flex["radius"]);mass = float(spec["mass"])
            bend,twist,damping = [float(from_flex[k]) for k in ("bend","twist","damping")]
            if not all(math.isfinite(v) and v>=0 for v in (radius,mass,bend,twist,damping)) or min(radius,mass)<=0:
                raise ValueError("Invalid flexible material.")
            shortest = min(math.dist(a,b) for a,b in zip(points,points[1:]))
            frequency = math.sqrt((bend+twist)*math.pi*radius**4/(mass/(len(points)-1)*shortest**3))
            needed = max(1,math.ceil(DT*frequency*4))
            if needed>32:raise ValueError("Cable is too stiff for this resolution. Reduce stiffness or use fewer segments.")
            self.substeps = max(self.substeps,needed)
            start = from_flex["start"]
            if start not in ("fixed","pinned","free"):raise ValueError("Invalid cable start.")
            parent = spec.get("reference")
            if start=="free" and parent:raise ValueError("Choose a clamped or pinned start before assigning a reference body.")
            if parent and parent not in elements:raise ValueError("Cable reference body is missing.")
            base = origins[parent] if parent else [0,0,0]
            prefix = f"flex{index}_"
            composite = ET.SubElement(elements[parent] if parent else world,"composite",prefix=prefix,type="cable",
                initial={"fixed":"none","pinned":"ball","free":"free"}[start],
                vertex=" ".join(numbers([p[k]-base[k] for k in range(3)]) for p in points))
            elastic = ET.SubElement(composite,"plugin",plugin="mujoco.elasticity.cable")
            for key,value in (("bend",bend),("twist",twist),("vmax",0),("flat","true")):
                ET.SubElement(elastic,"config",key=key,value=str(value))
            ET.SubElement(composite,"joint",kind="main",damping=str(damping))
            override = environment_override(spec.get("simulation_override")) or {}
            floor = override.get("floor",global_floor)
            bounce = float(spec.get("restitution",0))
            if not 0<=bounce<=1:raise ValueError("Invalid contact properties.")
            contact_damping = 1. if bounce<.001 else max(.05,-math.log(bounce)/math.sqrt(math.pi**2+math.log(bounce)**2))
            if floor and not any(e.tag=="geom" and e.get("type")=="plane" for e in world):
                ET.SubElement(world,"geom",type="plane",size="0 0 .1",contype="1",conaffinity="0")
            ET.SubElement(composite,"geom",type="capsule",size=str(radius),mass=str(mass/(len(points)-1)),
                contype="2",conaffinity="3" if floor else "2",friction=f"{float(spec.get('friction',.5))} .005 .0001",solref=f".02 {contact_damping}")
            segment_names = []
            for i in range(len(points)-1):
                uid = f"{spec['uid']}:flex:{i}"
                name = prefix+("B_first" if i==0 else "B_last" if i==len(points)-2 else f"B_{i}")
                self.bodies[uid] = name;segment_names.append(name)
                specs[uid] = dict(segment_specs.get(uid,{}),mass=mass/(len(points)-1),joint=None)
                g = vector(override.get("gravity",self.global_gravity),"gravity")
                environments[uid] = dict(gravity=g,linear=override.get("linear_damping",self.global_damping[0]),
                    angular=override.get("angular_damping",self.global_damping[1]),floor=floor,
                    attraction=override.get("attraction",0)/(len(points)-1),softening=override.get("softening",.01),
                    initial_velocity=override.get("initial_velocity",[0,0,0]) if i==0 else [0,0,0])
            end = from_flex.get("end_reference")
            if end:
                if end not in names:raise ValueError("Cable end body is missing.")
                ET.SubElement(equality,"connect",body1=segment_names[-1],body2=names[end],
                    anchor=numbers([math.dist(points[-2],points[-1]),0,0]),solref=".01 1")
                ET.SubElement(contacts,"exclude",body1=segment_names[-1],body2=names[end])
            if parent:ET.SubElement(contacts,"exclude",body1=segment_names[0],body2=names[parent])
            existing = {tuple(sorted((e.get("body1"),e.get("body2")))) for e in contacts if e.tag=="exclude"}
            for other in spec.get("no_collision",[]):
                if other not in names:continue
                for name in segment_names:
                    pair = tuple(sorted((name,names[other])))
                    if pair not in existing:
                        ET.SubElement(contacts,"exclude",body1=name,body2=names[other]);existing.add(pair)
        self.model = self.mj.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
        self.model.opt.timestep = DT/self.substeps
        self.quality = data.get("quality","balanced")
        if self.quality not in ("quick","balanced","precise"):raise ValueError("Unknown simulation quality.")
        # Long cable trees have dense constraint coupling. CG avoids Newton's
        # expensive Hessian factorisation while retaining elliptic friction.
        use_cg = self.model.nv>80 and (bool(flexible) or self.quality=="quick")
        self.model.opt.solver = self.mj.mjtSolver.mjSOL_CG if use_cg and self.quality!="precise" else self.mj.mjtSolver.mjSOL_NEWTON
        self.model.opt.iterations = {"quick":40 if use_cg else 20,"balanced":80,"precise":120}[self.quality]
        self.model.opt.tolerance = {"quick":1e-5,"balanced":1e-6 if use_cg else 1e-8,"precise":1e-9}[self.quality]
        self.data = self.mj.MjData(self.model)
        self.bodies = {uid: self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_BODY, name)
                       for uid, name in self.bodies.items()}
        self.environments = []
        self.attractors = []
        for uid,e in environments.items():
            delta = self.np.asarray(e["gravity"])-self.global_gravity
            if self.np.any(delta) or e["linear"] or e["angular"]:
                self.environments.append((self.bodies[uid],delta,e["linear"],e["angular"]))
            if e["attraction"]:
                self.attractors.append((self.bodies[uid],e["attraction"],e["softening"]))
            if any(e["initial_velocity"]):
                bid = self.bodies[uid]
                jid = int(self.model.body_jntadr[bid])
                if jid<0 or self.model.jnt_type[jid]!=self.mj.mjtJoint.mjJNT_FREE:
                    raise ValueError("Initial velocity needs a freely movable body.")
                dof = int(self.model.jnt_dofadr[jid])
                self.data.qvel[dof:dof+3] = e["initial_velocity"]
        for uid, name, cfg in pending:
            jid = self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_JOINT, name)
            self.motors[uid] = dict(cfg, dof=int(self.model.jnt_dofadr[jid]),
                                    qpos=int(self.model.jnt_qposadr[jid]),command_pos=float(cfg["start"]),command_vel=0.)
        for j in self.motors.values():
            if j.get("coupling"):
                c = j["coupling"]
                self.motors[c["master"]].setdefault("followers",[]).append((j["dof"],c["ratio"]))
        self.actuators = [j for j in self.motors.values() if j["drive"]!="free" and not j.get("coupling")]
        for j in self.actuators:
            j["inertia"] = max(float(self.model.dof_M0[j["dof"]]),.001)+sum(ratio*ratio*float(self.model.dof_M0[dof]) for dof,ratio in j.get("followers",[]))
            j["integral"] = 0.;j["effort"] = 0.;j["limited_effort"] = False
        self.specs = specs
        self.mj.mj_forward(self.model, self.data)
        return dict(self.poses(),colliders=self.collider_lines())

    def collider_lines(self):
        """All compiled shapes, including openings in compound bodies."""
        result = {}
        for uid,bid in self.bodies.items():
            first,count = int(self.model.body_geomadr[bid]),int(self.model.body_geomnum[bid])
            points,edges,faces = [],[],[]
            for gid in range(first,first+count):
                shape = self.geom_lines(gid);offset = len(points)
                points.extend(shape["points"])
                edges.extend((a+offset,b+offset) for a,b in shape["edges"])
                faces.extend([i+offset for i in face] for face in shape["faces"])
            result[uid] = dict(points=points,edges=edges,faces=faces,kind="Compound" if count>1 else shape["kind"])
        return result

    def geom_lines(self,gid):
        import itertools
        kind = int(self.model.geom_type[gid])
        size = self.model.geom_size[gid]
        if kind==self.mj.mjtGeom.mjGEOM_BOX:
            points = self.np.asarray(list(itertools.product((-1,1),repeat=3)))*size
            edges = [(i,j) for i in range(8) for j in range(i+1,8)
                     if sum(a!=b for a,b in zip(points[i],points[j]))==1]
            faces = [[i for i,p in enumerate(points) if p[axis]==sign*size[axis]]
                     for axis in range(3) for sign in (-1,1)]
            # Product order walks a quad as 0,1,3,2 rather than a bow tie.
            faces = [[f[i] for i in (0,1,3,2)] for f in faces]
            label = "Box"
        elif kind==self.mj.mjtGeom.mjGEOM_SPHERE:
            points,edges = [],[]
            for plane in range(3):
                start = len(points)
                for i in range(32):
                    p = [0.,0.,0.]
                    p[(plane+1)%3] = float(size[0])*math.cos(i*math.pi/16)
                    p[(plane+2)%3] = float(size[0])*math.sin(i*math.pi/16)
                    points.append(p)
                    edges.append((start+i,start+(i+1)%32))
            points = self.np.asarray(points)
            faces = []
            label = "Sphere"
        elif kind==self.mj.mjtGeom.mjGEOM_CAPSULE:
            points,edges,faces = [],[],[]
            for j in range(10):
                angle = -math.pi/2+(j if j<5 else j-1)*math.pi/8
                z = (-size[1] if j<5 else size[1])+size[0]*math.sin(angle)
                r = size[0]*math.cos(angle)
                for i in range(16):points.append([r*math.cos(i*math.pi/8),r*math.sin(i*math.pi/8),z])
            for j in range(10):
                for i in range(16):
                    a,b = j*16+i,j*16+(i+1)%16
                    edges.append((a,b))
                    if j<9:edges.append((a,a+16));faces.append([a,b,b+16,a+16])
            label = "Capsule"
        else:
            mid = int(self.model.geom_dataid[gid])
            start,count = int(self.model.mesh_vertadr[mid]),int(self.model.mesh_vertnum[mid])
            points = self.model.mesh_vert[start:start+count].copy()
            first,nfaces = int(self.model.mesh_faceadr[mid]),int(self.model.mesh_facenum[mid])
            faces = self.model.mesh_face[first:first+nfaces]
            by_edge = {}
            for f in faces:
                normal = self.np.cross(points[f[1]]-points[f[0]],points[f[2]]-points[f[0]])
                length = self.np.linalg.norm(normal)
                if length>1e-12:normal /= length
                for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):
                    by_edge.setdefault(tuple(sorted((int(a),int(b)))),[]).append(normal)
            edges = [e for e,n in by_edge.items() if len(n)!=2 or abs(float(self.np.dot(n[0],n[1])))<.9999]
            label = "Convex hull"
        rotation = self.np.empty(9)
        self.mj.mju_quat2Mat(rotation,self.model.geom_quat[gid])
        points = self.np.asarray(points)@rotation.reshape(3,3).T+self.model.geom_pos[gid]
        return dict(points=points.tolist(),edges=edges,faces=self.np.asarray(faces).tolist() if len(faces) else [],kind=label)

    def poses(self):
        result = {}
        for uid, bid in self.bodies.items():
            q = self.data.xquat[bid]
            result[uid] = [self.data.xpos[bid].tolist(), [float(q[1]), float(q[2]), float(q[3]), float(q[0])]]
        state = {uid: dict(position=float(self.data.qpos[j["qpos"]]),
                           velocity=float(self.data.qvel[j["dof"]]),target=j["target"],
                           command=j["command_vel"] if j["drive"]=="velocity" else j["command_pos"],
                           effort=j.get("effort",0),load=abs(j.get("effort",0))/j["force"] if j["force"] else 0,
                           at_limit=j.get("limited_effort",False))
                 for uid, j in self.motors.items()}
        return {"poses": result, "joints": state, "time": float(self.data.time)}

    def step(self, count, targets=None, drag=None):
        started = time.perf_counter()
        count = int(count)
        if self.model is None or not 1 <= count <= 24:
            raise ValueError("Simulation not ready or step count outside 1 to 24.")
        for uid, target in (targets or {}).items():
            if uid not in self.motors or not math.isfinite(float(target)):
                raise ValueError("Invalid control target or unknown joint.")
            j = self.motors[uid]
            if j.get("coupling"):
                raise ValueError("Use the shared actuator control.")
            target = float(target)
            if j["drive"] == "position" and j["limited"]:
                target = max(j["lower"], min(j["upper"], target))
            j["target"] = target
        self.set_drag(drag)
        dt = float(self.model.opt.timestep)
        for _ in range(count*self.substeps):
            self.data.qfrc_applied[:] = 0
            if self.attractors:self.mj.mj_fwdPosition(self.model,self.data)
            for j in self.actuators:
                dof, target, force = j["dof"], j["target"], j["force"]
                inertia = j["inertia"]
                desired = max(-j["max_speed"],min(j["max_speed"],target))
                if j["drive"] == "position":
                    distance = target-j["command_pos"]
                    desired = math.copysign(min(j["max_speed"],math.sqrt(2*j["deceleration"]*abs(distance))),distance) if distance else 0
                reversing = desired*j["command_vel"]<0
                if reversing:desired = 0
                slowing = reversing or abs(desired)<abs(j["command_vel"])
                dv = (j["deceleration"] if slowing else j["acceleration"])*dt
                old_velocity = j["command_vel"]
                j["command_vel"] += max(-dv,min(dv,desired-j["command_vel"]))
                feedforward = inertia*(j["command_vel"]-old_velocity)/dt
                candidate = j["integral"]
                if j["drive"] == "position":
                    new_position = j["command_pos"]+j["command_vel"]*dt
                    if (target-j["command_pos"])*(target-new_position)<=0:
                        new_position = target
                        j["command_vel"] = 0.
                    j["command_pos"] = new_position
                    kp = 100 * inertia
                    error = j["command_pos"]-float(self.data.qpos[j["qpos"]])
                    limit = INTEGRAL_SHARE*force/(KI_POSITION*inertia)
                    candidate = max(-limit,min(limit,j["integral"]+error*dt))
                    effort = kp*error+20*inertia*(j["command_vel"]-self.data.qvel[dof])+KI_POSITION*inertia*candidate
                elif j["drive"] == "velocity":
                    error = j["command_vel"]-float(self.data.qvel[dof])
                    candidate = max(-force/(80*inertia),min(force/(80*inertia),j["integral"]+error*dt))
                    effort = 20*inertia*error+80*inertia*candidate+feedforward
                else:
                    effort = 0
                if j["drive"] != "free":
                    effort += float(self.data.qfrc_bias[dof])
                    effort += sum(ratio*float(self.data.qfrc_bias[slave]) for slave,ratio in j.get("followers",[]))
                applied = max(-force,min(force,effort))
                if j["drive"] in ("velocity","position") and (abs(effort)<=force or (effort-applied)*error<0):j["integral"] = candidate
                j["effort"],j["limited_effort"] = float(applied),bool(abs(effort)>force+1e-8)
                self.data.qfrc_applied[dof] = applied
            self.apply_drag()
            self.apply_environment()
            self.apply_attraction()
            self.mj.mj_step(self.model, self.data)
        if any(self.data.warning[int(w)].number for w in (self.mj.mjtWarning.mjWARN_BADQPOS,self.mj.mjtWarning.mjWARN_BADQVEL,self.mj.mjtWarning.mjWARN_BADQACC)):
            raise ValueError("Simulation became unstable. Reduce stiffness or use fewer segments.")
        # Refresh output poses/contact distances without solving constraints
        # a second time merely to send a frame to the host.
        self.mj.mj_fwdPosition(self.model, self.data)
        newton_ms = (time.perf_counter()-started)*1000
        posed = time.perf_counter();result = self.poses()
        result["performance"] = dict(newton_ms=newton_ms,output_ms=(time.perf_counter()-posed)*1000,
            contacts=int(self.data.ncon),constraints=int(self.data.nefc),bodies=len(self.bodies),
            iterations=int(self.data.solver_niter[0]),substeps=self.substeps,quality=self.quality)
        return result

    def apply_environment(self):
        for bid,gravity,linear,angular in self.environments:
            mass = float(self.model.body_mass[bid])
            jp = self.np.zeros((3,self.model.nv));jr = self.np.zeros((3,self.model.nv))
            self.mj.mj_jacBodyCom(self.model,self.data,jp,jr,bid)
            force = mass*gravity-linear*mass*(jp@self.data.qvel)
            rotation = self.data.ximat[bid].reshape(3,3)
            omega = jr@self.data.qvel
            torque = -angular*(rotation@(self.model.body_inertia[bid]*(rotation.T@omega)))
            self.data.qfrc_applied[:] += jp.T@force+jr.T@torque

    def apply_attraction(self):
        # Sources emit a Newtonian field mu = G*M. With the same G on all
        # bodies the forces are reciprocal and conserve total momentum.
        for source,mu,softening in self.attractors:
            for target in self.bodies.values():
                if target==source:continue
                delta = self.data.xipos[source]-self.data.xipos[target]
                distance2 = float(delta@delta)+softening**2
                if distance2<1e-18:continue
                force = self.model.body_mass[target]*mu*delta/distance2**1.5
                jp = self.np.zeros((3,self.model.nv))
                self.mj.mj_jacBodyCom(self.model,self.data,jp,None,target)
                self.data.qfrc_applied[:] += jp.T@force

    def set_drag(self, drag):
        if drag is None:
            self.drag = None
            return
        uid = drag["uid"]
        if uid not in self.specs or self.specs[uid].get("mass",0)<=0:
            raise ValueError("Fixed bodies cannot be dragged.")
        if uid in self.motors and (self.motors[uid]["drive"] != "free" or self.motors[uid].get("coupling")):
            raise ValueError("Actuated bodies must use their controls.")
        point,target = vector(drag["point"],"Greifpunkt"),vector(drag["target"],"Zugziel")
        if self.drag is None or self.drag["id"] != drag["id"]:
            bid = self.bodies[uid]
            rotation = self.data.xmat[bid].reshape(3,3)
            local = rotation.T@(self.np.array(point)-self.data.xpos[bid])
            self.drag = dict(id=drag["id"],uid=uid,local=local)
        self.drag["target"] = self.np.array(target)

    def apply_drag(self):
        if not self.drag:
            return
        uid = self.drag["uid"]
        bid = self.bodies[uid]
        point = self.data.xpos[bid]+self.data.xmat[bid].reshape(3,3)@self.drag["local"]
        jac = self.np.zeros((3,self.model.nv))
        self.mj.mj_jac(self.model,self.data,jac,None,point,bid)
        mass = max(.1,float(self.specs[uid]["mass"]))
        force = 400*mass*(self.drag["target"]-point)-40*mass*(jac@self.data.qvel)
        norm = self.np.linalg.norm(force)
        if norm > 500*mass:
            force *= 500*mass/norm
        self.data.qfrc_applied[:] += jac.T@force


def main():
    world = None
    try:
        world = World()
        for line in sys.stdin:
            try:
                req = json.loads(line)
                op = req["op"]
                if op == "init":
                    result = world.load(req)
                elif op == "step":
                    result = world.step(req.get("count", 8), req.get("targets"),req.get("drag"))
                elif op == "quit":
                    break
                else:
                    raise ValueError(f"Unknown command: {op}")
                print(PREFIX + json.dumps({"ok": True, **result}, allow_nan=False), flush=True)
            except Exception as exc:
                print(PREFIX + json.dumps({"ok": False, "error": str(exc)}), flush=True)
    except Exception as exc:
        print(PREFIX + json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 1
    finally:
        if world:
            world.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
