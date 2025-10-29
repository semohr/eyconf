"""Configuration base classes for EYconf.

Allows to create configuration classes based on dataclass schemas,
with validation and serialization capabilities.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

from eyconf.generate_yaml import dataclass_to_yaml
from eyconf.type_utils import get_type_hints_resolve_namespace
from eyconf.utils import (
    AttributeDict,
    dataclass_from_dict,
)
from eyconf.validation import to_json_schema, validate_json

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")

log = logging.getLogger(__name__)


class EYConfBase(Generic[D]):
    """Base class for EYconf.

    Can be used to create custom configuration classes in memory without file I/O.
    """

    _schema: type[D]
    _data: D
    _json_schema: dict

    def __init__(
        self,
        data: dict | D,
        schema: type[D] | None = None,
        allow_additional_properties: bool = False,
    ):
        if schema is not None:
            self._schema = schema
        else:
            if not is_dataclass(data):
                raise ValueError(
                    "If no schema is provided, data must be of the schema dataclass instance."
                )
            self._schema = type(data)

        # Create schema, raise if Schema is invalid
        self._json_schema = to_json_schema(
            self._schema,
            allow_additional=allow_additional_properties,
        )

        # Will raise ConfigurationError if the data does not comply with the schema
        validate_json(data, self._json_schema)
        if is_dataclass(data):
            self._data = data
        else:
            self._data = self._schema()  # type: ignore[bad-assignment]
            self.update(data)

    def validate(self):
        """Validate the current data against the schema."""
        validate_json(self._data, self._json_schema)

    def update(self, data: dict):
        """Update the configuration with provided data.

        This applies an partial update to the existing configuration data.
        Only the provided keys will be updated, others will remain unchanged.
        """

        def _update(
            target_type: type[DataclassInstance],
            target: DataclassInstance,
            update_data: dict,
        ):
            target_annotations = get_type_hints_resolve_namespace(target_type)

            for key, value in update_data.items():
                if hasattr(target, key):
                    current_value = getattr(target, key)

                    # Handle dataclass fields
                    if is_dataclass(current_value):
                        _update(
                            target_annotations[key],
                            current_value,  # type: ignore[arg-type]
                            value,
                        )
                    # Handle Optional fields that were previously None
                    elif current_value is None and isinstance(value, dict):
                        nested_instance = dataclass_from_dict(
                            target_annotations[key], value
                        )
                        setattr(target, key, nested_instance)
                    else:
                        # Primitives and direct assignments
                        setattr(target, key, value)
                else:
                    # Non-schema fields (EYConfAdditional)
                    if isinstance(value, dict):
                        setattr(target, key, AttributeDict(**value))
                    else:
                        setattr(target, key, value)

        old_data = deepcopy(self._data)
        update_dict = data if not is_dataclass(data) else asdict(data)

        _update(self._schema, self._data, update_dict)

        try:
            self.validate()
        except Exception as e:
            self._data = old_data
            raise e from e

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

    def default_yaml(self) -> str:
        """Return the configs' defaults (inferred from schema) as yaml.

        You may overwrite this method to customize the default configuration
        generation.
        """
        return dataclass_to_yaml(self._schema)

    def to_dict(self, include_additional: bool = False) -> dict:
        """Convert the configuration data to a dictionary.

        Parameters
        ----------
        include_additional : bool
            Whether to include extra data not part of the schema.
        """
        if include_additional:
            # A bit hacky but works for now
            return json.loads(json.dumps(self._data, default=lambda o: o.__dict__))
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
