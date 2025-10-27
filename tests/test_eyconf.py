from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import NoneType
from typing import Optional
import pytest
from eyconf import EYConf, EYConfBase
import os

from eyconf.utils import AttributeDict
from eyconf.validation import MultiConfigurationError


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = "Hello, World!"


@pytest.fixture(autouse=True)
def tmp_config_path(tmp_path) -> Path:
    config_file_path = tmp_path / "config.yml"
    os.environ["EYCONF_CONFIG_FILE"] = str(config_file_path)
    return config_file_path


def test_invalid_schema():
    with pytest.raises(ValueError):
        EYConf(int)  # type: ignore


def test_write_default(tmp_config_path):
    from eyconf import EYConf

    conf = EYConf(Config42)
    assert conf._schema == Config42
    assert conf.path == tmp_config_path
    assert conf.path.exists()
    assert conf.path.read_text() == "int_field: 42\nstr_field: Hello, World!\n"


def test_load_existing(tmp_config_path):
    from eyconf import EYConf

    with open(tmp_config_path, "w") as f:
        f.write("int_field: 20\nstr_field: Another value!\n")

    conf = EYConf(Config42)

    assert conf.path == tmp_config_path
    assert conf.path.read_text() == "int_field: 20\nstr_field: Another value!\n"
    assert conf.data.int_field == 20
    assert conf.data.str_field == "Another value!"

    # Test reload
    with open(tmp_config_path, "w") as f:
        f.write("int_field: 30\nstr_field: Another value!\n")
    conf.refresh()
    assert conf.data.int_field == 30


def test_load_nested():
    from eyconf import EYConf

    @dataclass
    class Nested:
        int_field: int = 42
        str_field: str = "Hello, World!"

    @dataclass
    class Parent:
        nested: Nested = field(default_factory=Nested)
        optional_nested: Optional[Nested] = None
        optional_with_default: Optional[int] = 42

    conf = EYConf(Parent)
    assert isinstance(conf._data.nested, Nested)
    assert isinstance(conf._data.optional_nested, NoneType)
    assert conf.data.optional_with_default == 42


def test_load_without_defaults():
    """Loading fails if required fields have no defaults."""

    @dataclass
    class Foo:
        a: int

    with pytest.raises(TypeError):
        EYConf(Foo)


def test_nested_getitem():
    from eyconf import EYConf

    @dataclass
    class Nested2:
        int_field: int = 42
        str_field: str = "Hello, World!"

    @dataclass
    class Parent2:
        nested: Nested2 = field(default_factory=Nested2)
        other_field: str = "Hello, World!"

    # This seems to be a bug in python!
    # with `future annotations` the `types["nested"]` yields the first definition ...
    # types = get_type_hints(Parent2)
    # assert types["nested"] == Nested2

    conf = EYConf(Parent2)
    assert isinstance(conf.data.nested, Nested2)


class TestBaseConfig:
    def test_init(self):
        conf = EYConfBase(Config42(), schema=Config42)
        assert conf.data.int_field == 42
        assert conf.data.str_field == "Hello, World!"

    def test_init_dict(self):
        conf_dict = EYConfBase(
            {"int_field": 100, "str_field": "Dict value!"},
            schema=Config42,
        )
        assert conf_dict.data.int_field == 100
        assert conf_dict.data.str_field == "Dict value!"
        assert isinstance(conf_dict.data, Config42)


