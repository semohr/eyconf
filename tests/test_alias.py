

from __future__ import annotations

from dataclasses import dataclass, field, fields

from typing import Any, Optional, Type, TypeVar, runtime_checkable
from typing_extensions import  Protocol
import pytest
from eyconf import EYConfBase
from eyconf.utils import asdict_with_aliases


T = TypeVar("T", bound=Any)
@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


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


@dataclass
class AliasConfig:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"

@dataclass
class NestedAliasConfig:
    nested: AliasConfig = field(default_factory= lambda : AliasConfig(attr_field=43))
    other_field: str = "Hello, World!"


# @dict_access
@dataclass
class AliasDictConfig:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"


class TestAlias:
    def test_utils(self):
        config = AliasConfig(attr_field=42)
        dump = asdict_with_aliases(config)
        assert dump["dict_field"] == 42

        nested_config= NestedAliasConfig()
        nested_dump = asdict_with_aliases(nested_config)
        assert nested_dump["nested"]["dict_field"] == 43


    def test_dict_alias_update(self):
        config = EYConfBase(AliasConfig(attr_field=42))

        # Update via alias
        # update also calls validate in the background
        config.update({"dict_field": 16})

        assert config.data.attr_field == 16


    def test_constructor_alias(self):
        # Constructor with dict using alias
        config = EYConfBase({"dict_field": 100, "str_field": "Test"}, schema=AliasConfig)

        assert config.data.attr_field == 100
        assert config.data.str_field == "Test"


# class TestAliasWithDictAccess:
#     def test_dict_alias_access(self):
#         c = EYConfBase(AliasDictConfig(attr_field=42))

#         # We want this asymetric access behavior
#         assert c.data.attr_field == 42
#         with pytest.raises(AttributeError):
#             c.data.dict_field # type: ignore

#         assert isinstance(c.data, DictAccess)

#         # By dict is inverted
#         assert c.data["dict_field"] == 42
#         with pytest.raises(KeyError):
#             c.data["attr_field"]
