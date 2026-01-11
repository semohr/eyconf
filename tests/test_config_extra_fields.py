from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
import pytest
from eyconf.config import ConfigExtra
from eyconf.config.extra_fields import AccessProxy


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


@pytest.fixture
def conf42() -> ConfigExtra[Config42]:
    return ConfigExtra(Config42())


class TestCreation:
    def test_init(self):
        config = ConfigExtra(Config42())

        assert isinstance(config.data, AccessProxy)
        assert config.data.int_field == 42
        assert config.data.str_field == "FortyTwo!"

    def test_init_dict(self):
        config = ConfigExtra({"int_field": 10, "str_field": "Ten"}, schema=Config42)

        assert isinstance(config.data, AccessProxy)
        assert config.data.int_field == 10
        assert config.data.str_field == "Ten"

        # Should raise if not schema provided
        with pytest.raises(ValueError):
            ConfigExtra({"int_field": 10, "str_field": "Ten"})


class TestDataProperties:
    def test_schema_data(self, conf42: ConfigExtra[Config42]):
        schema_data = conf42.schema_data
        assert isinstance(schema_data, Config42)
        assert schema_data.int_field == 42
        assert schema_data.str_field == "FortyTwo!"

    def test_extra_data(self, conf42: ConfigExtra[Config42]):
        conf42.proxy.new_field = "New Value"
        assert isinstance(conf42.proxy._extra_data, dict)
        assert conf42.proxy._extra_data["new_field"] == "New Value"
        assert conf42.proxy["new_field"] == "New Value"
        assert conf42.proxy.new_field == "New Value"


class TestUpdate:
    def test_unknown_field(self):
        config = ConfigExtra(Config42())

        config.update({"unknown_field": "I am unknown!"})

        assert config.proxy.unknown_field == "I am unknown!"
        assert config._extra_data["unknown_field"] == "I am unknown!"
        with pytest.raises(AttributeError):
            _ = config._data.non_existent_field  # type: ignore[attr-defined]

    def test_dict(self):
        @dataclass
        class SchemaDict:
            folders: dict[str, Config42] = field(
                default_factory=lambda: {"placeholder": Config42()}
            )

        config = ConfigExtra(SchemaDict())

        assert config.data.folders["placeholder"].int_field == 42
        for folder in config.data.folders.values():
            assert isinstance(folder, Config42)

        config.update(
            {
                "folders": {
                    "config1": {"int_field": 1, "str_field": "One"},
                    "config2": {"int_field": 2, "str_field": "Two"},
                }
            }
        )

        assert config.data.folders["config1"].int_field == 1
        assert config.data.folders["config1"].str_field == "One"
        assert config.data.folders["config2"].int_field == 2
        assert config.data.folders["config2"].str_field == "Two"

        # We should revise this with a merge strategy later
        with pytest.raises(KeyError):
            config.data.folders["placeholder"]

    def test_dict_nested(self):
        @dataclass
        class NestedSchema:
            folders: dict[str, Config42] = field(
                default_factory=lambda: {"placeholder": Config42()}
            )

        @dataclass
        class SchemaWithNested:
            nested: NestedSchema = field(default_factory=NestedSchema)

        config = ConfigExtra(SchemaWithNested())

        assert config.data.nested.folders["placeholder"].int_field == 42
        for folder in config.data.nested.folders.values():
            assert isinstance(folder, Config42)

        config.update(
            {
                "nested": {
                    "folders": {
                        "config1": {"int_field": 1, "str_field": "One"},
                        "config2": {"int_field": 2, "str_field": "Two"},
                    },
                    "unknown_field": "I am unknown!",
                }
            }
        )

        assert config.data.nested.folders["config1"].int_field == 1
        assert config.data.nested.folders["config1"].str_field == "One"
        assert config.data.nested.folders["config2"].int_field == 2
        assert config.data.nested.folders["config2"].str_field == "Two"
        assert config.proxy.nested.unknown_field == "I am unknown!"

    @pytest.mark.skip(reason="Changed design, no longer using attribute dicts")
    def test_unknown_nested(self):
        config = ConfigExtra(Config42())

        config.update({"level_one": {"level_two": {"level_three": "Deep Value"}}})
        assert config.proxy.level_one.level_two.level_three == "Deep Value"


