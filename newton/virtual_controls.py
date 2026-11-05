"""Virtual controls: named switches and sliders that set several joint targets.

See docs/adr/0001-virtual-controls.md. The controls are document data
(``app.document_data()``); the session turns their values into the joint
targets the worker already understands.
"""
import math
import uuid
from .i18n import tr

KINDS = ("switch", "slider")


def new_control(kind, name):
    return dict(id=uuid.uuid4().hex[:16], name=name, kind=kind, joints=[],
                states=[dict(name=tr("Off") if kind == "switch" else tr("Start position"), values=[]),
                        dict(name=tr("On") if kind == "switch" else tr("End position"), values=[])],
                initial=0)


def check(control):
    """Raise ValueError unless ``control`` is a well-formed control; returns it."""
    def bad():
        name = control.get("name") if isinstance(control, dict) else None
        return ValueError(tr("The virtual control “{name}” is damaged. Delete it and create it again.",
                             name=name if isinstance(name, str) else "?"))
    if not isinstance(control, dict) or control.get("kind") not in KINDS:
        raise bad()
    if not all(isinstance(control.get(k), str) and control[k] for k in ("id", "name")):
        raise bad()
    joints, states = control.get("joints"), control.get("states")
    if not isinstance(joints, list) or not all(isinstance(j, str) for j in joints) or len(set(joints)) != len(joints):
        raise bad()
    if not isinstance(states, list) or len(states) < 2:
        raise bad()
    for state in states:
        values = state.get("values") if isinstance(state, dict) else None
        if not isinstance(state.get("name"), str) or not isinstance(values, list) or len(values) != len(joints):
            raise bad()
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
            raise bad()
    initial = control.get("initial")
    if not isinstance(initial, (int, float)) or isinstance(initial, bool) or not math.isfinite(initial):
        raise bad()
    if control["kind"] == "switch" and (initial != int(initial) or not 0 <= initial < len(states)):
        raise bad()
    if control["kind"] == "slider" and not 0 <= initial <= 1:
        raise bad()
    if not isinstance(control.get("sequential", False), bool):
        raise bad()
    return control


def stored(data):
    """The checked controls in the extension's document data."""
    if data is None:
        return []
    controls = data.get("controls", []) if isinstance(data, dict) else None
    if not isinstance(controls, list):
        raise ValueError(tr("The virtual controls of this document are damaged."))
    for control in controls:
        check(control)
    if len({c["id"] for c in controls}) != len(controls):
        raise ValueError(tr("The virtual controls of this document are damaged."))
    return controls


def with_controls(data, controls):
    """``data`` with ``controls`` replaced; ``None`` when nothing is left, so the document entry goes away."""
    data = dict(data) if isinstance(data, dict) else {}
    if controls:
        data["controls"] = controls
    else:
        data.pop("controls", None)
    return data or None


def eligible(rows):
    """Joints a virtual control can drive: own control, not passive, not a coupling follower."""
    return {r["uid"]: r for r in rows if r["drive"] != "free" and not r.get("coupling")}


def resolve(controls, rows):
    """The controls reduced to joints that can take part now.

    A joint that is gone or no longer has a control of its own is left out;
    a joint in two controls is refused, as the two would fight over its target.
    """
    available = eligible(rows)
    owner = {}
    result = []
    for control in controls:
        keep = [i for i, uid in enumerate(control["joints"]) if uid in available]
        for i in keep:
            uid = control["joints"][i]
            if uid in owner:
                raise ValueError(tr("“{body}” belongs to two virtual controls, “{first}” and “{second}”. Remove it from one of them.",
                                    body=available[uid]["body"], first=owner[uid], second=control["name"]))
            owner[uid] = control["name"]
        result.append(dict(control, joints=[control["joints"][i] for i in keep],
                           states=[dict(s, values=[s["values"][i] for i in keep]) for s in control["states"]]))
    return result


def managed(controls):
    """Joint ID → control for every joint a control drives."""
    return {uid: control for control in controls for uid in control["joints"]}


def clamp(control, value):
    if control["kind"] == "switch":
        return max(0, min(len(control["states"])-1, int(round(value))))
    return max(0.0, min(1.0, float(value)))


def targets(control, value):
    """Joint ID → target for ``value``: a state index for a switch, a position 0–1 along the states for a slider."""
    states = control["states"]
    value = clamp(control, value)
    if control["kind"] == "switch":
        return dict(zip(control["joints"], states[value]["values"]))
    position = value*(len(states)-1)
    index = min(int(position), len(states)-2)
    share = position-index
    return {uid: a+(b-a)*share for uid, a, b in
            zip(control["joints"], states[index]["values"], states[index+1]["values"])}
