from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

import pytest
from eyconf import EYConfBase

from eyconf.utils import AttributeDict
from eyconf.validation import MultiConfigurationError


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "FortyTwo!"


@dataclass
class Config42AllowAdditional(Config42):
    __allow_additional: ClassVar[bool] = True


@dataclass
class Config42Required:
    int_field: int
    str_field: str = "FortyTwo!"


@dataclass
class ConfigNested:
    nested: Config42 = field(default_factory=Config42)
    nested_optional: Config42 | None = None
    other_field: str = "Hello, World!"


@pytest.fixture
def conf42() -> EYConfBase[Config42]:
    return EYConfBase(Config42(), schema=Config42)


@pytest.fixture
def conf_nested() -> EYConfBase[ConfigNested]:
    return EYConfBase(ConfigNested(), schema=ConfigNested)


@pytest.fixture
def conf42_add() -> EYConfBase[Config42AllowAdditional]:
    return EYConfBase(Config42AllowAdditional(), schema=Config42AllowAdditional)


class TestCreation:
    def test_init(self):
        conf = EYConfBase(Config42(), schema=Config42)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

    def test_init_dict(self):
        conf_dict = EYConfBase(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42)

    def test_init_dict_with_required(self):
        conf_dict = EYConfBase(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42Required,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42Required)

    def test_init_dict_no_schema(self):
        conf = EYConfBase(Config42())
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

        with pytest.raises(ValueError):
            EYConfBase(
                {"int_field": "not_an_int", "str_field": "Dict value!"},
            )

    def test_init_with_invalid_data(self):
        with pytest.raises(MultiConfigurationError):
            EYConfBase({"int_field": "not_an_int"}, schema=Config42)

    def test_init_with_missing_required_fields(self):
        with pytest.raises(MultiConfigurationError):
            EYConfBase({"str_field": "test"}, schema=Config42)

    def test_init_with_extra_fields(self):
        data = {"int_field": 42, "str_field": "test", "extra_field": "unexpected"}
        with pytest.raises(MultiConfigurationError):
            EYConfBase(
                data,
                schema=Config42,
            )

        conf = EYConfBase(
            data,
            schema=Config42AllowAdditional,
        )
        assert conf.data.int_field == 42
        assert conf.data.str_field == "test"
        assert conf.data.extra_field == "unexpected"  # type: ignore


class TestUpdate:
    """Update should allow to apply partial updates to the configuration,
    validating only the provided fields, and leaving others unchanged.
    """

    def test_simple(self, conf42: EYConfBase[Config42]):
        conf42.update({"int_field": 100, "str_field": "Updated value!"})

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Updated value!"

    def test_partial(self, conf42: EYConfBase[Config42]):
        conf42.update({"int_field": 100})

        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "FortyTwo!"

    def test_nested(self, conf_nested: EYConfBase[ConfigNested]):
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

    def test_nested_partial(self, conf_nested: EYConfBase[ConfigNested]):
        conf_nested.update(
            {
                "nested": {"int_field": 100},
            }
        )

        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "FortyTwo!"
        assert conf_nested.data.other_field == "Hello, World!"
        assert conf_nested.data.nested_optional is None

    def test_invalid(self, conf42: EYConfBase[Config42]):
        with pytest.raises(MultiConfigurationError):
            conf42.update({"int_field": "not an int"})

        assert conf42.data.int_field == 42

    def test_additional_fields(self, conf42_add: EYConfBase[Config42AllowAdditional]):
        conf42_add.update({"int_field": 100, "new_field": "I am new!"})

        assert conf42_add.data.int_field == 100
        assert conf42_add.data.new_field == "I am new!"  # type: ignore[attr-defined]

    def test_additional_fields_nested(
        self, conf42_add: EYConfBase[Config42AllowAdditional]
    ):
        conf42_add.update(
            {
                "nested": {"new_nested_field": {"foo": "bar"}},
            }
        )

        assert conf42_add.data.nested.new_nested_field.foo == "bar"  # type: ignore[attr-defined]
        assert isinstance(conf42_add.data.nested.new_nested_field, AttributeDict)  # type: ignore[attr-defined]

    def test_additional_fields_nested_deep(
        self, conf42_add: EYConfBase[Config42AllowAdditional]
    ):
        # Even more nesting
        conf42_add.update(
            {
                "nested": {"d1": {"d2": {"d3": {"d4_field": "deep value!"}}}},
            }
        )
        assert conf42_add.data.nested.d1.d2.d3.d4_field == "deep value!"  # type: ignore[attr-defined]


