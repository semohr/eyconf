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
        assert extra_data.new_field == "New Value"  # type: ignore


class TestUpdate:
    def test_unknown_field(self):
        config = ConfigExtra(Config42())

        config.update({"unknown_field": "I am unknown!"})

        assert config.data.unknown_field == "I am unknown!"  # type: ignore[attr-defined]
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
                    }
                }
            }
        )

        assert config.data.nested.folders["config1"].int_field == 1
        assert config.data.nested.folders["config1"].str_field == "One"
        assert config.data.nested.folders["config2"].int_field == 2
        assert config.data.nested.folders["config2"].str_field == "Two"

    def test_unknown_nested(self):
        config = ConfigExtra(Config42())

        config.update({"level_one": {"level_two": {"level_three": "Deep Value"}}})
        assert config.data.level_one.level_two.level_three == "Deep Value"  # type: ignore[attr-defined]


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

        # Should also be possible with the .data
        result_data = conf42.data.to_dict()
        assert result_data == expected

    def test_to_dict_with_extra(self, conf42: ConfigExtra[Config42]):
        conf42.data.new_field = "New Value"
        result = conf42.to_dict()
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "new_field": "New Value",
        }
        assert result == expected

        # Should also be possible with the .extra_data
        extra_dict = conf42.extra_data.to_dict()
        assert extra_dict == {"new_field": "New Value"}
