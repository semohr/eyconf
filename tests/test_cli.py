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
        assert "Manage configuration file" in result.output

    def test_validate(self, cli_app):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["validate"])
        assert result.exit_code == 0
        assert "Configuration is valid." in result.output

    def test_validate_invalid(self, cli_app, mock_get_file_path):
        runner = CliRunner()

        with open(mock_get_file_path, "a") as f:
            f.write("invalid value")

        result = runner.invoke(cli_app, ["validate"])
        assert result.exit_code == 1
        assert "Invalid YAML file!" in result.output

    def test_validate_invalid_schema(self, cli_app, mock_get_file_path):
        runner = CliRunner()

        with open(mock_get_file_path, "a+") as f:
            f.write("foo : 'bar'")

        result = runner.invoke(cli_app, ["validate"])
        assert result.exit_code == 1
        assert "Additional properties are not allowed" in result.output

    def test_diff(self, cli_app):
        """Test the 'diff' command to show differences between current and default config."""
        runner = CliRunner()
        result = runner.invoke(cli_app, ["diff"])

        assert result.exit_code == 0
        # Should show "No changes!" when configs are identical
        assert "No changes!" in result.output

    def test_diff_with_changes(self, cli_app, mock_get_file_path):
        """Test the 'diff' command with actual configuration changes."""
        runner = CliRunner()

        # Modify config file to have different values
        with open(mock_get_file_path, "w") as f:
            f.write("int_field: 100\nstr_field: 'Custom Value'\n")

        result = runner.invoke(cli_app, ["diff"])

        assert result.exit_code == 0
        # Should show differences between default and current values
        assert "+" in result.output or "-" in result.output

    def test_reset(self, cli_app):
        """Test the 'reset' command to reset configuration to defaults."""
        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            [
                "reset",
            ],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "Configuration has been reset to default values." in result.output

        # Exit if no confirm
        result = runner.invoke(
            cli_app,
            [
                "reset",
            ],
            input="N\n",
        )
        assert result.exit_code == 0
        assert "Aborted!" in result.output
