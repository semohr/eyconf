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
    get_type_hints,
)
import pytest
from eyconf.validate import to_json_schema
from dataclasses import dataclass


class TestToSchema:
    """
    Test the dataclass to json schema function
    """

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_primitives(self, as_dataclass):
        """Test a simple dataclass."""

        @dataclass
        class Primitives:
            foo: str
            bar: int
            baz: float
            qux: bool

        if not as_dataclass:
            Primitives = dataclass_to_typeddict(Primitives)  # type: ignore

        schema = to_json_schema(Primitives)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
                "qux": {"type": "boolean"},
            },
            "required": ["foo", "bar", "baz", "qux"],
        }

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_literal(self, as_dataclass):
        @dataclass
        class Schema:
            foo: Literal["bar", "baz"]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string", "enum": ["bar", "baz"]},
            },
            "required": ["foo"],
        }

        @dataclass
        class InvalidLiteral:
            foo: Literal[1, "foo"]

        if not as_dataclass:
            InvalidLiteral = dataclass_to_typeddict(InvalidLiteral)  # type: ignore

        with pytest.raises(ValueError):
            to_json_schema(InvalidLiteral)

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_optional(self, as_dataclass):
        @dataclass
        class Schema:
            foo: Optional[str]
            bar: Optional[int]
            baz: float

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema)
        print(schema)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
            },
            "required": ["baz"],
        }

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_union(self, as_dataclass):
        @dataclass
        class Schema:
            foo: str | int
            bar: int | float

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema)
        print(schema)

        assert sorted(
            schema["properties"]["foo"]["anyOf"], key=lambda x: x["type"]
        ) == [{"type": "integer"}, {"type": "string"}]
        assert sorted(
            schema["properties"]["bar"]["anyOf"], key=lambda x: x["type"]
        ) == [{"type": "integer"}, {"type": "number"}]

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_nested_dict(self, as_dataclass):
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

        schema = to_json_schema(NestedTyped)
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
        }

        assert schema["properties"]["dict1"] == dict1_obj
        assert schema["properties"]["dict_opt"] == dict1_obj

        assert "anyOf" in schema["properties"]["dict_uni"]
        assert (
            schema["properties"]["dict_uni"]["anyOf"][0] == dict1_obj
            or schema["properties"]["dict_uni"]["anyOf"][1] == dict1_obj
        )

    @pytest.mark.parametrize(
        "as_dataclass",
        (True, False),
    )
    def test_lists(self, as_dataclass):
        @dataclass
        class Schema:
            foo: list[str]
            bar: Optional[Sequence[int]]

        if not as_dataclass:
            Schema = dataclass_to_typeddict(Schema)  # type: ignore

        schema = to_json_schema(Schema)
        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "array", "items": {"type": "string"}},
                "bar": {"type": "array", "items": {"type": "integer"}},
            },
            "required": [
                "foo",
            ],
        }

    def test_not_required(self):
        from typing_extensions import NotRequired

        class MyTypedDict1(TypedDict):
            foo: NotRequired[str]
            bar: NotRequired[int]
            baz: NotRequired[float]
            qux: NotRequired[bool]

        schema = to_json_schema(MyTypedDict1)

        assert schema == {
            "type": "object",
            "properties": {
                "foo": {"type": "string"},
                "bar": {"type": "integer"},
                "baz": {"type": "number"},
                "qux": {"type": "boolean"},
            },
            "required": [],
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
    type_hints = get_type_hints(dc_cls)

    # Extract the fields and their types
    typeddict_fields: Dict = {
        field.name: type_hints[field.name] for field in fields(dc_cls)
    }

    # Create the TypedDict dynamically
    return TypedDict(f"{dc_cls.__name__}Dict", typeddict_fields)  # type: ignore
