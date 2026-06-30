"""Defines the common validation interface."""

from abc import abstractmethod
from dataclasses import is_dataclass
from functools import cache
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from eyconf.utils import dataclass_from_dict

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

D = TypeVar("D", bound="DataclassInstance")
JsonSchema = dict[str, Any]


@runtime_checkable
class Validator(Protocol[D]):
    """Protocol for pluggable validation backends supporting dataclass schemas.

    Backends (e.g., JSONSchema, Pydantic) implement this to enable switching
    validation logic in Config classes. Ensures consistent API for schema
    generation, validation, instantiation, and instance checks.
    """

    @cache
    @abstractmethod
    def to_json_schema(self, schema: type[D]) -> JsonSchema:
        """Generate JSON Schema from dataclass type.

        Parameters
        ----------
        schema : type[D]
            Dataclass type to convert to JSON Schema.

        Returns
        -------
        JsonSchema
            JSON Schema dictionary compatible with draft-07+ specs.

        Raises
        ------
        ValueError
            If schema is invalid or unsupported by backend.


        """
        ...

    @abstractmethod
    def validate(self, data: dict[str, Any] | D, schema: type[D]) -> None:
        """Validate raw data against JSON Schema.

        Converts dataclass instances to dicts internally if needed.

        Parameters
        ----------
        data : dict[str, Any] | D
            Input data to validate (dict or dataclass instance).
        json_schema : JsonSchema
            Pre-generated JSON Schema from `to_json_schema`.

        Raises
        ------
        ConfigurationError
            If data fails validation rules.
        MultiConfigurationError
            If multiple validation errors occur.

        Notes
        -----
        Backends may implement custom error types but must be catchable
        by Config's exception handling.
        """
        ...

    def validate_and_construct(self, data: D | dict[str, Any], schema: type[D]) -> D:
        """Create validated dataclass instance from dictionary.

        Validates data against derived JSON Schema before instantiation.

        Parameters
        ----------
        schema : type[D]
            Target dataclass type.
        data : dict[str, Any]
            Dictionary data to populate instance.

        Returns
        -------
        D
            New dataclass instance of type `schema`.

        Raises
        ------
        ConfigurationError
            If data is invalid or incompatible with schema.
        ValueError
            If instantiation fails post-validation.

        Examples
        --------
        >>> schema = MyConfigDataclass
        >>> data = {"field1": "value", "field2": 42}
        >>> validator = JsonSchemaBackend()
        >>> instance = validator.from_dict(schema, data)

        """
        self.validate(data, schema)
        if is_dataclass(data):
            return data
        return dataclass_from_dict(schema, data)
