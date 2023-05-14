from functools import partial
from inspect import ismethod, isfunction, getmodule, isbuiltin, getmro


def get_class_that_defined_method(meth):
    if isinstance(meth, partial):
        return get_class_that_defined_method(meth.func)
    if ismethod(meth) or (
            isbuiltin(meth)
            and getattr(meth, '__self__', None) is not None
            and getattr(meth.__self__, '__class__', None)
    ):
        for cls in getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if isfunction(meth):
        cls = getattr(
            getmodule(meth), meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0], None
        )
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects
