from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NamedTuple

import pytest
from eyconf import Config

from eyconf.decorators import allow_additional
from eyconf.validation import ConfigurationError, MultiConfigurationError
from eyconf.validation.backends.interface import Validator


# --------------------------------------------------------------------------- #
# Backend-parametrised fixtures (same pattern as validation/conftest.py)
# --------------------------------------------------------------------------- #


class ValidatorConfig(NamedTuple):
    backend: str
    allow_additional: bool


_VALIDATOR_PARAMS = [
    pytest.param(("json_schema", False), id="json_schema"),
    pytest.param(("pydantic", False), id="pydantic"),
]


@pytest.fixture(params=_VALIDATOR_PARAMS)
def validator_config(request: Any) -> ValidatorConfig:
    """Parametrised fixture yielding (backend, allow_additional) tuples."""
    return ValidatorConfig(*request.param)


@pytest.fixture
def validator(validator_config: ValidatorConfig) -> Validator[Any]:
    """Create a validator instance for the current backend configuration."""
    backend, allow_additional = validator_config

    if backend == "json_schema":
        from eyconf.validation.backends.json_schema import JsonSchemaValidator

        return JsonSchemaValidator(allow_additional=allow_additional)
    if backend == "pydantic":
        from eyconf.validation.backends.pydantic import PydanticValidator

        return PydanticValidator(allow_additional=allow_additional)

    raise ValueError(f"Unknown backend: {backend!r}")


# --------------------------------------------------------------------------- #
# Dataclass schemas
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Config fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def conf42(validator: Validator[Any]) -> Config[Config42]:
    return Config(Config42(), schema=Config42, validator=validator)


@pytest.fixture
def conf_nested(validator: Validator[Any]) -> Config[ConfigNested]:
    return Config(ConfigNested(), schema=ConfigNested, validator=validator)


class TestCreation:
    def test_init(self, validator: Validator[Any]) -> None:
        conf = Config(Config42(), schema=Config42, validator=validator)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

    def test_init_dict(self, validator: Validator[Any]) -> None:
        conf_dict = Config(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42,
            validator=validator,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42)

    def test_init_dict_with_required(self, validator: Validator[Any]) -> None:
        conf_dict = Config(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42Required,
            validator=validator,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42Required)

    def test_init_dict_no_schema(self, validator: Validator[Any]) -> None:
        conf = Config(Config42(), validator=validator)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "FortyTwo!"
        assert isinstance(conf.data, Config42)

        with pytest.raises(ValueError):
            Config(
                {"int_field": "not_an_int", "str_field": "Dict value!"},
                validator=validator,
            )

    def test_init_with_invalid_data(self, validator: Validator[Any]) -> None:
        with pytest.raises((MultiConfigurationError, ConfigurationError)):
            Config(
                {"int_field": "not_an_int"},
                schema=Config42,
                validator=validator,
            )

    def test_init_with_missing_required_fields(self, validator: Validator[Any]) -> None:
        # Config42 has defaults for both fields; providing only str_field
        # should succeed (int_field falls back to its default of 42).
        conf = Config({"str_field": "test"}, schema=Config42, validator=validator)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "test"

    def test_init_with_allow_additional(self, validator: Validator[Any]) -> None:
        """Test that additional fields are handled correctly based on schema."""
        data = {"int_field": 42, "str_field": "test", "extra_field": "unexpected"}
        with pytest.raises((MultiConfigurationError, ConfigurationError)):
            Config(data, schema=Config42, validator=validator)

        conf = Config(data, schema=Config42AllowAdditional, validator=validator)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "test"
        # Extra fields may or may not be directly accessible depending on
        # the backend (e.g. Pydantic stores them, JsonSchema does not).
        if hasattr(conf.data, "extra_field"):
            assert conf.data.extra_field == "unexpected"  # type: ignore[attr-defined]
        else:
            with pytest.raises(AttributeError):
                conf.data.extra_field  # type: ignore[attr-defined]

    def test_init_invalid(self, validator: Validator[Any]) -> None:
        with pytest.raises(ValueError):
            Config(
                ConfigNested,  # type: ignore
                ConfigNested,
                validator=validator,
            )


