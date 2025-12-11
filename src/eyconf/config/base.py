"""Configuration base classes for EYconf.

Allows to create configuration classes based on dataclass schemas,
with validation and serialization capabilities.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    cast,
)

from eyconf.asdict import asdict_with_aliases
from eyconf.generate_yaml import dataclass_to_yaml
from eyconf.type_utils import (
    get_type_hints_resolve_namespace,
    is_dataclass_instance,
    is_dataclass_type,
)
from eyconf.utils import dataclass_from_dict, dict_items_resolve_aliases
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

    def update(self, data: dict[str, Any]):
        """Update the configuration with provided data.

        This applies an partial update to the existing configuration data.
        Only the provided keys will be updated, others will remain unchanged.
        """

        def _update(
            target_type: type[DataclassInstance],
            target: DataclassInstance,
            update_data: dict[str, Any],
            path: list[tuple[DataclassInstance, str]] | None = None,
        ):
            """Recursive update helper function.

            Parameters
            ----------
            target_type : type[DataclassInstance]
                The dataclass type of the target instance.
            target : DataclassInstance
                The dataclass instance to update.
            update_data : dict
                The update data to apply.
            path : list[tuple[DataclassInstance, str]] | None
                The current path in the dataclass tree (root-to-leaf).
                [0] is parent instance,
                [1] is attr key used to access the target from from its parent. E.g.
                [(root_instance, "child_field"), (child_instance, "grandchild_field")]
            """
            target_annotations = get_type_hints_resolve_namespace(target_type)

            for key, value in dict_items_resolve_aliases(update_data, target_type):
                if hasattr(target, key):
                    current_value = getattr(target, key)

                    # Handle dataclass fields
                    if is_dataclass_instance(current_value):
                        _update(
                            target_annotations[key],
                            current_value,
                            value,
                            path=(path or []) + [(target, key)],
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
                        # Can only be reached if a dynamic field is added
                        # to the dataclass instance
                        setattr(target, key, value)
                else:
                    # Non-schema fields
                    self._update_additional(
                        value,
                        path=(path or []) + [(target, key)],
                    )

        old_data = deepcopy(self._data)
        _update(self._schema, self._data, data)

        try:
            self.validate()
        except Exception:
            self._data = old_data
            raise

    def _update_additional(
        self,
        value: Any,
        path: list[tuple[DataclassInstance, str]],
    ) -> None:
        """Handle updating additional (non-schema) fields.

        Can be overwritten in subclasses.
        """
        target, attr_key = path[-1]
        root_name = type(path[0][0]).__name__
        path_str = f"{root_name}" + "".join(f".{attr}" for _, attr in path)
        raise AttributeError(
            f"Cannot set non-schema field '{attr_key}' "
            f"on dataclass '{type(target).__name__}'!"
            f"\n(at {path_str})"
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
        return asdict_with_aliases(self._data)

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
