"""Shared fixtures and dataclass schemas for all validation backend tests.

This module provides:
- Reusable dataclass schemas that all backends must handle
- A parametrized fixture yielding (validator, allow_additional) tuples
- Factory functions for creating validator instances
"""

from __future__ import annotations


from dataclasses import dataclass, field, fields
from pprint import pformat
from typing import Annotated, Any, ClassVar, Literal, NamedTuple, TypedDict

from eyconf.type_utils import get_type_hints_resolve_namespace
import pytest

from typing_extensions import NotRequired


# ------------------------- Shared Dataclass Schemas ------------------------- #


@dataclass
class PrimitiveSchema:
    """Schema with all primitive types."""

    foo: str
    bar: int
    baz: float
    qux: bool
    nay: None


@dataclass
class BytesSchema:
    """Invalid primitives."""

    foo: bytes


@dataclass
class PrimitiveSchemaWithDefaults:
    """Primitive schema with defaults (used for partial update tests)."""

    name: str = "default"
    count: int = 0
    score: float = 0.0
    enabled: bool = True
    nothing: None = None


@dataclass
class LiteralSchema:
    """Schema with Literal types."""

    mode: Literal["dev", "prod", "staging"]
    level: Literal[0, 1, 2]
    mixed: Literal["a", "b", False]


@dataclass
class LiteralBytesSchema:
    """Invalid primitives."""

    foo: Literal[b"0"]


@dataclass
class OptionalSchema:
    """Schema with Optional / union-with-None fields."""

    required: str
    maybe_name: str | None = None
    maybe_count: int | None = None


@dataclass
class UnionSchema:
    """Schema with union types."""

    foo: str | int
    bar: int | float


@dataclass
class AliasSchema:
    """Schema with field aliases."""

    bar: int = field(metadata={"alias": "the_bar"})
    foo: str = "hello"


@dataclass
class NestedInner:
    """Nested dataclass for testing."""

    value: int = 42
    name: str = "inner"


@dataclass
class AliasNestedInner:
    """Nested dataclass with aliases for deep alias resolution testing."""

    the_value: int = field(metadata={"alias": "value"})
    the_name: str = field(metadata={"alias": "name"})


@dataclass
class NestedSchema:
    """Schema with a nested dataclass field."""

    outer_name: str = "outer"
    inner: NestedInner = field(default_factory=NestedInner)


@dataclass
class AliasNestedSchema:
    """Schema with a nested dataclass that has aliases."""

    outer_name: str = "outer"
    inner: AliasNestedInner = field(
        default_factory=lambda: AliasNestedInner(42, "name")
    )


@dataclass
class OptionalNestedSchema:
    """Schema with an optional nested dataclass."""

    name: str = "test"
    inner: NestedInner | None = None


@dataclass
class ListSchema:
    """Schema with list fields."""

    items: list[str] = field(default_factory=list)
    numbers: list[int] = field(default_factory=list)


@dataclass
class DeepNestedLevel3:
    """Three levels deep for deep nesting tests."""

    leaf_value: int = 1


@dataclass
class DeepNestedLevel2:
    """Middle level of deep nesting."""

    level3: DeepNestedLevel3 = field(default_factory=DeepNestedLevel3)
    mid_name: str = "middle"


@dataclass
class DeepNestedLevel1:
    """Top level of deep nesting."""

    level2: DeepNestedLevel2 = field(default_factory=DeepNestedLevel2)
    top_name: str = "top"


# -------------------- ClassVar / Allow-Additional Schemas ------------------- #


@dataclass
class ClassVarSchema:
    """Schema with a ClassVar (should be ignored by validators)."""

    name: str = "test"
    class_counter: ClassVar[int] = 0


@dataclass
class AllowAdditionalSchema:
    """Schema that explicitly allows additional properties."""

    name: str = "test"
    __allow_additional: ClassVar[bool] = True


# ------------------------- Nested / Collection Schemas ------------------------ #


@dataclass
class NestedDict1:
    """Inner dataclass for nested dict tests."""

    foo: str


@dataclass
class NestedDict:
    """Schema with nested dataclass fields."""

    dict1: NestedDict1
    dict_opt: NestedDict1 | None
    dict_uni: NestedDict1 | str
    baz: float | None


@dataclass
class ListFieldsSchema:
    """Schema with list fields."""

    foo: list[str]
    bar: list[int] | None = None


@dataclass
class DictFieldsSchema:
    """Schema with dict fields."""

    foo: dict[str, int]
    bar: dict[str, str]


@dataclass
class DictNestedInner:
    """Inner dataclass for dict-of-nested tests."""

    inner: int


