"""Configuration base classes for EYconf.

Allows to create configuration classes based on dataclass schemas,
with validation and serialization capabilities.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import asdict, fields, is_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    cast,
)

from eyconf.generate_yaml import dataclass_to_yaml
from eyconf.type_utils import get_type_hints_resolve_namespace, is_dataclass_type
from eyconf.utils import (
    dataclass_from_dict,
)
from eyconf.validation import to_json_schema, validate, validate_json

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")

log = logging.getLogger(__name__)


class Config(Generic[D]):
    """Base configuration class.

    This class allows to create configuration objects based on dataclass schemas.
    It provides methods for validation, updating, overwriting, and converting
    configuration data.

    This can be used to create custom configuration classes in memory without file I/O.
    """

    _schema: type[D]
    _data: D
    _json_schema: dict

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

        # Create schema, raise if Schema is invalid
        self._json_schema = to_json_schema(self._schema)

        # Will raise ConfigurationError if the data does not comply with the schema
        validate(data, self._json_schema)

        if is_dataclass(data):
            self._data = cast(D, data)
        else:
            self._data = dataclass_from_dict(self._schema, data)

    def validate(self):
        """Validate the current data against the schema."""
        validate(self._data, self._json_schema)

    def update(self, data: dict):
        """Update the configuration with provided data.

        This applies an partial update to the existing configuration data.
        Only the provided keys will be updated, others will remain unchanged.
        """

        def _update(
            target_type: type[DataclassInstance],
            target: DataclassInstance,
            update_data: dict,
            _current_path: list[str] = [],
        ):
            target_annotations = get_type_hints_resolve_namespace(target_type)

            # Rewrite key, from alias to field name
            alias_fields = {
                f.metadata["alias"]: f
                for f in fields(target_type)
                if "alias" in f.metadata
            }

            for key, value in update_data.items():
                # resolve if key has an alias
                if alias_field := alias_fields.get(key):
                    key = alias_field.name

                if hasattr(target, key):
                    # folders : dict[str, InboxFolder]
                    current_value = getattr(target, key)
                    # current_value = {placeholder:Config42()}

                    # Handle dataclass fields
                    if is_dataclass(current_value):
                        _update(
                            target_annotations[key],
                            current_value,  # type: ignore[arg-type]
                            value,
                            _current_path + [key],
                        )
                    # Handle Optional fields that were previously None
                    elif current_value is None and isinstance(value, dict):
                        nested_instance = dataclass_from_dict(
                            target_annotations[key], value
                        )
                        setattr(target, key, nested_instance)
                    elif current_annotation := target_annotations.get(key):
                        nested = dataclass_from_dict(
                            current_annotation,
                            # TODO: If we want to implement a merge strategy
                            # some like this could work:
                            # merge_dicts(asdict(current_value), value),  # type: ignore[arg-type]
                            value,
                        )
                        setattr(target, key, nested)
                    else:
                        # Primitives and direct assignments
                        setattr(target, key, value)
                else:
                    # Non-schema fields
                    self._update_additional(
                        target, key, value, _current_path=_current_path
                    )

        old_data = deepcopy(self._data)
        update_dict = data if not is_dataclass(data) else asdict(data)

        _update(self._schema, self._data, update_dict)

        try:
            self.validate()
        except Exception as e:
            self._data = old_data
            raise e from e

    def _update_additional(
        self, target, key, value: Any, _current_path: list[str]
    ) -> None:
        """Handle updating additional (non-schema) fields.

        Can be overwritten in subclasses.
        """
        raise AttributeError(
            "Cannot set unknown attribute"
            f" '{'.'.join(_current_path + [key])}' on configuration."
        )

    def overwrite(self, data: dict | D):
        """Overwrite the configuration with provided data.

        If the provided data is missing required fields, an error will be raised.
        """
        data = asdict(data) if is_dataclass(data) else data
        validate_json(data, self._json_schema)
        self._data = dataclass_from_dict(self._schema, data)

    def reset(self):
        """Reset the configuration data to the default values."""
        self._data = self._schema()

    # -------------------------------- Converters -------------------------------- #

    @property
    def data(self) -> D:
        """Get the configuration data."""
        return self._data

    def to_dict(self) -> dict:
        """Convert the configuration data to a dictionary."""
        return asdict(self._data)

    def to_yaml(self) -> str:
        """Convert the configuration data to a yaml string."""
        return dataclass_to_yaml(self._data)

    # --------------------------------- Printing --------------------------------- #

    def __repr__(self) -> str:
        """Return a custom string representation of the configuration object."""
        class_name = type(self).__name__
        memory_address = hex(id(self))
        prefix = f"<{class_name} object at {memory_address}>:\n"
        return f"{prefix}{self.__str__()}"

    def __str__(self):
        """Return a custom formatted string representation of the configuration data."""
        data_dict = asdict(self._data)
        s = "\n".join(
            "  " + line for line in self._pretty_format(data_dict).splitlines()
        )
        return s

    def _pretty_format(self, data, indent=0):
        """Format the dict with pretty indentation."""
        result: list[str] = []
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(" " * indent + f"{key}:")
                result.append(self._pretty_format(value, indent + 4))
            else:
                result.append(" " * indent + f"{key}: {value}")
        return "\n".join(result)
