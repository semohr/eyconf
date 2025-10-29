from dataclasses import dataclass
from eyconf.config import EYConfExtraFields
from eyconf.utils import AccessProxy


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
