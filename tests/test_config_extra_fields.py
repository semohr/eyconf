from copy import deepcopy
from dataclasses import dataclass, field
import pytest
from eyconf.config import ConfigExtra
from eyconf.config.extra_fields import AccessProxy, AttributeDict


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

    def test_init_invalid(self):
        with pytest.raises(ValueError):
            ConfigExtra(Config42)  # type: ignore


class TestDataProperties:
    def test_schema_data(self, conf42: ConfigExtra[Config42]):
        schema_data = conf42.schema_data
        assert isinstance(schema_data, Config42)
        assert schema_data.int_field == 42
        assert schema_data.str_field == "FortyTwo!"

    def test_extra_data(self, conf42: ConfigExtra[Config42]):
        conf42.data.new_field = "New Value"
        extra_data = conf42.extra_data
        assert isinstance(extra_data, AttributeDict)
        assert extra_data.new_field == "New Value"


class TestUpdate:
    def test_unknown_field(self):
        config = ConfigExtra(Config42())

        config.update({"unknown_field": "I am unknown!"})

        assert config.data.unknown_field == "I am unknown!"
        assert config._extra_data.unknown_field == "I am unknown!"
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
        assert config.data.nested.unknown_field == "I am unknown!"

    def test_unknown_nested(self):
        config = ConfigExtra(Config42())

        config.update({"level_one": {"level_two": {"level_three": "Deep Value"}}})
        assert config.data.level_one.level_two.level_three == "Deep Value"


class TestToDict:
    """Tests for the to_dict method.
    This should resolve AccessProxy and AttributeDict instances correctly.
    """

    def test_to_dict_no_extra(self, conf42: ConfigExtra[Config42]):
        result = conf42.to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }
        assert result == expected

    def test_to_dict_with_extra(self, conf42: ConfigExtra[Config42]):
        conf42.data.new_field = "New Value"
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


class TestAttributeDict:
    def test_init(self):
        attr_dict = AttributeDict(**{"foo": "bar", "nested": {"level": 42}})
        assert isinstance(attr_dict, AttributeDict)
        assert attr_dict.foo == "bar"

        assert isinstance(attr_dict.nested, AttributeDict)
        assert attr_dict.nested.level == 42

    def test_attribute_assignment(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"
        assert attr_dict.foo == "bar"

    def test_attribute_assignment_nested(self):
        attr_dict = AttributeDict()
        attr_dict.nested.level = 42

        assert attr_dict.nested.level == 42

    def test_item_assignment(self):
        attr_dict = AttributeDict()
        attr_dict["foo"] = "bar"
        assert attr_dict["foo"] == "bar"

    def test_item_assignment_nested(self):
        attr_dict = AttributeDict()
        attr_dict["nested"] = {}
        attr_dict["nested"]["level"] = 42

        assert attr_dict["nested"]["level"] == 42

    def test_to_dict(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"
        attr_dict.nested.level = 42

        expected = {
            "foo": "bar",
            "nested": {
                "level": 42,
            },
        }
        assert attr_dict.to_dict() == expected

    @pytest.mark.parametrize(
        "data,expected",
        [
            ({"foo": "bar"}, True),
            ({}, False),
        ],
    )
    def test_bool_conversion(self, data, expected):
        attr_dict = AttributeDict(**data)
        assert bool(attr_dict) is expected

    def test_deepcopy(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"
        attr_dict.nested.level = 42

        copied = deepcopy(attr_dict)

        assert copied.foo == "bar"
        assert copied.nested.level == 42

        # Modify original to ensure deep copy
        attr_dict.foo = "changed"
        attr_dict.nested.level = 100

        assert copied.foo == "bar"
        assert copied.nested.level == 42

    def test_repr_str(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"
        attr_dict.nested.level = 42

        repr_str = repr(attr_dict)
        str_str = str(attr_dict)

        expected_dict = {
            "foo": "bar",
            "nested": {
                "level": 42,
            },
        }

        assert repr_str == f"AttributeDict({expected_dict})"
        assert str_str == str(expected_dict)

    @pytest.mark.parametrize(
        "data,other,expected",
        [
            (
                AttributeDict(**{"foo": "bar"}),
                AttributeDict(**{"foo": "bar"}),
                True,
            ),
            (
                AttributeDict(**{"foo": "bar"}),
                AttributeDict(**{"foo": "different"}),
                False,
            ),
            (
                AttributeDict(**{"foo": "bar"}),
                {"foo": "bar"},
                True,
            ),
            (
                AttributeDict(**{"foo": "bar"}),
                {"foo": "different"},
                False,
            ),
            (
                AttributeDict(**{"foo": "bar"}),
                "not a dict",
                False,
            ),
        ],
    )
    def test_equality(self, data, other, expected):
        if expected:
            assert data == other
        else:
            assert data != other


class TestAccessProxy:
    @pytest.fixture
    def proxy(self):
        config_data = Config42()
        extra_data = AttributeDict()
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
        assert proxy._extra_data.new_field == "baz"

    def test_attribute_assignment_nested(self, proxy):
        proxy.nested.level = 42
        assert proxy.nested.level == 42
        assert proxy._extra_data.nested.level == 42

    def test_item_assignment(self, proxy):
        proxy["int_field"] = 100
        proxy["new_field"] = "baz"

        assert proxy["int_field"] == 100
        assert proxy["new_field"] == "baz"

    def test_item_assignment_nested(self, proxy):
        proxy["nested"] = {}
        proxy["nested"]["level"] = 42

        assert proxy["nested"]["level"] == 42
        assert proxy._extra_data.nested.level == 42

    def test_to_dict(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"

        result = proxy.to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "foo": "bar",
        }
        assert result == expected
