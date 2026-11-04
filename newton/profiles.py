"""Validated parameter presets. Never copy IDs, placement or reference links."""
import copy
import json
import math
import uuid
from PySide6.QtCore import QSettings
from .model import DEFAULTS,settings
from .worker import joint_settings,environment_override

STORE = "newton/profiles_v1"
JOINT_KEYS = ("type","drive","limited","lower","upper","target","max_speed","acceleration","deceleration","deceleration_sync","force")


def builtins():
    profiles = []
    for kind in ("hinge","slide"):
        for drive in ("free","velocity","position"):
            names = {("hinge","free"):"Free rotation",("hinge","velocity"):"Rotary motor",
                ("hinge","position"):"Rotary servo",("slide","free"):"Free linear axis",
                ("slide","velocity"):"Linear motor",("slide","position"):"Linear positioning"}
            j = joint_settings(dict(type=kind,drive=drive,pivot=[0,0,0],axis=[0,0,1],force=100))
            if kind=="slide":
                j.update(max_speed=.25,acceleration=1,deceleration=1)
            profiles.append(dict(id="builtin_"+kind+"_"+drive,name=names[kind,drive],builtin=True,
                body=dict(DEFAULTS),joint={k:j[k] for k in JOINT_KEYS}))
    for mode,name in (("static","Fixed body"),("dynamic","Free body")):
        profiles.append(dict(id="builtin_"+mode,name=name,builtin=True,body=dict(DEFAULTS,mode=mode),joint=None))
    return profiles


def validate(profile):
    if not isinstance(profile,dict) or not isinstance(profile.get("body",{}),dict):
        raise ValueError("Invalid body profile.")
    p = copy.deepcopy(profile)
    if not isinstance(p.get("name"),str) or not p["name"].strip():
        raise ValueError("A profile needs a name.")
    body = {key:p.get("body",{}).get(key,value) for key,value in DEFAULTS.items()}
    body["simulation_override"] = environment_override(body["simulation_override"])
    if body["mode"] not in ("dynamic","static","ignore") or body["shape"] not in ("box","sphere","hull","compound"):
        raise ValueError("Invalid body profile.")
    for key in ("mass","friction","restitution"):
        body[key] = float(body[key])
        if not math.isfinite(body[key]):
            raise ValueError("Invalid body profile.")
    if body["mass"]<=0 or body["friction"]<0 or not 0<=body["restitution"]<=1:
        raise ValueError("Invalid body profile.")
    joint = p.get("joint")
    if joint is not None:
        if not isinstance(joint,dict):
            raise ValueError("Invalid joint parameter.")
        j = joint_settings(dict(joint,pivot=[0,0,0],axis=[0,0,1]))
        joint = {key:j[key] for key in JOINT_KEYS}
    return dict(id=str(p.get("id") or uuid.uuid4().hex),name=p["name"].strip(),
        builtin=bool(p.get("builtin",False)),body=body,joint=joint)


def from_group(group,name):
    cfg = settings(group)
    j = joint_settings(cfg["joint"]) if cfg.get("joint") else None
    return validate(dict(name=name,body={k:cfg[k] for k in DEFAULTS},
                         joint={k:j[k] for k in JOINT_KEYS} if j else None))


def custom_profiles():
    try:
        values = json.loads(QSettings().value(STORE,"[]"))
        if not isinstance(values,list):
            return []
        result = []
        for value in values:
            try:
                p = validate(value)
                p["builtin"] = False
                result.append(p)
            except (ValueError,TypeError,KeyError):
                continue
        return result
    except (ValueError,TypeError):
        return []


def all_profiles():
    return builtins()+custom_profiles()


def save_custom(profile):
    p = validate(profile)
    p["builtin"] = False
    if p["id"].startswith("builtin_"):
        p["id"] = uuid.uuid4().hex
    values = [v for v in custom_profiles() if v["id"]!=p["id"]]
    values.append(p)
    QSettings().setValue(STORE,json.dumps(values,ensure_ascii=False,allow_nan=False))
    return p


def delete_custom(identifier):
    values = [v for v in custom_profiles() if v["id"]!=identifier]
    QSettings().setValue(STORE,json.dumps(values,ensure_ascii=False))
