from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from eyconf.asdict import asdict_with_aliases
from eyconf.decorators import (
    _aliases_map,
    _get_attr_resolve_alias,
    _set_attr_resolve_alias,
)
from eyconf.type_utils import is_dataclass_type, iter_dataclass_type
from eyconf.utils import merge_dicts
from eyconf.validation import validate
from eyconf.validation._to_json import to_json_schema

from .base import Config

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

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item dynamically."""
        return self.__setattr__(key, value)

    def to_dict(self) -> dict:
        """Convert the AttributeDict to a standard dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("__"):
                continue
            if isinstance(value, AttributeDict):
                result[key] = value.to_dict()
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
        return f"AttributeDict({self.to_dict()})"

    def __str__(self) -> str:
        """Use the dict string representation."""
        return str(self.to_dict())

    def __bool__(self) -> bool:
        """Return False if the AttributeDict is empty, True otherwise."""
        return bool(self.__dict__)

    def __eq__(self, other: Any) -> bool:
        """Equality comparison based on the internal dictionary."""
        if isinstance(other, AttributeDict):
            return self.to_dict() == other.to_dict()
        if isinstance(other, dict):
            return self.to_dict() == other
        return False


class AccessProxy(Generic[D]):
    """Proxy to access attributes dynamically."""

    _data: D
    _extra_data: AttributeDict

    def __init__(self, data: D, extra_data: AttributeDict):
        self._data = data
        self._extra_data = extra_data

    def to_dict(self) -> dict:
        """Convert the AccessProxy to a standard dictionary."""
        merged = deepcopy(self._extra_data.to_dict())
        data_dict = deepcopy(asdict_with_aliases(self._data))
        result = merge_dicts(data_dict, merged)
        return result

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

    def __getitem__(self, key: str) -> Any:
        """Get item dynamically."""
        # We need a bit of extra work here for alias resolution
        aliases = _aliases_map(self._data)
        if key in aliases.keys() or hasattr(self._data, key):
            return _get_attr_resolve_alias(self._data, key)
        else:
            return getattr(self._extra_data, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item dynamically."""
        # We need a bit of extra work here for alias resolution
        aliases = _aliases_map(self._data)
        if key in aliases.keys() or hasattr(self._data, key):
            _set_attr_resolve_alias(self._data, key, value)
        else:
            setattr(self._extra_data, key, value)


class ConfigExtra(Config[D]):
    """Configuration class that supports extra fields explicitly.

    This class extends the base configuration functionality to allow
    for additional fields that are not defined in the original schema.

    This additional fields are accessible via the `extra_data` property. They
    are merged into the schema data when accessing via the `data` property.
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
    def data(self) -> AccessProxy[D]:  # type: ignore
        """Get the configuration data wrapped in a dynamic accessor.

        Care: Instance checks will not work as expected on this property.
        """
        return AccessProxy(self._data, self._extra_data)

    @property
    def schema_data(self) -> D:
        """Get the schema dataclass type excluding extra fields."""
        return self._data

    @property
    def extra_data(self) -> AttributeDict:
        """Get the extra data as an AttributeDict."""
        return self._extra_data

    def to_dict(self, extra_fields: bool = True) -> dict:
        """Get the full configuration data as a dictionary, including extra fields."""
        data = asdict_with_aliases(self._data)
        if extra_fields:
            data = merge_dicts(data, self.extra_data.to_dict())
        return data

    def _update_additional(
        self, target, key, value: Any, _current_path: list[str]
    ) -> None:
        """Handle updating additional (non-schema) fields used in `super.update`."""

        extra_data: AttributeDict = self._extra_data
        for path_part in _current_path:
            extra_data = getattr(extra_data, path_part)

        if isinstance(value, dict):
            setattr(extra_data, key, AttributeDict(**value))
        else:
            setattr(extra_data, key, value)
