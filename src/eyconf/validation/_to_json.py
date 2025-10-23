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
)

from jsonschema import Draft202012Validator
from typing_extensions import NotRequired

from eyconf.constants import primitive_type_mapping
from eyconf.type_utils import get_type_hints_resolve_namespace

__all__ = ["to_json_schema"]


@lru_cache(maxsize=None)
def to_json_schema(
    type: type,
    check_schema: bool = True,
    allow_additional: bool = True,
) -> dict:
    """Convert a TypedDict or dataclass to a JSON schema.

    Parameters
    ----------
    type : type
        The TypedDict or dataclass to convert.
    check_schema : bool
        Whether to check the schema for validity.
    allow_additional : bool
        Whether to allow extra, unrecognized properties in the schema.

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
        "additionalProperties": allow_additional,
    }

    # Get type hints for the TypedDict
    type_hints = get_type_hints_resolve_namespace(type, include_extras=True)

    # Add the type hints to the schema
    for field_name, field_type in type_hints.items():
        p, r = __convert_type_to_schema(field_type, allow_additional=allow_additional)
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
                    __convert_type_to_schema(allowed_type, **kwargs)[0]
                    for allowed_type in allowed_types
                ]
            }, is_required
        elif len(allowed_types) == 1:
            t, _ = __convert_type_to_schema(allowed_types.pop(), **kwargs)
            return t, is_required
        else:
            raise ValueError("Union type must have at least one type!")

    # Handle sequence types
    if origin in [list, set, tuple, Sequence, ABCSequence]:
        return {
            "type": "array",
            "items": __convert_type_to_schema(get_args(field_type)[0], **kwargs)[0],
        }, is_required

    # Handle TypedDict and dataclasses
    try:
        if issubclass(field_type, Dict) or is_dataclass(field_type):
            return to_json_schema(field_type, **kwargs), is_required
    except TypeError:
        # Throws an error in case of a type that is not a class
        pass

    # Handle Dicts - arbitrary keys with typed values
    if origin in [dict, Dict]:
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
