from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from eyconf.asdict import asdict_with_aliases
from eyconf.decorators import dict_access
from eyconf.type_utils import is_dataclass_type, iter_dataclass_type
from eyconf.utils import merge_dicts
from eyconf.validation import validate
from eyconf.validation._to_json import to_json_schema

from .base import EYConfBase

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")


log = logging.getLogger(__name__)


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


@dict_access
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


class EYConfExtraFields(EYConfBase[D]):
    """Configuration class that supports extra fields explicitly.

    This class extends the base configuration functionality to allow
    for additional fields that are not defined in the original schema.

    This additional field is accessible via the `extra_data_as_dict` property.
    """

    _extra_data: AttributeDict

    def __init__(
        self,
        data: dict | D,
        schema: type[D] | None = None,
    ):
        if is_dataclass_type(data):
            raise ValueError("Data must be a dict or datacalss instance, not schema!")

        if schema is not None:
            self._schema = schema
        else:
            if not is_dataclass(data):
                raise ValueError(
                    "If no schema is provided, data must be of the schema dataclass instance."
                )
            self._schema = type(data)

        # Automatically set __allow_additional to True in the schema(s) if not set
        for s in iter_dataclass_type(self._schema):
            if not hasattr(s, "__allow_additional"):
                setattr(s, "__allow_additional", True)
            else:
                log.debug(
                    f"Schema {s.__name__} already has __allow_additional set to "
                    f"{getattr(s, '__allow_additional')}."
                )

        # Create schema, raise if Schema is invalid
        self._json_schema = to_json_schema(self._schema)

        # Will raise ConfigurationError if the data does not comply with the schema
        validate(data, self._json_schema)

        self._extra_data = AttributeDict()

        if is_dataclass(data):
            self._data = cast(D, data)
        else:
            self._data = None  # type: ignore
            self.update(data)

    @property
    def data(self) -> D:
        """Get the configuration data wrapped in a dynamic accessor.

        Care: Instance checks will not work as expected on this property.
        """
        return AccessProxy(self._data, self._extra_data)  # type: ignore

    @property
    def extra_data(self) -> AttributeDict:
        """Get the extra data as an AttributeDict."""
        return self._extra_data

    def to_dict(self, include_additional: bool = True) -> dict:
        """Get the full configuration data as a dictionary, including extra fields."""
        data = asdict(self._data)
        if include_additional:
            data = merge_dicts(data, self.extra_data.as_dict())
        return data

    def _update_additional(self, target, key, value: Any, _current_path: list[str]):
        extra_data: AttributeDict = self._extra_data
        for path_part in _current_path:
            extra_data = getattr(extra_data, path_part)

        if isinstance(value, dict):
            setattr(extra_data, key, AttributeDict(**value))
        else:
            setattr(extra_data, key, value)
