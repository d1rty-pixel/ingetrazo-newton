"""Key bindings: assign a key slot to a joint target or a virtual control.

See docs/adr/0001-virtual-controls.md. The bindings are document data
(``app.document_data()["bindings"]``); the keys themselves belong to the
slot actions (``key_slots.py``).
"""
import math
from .i18n import tr
from .units import SPAN_METRES
from .virtual_controls import eligible, managed

MODES = ("toggle", "step")
MAX_SLOT = 999


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def slot_number(value):
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SLOT


def target_of(binding):
    """``("joint" | "control", id)``."""
    return next(iter(binding["target"].items()))


def check(binding):
    """Raise ValueError unless ``binding`` is well-formed; returns it."""
    def bad():
        return ValueError(tr("The key bindings of this document are damaged."))
    if not isinstance(binding, dict):
        raise bad()
    target = binding.get("target")
    if not isinstance(target, dict) or len(target) != 1:
        raise bad()
    (kind, ident), = target.items()
    if kind not in ("joint", "control") or not isinstance(ident, str) or not ident:
        raise bad()
    if not slot_number(binding.get("slot")):
        raise bad()
    mode = binding.get("mode")
    if mode == "toggle":
        if not (number(binding.get("value")) and number(binding.get("rest"))):
            raise bad()
    elif mode == "step":
        if not (number(binding.get("step")) and binding["step"] > 0):
            raise bad()
        if binding.get("slot_down") is not None and not slot_number(binding["slot_down"]):
            raise bad()
    else:
        raise bad()
    return binding


def stored(data):
    """The checked bindings in the extension's document data."""
    if data is None:
        return []
    bindings = data.get("bindings", []) if isinstance(data, dict) else None
    if not isinstance(bindings, list):
        raise ValueError(tr("The key bindings of this document are damaged."))
    for binding in bindings:
        check(binding)
    if len({tuple(target_of(b)) for b in bindings}) != len(bindings):
        raise ValueError(tr("The key bindings of this document are damaged."))
    return bindings


def with_bindings(data, bindings):
    """``data`` with ``bindings`` replaced; ``None`` when nothing is left, so the document entry goes away."""
    data = dict(data) if isinstance(data, dict) else {}
    if bindings:
        data["bindings"] = bindings
    else:
        data.pop("bindings", None)
    return data or None


def find(bindings, kind, ident):
    return next((b for b in bindings if target_of(b) == (kind, ident)), None)


def replaced(bindings, kind, ident, binding):
    """``bindings`` with the target's binding replaced, added or (``binding`` None) removed; order kept."""
    result, done = [], False
    for old in bindings:
        if target_of(old) != (kind, ident):
            result.append(old)
        elif binding is not None and not done:
            result.append(binding)
            done = True
    if binding is not None and not done:
        result.append(binding)
    return result


def target_range(kind, subject):
    """``(low, high, integer)`` of a joint row or a virtual control, in internal units."""
    if kind == "joint":
        return (*joint_range(subject), False)
    if subject["kind"] == "switch":
        return (0, len(subject["states"])-1, True)
    return (0, 1, False)


def fresh(kind, ident, subject, slot, mode="toggle"):
    """A new binding with values that do something visible: toggle between the rest position and the far end."""
    low, high, integer = target_range(kind, subject)
    binding = dict(target={kind: ident}, slot=slot, mode=mode)
    if mode == "step":
        binding["step"] = 1 if integer else (high-low)/10
    elif kind == "joint":
        rest = max(low, min(high, subject["target"]))
        binding.update(value=high if abs(high-rest) > 1e-9 else low, rest=rest)
    else:
        binding.update(value=1, rest=0)
    return binding


def joint_range(row):
    """The internal range the control panel offers for a joint, before its display mapping."""
    if row["drive"] == "velocity":
        return (-row["max_speed"], row["max_speed"])
    if row["limited"]:
        return (row["lower"], row["upper"])
    return (-math.pi, math.pi) if row["type"] == "hinge" else (-SPAN_METRES, SPAN_METRES)


def resolve(bindings, rows, controls):
    """The bindings whose target can take part now, each with its value ``range``.

    A target that is gone, passive, a coupling follower or driven by a virtual
    control is skipped, not an error.
    """
    available = eligible(rows)
    taken = managed(controls)
    by_id = {c["id"]: c for c in controls}
    result = []
    for binding in bindings:
        kind, ident = target_of(binding)
        if kind == "joint":
            if ident not in available or ident in taken:
                continue
            subject = available[ident]
        else:
            subject = by_id.get(ident)
            if subject is None:
                continue
        low, high, integer = target_range(kind, subject)
        result.append(dict(binding, range=(low, high), integer=integer))
    return result


def next_value(binding, current, down=False):
    """The target after one press of ``binding``'s key (``down``: the second step key)."""
    low, high = binding["range"]
    if binding["mode"] == "toggle":
        value = binding["rest"] if abs(current-binding["value"]) <= 1e-9 else binding["value"]
    else:
        value = current-binding["step"] if down else current+binding["step"]
    value = max(low, min(high, value))
    return int(round(value)) if binding.get("integer") else value
