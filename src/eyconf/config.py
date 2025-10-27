"""Configuration class for easy configuration management."""

from __future__ import annotations

import logging
import os
from copy import deepcopy
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

import yaml

from eyconf.utils import (
    AccessProxy,
    AttributeDict,
    dataclass_from_dict,
)

from .generate_yaml import dataclass_to_yaml
from .validation import to_json_schema, validate_json

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")
DA = TypeVar("DA", bound="DataclassInstance")

log = logging.getLogger(__name__)

__all__ = [
    "EYConf",
    "EYConfBase",
]


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
        self._data = self._schema(**data) if not is_dataclass(data) else data

    def validate(self):
        """Validate the current data against the schema."""
        validate_json(self._data, self._json_schema)

    def update(self, data: dict | D):
        def _update(st: type[DataclassInstance], di: DataclassInstance, ud: dict):
            s_keys = set(st.__dataclass_fields__.keys())
            d_keys = set(di.__dataclass_fields__.keys())
            d_keys = set([k for k in d_keys if hasattr(di, k)])
            u_keys = set(ud.keys())

            for key in u_keys:
                if key in d_keys:
                    # easy, update recursively
                    if is_dataclass(getattr(di, key)):
                        _update(
                            st.__annotations__[key],
                            getattr(di, key),
                            ud[key],
                        )
                    elif getattr(di, key) is None and isinstance(ud[key], dict):
                        # Optional field was previously not populated
                        nested_instance = dataclass_from_dict(
                            st.__annotations__[key], ud[key]
                        )
                        setattr(di, key, nested_instance)
                    else:
                        # Primitives
                        setattr(di, key, ud[key])
                else:
                    # can only happen for non-schema fields
                    # i.e. in EYConfAdditional
                    # breakpoint()
                    if isinstance(ud[key], dict):
                        setattr(di, key, AttributeDict(**ud[key]))
                    else:
                        # Primitives
                        setattr(di, key, ud[key])

        old_data = deepcopy(self._data)
        _update(
            self._schema, self._data, data if not is_dataclass(data) else asdict(data)
        )
        try:
            self.validate()
        except Exception as e:
            self._data = old_data
            raise e from e

    def overwrite(self, data: dict | D):
        """
        Set all keys from provided data.

        Keys missing in new provided data, but present in old will be lost.
        """
        data = asdict(data) if is_dataclass(data) else data
        validate_json(data, self._json_schema)
        self._data = dataclass_from_dict(self._schema, data)

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
        result = []
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(" " * indent + f"{key}:")
                result.append(self._pretty_format(value, indent + 4))
            else:
                result.append(" " * indent + f"{key}: {value}")
        return "\n".join(result)


"""
config._data
config._additional_data

config.data
-> _data
-> _additional_data
-> type : D
"""


class EYConfAdditional(EYConfBase[D]):
    _extra_data: AttributeDict

    def __init__(
        self,
        data: dict | D,
        schema: type[D] | None = None,
    ):
        super().__init__(data, schema=schema)
        self._extra_data = AttributeDict()

    @property
    def data(self) -> D:
        """Get the configuration data wrapped in a dynamic accessor."""
        return AccessProxy(self._data, self._extra_data)  # type: ignore

    @property
    def schema_data_as_dict(self) -> dict:
        """Get all attributes that are part of the original schema."""
        return asdict(self._data)

    @property
    def extra_data_as_dict(self) -> dict:
        """Get all attributes that are not part of the original schema."""
        # We use __dict__ here to include dynamically added attributes
        # asdict only considers defined dataclass fields
        return self._extra_data.as_dict()


class EYConf(EYConfBase[D]):
    """Configuration class.

    This class is used to generate a default configuration file from a schema
    represented by a dataclass.

    It allows to generate, validate and load a configuration file.
    """

    path: Path

    def __init__(
        self,
        schema: type[D],
    ):
        if not is_dataclass(schema) or not isinstance(schema, type):
            raise ValueError(
                "Schema must be a dataclass class. Instances are not supported yet."
            )
        self.path = self.get_file()

        # Generate default configuration if it does not exist
        self._schema = schema
        self._json_schema = to_json_schema(self._schema)
        if not self.path.exists():
            try:
                self._data = schema()
            except TypeError:
                log.exception(
                    "Schema dataclass has required fields without defaults. Consider using field with default_factory in your schema."
                )
                raise
            self._write_default()
        else:
            self._data = self._load_and_validate()

    @staticmethod
    def get_file() -> Path:
        """Get the path to the configuration file."""
        return (
            Path(os.environ.get("EYCONF_CONFIG_FILE", "./config.yaml"))
            .expanduser()
            .resolve()
        )

    def refresh(self):
        """Reload the configuration file."""
        self._data = self._load_and_validate()

    def __repr__(self) -> str:
        """Return a custom string representation of the configuration object."""
        class_name = type(self).__name__
        memory_address = hex(id(self))
        prefix = f"<{class_name} object at {memory_address} loaded from {self.path.absolute()}>:\n"

        return f"{prefix}{self.__str__()}"

    # ------------------ Helpers for file generation and loading ----------------- #

    def _write_default(self):
        """Generate default yaml configuration."""
        if self.path.exists():
            log.warning(f"Configuration file {self.path} already exists. Overwriting!")

        yaml_str = self.default_yaml()
        os.makedirs(self.path.parent, exist_ok=True)
        with open(self.path, "w") as f:
            f.write(yaml_str)
            f.write("\n")  # Add a newline at the end of the file
        log.info(f"Configuration file created at '{self.path.absolute()}'")

    def _load_and_validate(self) -> D:
        """Load the configuration file and validate it against the schema."""
        log.info(f"Loading config file: {self.path.absolute()}")

        if not self.path.exists():
            raise FileNotFoundError(
                f"Configuration file '{self.path.absolute()}' not found. Please generate with `write_default()`."
            )

        # Load the config file
        with open(self.path, "r") as file:
            data = yaml.safe_load(file)

        # Will raise ConfigurationError if the data does not comply with the schema
        validate_json(data, self._json_schema)

        return dataclass_from_dict(self._schema, data)
