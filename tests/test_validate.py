from __future__ import annotations
from dataclasses import fields
from pprint import pprint
from typing import (
    Any,
    Dict,
    Literal,
    Optional,
    Sequence,
    TypedDict,
    Union,
)
from typing_extensions import NotRequired
import pytest
from eyconf.type_utils import get_type_hints_resolve_namespace
from eyconf.validation import to_json_schema
from dataclasses import dataclass


class TestToSchema:
    """
    Test the dataclass to json schema function
    """

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_primitives(self, as_dataclass, allow_additional):
        """Test a simple dataclass."""

        @dataclass
        class Primitives:
            foo: str
            bar: int
            baz: float
            qux: bool
            nay: None

        if not as_dataclass:
            Primitives = dataclass_to_typeddict(Primitives)  # type: ignore

        schema = to_json_schema(Primitives, allow_additional=allow_additional)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
                "qux": {"type": "boolean"},
                "nay": {"type": "null"},
            },
            "required": ["foo", "bar", "baz", "qux", "nay"],
            "additionalProperties": allow_additional,
        }

        @dataclass
        class InvalidPrimitive:
            foo: bytes

        if not as_dataclass:
            InvalidPrimitive = dataclass_to_typeddict(InvalidPrimitive)  # type: ignore

        with pytest.raises(ValueError):
            to_json_schema(InvalidPrimitive)

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_literal(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: Literal["bar", "baz"]
            bar: Literal[None]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string", "enum": ["bar", "baz"]},
                "bar": {"type": "null", "enum": [None]},
            },
            "required": ["foo", "bar"],
            "additionalProperties": allow_additional,
        }

        @dataclass
        class InvalidLiteral:
            foo: Literal[b"0"]

        if not as_dataclass:
            InvalidLiteral = dataclass_to_typeddict(InvalidLiteral)  # type: ignore

        with pytest.raises(ValueError):
            to_json_schema(InvalidLiteral)

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_literal_with_different_types(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: Literal["a", "b", False]
            bar: Literal[1, None]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema, allow_additional=allow_additional)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": ["string", "boolean"], "enum": ["a", "b", False]},
                "bar": {"type": ["integer", "null"], "enum": [1, None]},
            },
            "required": ["foo", "bar"],
            "additionalProperties": allow_additional,
        }

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_optional(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: Optional[str]
            bar: Optional[int]
            baz: float

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema, allow_additional=allow_additional)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)
        print(schema)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
            },
            "required": ["baz"],
            "additionalProperties": allow_additional,
        }

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_union(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: str | int
            bar: int | float

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema, allow_additional=allow_additional)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)

        assert sorted(
            schema["properties"]["foo"]["anyOf"], key=lambda x: x["type"]
        ) == [{"type": "integer"}, {"type": "string"}]
        assert sorted(
            schema["properties"]["bar"]["anyOf"], key=lambda x: x["type"]
        ) == [{"type": "integer"}, {"type": "number"}]

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_nested_dict(self, as_dataclass, allow_additional):
        @dataclass
        class Dict1:
            foo: str

        if not as_dataclass:
            Dict1 = dataclass_to_typeddict(Dict1)  # type: ignore

        @dataclass
        class NestedTyped:
            dict1: Dict1
            dict_opt: Optional[Dict1]
            dict_uni: Dict1 | str
            baz: Optional[float]

        if not as_dataclass:
            NestedTyped = dataclass_to_typeddict(NestedTyped)  # type: ignore

        schema = to_json_schema(NestedTyped, allow_additional=allow_additional)
        pprint(schema)
        assert schema["type"] == "object"
        assert schema["required"] == ["dict1", "dict_uni"]
        assert ["dict1", "dict_opt", "dict_uni", "baz"] == list(
            schema["properties"].keys()
        )

        dict1_obj = {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
            "additionalProperties": allow_additional,
        }

        assert schema["properties"]["dict1"] == dict1_obj
        assert schema["properties"]["dict_opt"] == dict1_obj

        assert "anyOf" in schema["properties"]["dict_uni"]
        assert (
            schema["properties"]["dict_uni"]["anyOf"][0] == dict1_obj
            or schema["properties"]["dict_uni"]["anyOf"][1] == dict1_obj
        )

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_lists(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: list[str]
            bar: Optional[Sequence[int]]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "array", "items": {"type": "string"}},
                "bar": {"type": "array", "items": {"type": "integer"}},
            },
            "required": [
                "foo",
            ],
            "additionalProperties": allow_additional,
        }

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_dicts(self, as_dataclass, allow_additional):
        @dataclass
        class Schema:
            foo: Dict[str, int]
            bar: dict[str, str]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema, allow_additional=allow_additional)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "integer"},
                    },
                },
                "bar": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "string"},
                    },
                },
            },
            "required": ["foo", "bar"],
            "additionalProperties": allow_additional,
        }

    @pytest.mark.parametrize(
        ["as_dataclass", "allow_additional"],
        [(True, False), (True, False)],
    )
    def test_dict_nested(self, as_dataclass, allow_additional):
        @dataclass
        class Inner:
            inner: int

        @dataclass
        class Outer:
            outer: Dict[str, Inner]

        if not as_dataclass:
            Outer = dataclass_to_typeddict(Outer)  # type: ignore

        schema = to_json_schema(Outer, allow_additional=allow_additional)

        assert schema == {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {
                            "type": "object",
                            "properties": {
                                "inner": {"type": "integer"},
                            },
                            "required": ["inner"],
                            "additionalProperties": allow_additional,
                        }
                    },
                },
            },
            "required": ["outer"],
            "additionalProperties": allow_additional,
        }

    def test_not_required(self):
        class MyTypedDict1(TypedDict):
            foo: NotRequired[str]
            bar: NotRequired[int]
            baz: NotRequired[float]
            qux: NotRequired[bool]
            nay: NotRequired[None]

        schema = to_json_schema(MyTypedDict1)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
                "qux": {"type": "boolean"},
                "nay": {"type": "null"},
            },
            "required": [],
            "additionalProperties": True,
        }

    def test_special(self):
        @dataclass
        class Schema:
            foo: None

        schema = to_json_schema(Schema)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "null"},
            },
            "required": ["foo"],
            "additionalProperties": True,
        }

        @dataclass
        class SchemaAny:
            foo: Any

        schema = to_json_schema(SchemaAny)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {},
            },
            "required": ["foo"],
            "additionalProperties": True,
        }

        @dataclass
        class UnionNone:
            foo: Union[None, None]

        schema = to_json_schema(UnionNone)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "null"},
            },
            "required": ["foo"],
            "additionalProperties": True,
        }

    def test_cache_hit(self):
        @dataclass
        class Schema:
            foo: str

        schema = to_json_schema(Schema)
        schema2 = to_json_schema(Schema)

        assert schema is schema2


# This function converts a dataclass to a TypedDict
def dataclass_to_typeddict(dc_cls: type):
    """Convert a dataclass to a TypedDict."""
    # Fetch type hints of the dataclass
    type_hints = get_type_hints_resolve_namespace(dc_cls)

    # Extract the fields and their types
    typeddict_fields: Dict = {
        field.name: type_hints[field.name] for field in fields(dc_cls)
    }

    # Create the TypedDict dynamically
    return TypedDict(f"{dc_cls.__name__}Dict", typeddict_fields)  # type: ignore
