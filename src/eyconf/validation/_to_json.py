from collections.abc import Sequence
from dataclasses import is_dataclass
from functools import cache
from types import NoneType, UnionType
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035

from jsonschema import Draft202012Validator
from typing_extensions import NotRequired

from eyconf.constants import primitive_type_mapping
from eyconf.decorators import check_allows_additional
from eyconf.type_utils import get_type_hints_resolve_namespace
from eyconf.utils import metadata_fields_from_dataclass

SchemaType = dict[str, Any] | dict[str, str] | dict[Any, Any]


__all__ = ["to_json_schema"]


@cache
def to_json_schema(
    type: type,
    check_schema: bool = True,
    allow_additional: bool | None = None,
) -> dict:
    """Convert a TypedDict or dataclass to a JSON schema.

    Parameters
    ----------
    type : type
        The TypedDict or dataclass to convert.
    check_schema : bool
        Whether to check the schema for validity.
    allow_additional : bool or None
        Whether to allow extra, unrecognized properties in the schema.
        If None (default), uses the `__allow_additional` attribute
        of the TypedDict or dataclass if present, otherwise False.

    Raises
    ------
    ValueError
        If the type is not supported.
    SchemaError
        If the schema is invalid (should not happen).
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": check_allows_additional(type)
        if allow_additional is None
        else allow_additional,
    }

    # Get type hints for the TypedDict
    type_hints = get_type_hints_resolve_namespace(type, include_extras=True)
    fieldname_to_metadata = metadata_fields_from_dataclass(type)
    # Add the type hints to the schema
    for field_name, field_type in type_hints.items():
        if alias := fieldname_to_metadata.get(field_name, {}).get("alias"):
            field_name = alias

        origin = get_origin(field_type)
        if origin is ClassVar:
            # ignore dunder like our __allow_additional
            continue

        p, r = __convert_type_to_schema(field_type, allow_additional=allow_additional)
        schema["properties"][field_name] = p

        # Handle required fields
        if r:
            schema["required"].append(field_name)

    if check_schema:
        Draft202012Validator.check_schema(schema)

    return schema


def __convert_type_to_schema(
    field_type: type,
    **kwargs,
) -> tuple[SchemaType, bool]:
    """
    Convert a type to a JSON schema.

    Parameters
    ----------
    field_type : type
        The type to convert.
    **kwargs : dict
        Passed recusrively and to `to_json_schema()` if called in here.

    Returns
    -------
    schema : dict | None
        The JSON schema. None if the type is not supported or is is resolves to optional none value.
    is_required : bool
        Whether the field is required.
    """
    is_required = True

    origin = get_origin(field_type)

    # Unpack annotated types
    if origin is Annotated:
        # We always assume the first argument is the type
        # all other arguments are metadata (docstrings)
        field_type = get_args(field_type)[0]
        return __convert_type_to_schema(field_type, **kwargs)

    # Handle Literal
    if origin is Literal:
        allowed_values = get_args(field_type)
        return {
            "type": __infer_type_from_values(allowed_values),
            "enum": list(allowed_values),
        }, is_required

    # Handle NotRequired
    if origin is NotRequired:
        field_type = get_args(field_type)[0]
        is_required = False
        return __convert_type_to_schema(field_type, **kwargs)[0], is_required

    # Handler union
    if origin is UnionType or origin is Union:
        allowed_types = set(get_args(field_type))
        if NoneType in allowed_types:
            is_required = False
            allowed_types.remove(NoneType)

        if len(allowed_types) > 1:
            return {
                "anyOf": [
                    __convert_type_to_schema(allowed_type, **kwargs)[0]
                    for allowed_type in allowed_types
                ]
            }, is_required
        else:
            # case length == 1
            # Another case is impossible as Union must have at least one type and
            # get simplified beforehand if it does not Union[int] -> int
            t, _ = __convert_type_to_schema(allowed_types.pop(), **kwargs)
            return t, is_required

    # Handle sequence types
    if origin in [list, set, tuple, Sequence, TypingSequence]:
        return {
            "type": "array",
            "items": __convert_type_to_schema(get_args(field_type)[0], **kwargs)[0],
        }, is_required

    # Handle TypedDict and dataclasses
    try:
        if issubclass(field_type, dict) or is_dataclass(field_type):
            return to_json_schema(field_type, **kwargs), is_required
    except TypeError:
        # Throws an error in case of a type that is not a class
        pass

    # Handle Dicts - arbitrary keys with typed values
    if origin is dict:
        key_type, value_type = get_args(field_type)
        if key_type is not str:
            raise ValueError("Only string keys are supported in dict types")

        return {
            "type": "object",
            "patternProperties": {
                ".*": __convert_type_to_schema(value_type, **kwargs)[0]
            },
        }, is_required

    # Handle other types
    match = primitive_type_mapping.get(field_type)

    if match:
        return {"type": match}, is_required

    if field_type is Any:
        return {}, is_required

    raise ValueError(f"Unsupported type: {field_type}")


def __infer_type_from_values(values: tuple | list):
    types: list[type] = []
    for value in values:
        value_type = type(value)
        if value_type not in types:
            types.append(value_type)

    type_names: list[str] = []
    for t in types:
        if t in primitive_type_mapping:
            type_names.append(primitive_type_mapping[t])
        else:
            raise ValueError(f"Unsupported literal type: {t}")
    if len(type_names) == 1:
        return type_names[0]
    else:
        return type_names
