import json
import logging
from collections.abc import Sequence
from dataclasses import is_dataclass
from functools import cache
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    ClassVar,
    Literal,
    Union,
    cast,
    get_args,
    get_origin,
)

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035  # noqa: UP035

from jsonschema import Draft202012Validator, ValidationError
from typing_extensions import NotRequired

from eyconf.asdict import asdict_with_aliases
from eyconf.constants import primitive_type_mapping
from eyconf.decorators import marked_as_allow_additional
from eyconf.type_utils import get_type_hints_resolve_namespace, is_dataclass_type
from eyconf.utils import metadata_fields_from_dataclass
from eyconf.validation import (
    ConfigurationError,
    MultiConfigurationError,
)

from .interface import D, JsonSchema, Validator

log = logging.getLogger(__name__)


class JsonSchemaValidator(Validator[D]):
    """JSON Schema validation backend for dataclass schemas using Draft 2020-12.

    Features full support for Annotated, Literal, NotRequired, Unions, nested
    dataclasses, aliases via metadata, and Sequence types. Cached schema generation.
    """

    allow_additional = False

    def __init__(self, allow_additional: bool = False) -> None:
        self.allow_additional = allow_additional

    @cache
    def to_json_schema(
        self,
        schema: type[D],
        check_schema: bool = True,
    ) -> JsonSchema:
        """Convert TypedDict/dataclass to JSON Schema.

        Parameters
        ----------
        schema : type[D]
            Dataclass/TypedDict type to convert.
        check_schema : bool, default=True
            Validate schema with Draft202012Validator.
        allow_additional : bool or None, default=None
            TODO: Allow extra properties; uses `__allow_additional__` if None.

        Returns
        -------
        JsonSchema
            Draft-2020-12 compliant schema.

        Raises
        ------
        ValueError
            Unsupported types (non-str dict keys, etc.).
        jsonschema.SchemaError
            Invalid generated schema.

        Notes
        -----
        Cached for repeated calls.
        """
        json_schema, _ = self._build_schema(schema)
        if check_schema:
            Draft202012Validator.check_schema(json_schema)

        return json_schema

    def validate(self, data: D | dict[str, Any], schema: type[D]) -> None:
        """**Protocol match**: Validate data against schema-derived JSON Schema."""
        if is_dataclass_type(schema):
            json_schema = self.to_json_schema(schema)
        else:
            json_schema = cast(JsonSchema, schema)
        if is_dataclass(data):
            data = asdict_with_aliases(data)
        self._validate_dict(data, json_schema)

    def _validate_dict(self, data: dict[str, Any], json_schema: JsonSchema):
        schema = self._allow_none_in_schema(json_schema)
        validator = Draft202012Validator(schema)  # type: ignore[bad-instantiation]

        errors = list(validator.iter_errors(data))
        if errors:
            log.error("Validation errors in configuration data!")
            log.debug(f"Data: {json.dumps(data, indent=2)}")
            log.debug(f"Schema: {json.dumps(schema, indent=2)}")
            raise to_ConfigurationError(errors)

    def _allow_none_in_schema(
        self,
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
            for _, value in schema.items():
                if isinstance(value, (dict, list)):
                    self._allow_none_in_schema(value)

        elif isinstance(schema, list):
            for item in schema:
                self._allow_none_in_schema(item)

        return cast(dict, schema)

    def _build_schema(
        self,
        type_: type,
    ) -> tuple[JsonSchema, bool]:
        r"""Recursive type/dataclass to schema builder → (schema, is_required)."""
        is_required = True

        # Unpack annotated types
        origin = get_origin(type_)
        if origin is Annotated:
            # We always assume the first argument is the type
            # all other arguments are metadata (docstrings)
            return self._build_schema(get_args(type_)[0])

        # Literal
        if origin is Literal:
            values = get_args(type_)
            return {
                "type": self._infer_type_from_values(values),
                "enum": list(values),
            }, is_required

        # NotRequired
        if origin is NotRequired:
            schema, _ = self._build_schema(get_args(type_)[0])
            return schema, False

        # Unions
        if origin in (UnionType, Union):
            types_ = list(get_args(type_))
            if NoneType in types_:
                is_required = False
                types_.remove(NoneType)
            if len(types_) == 1:
                t, _ = self._build_schema(types_[0])
                return t, is_required
            return {"anyOf": [self._build_schema(t)[0] for t in types_]}, is_required

        # Sequence types
        if origin in [list, set, tuple, Sequence, TypingSequence]:
            item_schema, _ = self._build_schema(get_args(type_)[0])
            return {"type": "array", "items": item_schema}, is_required

        # TypedDict and dataclasses
        try:
            is_dict_subclass = issubclass(type_, dict)
        except TypeError:
            is_dict_subclass = False
        if is_dict_subclass or is_dataclass(type_):
            marked_allow_additional = marked_as_allow_additional(type_)
            json_schema: JsonSchema = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": marked_allow_additional
                if marked_allow_additional is not None
                else self.allow_additional,
            }
            hints = get_type_hints_resolve_namespace(type_, include_extras=True)
            metadata = metadata_fields_from_dataclass(type_)

            for field, ftype in hints.items():
                if get_origin(ftype) is ClassVar:
                    continue
                if alias := metadata.get(field, {}).get("alias"):
                    field = alias  # Note: alias applied here

                prop_schema, prop_required = self._build_schema(ftype)
                json_schema["properties"][field] = prop_schema
                if prop_required:
                    json_schema["required"].append(field)

            return json_schema, is_required

        # Dicts - arbitrary keys with typed values
        if origin is dict:
            key_type, value_type = get_args(type_)
            if key_type is not str:
                raise ValueError("Only string keys are supported in dict types")
            value_schema, _ = self._build_schema(value_type)
            return {
                "type": "object",
                "patternProperties": {"^.*$": value_schema},
            }, is_required

        # Primitives
        match = primitive_type_mapping.get(type_)
        if match:
            return {"type": match}, is_required
        if type_ is Any:
            return {}, is_required

        raise ValueError(f"Unsupported type: {type_}")

    def _infer_type_from_values(self, values: tuple | list) -> str | list[str]:
        r"""Infer JSON type(s) from Literal values (your helper)."""
        types = {type(v) for v in values}
        type_names = sorted(
            [primitive_type_mapping[t] for t in types if t in primitive_type_mapping]
        )
        return type_names[0] if len(type_names) == 1 else type_names


def to_ConfigurationError(
    error: ValidationError | list[ValidationError],
) -> ConfigurationError | MultiConfigurationError:
    """Create a ConfigurationError from a ValidationError or a list of ValidationErrors."""
    if isinstance(error, list):
        errors = []
        for e in error:
            path = [str(p) for p in e.path]
            errors.append(ConfigurationError(e.message, ".".join(path)))
        return MultiConfigurationError(errors)
    else:
        return ConfigurationError(error.message, str(error.path))
