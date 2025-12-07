from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from eyconf import Config

from eyconf.decorators import allow_additional
from eyconf.validation import MultiConfigurationError


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


@dataclass
class Config42Required:
    int_field: int
    str_field: str = "FortyTwo!"


@dataclass
class ConfigNested:
    nested: Config42 = field(default_factory=Config42)
    nested_optional: Config42 | None = None
    other_field: str = "Hello, World!"


@allow_additional
@dataclass
class Config42AllowAdditional(Config42):
    pass


@pytest.fixture
def conf42() -> Config[Config42]:
    return Config(Config42(), schema=Config42)


@pytest.fixture
def conf_nested() -> Config[ConfigNested]:
    return Config(ConfigNested(), schema=ConfigNested)


class TestCreation:
    def test_init(self):
        conf = Config(Config42(), schema=Config42)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

    def test_init_dict(self):
        conf_dict = Config(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42)

    def test_init_dict_with_required(self):
        conf_dict = Config(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42Required,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42Required)

    def test_init_dict_no_schema(self):
        conf = Config(Config42())
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

        with pytest.raises(ValueError):
            Config(
                {"int_field": "not_an_int", "str_field": "Dict value!"},
            )

    def test_init_with_invalid_data(self):
        with pytest.raises(MultiConfigurationError):
            Config({"int_field": "not_an_int"}, schema=Config42)

    def test_init_with_missing_required_fields(self):
        with pytest.raises(MultiConfigurationError):
            Config({"str_field": "test"}, schema=Config42)

    def test_init_with_allow_additional(self):
        """Test that additional fields are handled correctly based on schema.
        Allow to validate additional fields when schema allows them.
        """
        data = {"int_field": 42, "str_field": "test", "extra_field": "unexpected"}
        with pytest.raises(MultiConfigurationError):
            Config(
                data,
                schema=Config42,
            )

        conf = Config(
            data,
            schema=Config42AllowAdditional,
        )
        assert conf.data.int_field == 42
        assert conf.data.str_field == "test"
        with pytest.raises(AttributeError):
            conf.data.extra_field  # type: ignore

    def test_init_invalid(self):
        with pytest.raises(ValueError):
            Config(
                ConfigNested,  # type: ignore
                ConfigNested,
            )


class TestUpdate:
    """Update should allow to apply partial updates to the configuration,
    validating only the provided fields, and leaving others unchanged.
    """

    def test_simple(self, conf42: Config[Config42]):
        conf42.update({"int_field": 100, "str_field": "Updated value!"})

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Updated value!"

    def test_partial(self, conf42: Config[Config42]):
        conf42.update({"int_field": 100})

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "FortyTwo!"

    def test_nested(self, conf_nested: Config[ConfigNested]):
        conf_nested.update(
            {
                "nested": {"int_field": 100, "str_field": "Updated nested value!"},
                "nested_optional": {"int_field": 200, "str_field": "Optional nested!"},
                "other_field": "Updated parent value!",
            }
        )

        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "Updated nested value!"
        assert conf_nested.data.nested_optional.int_field == 200  # type: ignore[union-attr]
        assert conf_nested.data.nested_optional.str_field == "Optional nested!"  # type: ignore[union-attr]
        assert conf_nested.data.other_field == "Updated parent value!"

    def test_nested_partial(self, conf_nested: Config[ConfigNested]):
        conf_nested.update(
            {
                "nested": {"int_field": 100},
            }
        )

        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "FortyTwo!"
        assert conf_nested.data.other_field == "Hello, World!"
        assert conf_nested.data.nested_optional is None

    def test_invalid(self, conf42: Config[Config42]):
        with pytest.raises(MultiConfigurationError):
            conf42.update({"int_field": "not an int"})

        assert conf42.data.int_field == 42

    def test_update_additional(self, conf_nested):
        with pytest.raises(AttributeError, match="Cannot set non-schema field"):
            conf_nested.update({"int_field": 100, "new_field": "I am new!"})

        with pytest.raises(AttributeError, match="nested.new_field"):
            conf_nested.update(
                {
                    "nested": {"int_field": 100, "new_field": "I am new in nested!"},
                }
            )

    def test_dynamic_fields(self):
        """Test that dynamic fields are not affected by update.

        This is a bit of an edge case, that should not really be used in practice...
        """
        conf42_add = Config(Config42AllowAdditional(), schema=Config42AllowAdditional)
        conf42_add.data.dynamic_field = "I am dynamic!"  # type: ignore

        conf42_add.update({"int_field": 100, "dynamic_field": "I am still dynamic!"})

        assert conf42_add.data.int_field == 100
        assert conf42_add.data.dynamic_field == "I am still dynamic!"  # type: ignore


