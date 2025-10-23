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
import os

import typer

from eyconf import EYConf


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
        edit: bool = typer.Option(
            False, "--edit", "-e", help="Edit the configuration."
        ),
    ):
        """Edit the plistsync configuration."""
        if edit:
            asyncio.run(edit_config(Config, *args, **kwargs))
        else:
            # Show help if no subcommand is provided
            if ctx.invoked_subcommand is None:
                print(ctx.get_help())

    @config_cli.command()
    def ls():
        """Show the current configuration."""
        config = Config(*args, **kwargs)
        typer.echo(str(config))

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
            os.startfile(path.absolute().as_posix())
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
