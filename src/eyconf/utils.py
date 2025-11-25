from __future__ import annotations

import logging
from dataclasses import fields, is_dataclass
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

log = logging.getLogger(__name__)

D = TypeVar("D", bound="DataclassInstance")


def merge_dicts(a: dict, b: dict, path=[]):
    """Merge dict b into dict a, raising an exception on conflicts."""
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                raise Exception("Conflict at " + ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def dataclass_from_dict(in_type: type[D], data: dict) -> D:
    """Convert a dict to a dataclass instance of the given type. Always returns a dataclass."""
    result = _dataclass_from_dict_inner(in_type, data)
    if result is None:
        raise ValueError(f"Could not parse data {data} with type {in_type}")
    return result


def _dataclass_from_dict_inner(target_type: type, data: Any) -> Any:
    """Inner function that handles Union types and may return None."""
    # Handle Union types
    origin = get_origin(target_type)
    if origin is UnionType:
        args = get_args(target_type)
        includes_none = any(arg is NoneType or arg is type(None) for arg in args)

        if data is None and includes_none:
            return None

        for arg in args:
            if arg is NoneType or arg is type(None):
                continue
            try:
                return _dataclass_from_dict_inner(arg, data)
            except (ValueError, TypeError, KeyError):
                continue
        return None

    # Handle dict data - convert to dataclass
    if isinstance(data, dict) and is_dataclass(target_type):
        field_types = get_type_hints(target_type, include_extras=False)
        found_fields = {}
        additional_fields = {}

        aliased_fields = {}  # alias to name, only aliased fields
        field_types_to_use = {}  # name to type, all fields
        for f in fields(target_type):
            if hasattr(f, "metadata"):
                aliased_fields[f.metadata.get("alias")] = f.name
            field_types_to_use[f.name] = field_types.get(f.name, f.type)

        for key, value in data.items():
            if key in aliased_fields.keys():
                key = aliased_fields[key]
                found_fields[key] = _dataclass_from_dict_inner(
                    field_types_to_use[key], value
                )
            elif key in field_types_to_use.keys():
                found_fields[key] = _dataclass_from_dict_inner(
                    field_types_to_use[key], value
                )
            else:
                additional_fields[key] = value

        try:
            res = target_type(**found_fields)  # type: ignore[bad-instantiation]
            if len(additional_fields) > 0:
                log.warning(
                    f"Additional fields {list(additional_fields.keys())} "
                    f"found for dataclass {target_type.__name__} but "
                    "not in schema and will be ignored."
                )
            return res
        except TypeError as e:
            raise ValueError(f"Failed to create {target_type.__name__}: {e}")

    # Potentially nested dataclass in dicts
    if isinstance(data, dict) and get_origin(target_type) is dict:
        key_type, value_type = get_args(target_type)
        return {
            _dataclass_from_dict_inner(key_type, k): _dataclass_from_dict_inner(
                value_type, v
            )
            for k, v in data.items()
        }

    # Handle sequence types (list, tuple)
    if isinstance(data, (list, tuple)):
        if hasattr(target_type, "__args__") and target_type.__args__:
            elem_type = target_type.__args__[0]
            return [_dataclass_from_dict_inner(elem_type, item) for item in data]
        else:
            return data

    # Handle primitive types
    return data
