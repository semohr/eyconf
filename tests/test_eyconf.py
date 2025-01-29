from dataclasses import dataclass
from pathlib import Path
import pytest
from eyconf import EYConf


@pytest.fixture
def tmp_config_path(tmp_path) -> Path:
    config_file_path = tmp_path / "config.yml"
    return config_file_path


def test_invalid_schema(tmp_config_path):

    with pytest.raises(ValueError):
        EYConf(int, tmp_config_path)  # type: ignore


def test_write_default(tmp_config_path):
    from eyconf import EYConf

    @dataclass
    class Config:
        int_field: int = 42
        str_field: str = "Hello, World!"

    conf = EYConf(Config, tmp_config_path)
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

    conf = EYConf(Config, tmp_config_path)

    assert conf.path == tmp_config_path
    assert conf.path.read_text() == "int_field: 20\nstr_field: Another value!\n"
    assert conf.int_field == 20
    assert conf.str_field == "Another value!"

    # Test reload
    with open(tmp_config_path, "w") as f:
        f.write("int_field: 30\nstr_field: Another value!\n")
    conf.refresh()
    assert conf.int_field == 30


def test_nested_getitem(tmp_config_path):
    from eyconf import EYConf

    @dataclass
    class Nested:
        int_field: int = 42
        str_field: str = "Hello, World!"

    @dataclass
    class Parent:
        nested: Nested
        other_field: str = "Hello, World!"

    conf = EYConf(Parent, tmp_config_path)

    assert type(conf.nested) == Nested