class TestUpdate:
    def test_update_simple(self):
        conf = EYConfBase(Config42(), schema=Config42)
        conf.update({"int_field": 100, "str_field": "Updated value!"})

        assert conf.data.int_field == 100
        assert conf.data.str_field == "Updated value!"

        # Update with Config instance
        new_conf = Config42(int_field=200, str_field="Another update!")
        conf.update(new_conf)
        assert conf.data.int_field == 200
        assert conf.data.str_field == "Another update!"

    def test_update_nested(self):
        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Nested = field(default_factory=Nested)
            other_field: str = "Hello, World!"

        conf = EYConfBase(Parent(), schema=Parent)
        conf.update(
            {
                "nested": {"int_field": 100, "str_field": "Updated nested value!"},
                "other_field": "Updated parent value!",
            }
        )

        assert conf.data.nested.int_field == 100
        assert conf.data.nested.str_field == "Updated nested value!"
        assert conf.data.other_field == "Updated parent value!"

    def test_update_partial_nested(self):
        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Nested = field(default_factory=Nested)
            other_field: str = "Hello, World!"

        conf = EYConfBase(Parent(), schema=Parent)
        conf.update(
            {
                "nested": {"int_field": 100},
            }
        )

        assert conf.data.nested.int_field == 100
        assert conf.data.nested.str_field == "Hello, World!"
        assert conf.data.other_field == "Hello, World!"

    def test_update_invalid(self):
        conf = EYConfBase(Config42(), schema=Config42)

        with pytest.raises(MultiConfigurationError):
            conf.update({"int_field": "not an int"})

        assert conf.data.int_field == 42

    def test_update_optional_field(self):
        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Optional[Nested] = None
            other_field: str = "Hello, World!"

        conf = EYConfBase(Parent(), schema=Parent)
        conf.update(
            {
                "nested": {"int_field": 100, "str_field": "Updated nested value!"},
                "other_field": "Updated parent value!",
            }
        )

        assert conf.data.nested is not None
        assert conf.data.nested.int_field == 100
        assert conf.data.nested.str_field == "Updated nested value!"
        assert conf.data.other_field == "Updated parent value!"

    def test_allow_additional_fields(self):
        from eyconf import EYConfBase

        @dataclass
        class BaseConfig:
            int_field: int = 42

        conf = EYConfBase(
            BaseConfig(), schema=BaseConfig, allow_additional_properties=True
        )
        conf.update({"int_field": 100, "new_field": "I am new!"})

        assert conf.data.int_field == 100
        assert conf.data.new_field == "I am new!"

    def test_allow_additional_fields_nested(self):
        from eyconf import EYConfBase

        @dataclass
        class Nested:
            int_field: int = 42

        @dataclass
        class Parent:
            nested: Nested = field(default_factory=Nested)

        conf = EYConfBase(Parent(), schema=Parent, allow_additional_properties=True)
        conf.update(
            {
                "nested": {"new_nested_field": {"foo": "bar"}},
            }
        )

        assert conf.data.nested.new_nested_field.foo == "bar"
        assert isinstance(conf.data.nested.new_nested_field, AttributeDict)

        # Even more nesting
        conf.update(
            {
                "nested": {"d1": {"d2": {"d3": {"d4_field": "deep value!"}}}},
            }
        )
        assert conf.data.nested.d1.d2.d3.d4_field == "deep value!"


class TestOverwrite:
    def test_overwrite_simple(self):
        from eyconf import EYConfBase

        conf = EYConfBase(Config42(), schema=Config42)
        conf.overwrite({"int_field": 100, "str_field": "Overwritten value!"})

        assert conf.data.int_field == 100
        assert conf.data.str_field == "Overwritten value!"

        # Overwrite with Config instance
        new_conf = Config42(int_field=200, str_field="Another overwrite!")
        conf.overwrite(new_conf)
        assert conf.data.int_field == 200
        assert conf.data.str_field == "Another overwrite!"

    def test_overwrite_invalid(self):
        from eyconf import EYConfBase

        conf = EYConfBase(Config42(), schema=Config42)

        with pytest.raises(MultiConfigurationError):
            conf.overwrite({"int_field": "not an int"})

    def test_overwrite_nested(self):
        from eyconf import EYConfBase

        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Nested = field(default_factory=Nested)
            other_field: str = "Hello, World!"

        conf = EYConfBase(Parent(), schema=Parent)
        conf.overwrite(
            {
                "nested": {"int_field": 100, "str_field": "Overwritten nested value!"},
                "other_field": "Overwritten parent value!",
            }
        )

        assert conf.data.nested.int_field == 100
        assert conf.data.nested.str_field == "Overwritten nested value!"
        assert conf.data.other_field == "Overwritten parent value!"