class TestUpdate:
    """Update should allow partial updates to the configuration,
    validating only the provided fields, and leaving others unchanged.
    """

    def test_simple(self, conf42: Config[Config42]) -> None:
        conf42.update({"int_field": 100, "str_field": "Updated value!"})
        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Updated value!"

    def test_partial(self, conf42: Config[Config42]) -> None:
        conf42.update({"int_field": 100})
        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "FortyTwo!"

    def test_nested(self, conf_nested: Config[ConfigNested]) -> None:
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

    def test_nested_partial(self, conf_nested: Config[ConfigNested]) -> None:
        conf_nested.update({"nested": {"int_field": 100}})
        assert conf_nested.data.nested.int_field == 100
        assert conf_nested.data.nested.str_field == "FortyTwo!"
        assert conf_nested.data.other_field == "Hello, World!"
        assert conf_nested.data.nested_optional is None

    def test_invalid(self, conf42: Config[Config42]) -> None:
        with pytest.raises((MultiConfigurationError, ConfigurationError)):
            conf42.update({"int_field": "not an int"})
        assert conf42.data.int_field == 42

    def test_update_additional(self, conf_nested: Config[ConfigNested]) -> None:
        with pytest.raises(AttributeError, match="Cannot set non-schema field"):
            conf_nested.update({"int_field": 100, "new_field": "I am new!"})

        with pytest.raises(AttributeError, match="nested.new_field"):
            conf_nested.update(
                {"nested": {"int_field": 100, "new_field": "I am new in nested!"}}
            )

    def test_dynamic_fields(self, validator: Validator[Any]) -> None:
        """Test that dynamic fields are not affected by update."""
        conf42_add = Config(
            Config42AllowAdditional(),
            schema=Config42AllowAdditional,
            validator=validator,
        )
        conf42_add.data.dynamic_field = "I am dynamic!"  # type: ignore

        conf42_add.update({"int_field": 100, "dynamic_field": "I am still dynamic!"})
        assert conf42_add.data.int_field == 100
        assert conf42_add.data.dynamic_field == "I am still dynamic!"  # type: ignore


class TestOverwrite:
    def test_simple(self, conf42: Config[Config42]) -> None:
        conf42.overwrite({"int_field": 100, "str_field": "Overwritten value!"})
        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Overwritten value!"

        # Overwrite with Config instance
        new_conf = Config42(int_field=200, str_field="Another overwrite!")
        conf42.overwrite(new_conf)
        assert conf42.data.int_field == 200
        assert conf42.data.str_field == "Another overwrite!"

    def test_invalid(self, conf42: Config[Config42]) -> None:
        with pytest.raises((MultiConfigurationError, ConfigurationError)):
            conf42.overwrite({"int_field": "not an int", "str_field": "Valid str"})

    def test_nested(self, conf_nested: Config[ConfigNested]) -> None:
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
    def test_simple(self, conf42: Config[Config42]) -> None:
        conf42.update({"int_field": 100, "str_field": "Updated value!"})
        assert conf42.data.int_field == 100
        assert conf42.data.str_field == "Updated value!"
        conf42.reset()
        assert conf42.data.int_field == 42
        assert conf42.data.str_field == "FortyTwo!"

    def test_nested(self, conf_nested: Config[ConfigNested]) -> None:
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
    def test_to_dict(self, conf42: Config[Config42]) -> None:
        expected = {"int_field": 42, "str_field": "FortyTwo!"}
        assert conf42.to_dict() == expected

    def test_to_yaml(self, conf42: Config[Config42]) -> None:
        yaml_str = conf42.to_yaml()
        assert "int_field: 42" in yaml_str
        assert "str_field: FortyTwo!" in yaml_str


class TestPrintingUtils:
    def test_str_formats_data_conf42(self, conf42: Config[Config42]) -> None:
        """Test that __str__ properly formats configuration data for conf42."""
        str_output = str(conf42)
        assert "  int_field: 42" in str_output
        assert "  str_field: FortyTwo!" in str_output

    def test_str_formats_data_conf_nested(
        self, conf_nested: Config[ConfigNested]
    ) -> None:
        """Test that __str__ properly formats configuration data for conf_nested."""
        str_output = str(conf_nested)
        assert "  nested:" in str_output
        assert "    int_field: 42" in str_output
        assert "  other_field: Hello, World!" in str_output

    def test_repr_includes_object_info_and_data(self, conf42: Config[Config42]) -> None:
        """Test that __repr__ includes basic object info and formatted data."""
        repr_str = repr(conf42)
        assert repr_str.startswith("<Config object at 0x")
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
        self, test_data: dict[str, Any], expected: list[str], conf42: Config[Config42]
    ) -> None:
        """Test _pretty_format with basic cases."""
        formatted = conf42._pretty_format(test_data)
        if expected:
            for line in expected:
                assert line in formatted
        else:
            assert formatted == ""
