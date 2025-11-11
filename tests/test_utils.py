from eyconf.utils import AttributeDict, AccessProxy, dict_access, DictAccess
from dataclasses import dataclass, field

from eyconf.asdict import asdict_with_aliases

@dict_access
@dataclass
class Nested:
    str_field: str = "FortyTwo"


@dict_access
@dataclass
class Config42:
    int_field: int = 42
    nested: Nested = field(default_factory=Nested)


class TestAttributeDict:
    def test_init(self):
        attr_dict = AttributeDict(**{"foo": "bar", "nested": {"level": 42}})
        assert isinstance(attr_dict, AttributeDict)
        assert attr_dict.foo == "bar"

        assert isinstance(attr_dict.nested, AttributeDict)
        assert attr_dict.nested.level == 42

    def test_set_get(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore

        assert attr_dict.foo == "bar"

    def test_nested(self):
        attr_dict = AttributeDict()
        attr_dict.nested.level = 42

        assert attr_dict.nested.level == 42

    def test_as_dict(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore
        attr_dict.nested.level = 42  # type: ignore

        expected = {
            "foo": "bar",
            "nested": {
                "level": 42,
            },
        }

        assert attr_dict.as_dict() == expected

    def test_bool_conversion(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore

        assert bool(attr_dict) is True

        empty_attr_dict = AttributeDict()
        assert bool(empty_attr_dict) is False


class TestAccessProxy:
    def test_access_fails(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        assert proxy.int_field == 42

    def test_set(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.int_field = 100

        assert proxy.int_field == 100
        assert config_data.int_field == 100

    def test_del(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        assert proxy.int_field == 42

        del proxy.int_field
        del proxy._data

    def test_set_extra(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"  # type: ignore

        assert proxy.int_field == 42
        assert proxy.foo == "bar"

        # make sure it actually sits in _additional_data
        assert proxy._extra_data.foo == "bar"  # type: ignore

    def test_del_extra(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"  # type: ignore

        assert proxy.foo == "bar"

        del proxy.foo  # type: ignore


class TestDictStyleAccess:
    """Test the @dict_access decorator functionality."""

    def test_get_data(self):
        config = Config42()

        # Note that placing `assert isinstance(config, DictAccess)` here
        # will make some runtime type checkers error about the attribute access
        # Once you place the assert, better stick to dict-style access
        # for the rest of the scope
        assert isinstance(config, DictAccess)
        assert isinstance(config["nested"], DictAccess)

        assert config.int_field == 42
        assert config.nested.str_field == "FortyTwo"

        assert config["int_field"] == 42
        assert config["nested"]["str_field"] == "FortyTwo"


@dataclass
class ConfigWithProperty:
    int_field: int = 42

    @property
    def computed_property(self) -> str:
        return f"int_filed={self.int_field}"


class TestAsDict:
    """Test our customized asdict_with_aliases function.

    Besides the alias resolution, it also supports extracting
    properties and non-field attributes.

    Alias resolution is tested in test_alias.py
    """

    def test_asdict(self):

        config = ConfigWithProperty()
        config.non_field_attr = 100 # type: ignore
        dump = asdict_with_aliases(config)

        assert config.computed_property == "int_filed=42"
        assert config.non_field_attr == 100  # type: ignore

        assert dump["int_field"] == 42
        # by defaults all extras are disabled
        assert "computed_property" not in dump
        assert "non_field_attr" not in dump

        dump_with_props = asdict_with_aliases(
            config,
            include_properties=True,
            include_attributes=False,
        )

        assert dump_with_props["int_field"] == 42
        assert dump_with_props["computed_property"] == "int_filed=42"
        assert "non_field_attr" not in dump_with_props

        dump_with_attrs = asdict_with_aliases(
            config,
            include_properties=False,
            include_attributes=True,
        )
        assert dump_with_attrs["int_field"] == 42
        assert dump_with_attrs["non_field_attr"] == 100  # type: ignore
        assert "computed_property" not in dump_with_attrs


