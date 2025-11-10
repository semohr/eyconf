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


def asdict_with_aliases(obj: DataclassInstance | DataclassInstance) -> dict:
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

    return _asdict_inner(obj, dict_factory=_alias_dict_factory)  # type: ignore[arg-type]


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


def _asdict_inner(obj, dict_factory):
    if type(obj) in _ATOMIC_TYPES:
        return obj
    elif hasattr(type(obj), "__dataclass_fields__"):
        # fast path for the common case
        if dict_factory is dict:
            return {
                f.name: _asdict_inner(getattr(obj, f.name), dict) for f in fields(obj)
            }
        else:
            result = []
            for f in fields(obj):
                value = _asdict_inner(getattr(obj, f.name), dict_factory)
                result.append((f.name, value))
            return dict_factory(obj, result)
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

        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        # Assume we can create an object of this type by passing in a
        # generator (which is not true for namedtuples, handled
        # above).
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))  # type: ignore
            for k, v in obj.items():
                result[_asdict_inner(k, dict_factory)] = _asdict_inner(v, dict_factory)
            return result
        return type(obj)(
            (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
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
