# CLI for eyconf


The `eyconf.cli` module provides a convenient way to create a command-line interface (CLI) for managing configuration files using the [typer library](https://typer.tiangolo.com/). This can be particularly useful when you want to provide users with the ability to interact and modify configuration files via the terminal.

You need to install the `cli` additions to use this feature. You can install it using pip:

```bash
pip install eyconf[cli]
```

## Integrating the CLI into Your Project

To integrate the CLI into your project, follow these steps:

```python
from eyconf.cli import create_config_cli
from eyconf import EYConf
from your_project.config import ConfigSchema  # Adjust the import to your actual config schema
from your_project import app  # Adjust the import to your actual Typer app

# Your main typer app
app = typer.Typer()
sub_app = create_config_cli(EYConf, schema)
app.add_typer(sub_app, name="config")
```


## The CLI Commands

The CLI provides several commands to manage your configuration:

<div class="only-light">

```{typer} eyconf.docs_cli_example:app.config
---
prog: config
theme: night_owlish
width: 80
---
```

</div>


<div class="only-dark">

```{typer} eyconf.docs_cli_example:app.config
---
prog: config
theme: dimmed_monokai
width: 80
---
```

</div>

