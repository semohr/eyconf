"""Configuration class for easy configuration management."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

import yaml

from eyconf.type_utils import get_type_hints_resolve_namespace

from .generate_yaml import dataclass_to_yaml
from .validation import to_json_schema, validate

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")

log = logging.getLogger(__name__)

__all__ = [
    "EYConf",
]


class EYConf(Generic[D]):
    """Configuration class.

    This class is used to generate a default configuration file from a schema
    represented by a dataclass.

    It allows to generate, validate and load a configuration file.
    """

    path: Path
    _schema: type[D]
    _data: D
    _json_schema: dict

    def __init__(
        self,
        schema: type[D],
    ):
        self.path = self.get_file()
        # At the moment we only support dataclass classes
        if not is_dataclass(schema) or not isinstance(schema, type):
            raise ValueError(
                "Schema must be a dataclass class. Instances are not supported yet."
            )
        self._schema = schema

        # Generate default configuration if it does not exist
        if not self.path.exists():
            self._write_default()

        # Create schema
        self._json_schema = to_json_schema(self._schema)

        # Load the configuration file
        self._data = self._load()

    def default_yaml(self) -> str:
        """Return the default yaml configuration as string.

        You may overwrite this method to customize the default configuration
        generation.
        """
        return dataclass_to_yaml(self._schema)

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

    def _load(self) -> D:
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
        validate(data, self._json_schema)

        return cast(D, dataclass_from_dict(self._schema, data))

    def refresh(self):
        """Reload the configuration file."""
        self._data = self._load()

    def __getattr__(self, key: str):
        """Get an item from the configuration."""
        return getattr(self._data, key)

    def __repr__(self) -> str:
        """Return a custom string representation of the configuration object."""
        class_name = type(self).__name__
        memory_address = hex(id(self))
        prefix = f"<{class_name} object at {memory_address} loaded from {self.path.absolute()}>:\n"

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

    @staticmethod
    def get_file() -> Path:
        """Get the path to the configuration file."""
        return (
            Path(os.environ.get("EYCONF_CONFIG_FILE", "./config.yaml"))
            .expanduser()
            .resolve()
        )


def dataclass_from_dict(in_type, data: dict):
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
        field_types = get_type_hints_resolve_namespace(in_type, include_extras=False)
        return in_type(
            **{f: dataclass_from_dict(field_types[f], data[f]) for f in data}
        )

    if isinstance(data, (tuple, list)):
        return [dataclass_from_dict(in_type.__args__[0], f) for f in data]

    return data
