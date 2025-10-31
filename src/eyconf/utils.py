from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from types import NoneType, UnionType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union, get_type_hints

from typing_extensions import get_args, get_origin

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

    def __deepcopy__(self, memo: dict) -> "AttributeDict":
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
        data_dict = deepcopy(asdict(self._data))
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
    if origin is Union or origin is UnionType:
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
        for field_name, field_type in field_types.items():
            if field_name in data:
                found_fields[field_name] = _dataclass_from_dict_inner(
                    field_type, data[field_name]
                )

        try:
            return target_type(**found_fields)  # type: ignore[bad-instantiation]
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
