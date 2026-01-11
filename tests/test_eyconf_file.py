from __future__ import annotations
from dataclasses import dataclass, field
import os
from pathlib import Path

import pytest

from eyconf import EYConf


@pytest.fixture(autouse=True)
def tmp_config_path(tmp_path) -> Path:
    config_file_path = tmp_path / "config.yml"
    os.environ["EYCONF_CONFIG_FILE"] = str(config_file_path)
    return config_file_path


@dataclass
class Config42:
    int_field: int = 42
    str_field: str = field(default="FortyTwo!")


class TestEYConfFile:
    """Tests the default EYConf configuration file handling."""

    def test_init(self, tmp_config_path):
        conf = EYConf(Config42)
        assert isinstance(conf, EYConf)
        assert conf._schema == Config42

        with pytest.raises(ValueError):
            EYConf("not a dataclass")  # type: ignore

    def test_init_bad_defaults(self):
        # Schema with bad defaults
        with pytest.raises(TypeError):

            @dataclass
            class BadConfig:
                foo: Config42

            EYConf(BadConfig)

    def test_write_default(self, tmp_config_path, caplog):
        conf = EYConf(Config42)

        assert conf.path == tmp_config_path
        assert conf.path.exists()
        assert conf.path.read_text() == "int_field: 42\nstr_field: FortyTwo!\n"

        # Overwrite again
        with caplog.at_level("WARNING"):
            conf._write_default()
            assert "overwriting" in caplog.text.lower()

    def test_load_existing(self, tmp_config_path):
        with open(tmp_config_path, "w") as f:
            f.write("int_field: 20\nstr_field: Another value!\n")
        conf = EYConf(Config42)
        assert conf._data.int_field == 20
        assert conf._data.str_field == "Another value!"

    def test_reload(self, tmp_config_path):
        with open(tmp_config_path, "w") as f:
            f.write("int_field: 10\nstr_field: Temp value!\n")
        conf = EYConf(Config42)
        assert conf._data.int_field == 10
        assert conf._data.str_field == "Temp value!"

        # Modify the config file
        with open(tmp_config_path, "w") as f:
            f.write("int_field: 99\nstr_field: Changed value!\n")

        conf.reload()
        assert conf._data.int_field == 99
        assert conf._data.str_field == "Changed value!"

        # Should raise for missing config
        tmp_config_path.unlink()
        with pytest.raises(FileNotFoundError):
            conf.reload()

    def test_reset(self, tmp_config_path):
        with open(tmp_config_path, "w") as f:
            f.write("int_field: 5\nstr_field: Old value!\n")
        conf = EYConf(Config42)
        assert conf._data.int_field == 5
        assert conf._data.str_field == "Old value!"

        conf.reset()
        assert conf._data.int_field == 42
        assert conf._data.str_field == "FortyTwo!"

    def test_repr(self, tmp_config_path):
        conf = EYConf(Config42)
        repr_str = repr(conf)
        assert "EYConf" in repr_str
        assert "int_field" in repr_str
        assert "str_field" in repr_str

    def test_default_validate(self, tmp_config_path):
        with open(tmp_config_path, "w") as f:
            f.write("int_field: 5\n")  # omit str_field to use default
        conf = EYConf(Config42)
        conf._data.str_field = "FortyTwo!"
