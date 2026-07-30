import logging
from enum import Enum
from functools import cache
from typing import Any

from pydantic import TypeAdapter, ValidationError
from pydantic.config import ConfigDict
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from eyconf.validation.exceptions import ConfigurationError, MultiConfigurationError

from .interface import D, JsonSchema, Validator

log = logging.getLogger(__name__)


class PydanticValidator(Validator[D]):
    """Pydantic vlidation backend."""

    allow_additional = False

    def __init__(self, allow_additional: bool = False) -> None:
        self.allow_additional = allow_additional

    @staticmethod
    @cache
    def _adapter(schema: type[D], allow_additional: bool):
        # https://pydantic.dev/docs/validation/latest/errors/usage_errors/#type-adapter-config-unused
        setattr(
            schema,
            "__pydantic_config__",
            ConfigDict(extra="allow" if allow_additional else "forbid"),
        )
        return TypeAdapter(schema)

    @cache
    def to_json_schema(self, schema: type[D], check_schema: bool = True) -> JsonSchema:
        return self._adapter(schema, self.allow_additional).json_schema(
            schema_generator=CustomGenerateJsonSchema,
        )

    def validate(self, data: dict[str, Any] | D, schema: type[D]) -> None:
        adapter = self._adapter(schema, self.allow_additional)
        try:
            adapter.validate_python(data)
        except ValidationError as e:
            raise to_ConfigurationError(e)

    def validate_and_construct(self, data: D | dict[str, Any], schema: type[D]) -> D:
        adapter = self._adapter(schema, self.allow_additional)
        try:
            return adapter.validate_python(data)
        except ValidationError as e:
            raise to_ConfigurationError(e)


class CustomGenerateJsonSchema(GenerateJsonSchema):
    """
    Allows to customize the JSON Schema generation process. We do this to unify the behavior of Pydantic with our other validation backends, and to raise errors for unsupported types (like bytes).

    See https://pydantic.dev/docs/validation/latest/concepts/json_schema/#customizing-the-json-schema-generation-process
    """

    def bytes_schema(self, schema: core_schema.BytesSchema) -> JsonSchemaValue:
        raise ValueError(
            "Bytes fields are not supported in JSON Schema / OpenAPI. "
            "The 'bytes' type cannot be consistently represented."
        )

    def literal_schema(self, schema: core_schema.LiteralSchema) -> JsonSchemaValue:
        for v in schema["expected"]:
            # Enum values wrap in the enum type; extract the raw value for the check
            inner = v.value if isinstance(v, Enum) else v
            if isinstance(inner, bytes):
                raise ValueError(
                    "Bytes literals are not supported in JSON Schema / OpenAPI. "
                    "Literal bytes values cannot be consistently represented."
                )
        return super().literal_schema(schema)


def to_ConfigurationError(
    error: ValidationError | list[ValidationError],
) -> ConfigurationError | MultiConfigurationError:
    """Create a ConfigurationError from a ValidationError or a list of ValidationErrors."""
    return ConfigurationError("TODO")
