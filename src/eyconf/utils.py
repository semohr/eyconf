from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from dataclasses import fields, is_dataclass
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035

from eyconf.type_utils import get_type_hints_resolve_namespace, is_dataclass_type

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
    # avoid circular import
    from eyconf.decorators import check_allows_additional

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
            if check_allows_additional(target_type):
                for key, value in additional_fields.items():
                    setattr(res, key, value)
            elif len(additional_fields) > 0:
                raise TypeError(
                    f"Found additional fields {list(additional_fields.keys())}. "
                    + "Consider using `__allow_additional: ClassVar[bool] = True`"
                    + " in the dataclass to allow them."
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


def iter_dataclass_type(schema: type[D]) -> Iterator[type[DataclassInstance]]:
    """Iterate over all dataclass nested instances in the given dataclass type.

    Duplicate types are automatically handled by using a set to track visited types.

    Yields
    ------
    DataclassInstance
        Each nested dataclass instance found within the schema (also the root).
    """
    visited = set()
    stack = [schema]

    def _add_type_to_stack(*t: type[Any]) -> None:
        """Add type to stack if it is a dataclass and not yet visited."""
        for item in t:
            if is_dataclass_type(item) and id(item) not in visited:
                stack.append(item)

    while stack:
        current_type = stack.pop()
        type_id = id(current_type)
        # Skip if we've already visited this type
        if type_id in visited:
            continue

        visited.add(type_id)
        yield current_type

        # Process fields of the current dataclass
        type_hints = get_type_hints_resolve_namespace(current_type, include_extras=True)
        for _, field_type in type_hints.items():
            origin = get_origin(field_type)

            if origin is Annotated:
                # Unpack Annotated types
                field_type = get_args(field_type)[0]
                origin = get_origin(field_type)

            if origin in {UnionType, list, tuple, set, Sequence, TypingSequence, dict}:
                # Handle collection types
                _add_type_to_stack(*get_args(field_type))

            if is_dataclass_type(field_type):
                _add_type_to_stack(field_type)
