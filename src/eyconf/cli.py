"""Optional CLI interface for eyconf configuration management.

Allows to easily integrate configuration management into command line applications.

Usage:
------
```python
from eyconf.cli import config_cli

app = typer.Typer()
app.subcommand(config_cli, name="config")
```
"""

import asyncio
import difflib
import os
from contextlib import contextmanager
from typing import Annotated, Any

import typer
from rich import print
from rich.text import Text
from yaml import YAMLError

from eyconf import EYConf
from eyconf.validation import MultiConfigurationError


def create_config_cli(
    Config: type[EYConf],
    *args,
    **kwargs,
):
    """Create a CLI for managing the configuration file.

    Parameter
    ---------
    config : type[EYConf]
        The EYConf class to manage the configuration for. Not the instance!
    *args, **kwargs
        Additional arguments and keyword arguments to pass to the
        Config class if it needs to be instantiated.

    Usage
    -----
    ```python
    from eyconf.cli import create_config_cli
    from my_config import MyConfig

    config_cli = create_config_cli(EYConf, schema=MyConfig)

    app = typer.Typer()
    app.add_typer(config_cli, name="config")
    ```
    """
    config_cli = typer.Typer(
        rich_markup_mode="rich",
        help="Manage configuration file",
    )

    @config_cli.callback(invoke_without_command=True)
    def main(
        ctx: typer.Context,
    ):
        # Show help if no subcommand is provided
        if ctx.invoked_subcommand is None:
            print(ctx.get_help())

    @config_cli.command()
    def ls(
        comments: Annotated[
            bool,
            typer.Option(help="Show the comments in returned configuration file."),
        ] = False,
    ):
        """Show the current configuration."""
        path = Config.get_file()
        config: EYConf[Any] | str = Config(*args, **kwargs)
        if comments:
            with open(path) as file:
                config = file.read()

        typer.echo(str(config))

    @config_cli.command()
    def path():
        """Show the path to the configuration file."""
        typer.echo(Config.get_file().absolute())

    @config_cli.command()
    def edit():
        """Edit the configuration file in you default editor."""
        asyncio.run(edit_config(Config, *args, **kwargs))

    @config_cli.command()
    def validate():
        """Validate the configuration file against the schema."""
        with human_readable_validation():
            Config(*args, **kwargs)

        typer.echo("Configuration is valid.")

    @config_cli.command()
    def diff():
        """Show differences between current default config values."""
        with human_readable_validation():
            from eyconf.generate_yaml import dataclass_to_yaml

            current_config = Config(*args, **kwargs)
            default_yaml_str = dataclass_to_yaml(current_config._schema())
            current_yaml_str = current_config.to_yaml()

            current_lines = current_yaml_str.splitlines(keepends=True)
            default_lines = default_yaml_str.splitlines(keepends=True)
            # Strange formatting if last lines do not end in newline
            if not default_yaml_str.endswith("\n"):
                current_lines[-1] += "\n"
            if not current_yaml_str.endswith("\n"):
                default_lines[-1] += "\n"

            diff_lines = difflib.unified_diff(
                default_lines,
                current_lines,
                fromfile="default",
                tofile="current",
            )
            lines = 0
            for line in diff_lines:
                text = Text(line)
                if line.startswith("+") and not line.startswith("+++"):
                    text.stylize("green")
                elif line.startswith("-") and not line.startswith("---"):
                    text.stylize("red")
                elif line.startswith("@@"):
                    text.stylize("bold cyan")
                elif line.startswith("+++"):
                    text.stylize("bold green")
                elif line.startswith("---"):
                    text.stylize("bold red")
                else:
                    text.stylize("gray")
                print(text, end="")  #
                lines += 1

            if lines == 0:
                typer.echo("No changes!")

    @config_cli.command()
    def reset(
        force: Annotated[
            bool,
            typer.Option(help="Force reset without confirmation."),
        ] = False,
    ):
        """Reset configuration to default values."""
        # TODO: Support to reset of specific sections
        if not force:
            if not typer.confirm(
                "Are you sure you want to reset the entire configuration?"
            ):
                typer.echo("Aborted!")
                raise typer.Exit(0)

        # Remove file incase of invalid schema/parsing errors
        path = Config.get_file()
        if path.exists():
            os.remove(path)
        Config(*args, **kwargs)
        typer.echo("Configuration has been reset to default values.")

    return config_cli


async def edit_config(Config: type[EYConf], *args, **kwargs):
    """Edit the configuration file."""
    path = Config.get_file()

    if not path.exists():
        # If the config file does not exist, create it with default values
        Config(*args, **kwargs)

    # Open the config file with the default system editor
    process = None
    typer.echo(f"Opening configuration file: {path.absolute().as_posix()}")
    try:
        if os.name == "nt":  # Windows
            os.startfile(path.absolute().as_posix())  # type: ignore[attr-defined]
        elif os.name == "posix":  # macOS or Linux
            process = await asyncio.create_subprocess_exec(
                *[
                    "open" if os.uname().sysname == "Darwin" else "xdg-open",
                    path.absolute().as_posix(),
                ]
            )
        else:
            typer.echo("Unsupported OS for the edit command.")
    except Exception as e:
        typer.echo(f"Failed to open the configuration editor: {e}")

    await process.wait() if process else None


@contextmanager
def human_readable_validation():
    """Show human readable exceptions instead of crashing."""
    try:
        yield
    except MultiConfigurationError as e:
        for error in e.errors:
            typer.echo(f"- {error}")
        raise typer.Exit(1)
    except YAMLError as e:
        typer.echo("Invalid YAML file!")
        typer.echo(e.__class__.__name__)
        raise typer.Exit(1)
