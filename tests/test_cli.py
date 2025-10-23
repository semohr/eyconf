from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from eyconf import EYConf

try:
    from typer.testing import CliRunner
    from eyconf.cli import create_config_cli

    typer_installed = True
except ImportError:
    typer_installed = False


skip = pytest.mark.skipif(
    not typer_installed, reason="typer is not installed, skipping CLI tests."
)


@dataclass
class Config:
    """Example configuration data class."""

    int_field: int = 42
    str_field: str = "Hello, World!"


@pytest.fixture(autouse=True)
def mock_get_file_path(tmp_path) -> Path:
    """Fixture to provide a temporary config file path."""
    config_file_path = tmp_path / "config.yml"
    os.environ["EYCONF_CONFIG_FILE"] = str(config_file_path)
    return config_file_path


@pytest.fixture
@skip
def cli_app():
    """Fixture to create a CLI app for the configuration commands."""
    config_cli = create_config_cli(EYConf, schema=Config)
    return config_cli


@skip
def test_ls_command(cli_app, mock_get_file_path):
    """Test the 'ls' command to list current configuration."""
    runner = CliRunner()

    # Instantiate the config to ensure file exists.
    EYConf(Config)

    result = runner.invoke(cli_app, ["ls"])

    assert result.exit_code == 0
    assert "int_field" in result.output
    assert "str_field" in result.output


@skip
def test_edit_command(monkeypatch, cli_app, mock_get_file_path):
    """Test the 'edit' command to open the configuration file in an editor."""

    async def mock_asyncio_create_subprocess_exec(*args, **kwargs):
        """Mock subprocess execution for opening a file."""

        class MockProcess:
            async def wait(self):
                pass

        return MockProcess()

    with patch("asyncio.create_subprocess_exec", mock_asyncio_create_subprocess_exec):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--edit"])

    print(result.output)  # For debugging purposes

    assert result.exit_code == 0
    assert "Opening configuration file:" in result.output