class TestToDict:
    """Tests for the to_dict method.
    This should resolve AccessProxy instances correctly.
    """

    def test_to_dict_no_extra(self, conf42: ConfigExtra[Config42]):
        result = conf42.to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }
        assert result == expected

    def test_to_dict_with_extra(self, conf42: ConfigExtra[Config42]):
        conf42.proxy.new_field = "New Value"
        result = conf42.to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "new_field": "New Value",
        }
        assert result == expected

        # Should also allow extra_fields=False
        result_no_extra = conf42.to_dict(extra_fields=False)
        expected_no_extra = {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }
        assert result_no_extra == expected_no_extra


class TestAccessProxy:
    @pytest.fixture
    def proxy(self):
        config_data = Config42()
        extra_data: dict[str, Any] = dict()
        return AccessProxy(
            config_data,
            extra_data,
        )

    def test_attribute_assignment(self, proxy):
        proxy.int_field = 100
        proxy.new_field = "baz"

        assert proxy.int_field == 100
        assert proxy.new_field == "baz"
        assert proxy._data.int_field == 100
        assert proxy._extra_data["new_field"] == "baz"

    @pytest.mark.skip(reason="Changed design, no longer using attribute dicts")
    def test_attribute_assignment_nested(self, proxy):
        proxy.nested.level = 42
        assert proxy.nested.level == 42
        assert proxy._extra_data.nested.level == 42

    def test_attribute_assignment_other_ap(self, proxy):
        """
        Access Proxies should never hold other Access Proxies, this can only happen
        if we (accidentally) set a custom field manually.
        """
        proxy.nested = AccessProxy(
            Config42(),
            {"lorem": "ipsum"},
        )

        assert not isinstance(proxy.nested, AccessProxy)

        unpacked = proxy._to_dict()
        assert unpacked == {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "nested": {
                "int_field": 42,
                "str_field": "FortyTwo!",
                "lorem": "ipsum",
            },
        }

    def test_item_assignment(self, proxy):
        proxy["int_field"] = 100
        proxy["new_field"] = "baz"

        assert proxy["int_field"] == 100
        assert proxy["new_field"] == "baz"

    def test_item_assignment_nested(self, proxy):
        proxy["nested"] = {}
        proxy["nested"]["level"] = 42

        assert proxy["nested"]["level"] == 42
        assert proxy._extra_data["nested"]["level"] == 42

    def test_to_dict(self):
        config_data = Config42()
        extra_data: dict[str, Any] = dict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"

        result = proxy._to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "foo": "bar",
        }
        assert result == expected

    def test_to_dict_nested(self):
        @dataclass
        class NestedConfig:
            nested_42: Config42

        config_data = NestedConfig(nested_42=Config42())
        extra_data: dict[str, Any] = dict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        result = proxy._to_dict()
        expected = {
            "nested_42": {
                "int_field": 42,
                "str_field": "FortyTwo!",
            }
        }
        assert result == expected

    def test_deepcopy_equality(self):
        config_data = Config42()
        extra_data: dict[str, Any] = dict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        proxy_2 = deepcopy(proxy)
        assert proxy_2 == proxy
        assert proxy_2._to_dict() == proxy._to_dict()

    def test_hash(self):
        config_data = Config42()
        extra_data: dict[str, Any] = dict(list_for_hash=[1, 2, 3])
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        proxy_2 = deepcopy(proxy)
        assert hash(proxy_2) == hash(proxy)


class TestReset:
    def test_simple(self, conf42: ConfigExtra[Config42]):
        conf42.update(
            {
                "int_field": 100,
                "str_field": "Updated value!",
            }
        )

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Updated value!"

        conf42.reset()

        assert conf42.data.int_field == 42
        assert conf42.data.str_field == "FortyTwo!"
