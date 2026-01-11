from __future__ import annotations

import json
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, TypeVar, cast

from jsonschema import Draft202012Validator

from eyconf.asdict import asdict_with_aliases
from eyconf.type_utils import is_dataclass_type
from eyconf.validation import log
from eyconf.validation._to_json import to_json_schema
from eyconf.validation.exceptions import ConfigurationError

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    D = TypeVar("D", bound="DataclassInstance")


def _allow_none_in_schema(
    schema: dict | list,
) -> dict:  # -> dict[Any, Any] | list[Any]:
    """
    Recursively modifies a JSON schema to allow `null` values for all fields.

    This is needed to parse Optional fields that hold dataclasses. May need a revisit later.
    """
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
                _allow_none_in_schema(value)

    elif isinstance(schema, list):
        for item in schema:
            _allow_none_in_schema(item)

    return cast(dict, schema)


def validate_json(data: dict, schema: dict) -> None:
    """Validate the provided data against the given schema.

    This function uses the Draft202012Validator to check if the data
    conforms to the specified schema. If there are any validation errors,
    it raises a ConfigurationError containing the details of the errors.

    Parameters
    ----------
    data (dict):
        The data to be validated.
        Whether or not additional fields are allowed is controlled by the schema.
    schema (dict):
        The JSON schema to validate against.

    Raises
    ------
    ConfigurationError: If the data does not comply with the schema,
                          this error is raised with details of the violations.
    """
    schema = _allow_none_in_schema(schema)
    validator = Draft202012Validator(schema)  # type: ignore[bad-instantiation]

    errors = list(validator.iter_errors(data))
    if errors:
        log.error("Validation errors in configuration data!")
        log.debug(f"Data: {json.dumps(data, indent=2)}")
        log.debug(f"Schema: {json.dumps(schema, indent=2)}")
        raise ConfigurationError.from_ValidationErrors(errors)


def validate(data: D | dict, schema: type[D] | dict) -> None:
    """Validate the provided data against the schema and return the dataclass instance.

    This function first converts the schema dataclass to a JSON schema using
    `to_json_schema`, then validates the provided data against this schema
    using `validate_json`. If validation is successful, it returns an instance
    of the schema dataclass populated with the validated data.

    For more controls over validation, consider using `to_json_schema` and `validate_json`.

    Parameters
    ----------
    data (D | dict):
        The data to be validated, either as a dictionary or an instance of the schema dataclass.
    schema (type[D] | dict):
        The dataclass type representing the schema to validate against.

    Returns
    -------
    D
        An instance of the schema dataclass populated with the validated data.

    Raises
    ------
    ConfigurationError: If the data does not comply with the schema,
        this error is raised with details of the violations.
    """
    if is_dataclass_type(schema):
        json_schema = to_json_schema(schema)
    else:
        json_schema = cast(dict, schema)

    if is_dataclass(data):
        data = asdict_with_aliases(data)

    validate_json(data, json_schema)
