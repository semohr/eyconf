"""Contains mostly a copy of dataclasses.asdict, but with support for field aliases."""

from __future__ import annotations

import copy
import logging
import types
from dataclasses import fields
from typing import (
    TYPE_CHECKING,
    TypeVar,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

log = logging.getLogger(__name__)

D = TypeVar("D", bound="DataclassInstance")


def asdict_with_aliases(
    obj: DataclassInstance | DataclassInstance,
    include_attributes: bool = True,
    include_properties: bool = False,
) -> dict:
    """
    Convert a dataclass to a dict, applying aliases if present.

    Every attribute in the dataclass that has an `alias` defined in the metadata
    will use the alias as the key in the resulting dictionary (instead of the attribute name).

    This is pretty much a copy of the standard `dataclasses.asdict` function,
    but we had to modify it, because the dict_factory needs to access obj recursively.
    (previously dataclass obj not passed down)
    """
    if not hasattr(type(obj), "__dataclass_fields__"):
        raise TypeError("asdict_with_aliases() should be called on dataclass instances")

    return _asdict_inner(
        obj,
        dict_factory=_alias_dict_factory,
        include_attributes=include_attributes,
        include_properties=include_properties,
    )  # type: ignore[arg-type]


# -------------- Slightly modified copy from dataclasses.asdict -------------- #

_ATOMIC_TYPES = frozenset(
    {
        # Common JSON Serializable types
        types.NoneType,
        bool,
        int,
        float,
        str,
        # Other common types
        complex,
        bytes,
        # Other types that are also unaffected by deepcopy
        types.EllipsisType,
        types.NotImplementedType,
        types.CodeType,
        types.BuiltinFunctionType,
        types.FunctionType,
        type,
        range,
        property,
    }
)


def _asdict_inner(obj, **kwargs):
    dict_factory = kwargs.get("dict_factory", dict)
    include_attributes = kwargs.get("include_attributes", False)
    include_properties = kwargs.get("include_properties", False)

    if type(obj) in _ATOMIC_TYPES:
        return obj
    elif hasattr(type(obj), "__dataclass_fields__"):
        # obj is dataclass
        # fast path for the common case
        if dict_factory is dict:
            result = {
                f.name: _asdict_inner(getattr(obj, f.name), dict_factory=dict)
                for f in fields(obj)
            }
        else:
            _result = []
            for f in fields(obj):
                value = _asdict_inner(getattr(obj, f.name), **kwargs)
                _result.append((f.name, value))
            result = dict_factory(obj, _result)

        field_names = {f.name for f in fields(obj)}
        extra_attrs = {}
        if include_attributes:
            for k, v in obj.__dict__.items():
                if not k.startswith("_") and k not in field_names:
                    extra_attrs[k] = _asdict_inner(v, **kwargs)

        if include_properties:
            for prop in dir(obj):
                if (
                    not prop.startswith("_")
                    and prop not in field_names
                    and prop not in extra_attrs
                ):
                    attr = getattr(type(obj), prop, None)
                    if isinstance(attr, property):
                        try:
                            extra_attrs[prop] = _asdict_inner(
                                getattr(obj, prop), **kwargs
                            )
                        except Exception:
                            pass  # Ignore property errors

        # Merge. Can we be sure that result is a dict? Depends on factory.
        if isinstance(result, dict):
            result.update(extra_attrs)

        return result

    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        # obj is a namedtuple.  Recurse into it, but the returned
        # object is another namedtuple of the same type.  This is
        # similar to how other list- or tuple-derived classes are
        # treated (see below), but we just need to create them
        # differently because a namedtuple's __init__ needs to be
        # called differently (see bpo-34363).

        # I'm not using namedtuple's _asdict()
        # method, because:
        # - it does not recurse in to the namedtuple fields and
        #   convert them to dicts (using dict_factory).
        # - I don't actually want to return a dict here.  The main
        #   use case here is json.dumps, and it handles converting
        #   namedtuples to lists.  Admittedly we're losing some
        #   information here when we produce a json list instead of a
        #   dict.  Note that if we returned dicts here instead of
        #   namedtuples, we could no longer call asdict() on a data
        #   structure where a namedtuple was used as a dict key.

        return type(obj)(*[_asdict_inner(v, dict_factory=dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        # Assume we can create an object of this type by passing in a
        # generator (which is not true for namedtuples, handled
        # above).
        return type(obj)(_asdict_inner(v, dict_factory=dict_factory) for v in obj)
    elif isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))  # type: ignore
            for k, v in obj.items():
                result[_asdict_inner(k, dict_factory=dict_factory)] = _asdict_inner(
                    v, dict_factory=dict_factory
                )
            return result
        return type(obj)(
            (
                _asdict_inner(k, dict_factory=dict_factory),
                _asdict_inner(v, dict_factory=dict_factory),
            )
            for k, v in obj.items()
        )
    else:
        return copy.deepcopy(obj)


def _alias_dict_factory(obj, items):
    result = {}
    for key, value in items:
        # Find the field object for this key
        field_obj = next((f for f in fields(obj) if f.name == key), None)
        if field_obj and "alias" in field_obj.metadata:
            result[field_obj.metadata["alias"]] = value
        else:
            result[key] = value
    return result