class TestOverwrite:
    def test_simple(self, conf42: EYConfBase[Config42]):
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

    def test_invalid(self, conf42: EYConfBase[Config42]):
        with pytest.raises(MultiConfigurationError):
            conf42.overwrite({"int_field": "not an int", "str_field": "Valid str"})

        with pytest.raises(MultiConfigurationError):
            conf42.overwrite({"str_field": "Missing int field"})

    def test_nested(self, conf_nested: EYConfBase[ConfigNested]):
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
    def test_simple(self, conf42: EYConfBase[Config42]):
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

    def test_nested(self, conf_nested: EYConfBase[ConfigNested]):
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

    def test_additional_fields_removed(
        self, conf42_add: EYConfBase[Config42AllowAdditional]
    ):
        conf42_add.update(
            {
                "int_field": 100,
                "new_field": "I am new!",
            }
        )

        assert conf42_add.data.int_field == 100
        assert conf42_add.data.new_field == "I am new!"  # type: ignore[attr-defined]

        conf42_add.reset()

        assert conf42_add.data.int_field == 42
        with pytest.raises(AttributeError):
            _ = conf42_add.data.new_field  # type: ignore[attr-defined]


class TestConverters:
    def test_schema_data_as_dict(self, conf42: EYConfBase[Config42]):
        expected = {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }
        assert conf42.to_dict() == expected

    def test_extra_data_as_dict(self, conf42_add: EYConfBase[Config42AllowAdditional]):
        conf42_add.update({"new_field": "I am new!"})

        assert conf42_add.to_dict(include_additional=True) == {
            "int_field": 42,
            "str_field": "FortyTwo!",
            "new_field": "I am new!",
        }
        assert conf42_add.to_dict() == {
            "int_field": 42,
            "str_field": "FortyTwo!",
        }

    def test_extra_data_as_dict_nested(self):
        @dataclass
        class NestedAllowAdditional:
            nested: Config42AllowAdditional = field(
                default_factory=Config42AllowAdditional
            )
            nested_optional: Config42AllowAdditional | None = None
            other_field: str = "Hello, World!"
            __allow_additional: ClassVar[bool] = True

        conf_nested = EYConfBase(NestedAllowAdditional(), schema=NestedAllowAdditional)
        conf_nested.update(
            {
                "nested": {"new_nested_field": {"foo": "bar"}},
                "another_extra": 123,
            }
        )

        assert conf_nested.to_dict(include_additional=True) == {
            "nested": {
                "int_field": 42,
                "str_field": "FortyTwo!",
                "new_nested_field": {"foo": "bar"},
            },
            "nested_optional": None,
            "other_field": "Hello, World!",
            "another_extra": 123,
        }
        assert conf_nested.to_dict() == {
            "nested": {
                "int_field": 42,
                "str_field": "FortyTwo!",
            },
            "nested_optional": None,
            "other_field": "Hello, World!",
        }

    def test_to_yaml(self, conf42: EYConfBase[Config42]):
        expected_yaml = "int_field: 42\nstr_field: FortyTwo!"
        assert conf42.to_yaml() == expected_yaml

    def test_update_additional_property_list(self, conf42_add: EYConfBase[Config42]):
        """Test updating additional list properties"""

        conf42_add.update({"extra_list": [1, 2, 3]})
        conf42_add.update({"extra_list": ["a", "b", "c"]})

        assert conf42_add.data.extra_list == ["a", "b", "c"]  # type: ignore[attr-defined]

    def test_error_without_additional_properties(self, conf42: EYConfBase[Config42]):
        """Test that updating additional properties without allowing them raises an error"""
        with pytest.raises(AttributeError):
            conf42.update({"extra_field": "not allowed"})


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

    def test_repr_includes_object_info_and_data(self, conf42: EYConfBase[Config42]):
        """Test that __repr__ includes basic object info and formatted data"""
        repr_str = repr(conf42)

        # Basic object info
        assert repr_str.startswith("<EYConfBase object at 0x")
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
        self, test_data, expected, conf42: EYConfBase[Config42]
    ):
        """Test _pretty_format with basic cases"""
        formatted = conf42._pretty_format(test_data)

        if expected:
            for line in expected:
                assert line in formatted
        else:
            assert formatted == ""
