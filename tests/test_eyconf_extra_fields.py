from dataclasses import dataclass, field
import pytest
from eyconf.config import EYConfExtraFields
from eyconf.config.extra_fields import AccessProxy


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


class TestEYConfExtraFields:
    def test_init(self):
        config = EYConfExtraFields(Config42())

        assert isinstance(config.data, AccessProxy)
        assert config.data.int_field == 42

    def test_set_data(self):
        config = EYConfExtraFields(Config42())

        config.data.int_field = 100
        config.data.new_field = "Hundred"  # type: ignore

        assert config.data.int_field == 100
        assert config.data.new_field == "Hundred"  # type: ignore

        assert config.to_dict() == {
            "int_field": 100,
            "str_field": "FortyTwo!",
            "new_field": "Hundred",
        }

        assert config.to_dict(False) == {
            "int_field": 100,
            "str_field": "FortyTwo!",
        }

    def test_set_mixed(self):
        config = EYConfExtraFields(Config42())

        config.data.new_field = "New Value"  # type: ignore
        config.data.nested.foo = "Bar"  # type: ignore
        config.data.nested.very_deep.another_level = 123  # type: ignore

        assert config.data.new_field == "New Value"  # type: ignore
        assert config.data.nested.foo == "Bar"  # type: ignore
        assert config.data.nested.very_deep.another_level == 123  # type: ignore

        assert config.to_dict() == {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "new_field": "New Value",
            "nested": {
                "foo": "Bar",
                "very_deep": {
                    "another_level": 123,
                },
            },
        }

        assert config.to_dict(False) == {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }

    def test_update_unknown_field(self):
        config = EYConfExtraFields(Config42())

        config.update({"unknown_field": "I am unknown!"})

        assert config.data.unknown_field == "I am unknown!"  # type: ignore[attr-defined]
        assert config._extra_data.unknown_field == "I am unknown!"
        with pytest.raises(AttributeError):
            _ = config._data.non_existent_field  # type: ignore[attr-defined]

    def test_update_dict(self):
        @dataclass
        class SchemaDict:
            folders: dict[str, Config42] = field(
                default_factory=lambda: {"placeholder": Config42()}
            )

        config = EYConfExtraFields(SchemaDict())

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

    def test_update_dict_nested(self):
        @dataclass
        class NestedSchema:
            folders: dict[str, Config42] = field(
                default_factory=lambda: {"placeholder": Config42()}
            )

        @dataclass
        class SchemaWithNested:
            nested: NestedSchema = field(default_factory=NestedSchema)

        config = EYConfExtraFields(SchemaWithNested())

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

    def test_update_unknown_nested(self):
        config = EYConfExtraFields(Config42())

        config.update({"level_one": {"level_two": {"level_three": "Deep Value"}}})
        assert config.data.level_one.level_two.level_three == "Deep Value"  # type: ignore[attr-defined]
