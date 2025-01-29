from collections.abc import Sequence as ABCSequence
from dataclasses import is_dataclass
from functools import lru_cache
from types import NoneType, UnionType
from typing import (
    Any,
    Dict,
    Literal,
    Sequence,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from jsonschema import Draft202012Validator
from typing_extensions import NotRequired

__all__ = ["to_json_schema", "primitives"]

primitives: dict[type[object], "str"] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


@lru_cache(maxsize=None)
def to_json_schema(type: type, check_schema: bool = True) -> dict:
    """Convert a TypedDict or dataclass to a JSON schema.

    Parameters
    ----------
    type : type
        The TypedDict or dataclass to convert.
    check_schema : bool
        Whether to check the schema for validity.

    Raises
    ------
    ValueError
        If the type is not supported.
    SchemaError
        If the schema is invalid (should not happen).
    """
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Get type hints for the TypedDict
    type_hints = get_type_hints(type, include_extras=True)

    # Add the type hints to the schema
    for field_name, field_type in type_hints.items():
        p, r = __convert_type_to_schema(field_type)
        schema["properties"][field_name] = p

        if r:
            schema["required"].append(field_name)

    if check_schema:
        Draft202012Validator.check_schema(schema)

    return schema


SchemaType = Union[
    dict[str, Any],
    dict[str, str],
    dict[Any, Any],
]


def __convert_type_to_schema(
    field_type: type,
) -> tuple[SchemaType, bool]:
    """
    Convert a type to a JSON schema.

    Parameters
    ----------
    field_type : type
        The type to convert.

    Returns
    -------
    schema : dict | None
        The JSON schema. None if the type is not supported or is is resolves to optional none value.
    is_required : bool
        Whether the field is required.
    """
    is_required = True

    origin = get_origin(field_type)

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
        return __convert_type_to_schema(field_type)[0], is_required

    # Handler union
    if origin is Union or origin is UnionType:
        allowed_types = set(get_args(field_type))
        if NoneType in allowed_types:
            is_required = False
            allowed_types.remove(NoneType)
        if None in allowed_types:
            is_required = False
            allowed_types.remove(None)
        if type(None) in allowed_types:
            is_required = False
            allowed_types.remove(type(None))

        if len(allowed_types) > 1:
            return {
                "anyOf": [
                    __convert_type_to_schema(allowed_type)[0]
                    for allowed_type in allowed_types
                ]
            }, is_required
        elif len(allowed_types) == 1:
            t, _ = __convert_type_to_schema(allowed_types.pop())
            return t, is_required
        else:
            raise ValueError("Union type must have at least one type!")

    # Handle sequence types
    if origin in [list, set, tuple, Sequence, ABCSequence]:
        return {
            "type": "array",
            "items": __convert_type_to_schema(get_args(field_type)[0])[0],
        }, is_required

    # Handle TypedDict and dataclasses
    if issubclass(field_type, Dict) or is_dataclass(field_type):
        return to_json_schema(field_type), is_required

    # Handle other types
    match = primitives.get(field_type)

    if match:
        return {"type": match}, is_required

    if field_type is None or field_type is NoneType:
        return {"type": "null"}, is_required

    if field_type is Any:
        return {}, is_required

    raise ValueError(f"Unsupported type: {field_type}")


def __infer_type_from_values(values: tuple | list):

    # Create set of types
    types = {type(value) for value in values}
    if len(types) > 1:
        raise ValueError("Literal values must all be of the same type")

    return primitives[types.pop()]
