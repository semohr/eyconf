from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pytest
from eyconf import EYConf
import os


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

    @dataclass
    class Config:
        int_field: int = 42
        str_field: str = "Hello, World!"

    conf = EYConf(Config)
    assert conf._schema == Config
    assert conf.path == tmp_config_path
    assert conf.path.exists()
    assert conf.path.read_text() == "int_field: 42\nstr_field: Hello, World!\n"


def test_load_existing(tmp_config_path):
    from eyconf import EYConf

    @dataclass
    class Config:
        int_field: int = 42
        str_field: str = "Hello, World!"

    with open(tmp_config_path, "w") as f:
        f.write("int_field: 20\nstr_field: Another value!\n")

    conf = EYConf(Config)

    assert conf.path == tmp_config_path
    assert conf.path.read_text() == "int_field: 20\nstr_field: Another value!\n"
    assert conf.int_field == 20
    assert conf.str_field == "Another value!"

    # Test reload
    with open(tmp_config_path, "w") as f:
        f.write("int_field: 30\nstr_field: Another value!\n")
    conf.refresh()
    assert conf.int_field == 30


def test_load_nested():
    from eyconf import EYConf

    @dataclass
    class Nested:
        int_field: int = 42
        str_field: str = "Hello, World!"

    @dataclass
    class Parent:
        nested: Nested
        optional_nested: Optional[Nested]
        optional_with_default: Optional[int] = 42

    conf = EYConf(Parent)
    assert isinstance(conf._data.nested, Nested)
    assert isinstance(conf._data.optional_nested, type(None))
    assert conf.optional_with_default == 42


def test_nested_getitem():
    from eyconf import EYConf

    @dataclass
    class Nested2:
        int_field: int = 42
        str_field: str = "Hello, World!"

    @dataclass
    class Parent2:
        nested: Nested2
        other_field: str = "Hello, World!"

    # This seems to be a bug in python!
    # with `future annotations` the `types["nested"]` yields the first definition ...
    # types = get_type_hints(Parent2)
    # assert types["nested"] == Nested2

    conf = EYConf(Parent2)

    assert type(conf.nested) == Nested2
