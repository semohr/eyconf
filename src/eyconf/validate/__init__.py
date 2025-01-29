from __future__ import annotations

import logging
from typing import cast

log = logging.getLogger(__name__)


from jsonschema import Draft202012Validator, ValidationError

from ._to_json import to_json_schema

__all__ = [
    "to_json_schema",
    "validate",
    "ConfigurationError",
    "MultiConfigurationError",
]


def validate(data: dict, schema: dict) -> None:
    """Validate the provided data against the given JSON schema.

    This function uses the Draft202012Validator to check if the data
    conforms to the specified schema. If there are any validation errors,
    it raises a ConfigurationError containing the details of the errors.

    Parameters
    ----------
    - data (dict): The data to be validated.
    - schema (dict): The JSON schema to validate against.

    Raises
    ------
    - ConfigurationError: If the data does not comply with the schema,
                          this error is raised with details of the violations.
    """
    schema = allow_none_in_schema(schema)
    validator = Draft202012Validator(schema)

    errors = list(validator.iter_errors(data))
    if errors:
        import json

        log.error("Validation errors in configuration data!")
        log.debug(f"Data: {data}")
        log.debug(f"Schema: {json.dumps(schema, indent=2)}")
        raise ConfigurationError.from_ValidationErrors(errors)


def allow_none_in_schema(schema: dict | list) -> dict:  # -> dict[Any, Any] | list[Any]:
    """Recursively modifies a JSON schema to allow `null` values for all fields."""
    if isinstance(schema, dict):
        # If current schema block has "type"
        if "type" in schema:
            # If the type is a list of types, add 'null' if it's not already present
            if isinstance(schema["type"], list):
                if "null" not in schema["type"]:
                    schema["type"].append("null")
            else:
                # Else, make it a list with the current type and 'null'
                schema["type"] = [schema["type"], "null"]

        # Recursively process properties in objects
        for key, value in schema.items():
            if isinstance(value, (dict, list)):
                allow_none_in_schema(value)

    elif isinstance(schema, list):
        for item in schema:
            allow_none_in_schema(item)

    return cast(dict, schema)


class ConfigurationError(Exception):
    """Exception raised for configuration validation errors."""

    def __init__(self, message="Configuration error", section=None):
        self.message = message
        self.section = section
        super().__init__(self.message)

    def __str__(self):
        """Return the error message."""
        return (
            f"{self.message} in section '{self.section}'"
            if self.section
            else self.message
        )

    @classmethod
    def from_ValidationErrors(cls, error: ValidationError | list[ValidationError]):
        """Create a ConfigurationError from a ValidationError or a list of ValidationErrors."""
        if isinstance(error, list):
            errors = []
            for e in error:
                path = [str(p) for p in e.path]
                errors.append(cls(e.message, ".".join(path)))
            return MultiConfigurationError(errors)
        else:
            return cls(error.message, str(error.path))


class MultiConfigurationError(Exception):
    """Exception raised for multiple configuration validation errors."""

    def __init__(self, errors: list[ConfigurationError]):
        self.errors = errors
        super().__init__("Multiple configuration errors")

    def __str__(self):
        """Return the error message."""
        return "\n".join([str(e) for e in self.errors])
