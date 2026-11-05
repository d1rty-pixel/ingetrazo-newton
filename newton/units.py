"""How Newton shows and reads length-type values in the document's unit.

Newton stores metres and radians; only the number in a field changes with
Window -> Units. Physical constants (gravity, pressure, damping, force, mass)
stay in SI, they are not model lengths.
"""
import math
from dataclasses import dataclass

# About 0.1 to 1 mm per step: finer is noise in a spin box, coarser cannot hold a typed value.
DECIMALS = {"m":3,"cm":2,"mm":1,"in":2,"in-frac":2,"ft":3,"ft-in":3,"ft-in-frac":3}

# A slider spans one metre either way until the limits say otherwise.
SPAN_METRES = 1.0


@dataclass(frozen=True)
class Scale:
    """Number shown in a field = stored value * factor."""
    factor:float
    suffix:str
    decimals:int

    def show(self,value):
        return value*self.factor

    def si(self,number):
        return number/self.factor

    @property
    def unit(self):
        return self.suffix.strip()

    def text(self,number):
        return f"{number:.{self.decimals}f}"

    @property
    def step(self):
        return 10**-self.decimals


ANGLE = Scale(180/math.pi," °",3)
ANGLE_RATE = Scale(180/math.pi," °/s",3)
ANGLE_ACCELERATION = Scale(180/math.pi," °/s²",3)


def _length(rate=""):
    from core import units
    name = units.model_unit()
    return Scale(units.length_number(1,name),units.length_suffix(name)+rate,DECIMALS.get(name,3))


def length():
    return _length()


def speed():
    return _length("/s")


def acceleration():
    return _length("/s²")


def signature():
    from core import units
    return units.model_unit()


def apply(widget,scale,minimum=None,maximum=None):
    """Suffix and precision of a spin box; no valueChanged for the rounding."""
    previous = widget.blockSignals(True)
    try:
        widget.setSuffix(scale.suffix);widget.setDecimals(scale.decimals)
        if minimum is not None:widget.setMinimum(minimum)
        if maximum is not None:widget.setMaximum(maximum)
    finally:widget.blockSignals(previous)
    widget.units_scale = scale


def tolerance(widget,default=5e-4):
    """Half a step of the box in stored units: what it shows is what is compared."""
    scale = getattr(widget,"units_scale",None)
    return default if scale is None else scale.si(scale.step/2)


def stored(widget):
    """The stored (SI) value a field shows."""
    scale = getattr(widget,"units_scale",None)
    return widget.value() if scale is None else scale.si(widget.value())


def show(widget,value):
    scale = getattr(widget,"units_scale",None)
    widget.setValue(value if scale is None else scale.show(value))
