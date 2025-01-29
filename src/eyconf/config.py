from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import yaml

from .generate_yaml import dataclass_to_yaml
from .validate import to_json_schema, validate

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
        path: str | Path,
    ):

        if isinstance(path, str):
            path = Path(path)
        self.path = path

        # At the moment we only support dataclass classes
        if not is_dataclass(schema) or not isinstance(schema, type):
            raise ValueError(
                "Schema must be a dataclass class. Instances are not supported yet."
            )
        self._schema = schema

        # Generate default configuration if it does not exist
        if not self.path.exists():
            self.write_default()

        # Create schema
        self._json_schema = to_json_schema(self._schema)

        # Load the configuration file
        self._data = self._load()
        print(self._data)

    def write_default(self):
        """Generate default yaml configuration."""
        if self.path.exists():
            log.warning(f"Configuration file {self.path} already exists. Overwriting!")

        yaml_str = dataclass_to_yaml(self._schema)
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

    def __str__(self):
        """Return a custom formatted string representation of the configuration data."""
        data_dict = asdict(self._data)
        class_name = type(self).__name__
        memory_address = hex(id(self))
        prefix = f"<{class_name} object at {memory_address} loaded from {self.path.absolute()}>:\n"
        s = "\n".join(
            "  " + line for line in self._pretty_format(data_dict).splitlines()
        )
        return f"{prefix}{s}"

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

    __repr__ = __str__  # Use the same formatted string for repr, if desired


def dataclass_from_dict(klass, dikt):
    try:
        fieldtypes = klass.__annotations__
        return klass(**{f: dataclass_from_dict(fieldtypes[f], dikt[f]) for f in dikt})
    except AttributeError:
        if isinstance(dikt, (tuple, list)):
            return [dataclass_from_dict(klass.__args__[0], f) for f in dikt]
        return dikt
