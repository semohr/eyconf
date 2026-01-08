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


@skip
class TestCommands:
    @pytest.fixture
    def cli_app(self):
        """Fixture to create a CLI app for the configuration commands."""
        config_cli = create_config_cli(EYConf, schema=Config)  # type: ignore
        EYConf(Config)  # Instantiate the config to ensure file exists.
        return config_cli

    @pytest.mark.parametrize("comments", [True, False])
    def test_ls(self, cli_app, comments):
        """Test the 'ls' command to list current configuration."""
        runner = CliRunner()
        command = ["ls", "--comments"] if comments else ["ls"]
        result = runner.invoke(cli_app, command)

        assert result.exit_code == 0
        assert "int_field" in result.output
        assert "str_field" in result.output

    def test_path(self, cli_app):
        """Test the 'path' command to show configuration path"""
        runner = CliRunner()

        result = runner.invoke(cli_app, ["path"])

        assert result.exit_code == 0
        assert os.environ["EYCONF_CONFIG_FILE"] in result.output

    def test_edit(self, cli_app):
        """Test the 'edit' command to open the configuration file in an editor."""

        async def mock_asyncio_create_subprocess_exec(*args, **kwargs):
            """Mock subprocess execution for opening a file."""

            class MockProcess:
                async def wait(self):
                    pass

            return MockProcess()

        with patch(
            "asyncio.create_subprocess_exec", mock_asyncio_create_subprocess_exec
        ):
            runner = CliRunner()
            result = runner.invoke(cli_app, ["edit"])

        assert result.exit_code == 0
        assert "Opening configuration file:" in result.output

    def test_help_default(self, cli_app):
        """Should show the help if no command is given"""
        runner = CliRunner()
        result = runner.invoke(cli_app)

        assert result.exit_code == 0
        assert "--help" in result.output
