"""Shared validation backend tests for to_json_schema.

Every test here runs against all backends via the ``validator`` fixture
from ``conftest.py``.  When a new backend is added, it only needs to be
registered in the fixture and the test suite covers it automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import is_typeddict

from eyconf.validation import MultiConfigurationError
from eyconf.validation.exceptions import ConfigurationError
import pytest

from .conftest import (
    AliasSchema,
    AllowAdditionalMarkerSchema,
    AnnotatedFieldsSchema,
    BytesSchema,
    DictFieldsSchema,
    DictNestedOuter,
    ListFieldsSchema,
    LiteralBytesSchema,
    LiteralSchema,
    NestedAllowAdditionalMarker,
    NestedAnnotated,
    NestedDict,
    NotRequiredDict,
    OptionalSchema,
    PrimitiveSchema,
    SchemaAny,
    SchemaLiteralUnion,
    SchemaNone,
    UnionNoneSchema,
    UnionSchema,
    dict_is_subset,
)


class TestToJsonSchema:
    # ------------------------------------------------------------------ #
    # Primitives
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [PrimitiveSchema])
    def test_primitives(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        """Test a simple dataclass."""
        schema = validator.to_json_schema(Schema)

        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "string"},
                    "bar": {"type": "integer"},
                    "baz": {"type": "number"},
                    "qux": {"type": "boolean"},
                    "nay": {"type": "null"},
                },
                "required": ["foo", "bar", "baz", "qux", "nay"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [BytesSchema])
    def test_invalid_primitive_bytes(
        self,
        Schema: type,
        validator,
    ):
        """Bytes can't be consistently represented."""
        with pytest.raises(ValueError):
            validator.to_json_schema(Schema)

    # ------------------------------------------------------------------ #
    # Literals
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [LiteralSchema])
    def test_literal(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["dev", "prod", "staging"],
                    },
                    "level": {
                        "type": "integer",
                        "enum": [0, 1, 2],
                    },
                    "mixed": {
                        # "type": ["boolean", "string"],
                        "enum": ["a", "b", False],
                    },
                },
                "required": ["mode", "level", "mixed"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.skip("TODO")
    @pytest.mark.parametrize("schema_cls", [LiteralBytesSchema])
    def test_invalid_literal(
        self,
        Schema: type,
        validator,
    ):
        """Literal bytes can't be consistently represented."""
        with pytest.raises(ValueError):
            validator.to_json_schema(Schema)

    # ------------------------------------------------------------------ #
    # Optional / Union
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [OptionalSchema])
    def test_optional(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "required": {"type": "string"},
                    "maybe_name": {"type": "string"},
                    "maybe_count": {"type": "integer"},
                },
                "required": ["required"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [UnionSchema])
    def test_union(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)

        assert sorted(
            schema["properties"]["foo"]["anyOf"], key=lambda x: x.get("type", "")
        ) == [{"type": "integer"}, {"type": "string"}]
        assert sorted(
            schema["properties"]["bar"]["anyOf"], key=lambda x: x.get("type", "")
        ) == [{"type": "integer"}, {"type": "number"}]

    # ------------------------------------------------------------------ #
    # Nested dataclasses
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [NestedDict])
    def test_nested_dict(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        assert schema["type"] == "object"
        assert set(["dict1", "dict_uni"]).issubset(set(schema["required"]))
        assert ["dict1", "dict_opt", "dict_uni", "baz"] == list(
            schema["properties"].keys()
        )

        dict1_obj = {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
            "additionalProperties": validator_config.allow_additional,
        }

        ok, diff = dict_is_subset(schema["properties"]["dict1"], dict1_obj)
        assert ok, f"Dict subset mismatch for dict1:\n{diff}"

        ok, diff = dict_is_subset(schema["properties"]["dict_opt"], dict1_obj)
        assert ok, f"Dict subset mismatch for dict_opt:\n{diff}"

        assert "anyOf" in schema["properties"]["dict_uni"]
        anyof = schema["properties"]["dict_uni"]["anyOf"]
        assert len(anyof) == 2
        # One alternative must match dict1_obj (possibly as a $ref or inlined)
        assert any(
            dict_is_subset(alt, dict1_obj)[0] if isinstance(alt, dict) else False
            for alt in anyof
        ), f"No anyOf alternative matches {dict1_obj}: {anyof}"
        # The other alternative is {"type": "string"}
        assert {"type": "string"} in anyof

    # ------------------------------------------------------------------ #
    # Lists
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [ListFieldsSchema])
    def test_lists(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "array", "items": {"type": "string"}},
                    "bar": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["foo"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    # ------------------------------------------------------------------ #
    # Dicts
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [DictFieldsSchema])
    def test_dicts(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "object",
                        "patternProperties": {
                            "^.*$": {"type": "integer"},
                        },
                    },
                    "bar": {
                        "type": "object",
                        "patternProperties": {
                            "^.*$": {"type": "string"},
                        },
                    },
                },
                "required": ["foo", "bar"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [DictNestedOuter])
    def test_dict_nested(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)

        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "outer": {
                        "type": "object",
                        "patternProperties": {
                            "^.*$": {
                                "type": "object",
                                "properties": {
                                    "inner": {"type": "integer"},
                                },
                                "required": ["inner"],
                                "additionalProperties": validator_config.allow_additional,
                            }
                        },
                    },
                },
                "required": ["outer"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    # ------------------------------------------------------------------ #
    # TypedDict (NotRequired)
    # ------------------------------------------------------------------ #

    def test_not_required(self, validator_config, validator):
        schema = validator.to_json_schema(NotRequiredDict)

        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "string"},
                    "bar": {"type": "integer"},
                    "baz": {"type": "number"},
                    "qux": {"type": "boolean"},
                    "nay": {"type": "null"},
                },
                "required": [],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    # ------------------------------------------------------------------ #
    # Special types (None, Any, Optional[None])
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [SchemaNone])
    def test_special_none(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "null"},
                },
                "required": ["foo"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [SchemaAny])
    def test_special_any(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {},
                },
                "required": ["foo"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [UnionNoneSchema])
    def test_special_union_none(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "null"},
                },
                "required": ["foo"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    # ------------------------------------------------------------------ #
    # Cache
    # ------------------------------------------------------------------ #

    def test_cache_hit(self, validator):
        schema = validator.to_json_schema(PrimitiveSchema)
        schema2 = validator.to_json_schema(PrimitiveSchema)

        assert schema is schema2

    # ------------------------------------------------------------------ #
    # Dict key type validation
    # ------------------------------------------------------------------ #

    def test_non_str_dict(self, validator):
        @dataclass
        class Schema:
            foo: dict[int, str]

        with pytest.raises(
            ValueError,
            match="Only string keys are supported in dict types",
        ):
            validator.to_json_schema(Schema)

    # ------------------------------------------------------------------ #
    # Annotated
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [AnnotatedFieldsSchema])
    def test_annotated(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "foo": {"type": "string"},
                    "bar": {"type": "integer"},
                },
                "required": ["foo", "bar"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    @pytest.mark.parametrize("schema_cls", [NestedAnnotated])
    def test_annotated_nested(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "foo": {"type": "string"},
                            "bar": {"type": "integer"},
                        },
                        "required": ["foo", "bar"],
                        "additionalProperties": validator_config.allow_additional,
                    }
                },
                "required": ["schema"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"

    # ------------------------------------------------------------------ #
    # __allow_additional marker
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize(
        "schema_cls",
        [AllowAdditionalMarkerSchema],
    )
    def test_allow_additional_marker(
        self,
        Schema: type,
        validator,
        validator_config,
    ):
        if is_typeddict(Schema):
            return pytest.skip("TODO")

        schema = validator.to_json_schema(Schema)

        assert schema["additionalProperties"] is True

    @pytest.mark.parametrize(
        "schema_cls",
        [NestedAllowAdditionalMarker],
    )
    def test_allow_additional_marker_nested(
        self,
        Schema: type,
        validator,
        validator_config,
    ):
        if is_typeddict(Schema):
            return pytest.skip("TODO")

        schema = validator.to_json_schema(Schema)

        assert schema["additionalProperties"] is False

        # Pydantic uses $ref for nested types; json_schema inlines them.
        bar_schema = schema["properties"]["bar"]
        if "$ref" in bar_schema:
            # Resolve the $ref from $defs
            ref_key = bar_schema["$ref"].split("/")[-1]
            bar_schema = schema["$defs"][ref_key]

        assert bar_schema["additionalProperties"] is True

    # ------------------------------------------------------------------ #
    # Literal in union
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [SchemaLiteralUnion])
    def test_literal_in_union(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        """For some reason Literals inside Unions have `Union` as their origin
        instead of `UnionType`. Might be a Python bug!

        >>> from typing import Literal, get_origin
        >>> get_origin(int | Literal["asd"])
        typing.Union
        >>> get_origin(int | str)
        <class 'types.UnionType'>
        """
        schema = validator.to_json_schema(Schema)
        assert sorted(schema["properties"]["foo"]["anyOf"], key=lambda x: str(x)) == [
            {"type": "string", "enum": ["bar", "baz"]},
            {"type": "string"},
        ]

    # ------------------------------------------------------------------ #
    # Aliases
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("schema_cls", [AliasSchema])
    def test_alias_handling(
        self,
        Schema: type,
        validator_config,
        validator,
    ):
        if is_typeddict(Schema):
            return pytest.skip("TODO")

        schema = validator.to_json_schema(Schema)
        ok, diff = dict_is_subset(
            schema,
            {
                "type": "object",
                "properties": {
                    "the_bar": {"type": "integer"},
                    "foo": {"type": "string"},
                },
                "required": ["the_bar"],
                "additionalProperties": validator_config.allow_additional,
            },
        )
        assert ok, f"Dict subset mismatch:\n{diff}"


class TestValidate:
    """Test the validate() method of all backends."""

    def test_validate_valid_data(self, validator):
        """Valid data should pass validation."""
        data = {
            "foo": "hello",
            "bar": 42,
            "baz": 3.14,
            "qux": True,
            "nay": None,
        }
        validator.validate(data, PrimitiveSchema)

    def test_validate_invalid_data(self, validator):
        """Invalid data should raise ConfigurationError."""
        data = {
            "foo": 123,
            "bar": "not an int",
            "baz": "not a float",
            "qux": "not a bool",
            "nay": "not none",
        }
        with pytest.raises((MultiConfigurationError, ConfigurationError)):
            validator.validate(data, PrimitiveSchema)

    def test_literal(self, validator):
        data = LiteralSchema(mode="dev", level=1, mixed=False)
        validator.validate(data, LiteralSchema)

    def test_optional(self, validator):
        data = {"required": "hello"}
        validator.validate_and_construct(data, OptionalSchema)
