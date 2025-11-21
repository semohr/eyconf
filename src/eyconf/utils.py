from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Protocol,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035

from eyconf.type_utils import get_type_hints_resolve_namespace, is_dataclass_type

from .asdict import asdict_with_aliases

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

log = logging.getLogger(__name__)

D = TypeVar("D", bound="DataclassInstance")


@dataclass
class AttributeDict:
    """A generic dataclass for holding dynamic attributes."""

    def __init__(self, **kwargs: Any):
        """Initialize the AttributeDict with given keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        """Get attribute dynamically. If it does not exist, we create it."""
        if name.startswith("_"):
            raise AttributeError(f"{name} not found")

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            n = AttributeDict()
            setattr(self, name, n)
            return n

    def __setattr__(self, name: str, value: Any):
        """Set attribute dynamically."""
        if isinstance(value, dict):
            value = AttributeDict(**value)
        object.__setattr__(self, name, value)

    def __getitem__(self, key: str) -> Any:
        """Get item dynamically."""
        return self.__getattr__(key)

    def as_dict(self) -> dict:
        """Convert the AttributeDict to a standard dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, AttributeDict):
                result[key] = value.as_dict()
            else:
                result[key] = value
        return result

    def __deepcopy__(self, memo: dict) -> AttributeDict:
        """Create a deep copy of the AttributeDict."""
        # Avoid infinite recursion with memo
        if id(self) in memo:
            return memo[id(self)]

        # Create new instance
        new_instance = AttributeDict()
        memo[id(self)] = new_instance

        # Deep copy all attributes
        for key, value in self.__dict__.items():
            # Use copy.deepcopy for nested objects, but handle AttributeDict specially
            if isinstance(value, AttributeDict):
                setattr(new_instance, key, deepcopy(value, memo))
            else:
                setattr(new_instance, key, deepcopy(value, memo))

        return new_instance

    def __repr__(self) -> str:
        """Representation of the AttributeDict."""
        return f"AttributeDict({self.as_dict()})"

    def __str__(self) -> str:
        """Use the dict string representation."""
        return str(self.as_dict())

    def __bool__(self) -> bool:
        """Return False if the AttributeDict is empty, True otherwise."""
        return bool(self.__dict__)


class AccessProxy(Generic[D]):
    """Proxy to access attributes dynamically."""

    _data: D
    _extra_data: AttributeDict

    def __init__(self, data: D, extra_data: AttributeDict):
        self._data = data
        self._extra_data = extra_data

    def __getattr__(self, name: str) -> Any:
        """Get attribute from either the typed data or additional data."""
        try:
            ret = getattr(self._data, name)
            # We need to wrap nested dataclasses as well
            # Needed for accessing a mixed case, where we add an unknown property to
            # a nested schema. In this case, we need the same extra level in _extra_data.
            if is_dataclass(ret):
                return AccessProxy(ret, getattr(self._extra_data, name))  # type: ignore[arg-type]
            return getattr(self._data, name)
        except AttributeError:
            return getattr(self._extra_data, name)

    def __getitem__(self, key: str) -> Any:
        """Get item dynamically."""
        return self.__getattr__(key)

    def __setattr__(self, name: str, value: Any):
        """Set attribute on either the typed data or additional data."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            if hasattr(self._data, name):
                setattr(self._data, name, value)
            else:
                setattr(self._extra_data, name, value)

    def __delattr__(self, name: str):
        """Delete attribute from either the typed data or additional data."""
        if name.startswith("_"):
            object.__delattr__(self, name)
        else:
            if hasattr(self._data, name):
                delattr(self._data, name)
            else:
                delattr(self._extra_data, name)

    def as_dict(self) -> dict:
        """Convert the AccessProxy to a standard dictionary."""
        merged = deepcopy(self._extra_data.as_dict())
        data_dict = deepcopy(asdict_with_aliases(self._data))
        result = merge_dicts(data_dict, merged)
        return result


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


T = TypeVar("T")


@runtime_checkable
class DictAccess(Protocol):
    """Protocol for dict-like access."""

    def __getitem__(self, key: str) -> Any: ...  # noqa: D105


def dict_access(cls: type[T]) -> type[T]:
    """Class decorator to add dict-like access to class attributes.

    Can be used to add `dict`-like access to any class, allowing
    attribute access via the `obj['attribute']` syntax.

    Use with care, dict-style access does not provide any type safety
    and will not be checked by static type checkers.

    Usage:

    ```python
    @dict_access
    class MySchema:
        forty_two: int = 42

    obj = MySchema()
    assert isinstance(obj, DictAccess)
    print(obj['forty_two'])  # Outputs: 42
    ```
    """

    def __getitem__(self, key: str) -> Any:
        # for dict access we _only_ want to allow the aliases,
        # not the attribute names!
        aliases = {
            f.metadata["alias"]: f.name for f in fields(self) if "alias" in f.metadata
        }
        if key in aliases.keys():
            return getattr(self, aliases[key])
        elif key in aliases.values():
            _suggestion = next((k for k, v in aliases.items() if v == key), None)
            raise KeyError(
                "If an alias is defined, subscripting is only allowed "
                + f"using the alias. Use ['{_suggestion}'] instead of ['{key}']!"
            )

        return getattr(self, key)

    setattr(cls, "__getitem__", __getitem__)
    return cls


def check_allows_additional(schema: D | type[D]) -> bool:
    """Whether the dataclass allows additional properties."""
    if is_dataclass_type(schema):
        return getattr(schema, f"_{schema.__name__}__allow_additional", False)
    elif is_dataclass(schema) and not isinstance(schema, type):
        return getattr(schema, f"_{schema.__class__.__name__}__allow_additional", False)
    return False


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
