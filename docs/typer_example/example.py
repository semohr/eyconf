from dataclasses import dataclass

import typer

from eyconf import EYConf
from eyconf.cli import create_config_cli


@dataclass
class ConfigSchema:
    """Example configuration data class."""

    int_field: int = 42
    str_field: str = "Hello, World!"


class Config(EYConf):
    """Custom configuration class."""

    pass


app = typer.Typer()

cli = create_config_cli(Config, ConfigSchema)
app.add_typer(cli, name="config")

if __name__ == "__main__":
    app()
