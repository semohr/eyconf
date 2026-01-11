from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import is_dataclass
from functools import cache
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from eyconf.asdict import asdict_with_aliases
from eyconf.type_utils import (
    is_dataclass_instance,
    is_dataclass_type,
    iter_dataclass_type,
)
from eyconf.utils import (
    Metadata,
    dataclass_from_dict,
    merge_dicts,
    metadata_fields_from_dataclass,
)
from eyconf.validation import validate
from eyconf.validation._to_json import to_json_schema

from .base import Config

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")


log = logging.getLogger(__name__)


class AccessProxy(Generic[D]):
    """Proxy to access attributes dynamically."""

    _data: D  # this should never be an access proxy!
    _extra_data: dict

    # this proxies' location in the overall config tree
    _parent: AccessProxy | None

    def __init__(
        self,
        data: D,
        extra_data: dict,
        parent: AccessProxy | None = None,
    ):
        self._data = data
        self._extra_data = extra_data
        self._parent = parent

    @property
    @cache
    def _fields_metadata(self) -> dict[str, Metadata]:
        """Get the fields of the current dataclass schema."""
        return metadata_fields_from_dataclass(self._data)

    def _resolve_attr_to_dict_key(self, attr_key: str) -> str:
        """Resolve an attribute key to its dict key using aliasing."""
        return self._fields_metadata.get(attr_key, {}).get("alias", attr_key)

    def _resolve_dict_to_attr_key(self, dict_key: str) -> str:
        """Resolve a dict key to its attribute key using aliasing."""
        for attr_key, metadata in self._fields_metadata.items():
            if metadata.get("alias") == dict_key:
                return attr_key
        return dict_key

    def _to_dict(self) -> dict:
        """Convert the AccessProxy to a standard dictionary."""
        extra = deepcopy(self._extra_data)
        data = deepcopy(asdict_with_aliases(self._data))
        result = merge_dicts(data, extra)
        return result

    def __getattr__(self, attr_key: str) -> Any:
        """Get field via attribute style access (non-aliased keys)."""
        dict_key: str = self._resolve_attr_to_dict_key(attr_key)
        try:
            data = getattr(self._data, attr_key)
            if is_dataclass_instance(data):
                if dict_key not in self._extra_data:
                    self._extra_data[dict_key] = dict()
                return AccessProxy(
                    data=data,
                    extra_data=self._extra_data[dict_key],
                    parent=self,
                )
            else:
                return data
        except AttributeError:
            return self._extra_data[dict_key]

    def __setattr__(self, attr_key: str, value: Any):
        """Set field via attribute style access (non-aliased keys)."""
        if isinstance(value, AccessProxy):
            value = value._to_dict()

        if attr_key.startswith("_"):
            object.__setattr__(self, attr_key, value)
        else:
            if hasattr(self._data, attr_key):
                setattr(self._data, attr_key, value)
            else:
                dict_key = self._resolve_attr_to_dict_key(attr_key)
                self._extra_data[dict_key] = value

    def __getitem__(self, dict_key: str) -> Any:
        """Get field via dict style acces (alias)."""
        attr_key = self._resolve_dict_to_attr_key(dict_key)
        if hasattr(self._data, attr_key):
            return self.__getattr__(attr_key)
        else:
            return self._extra_data[dict_key]

    def __setitem__(self, dict_key: str, value: Any) -> None:
        """Set field via dict style access (alias)."""
        attr_key = self._resolve_dict_to_attr_key(dict_key)
        if hasattr(self._data, attr_key):
            self.__setattr__(attr_key, value)
        else:
            self._extra_data[dict_key] = value

    def __deepcopy__(self, memo):
        """Implement deepcopy to avoid issues with nested dataclasses."""
        new_proxy = type(self)(
            data=deepcopy(self._data, memo),
            extra_data=deepcopy(self._extra_data, memo),
            parent=self._parent,
        )
        return new_proxy

    def __hash__(self) -> int:
        """Make Access Proxy hashable by recursively hashing its internal data."""

        def make_hashable(obj):
            if isinstance(obj, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
            elif isinstance(obj, list):
                return tuple(make_hashable(item) for item in obj)
            else:
                return obj

        return hash(make_hashable(self._to_dict()))

    def __eq__(self, value: object, /) -> bool:
        """Compare Access Proxies via their data."""
        if isinstance(value, AccessProxy):
            value = value._to_dict()
        return self._to_dict() == value


class ConfigExtra(Config[D]):
    """Configuration class that supports extra fields explicitly.

    This class extends the base configuration functionality to allow
    for additional fields that are not defined in the original schema.

    This additional fields are accessible via the `extra_data` property. They
    are merged into the schema data when accessing via the `data` property.
    """

    _extra_data: dict[str, Any]
    _access_proxy: AccessProxy[D]

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

        self._extra_data = dict()

        if is_dataclass(data):
            self._data = cast(D, data)
        else:
            self._data = dataclass_from_dict(self._schema, data)

        self._access_proxy = AccessProxy(
            data=self._data,
            extra_data=self._extra_data,
        )

    def reset(self):
        """Reset the configuration data to the default values."""
        super().reset()
        self._access_proxy = AccessProxy(
            data=self._data,
            extra_data=self._extra_data,
        )

    @property
    def data(self) -> D:
        """Get the configuration data wrapped in a dynamic accessor.

        Care: Instance checks will not work as expected on this property.

        We have two non-ideal choices for the type hint here:
        - if we use D, we will get a wrong type_error for e.g. `config.data.my_field.to_dict()`
        - if we use AccessProxy[D], we wont get the nice type_checking against the schema.
        """
        return self._access_proxy  # type: ignore

    @property
    def proxy(self) -> AccessProxy[D]:
        """Convenience Property for setting non-schema fields."""
        return self._access_proxy

    @property
    def schema_data(self) -> D:
        """Get the schema dataclass type excluding extra fields."""
        return self._data

    @property
    def extra_data(self) -> dict:
        """Get the extra data as a dict."""
        return self._extra_data

    def to_dict(self, extra_fields: bool = True) -> dict:
        """Get the full configuration data as a dictionary, including extra fields."""
        data = asdict_with_aliases(self.proxy._data)
        if extra_fields:
            data = merge_dicts(data, self.proxy._extra_data)
        return data

    def _update_additional(
        self,
        value: Any,
        path: list[tuple[DataclassInstance, str]],
    ) -> None:
        """Handle updating additional (non-schema) fields used in `super.update`.

        Here, we update extra_data, which is a dict. So we use dict style.
        """
        dict_key_path = []
        for target, attr_key in path:
            # resolve attr_key to dict_key using aliasing
            field_metadata = metadata_fields_from_dataclass(target)
            dict_key = field_metadata.get(attr_key, {}).get("alias", attr_key)
            dict_key_path.append(dict_key)

        extra_data: dict[str, Any] = self._extra_data
        for dict_key in dict_key_path[:-1]:
            if dict_key not in extra_data.keys():
                extra_data[dict_key] = dict()
            extra_data = extra_data[dict_key]

        extra_data[dict_key_path[-1]] = value
