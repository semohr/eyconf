"""
Tests around accessing the config via dict notation `config.data["key"]`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from typing import Any, Optional, Type, TypeVar, runtime_checkable
from typing_extensions import  Protocol
import pytest
from eyconf import EYConfBase


T = TypeVar("T", bound=Any)


@runtime_checkable
class DictAccess(Protocol):
    def __getitem__(self, key: str) -> Any: ...


def add_dict_access(cls: Type[T]) -> Type[T]:
    # Define __getitem__ to enable dict-like access
    fields_ = fields(cls)
    keys = {f.metadata.get("alias", f.name) for f in fields_}

    alias_rewrites = {
        f.metadata["alias"]: f.name
        for f in fields_
        if "alias" in f.metadata
    }

    def __getitem__(self, key: str) -> Any:
        # Apply alias rewrite if necessary

        if key in keys:
            if key in alias_rewrites:
                key = alias_rewrites[key]
            return getattr(self, key)
        raise KeyError(f"{key} is not a valid field name")

    setattr(cls, "__getitem__", __getitem__)
    return cls


@add_dict_access
@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


@add_dict_access
@dataclass
class ConfigNested:
    nested: Config42 = field(default_factory=Config42)
    nested_optional: Optional[Config42] = None
    other_field: str = "Hello, World!"


@pytest.fixture
def conf42() -> EYConfBase[Config42]:
    return EYConfBase(Config42(), schema=Config42)


@pytest.fixture
def conf_nested() -> EYConfBase[ConfigNested]:
    return EYConfBase(ConfigNested(), schema=ConfigNested)


class TestDictAccess:
    def test_dict_access_basic(self, conf42: EYConfBase[Config42]):
        assert isinstance(conf42.data, DictAccess)

        assert conf42.data["int_field"] == 42
        assert conf42.data["str_field"] == "FortyTwo!"

    def test_dict_access_nested(self, conf_nested):
        assert isinstance(conf_nested.data, DictAccess)

        assert conf_nested.data["other_field"] == "Hello, World!"
        assert conf_nested.data["nested"]["int_field"] == 42
        assert conf_nested.data["nested"]["str_field"] == "FortyTwo!"
        assert conf_nested.data["nested_optional"] is None


@add_dict_access
@dataclass
class AliasConfig:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"


class TestDictAlias:
    def test_dict_alias_access(self, conf42: EYConfBase[Config42]):
        c = EYConfBase(AliasConfig(attr_field=42))

        # We want this asymetric access behavior
        assert c.data.attr_field == 42
        with pytest.raises(AttributeError):
            c.data.dict_field # type: ignore

        assert isinstance(c.data, DictAccess)

        # By dict is inverted
        assert c.data["dict_field"] == 42
        with pytest.raises(KeyError):
            c.data["attr_field"]


    def test_dict_alias_update(self):
        c = EYConfBase(AliasConfig(attr_field=42))

        # Update via alias
        # update also calls validate in the background
        c.update({"dict_field": 16})


        assert isinstance(c.data, DictAccess)

        assert c.data.attr_field == 16
        assert c.data["dict_field"] == 16

    def test_constructor_alias(self):
        # Constructor with dict using alias
        c = EYConfBase({"dict_field": 100, "str_field": "Test"}, schema=AliasConfig)

        assert c.data.attr_field == 100
        assert c.data.str_field == "Test"