class TestOverwrite:
    def test_simple(self, conf42: Config[Config42]):
        conf42.overwrite(
            {
                "int_field": 100,
                "str_field": "Overwritten value!",
            }
        )

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Overwritten value!"

        # Overwrite with Config instance
        new_conf = Config42(int_field=200, str_field="Another overwrite!")
        conf42.overwrite(new_conf)
        assert conf42.data.int_field == 200
        assert conf42.data.str_field == "Another overwrite!"

    def test_invalid(self, conf42: Config[Config42]):
        with pytest.raises(MultiConfigurationError):
            conf42.overwrite({"int_field": "not an int", "str_field": "Valid str"})

        with pytest.raises(MultiConfigurationError):
            conf42.overwrite({"str_field": "Missing int field"})

    def test_nested(self, conf_nested: Config[ConfigNested]):
        conf_nested.overwrite(
            {
                "nested": {"int_field": 100, "str_field": "Overwritten nested!"},
                "nested_optional": {"int_field": 200, "str_field": "Optional nested!"},
                "other_field": "Overwritten parent!",
            }
        )

        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "Overwritten nested!"
        assert conf_nested.data.nested_optional.int_field == 200  # type: ignore[union-attr]
        assert conf_nested.data.nested_optional.str_field == "Optional nested!"  # type: ignore[union-attr]
        assert conf_nested.data.other_field == "Overwritten parent!"


class TestReset:
    def test_simple(self, conf42: Config[Config42]):
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

    def test_nested(self, conf_nested: Config[ConfigNested]):
        conf_nested.update(
            {
                "nested": {"int_field": 100, "str_field": "Updated nested value!"},
                "nested_optional": {"int_field": 200, "str_field": "Optional nested!"},
                "other_field": "Updated parent value!",
            }
        )

        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "Updated nested value!"
        assert conf_nested.data.nested_optional.int_field == 200  # type: ignore[union-attr]
        assert conf_nested.data.nested_optional.str_field == "Optional nested!"  # type: ignore[union-attr]
        assert conf_nested.data.other_field == "Updated parent value!"

        conf_nested.reset()

        assert conf_nested.data.nested.int_field == 42
        assert conf_nested.data.nested.str_field == "FortyTwo!"
        assert conf_nested.data.nested_optional is None
        assert conf_nested.data.other_field == "Hello, World!"


class TestConverters:
    def test_to_dict(self, conf42: Config[Config42]):
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }
        assert conf42.to_dict() == expected

    def test_to_yaml(self, conf42: Config[Config42]):
        yaml_str = conf42.to_yaml()
        assert "int_field: 42" in yaml_str
        assert "str_field: FortyTwo!" in yaml_str


class TestPrintingUtils:
    @pytest.mark.parametrize(
        "fixture_name,expected_lines",
        [
            ("conf42", ["  int_field: 42", "  str_field: FortyTwo!"]),
            (
                "conf_nested",
                ["  nested:", "    int_field: 42", "  other_field: Hello, World!"],
            ),
        ],
    )
    def test_str_formats_data(self, fixture_name, expected_lines, request):
        """Test that __str__ properly formats configuration data"""
        conf = request.getfixturevalue(fixture_name)
        str_output = str(conf)

        for expected_line in expected_lines:
            assert expected_line in str_output

    def test_repr_includes_object_info_and_data(self, conf42: Config[Config42]):
        """Test that __repr__ includes basic object info and formatted data"""
        repr_str = repr(conf42)

        # Basic object info
        assert repr_str.startswith("<Config object at 0x")
        # Delegates to __str__ for data
        assert "int_field: 42" in repr_str

    @pytest.mark.parametrize(
        "test_data,expected",
        [
            ({"key": "value"}, ["key: value"]),
            ({"nested": {"inner": "val"}}, ["nested:", "    inner: val"]),
            ({}, []),
        ],
    )
    def test_pretty_format_basic_cases(
        self, test_data, expected, conf42: Config[Config42]
    ):
        """Test _pretty_format with basic cases"""
        formatted = conf42._pretty_format(test_data)

        if expected:
            for line in expected:
                assert line in formatted
        else:
            assert formatted == ""
