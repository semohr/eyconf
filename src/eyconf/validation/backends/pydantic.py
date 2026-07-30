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
    """Pydantic validation backend.

    Uses :class:`pydantic.TypeAdapter` for runtime validation and JSON Schema
    generation from dataclass types. Supports optional allowance of extra
    fields not defined in the schema.

    Parameters
    ----------
    allow_additional : bool, optional
        If ``True``, extra fields present in the data but not declared on the
        schema are permitted. Defaults to ``False``.
    """

    allow_additional = False

    def __init__(self, allow_additional: bool = False) -> None:
        """Initialize the Pydantic validator.

        Parameters
        ----------
        allow_additional : bool, optional
            Whether extra fields outside the schema are allowed.
        """
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
        """Generate a JSON Schema for the given dataclass type.

        Parameters
        ----------
        schema : type[D]
            The dataclass type to derive a JSON Schema from.
        check_schema : bool, optional
            Whether to validate the generated schema. Defaults to ``True``.

        Returns
        -------
        JsonSchema
            JSON Schema dictionary representing the type.
        """
        return self._adapter(schema, self.allow_additional).json_schema(
            schema_generator=CustomGenerateJsonSchema,
        )

    def validate(self, data: dict[str, Any] | D, schema: type[D]) -> None:
        """Validate data against a dataclass schema.

        Parameters
        ----------
        data : dict[str, Any] | D
            The input data to validate, either as a dict or an existing
            dataclass instance.
        schema : type[D]
            The target dataclass type defining the expected shape.

        Raises
        ------
        ConfigurationError
            If validation fails.

        Notes
        -----
        Validation is performed via :meth:`pydantic.TypeAdapter.validate_python`.
        Extra fields are rejected unless ``allow_additional`` was set at init.
        """
        adapter = self._adapter(schema, self.allow_additional)
        try:
            adapter.validate_python(data)
        except ValidationError as e:
            raise to_ConfigurationError(e)

    def validate_and_construct(self, data: D | dict[str, Any], schema: type[D]) -> D:
        """Validate and construct a dataclass instance from raw data.

        Unlike the default :class:`Validator` implementation that delegates to
        :func:`dataclass_from_dict`, this method lets Pydantic perform both
        validation and construction in a single pass.

        Parameters
        ----------
        data : D | dict[str, Any]
            The input data, either as a dict or an existing dataclass instance.
        schema : type[D]
            The target dataclass type to construct.

        Returns
        -------
        D
            A fully validated instance of ``schema``.

        Raises
        ------
        ConfigurationError
            If validation or construction fails.
        """
        adapter = self._adapter(schema, self.allow_additional)
        try:
            return adapter.validate_python(data)
        except ValidationError as e:
            raise to_ConfigurationError(e)


class CustomGenerateJsonSchema(GenerateJsonSchema):
    """Custom JSON Schema generator.

    Raises errors for unsupported types and transforms some outputs to unify output between backends.

    See https://docs.pydantic.dev/latest/concepts/json_schema/#customizing-the-json-schema-generation-process
    """

    def bytes_schema(self, schema: core_schema.BytesSchema) -> JsonSchemaValue:
        """Generate JSON Schema for a bytes field.

        Parameters
        ----------
        schema : core_schema.BytesSchema
            The Pydantic core schema for a bytes field.

        Returns
        -------
        JsonSchemaValue
            Never returns; always raises.

        Raises
        ------
        ValueError
            Bytes fields are unsupported in JSON Schema / OpenAPI.
        """
        raise ValueError(
            "Bytes fields are not supported in JSON Schema / OpenAPI. "
            "The 'bytes' type cannot be consistently represented."
        )

    def dict_schema(self, schema: core_schema.DictSchema) -> JsonSchemaValue:
        """Generate JSON Schema for a dict field.

        Enforces that only string-keyed dicts are supported, as JSON Schema
        cannot represent non-string keys.

        Parameters
        ----------
        schema : core_schema.DictSchema
            The Pydantic core schema for a dict field.

        Returns
        -------
        JsonSchemaValue
            The generated JSON Schema fragment.

        Raises
        ------
        ValueError
            If the dict has non-string keys.
        """
        keys_schema = schema.get("keys_schema", {})
        if (
            isinstance(keys_schema, dict)
            and keys_schema.get("type") not in ("str", "string", None)
            and "$ref" not in keys_schema
        ):
            raise ValueError(
                "Only string keys are supported in dict types, "
                f"got {keys_schema.get('type', 'unknown')!r}"
            )
        return super().dict_schema(schema)

    def literal_schema(self, schema: core_schema.LiteralSchema) -> JsonSchemaValue:
        """Generate JSON Schema for a literal field.

        Rejects bytes literals, which cannot be represented in JSON Schema.

        Parameters
        ----------
        schema : core_schema.LiteralSchema
            The Pydantic core schema for a literal field.

        Returns
        -------
        JsonSchemaValue
            The generated JSON Schema fragment.

        Raises
        ------
        ValueError
            If any literal value is of type :class:`bytes`.
        """
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
    """Convert Pydantic validation errors into domain configuration errors.

    Maps Pydantic's :class:`pydantic.ValidationError` (or a list of them)
    into the project's :class:`ConfigurationError` or
    :class:`MultiConfigurationError` for consistent error handling.

    Parameters
    ----------
    error : ValidationError | list[ValidationError]
        One or more Pydantic validation errors to convert.

    Returns
    -------
    ConfigurationError | MultiConfigurationError
        The corresponding domain-level error(s).
    """
    return ConfigurationError("TODO")
