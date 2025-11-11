from __future__ import annotations

from dataclasses import asdict, dataclass, field

from typing import Any, Optional, TypeVar
import pytest
from eyconf import EYConfBase
from eyconf.config.extra_fields import EYConfExtraFields
from eyconf.utils import AttributeDict, DictAccess, asdict_with_aliases, dict_access
from eyconf.validation import validate, validate_json
from eyconf.validation._to_json import to_json_schema


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
    nested: AliasConfig = field(default_factory=lambda: AliasConfig(attr_field=43))
    other_field: str = "Hello, World!"


@dict_access
@dataclass
class AliasDictConfig:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"


class TestAlias:
    def test_utils(self):
        config = AliasConfig(attr_field=42)
        dump = asdict_with_aliases(config)
        assert dump["dict_field"] == 42

        nested_config = NestedAliasConfig()
        nested_dump = asdict_with_aliases(nested_config)
        assert nested_dump["nested"]["dict_field"] == 43

    def test_validate_json(self):
        config = AliasConfig(attr_field=42)
        json_schema = to_json_schema(AliasConfig)

        # raises if invalid
        validate_json(config, schema = json_schema)

        with pytest.raises(Exception):
            # using the dataclasses native asdict
            # will not do our alias mapping so it should fail
            validate_json(asdict(config), schema=json_schema)

        # but this should not raise
        validate_json(asdict_with_aliases(config), schema=json_schema)

    def test_validate(self):
        config = AliasConfig(attr_field=42)

        # we use the same logic as in test_validate_json in our wrapper
        validate(config, schema=AliasConfig)
        validate(asdict_with_aliases(config), schema=AliasConfig)

        with pytest.raises(Exception):
            validate(asdict(config), schema=AliasConfig)

    def test_validate_additional(self):
        config = AliasConfig(attr_field=42)

        config.foo = "bar" # type: ignore
        validate(config, schema=AliasConfig, allow_additional=True)

        with pytest.raises(Exception):
            # Currently does not raise, not sure why our json validator does not catch this. The whole allow_additional flag needs 4-eye decisions, anyway.
            # (Having it non-effective for dicts sucks)
            validate(config, schema=AliasConfig, allow_additional=False)




    def test_dict_alias_update(self):
        config = EYConfBase(AliasConfig(attr_field=42))

        # Update via alias
        # update also calls validate in the background
        config.update({"dict_field": 16})

        assert config.data.attr_field == 16

    def test_constructor_alias(self):
        # Constructor with dict using alias
        config = EYConfBase(
            {"dict_field": 100, "str_field": "Test"}, schema=AliasConfig
        )

        assert config.data.attr_field == 100
        assert config.data.str_field == "Test"




class TestAliasWithDictAccess:
    def test_dict_alias_access(self):
        config = EYConfBase(AliasDictConfig(attr_field=42))

        # We want this asymetric access behavior
        assert config.data.attr_field == 42
        with pytest.raises(AttributeError):
            config.data.dict_field # type: ignore

        assert isinstance(config.data, DictAccess)

        # By dict is inverted
        assert config.data["dict_field"] == 42
        with pytest.raises(KeyError):
            config.data["attr_field"]

def test_extra_fields_dict_alias_access(self):
    config = EYConfExtraFields(AliasDictConfig(attr_field=42))

    assert config.data.attr_field == 42
    # assert config.data.dict_field == ???

    assert isinstance(config.data, DictAccess)

    assert config.data["dict_field"] == 42
    with pytest.raises(KeyError):
        config.data["attr_field"]
