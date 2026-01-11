"""Default file-based configuration class.

Allows to generate, validate and load a yaml configuration file based
on a dataclass schema.
"""

from __future__ import annotations

import logging
import os
from dataclasses import is_dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    TypeVar,
)

import yaml

from eyconf.asdict import asdict_with_aliases
from eyconf.utils import (
    dataclass_from_dict,
    merge_dicts,
)
from eyconf.validation import to_json_schema, validate_json

from .base import Config, dataclass_to_yaml

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")

log = logging.getLogger(__name__)


class EYConf(Config[D]):
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

    def reset(self):
        """Reset the configuration file to the default values.

        This will overwrite the existing configuration file!
        """
        self._write_default()
        self._data = self._load_and_validate()

    def reload(self):
        """Reload the configuration by reloading and validating the file."""
        self._data = self._load_and_validate()

    def __repr__(self) -> str:
        """Return a custom string representation of the configuration object."""
        class_name = type(self).__name__
        memory_address = hex(id(self))
        prefix = f"<{class_name} object at {memory_address} loaded from {self.path.absolute()}>:\n"

        return f"{prefix}{self.__str__()}"

    # ------------------ Helpers for file generation and loading ----------------- #

    def default_yaml(self) -> str:
        """Return the configs' defaults (inferred from schema) as yaml.

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

    def _load_and_validate(self) -> D:
        """Load the configuration file and validate it against the schema."""
        log.info(f"Loading config file: {self.path.absolute()}")

        if not self.path.exists():
            raise FileNotFoundError(
                f"Configuration file '{self.path.absolute()}' not found. Please generate with `write_default()`."
            )

        # We load the schema first to allow for sane default merging
        # -> Load defaults, then merge with file contents
        data: dict = asdict_with_aliases(self._schema())
        with open(self.path) as file:
            data = merge_dicts(data, yaml.safe_load(file), priority="b")

        # Will raise ConfigurationError if the data does not comply with the schema
        validate_json(data, self._json_schema)

        return dataclass_from_dict(self._schema, data)
