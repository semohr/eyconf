from __future__ import annotations

from dataclasses import asdict, dataclass, field

from typing import Any, TypeVar
import pytest
from eyconf import Config, ConfigExtra
from eyconf.asdict import asdict_with_aliases
from eyconf.decorators import allow_additional, dict_access
from eyconf.validation import (
    MultiConfigurationError,
    validate,
)

T = TypeVar("T", bound=Any)


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


@dataclass
class ConfigNested:
    nested: Config42 = field(default_factory=Config42)
    nested_optional: Config42 | None = None
    other_field: str = "Hello, World!"


@pytest.fixture
def conf42() -> Config[Config42]:
    return Config(Config42(), schema=Config42)


@pytest.fixture
def conf_nested() -> Config[ConfigNested]:
    return Config(ConfigNested(), schema=ConfigNested)


@dataclass
class AliasConfig:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"


@allow_additional
@dataclass
class AliasConfigAdditional:
    attr_field: int = field(metadata={"alias": "dict_field"})
    str_field: str = "FortyTwo!"

    # __allow_additional: ClassVar[bool] = True


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

    def test_validate(self):
        config = AliasConfig(attr_field=42)

        # this should not raise, since we have aliases
        validate(config, schema=AliasConfig)
        validate(asdict_with_aliases(config), schema=AliasConfig)

        with pytest.raises(MultiConfigurationError):
            # using the dataclasses native asdict
            # will not do our alias mapping so it should fail
            validate(asdict(config), schema=AliasConfig)

    def test_validate_additional(self):
        config = AliasConfig(attr_field=42)

        config.foo = "bar"  # type: ignore

        with pytest.raises(MultiConfigurationError):
            # By default, no additional attributes are allowed.
            validate(config, schema=AliasConfig)

        validate(config, schema=AliasConfigAdditional)

    def test_dict_alias_update(self):
        config = Config(AliasConfig(attr_field=42))

        # Update via alias
        # update also calls validate in the background
        config.update({"dict_field": 16})

        assert config.data.attr_field == 16

    def test_constructor_alias(self):
        # Constructor with dict using alias
        config = Config({"dict_field": 100, "str_field": "Test"}, schema=AliasConfig)

        assert config.data.attr_field == 100
        assert config.data.str_field == "Test"

    def test_extra_data_nested_aliased(self):
        @dataclass
        class ConfigAliasedParent:
            import_: Config42 = field(
                default_factory=lambda: Config42(), metadata={"alias": "import"}
            )

        config = ConfigExtra(ConfigAliasedParent())
        assert config.data.import_.int_field == 42
        assert config.proxy["import"].int_field == 42

        config.proxy.import_.new_field = "New Value"
        assert config.proxy.import_.new_field == "New Value"
        assert config.proxy._extra_data["import"]["new_field"] == "New Value"
        assert config._extra_data["import"]["new_field"] == "New Value"
        assert config.proxy["import"].new_field == "New Value"
        assert config.proxy["import"]["new_field"] == "New Value"


class TestToDictAlias:
    """Test that aliases are resolved properly when using the to_dict function."""

    @pytest.mark.parametrize(
        "config_class",
        [
            Config,
            ConfigExtra,
        ],
    )
    def test_to_dict_with_aliases(
        self,
        config_class: type[Config | ConfigExtra],
    ):
        config = config_class(
            data=AliasConfig(attr_field=55, str_field="AliasTest"), schema=AliasConfig
        )

        dump = config.to_dict()
        assert dump["dict_field"] == 55
        assert dump["str_field"] == "AliasTest"
        assert "attr_field" not in dump