@dataclass
class DictNestedOuter:
    """Schema with dict[str, Inner]."""

    outer: dict[str, DictNestedInner]


# ------------------------- Special / Edge Case Schemas ------------------------ #


@dataclass
class SchemaNone:
    """Schema with only None field."""

    foo: None


@dataclass
class SchemaAny:
    """Schema with Any field."""

    foo: Any  # type: ignore[name-defined]


@dataclass
class UnionNoneSchema:
    """Schema with Optional[None]."""

    foo: None


@dataclass
class SchemaLiteralUnion:
    """Schema with Literal inside union."""

    foo: str | Literal["bar", "baz"]


# ------------------------- Annotation / Metadata Schemas ---------------------- #


@dataclass
class AnnotatedFieldsSchema:
    """Schema with Annotated fields."""

    foo: Annotated[str, "some metadata"]  # type: ignore[name-defined]
    bar: Annotated[int, "some metadata", "more metadata"]  # type: ignore[name-defined]


@dataclass
class NestedAnnotated:
    """Schema with nested AnnotatedFieldsSchema."""

    schema: AnnotatedFieldsSchema


# ------------------------- Alias / Marker Schemas ----------------------------- #


@dataclass
class AllowAdditionalMarkerSchema:
    """Schema with __allow_additional ClassVar = True."""

    foo: str
    __allow_additional: ClassVar[bool] = True


@dataclass
class NestedAllowAdditionalMarker:
    """Schema with __allow_additional ClassVar = False wrapping AllowAdditionalMarkerSchema."""

    bar: AllowAdditionalMarkerSchema
    __allow_additional: ClassVar[bool] = False


# ------------------------- TypedDict Schemas ---------------------------------- #


class NotRequiredTotalDict(TypedDict, total=False):
    """TypedDict with all NotRequired fields."""

    foo: str
    bar: int
    baz: float
    qux: bool
    nay: None


class NotRequiredDict(TypedDict, total=False):
    """TypedDict with all NotRequired fields."""

    foo: NotRequired[str]
    bar: NotRequired[int]
    baz: NotRequired[float]
    qux: NotRequired[bool]
    nay: NotRequired[None]


# ---------------------------- Validator Fixtures ---------------------------- #


class ValidatorConfig(NamedTuple):
    backend: str
    allow_additional: bool


@pytest.fixture(
    params=[
        pytest.param(("json_schema", True), id="json-allow"),
        pytest.param(("json_schema", False), id="json-deny"),
        # pytest.param(("msgspec", True), id="msgspec-allow"),
        # pytest.param(("msgspec", False), id="msgspec-deny"),
    ],
    scope="session",
)
def validator_config(request):
    """Usage:

    def test_primitives(validator_config, validator, Schema):
        backend, allow_additional = validator_config
    """
    return ValidatorConfig(*request.param)


@pytest.fixture(
    scope="session",
)
def validator(validator_config):
    """Combine backend selection with allow_additional param."""
    backend, allow_additional = validator_config

    if backend == "json_schema":
        from eyconf.validation.backends.json_schema import JsonSchemaValidator

        return JsonSchemaValidator(allow_additional=allow_additional)


@pytest.fixture(params=["dataclass", "typeddict"], ids=["dataclass", "typeddict"])
def Schema(request, schema_cls):
    """Dataclass OR TypedDict version."""
    if request.param == "dataclass":
        return schema_cls
    else:
        return dataclass_to_typeddict(schema_cls)


def dataclass_to_typeddict(dc_cls: type):
    """Convert a dataclass to a TypedDict."""
    # Fetch type hints of the dataclass
    type_hints = get_type_hints_resolve_namespace(dc_cls)

    # Extract the fields and their types
    typeddict_fields: dict = {
        field.name: type_hints[field.name] for field in fields(dc_cls)
    }

    # Create the TypedDict dynamically
    return TypedDict(f"{dc_cls.__name__}Dict", typeddict_fields)  # type: ignore


def dict_is_subset(actual, expected):
    """
    Return (ok, diff) where:
      ok   -> True if expected is a subset of actual
      diff -> dict of mismatches/missing keys
    """
    diff = {}

    for key, exp_val in expected.items():
        if key not in actual:
            diff[key] = {"expected": exp_val, "actual": "<missing>"}
            continue

        act_val = actual[key]

        if isinstance(exp_val, dict) and isinstance(act_val, dict):
            ok, subdiff = dict_is_subset(act_val, exp_val)
            if not ok:
                diff[key] = subdiff
        elif act_val != exp_val:
            diff[key] = {"expected": exp_val, "actual": act_val}

    return (len(diff) == 0), pformat(diff)
