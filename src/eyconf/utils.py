import logging
from copy import deepcopy
from dataclasses import dataclass, is_dataclass
from types import NoneType, UnionType
from typing import Any, Generic, TypeVar, Union, get_type_hints

from typing_extensions import get_args, get_origin

log = logging.getLogger(__name__)
D = TypeVar("D")


@dataclass
class AttributeDict:
    """A generic dataclass for holding dynamic attributes."""

    def __init__(self, **kwargs: Any):
        """Initialize the AttributeDict with given keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        """Get attribute dynamically. If it does not exist, we create it."""
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
                return AccessProxy(ret, getattr(self._extra_data, name))
            return getattr(self._data, name)
        except AttributeError:
            return getattr(self._extra_data, name)

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


def dataclass_from_dict(in_type: type[D], data: dict) -> D:
    """Convert a dict to a dataclass instance of the given type."""
    # If type is a union try all args
    origin = get_origin(in_type)
    if origin is Union or origin is UnionType:
        args = get_args(in_type)
        includes_none = False
        for arg in args:
            if arg is NoneType or arg is None or arg is type(None):
                includes_none = True

        if data is None and includes_none:
            return None
        for arg in args:
            try:
                return dataclass_from_dict(arg, data)
            except Exception as _e:
                pass
        raise ValueError(f"Could not parse data {data} with type {in_type}")

    if isinstance(data, dict):
        field_types = get_type_hints(in_type, include_extras=False)

        # It is possible that additional fields are present in data that are not
        # part of the dataclass. We ignore them here.
        found_fields = {}
        for f in data:
            if found_field := field_types.get(f, None):
                found_fields[f] = dataclass_from_dict(found_field, data[f])
        return in_type(**found_fields)

    if isinstance(data, (tuple, list)):
        return [dataclass_from_dict(in_type.__args__[0], f) for f in data]

    return data
