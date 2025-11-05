# Advanced Usage

EYConf provides several advanced features to customize its behavior and integrate seamlessly into your projects.


## Change Configuration File Path

To change the path of the configuration file, you can set the `EYCONF_CONFIG_FILE` environment variable to the desired path before creating the {py:class}`~eyconf.config.EYConf` instance:

```bash
export EYCONF_CONFIG_FILE="/path/to/your/config.yaml"
```

Alternatively, you can pass override the {py:meth}`~eyconf.config.EYConf.get_file` method in a subclass of {py:class}`~eyconf.config.EYConf`. We recommend this approach if you want to have more control over the configuration file location, this also allows you to add helper methods specific to your application configuration.

```python
from eyconf import EYConf
class CustomConfig(EYConf):
    @staticmethod
    def get_file() -> Path:
        return Path("/path/to/your/config.yaml").expanduser().resolve()
config = CustomConfig(ConfigSchema)
```

{ref}`Why can I not just provide a path to the constructor? <faq:why-can-i-not-just-provide-a-path-to-the-constructor>`


## Without YAML File / Memory Only Validation

Sometimes you might want to create a configuration without creating or loading a YAML file. This is possible be using
the {py:class}`~eyconf.config.EYConfBase` base class. We still expect you to provide a schema using dataclasses.

```python
from eyconf import EYConfBase


@dataclass
class Transport:
    """Email transport configuration"""
    host: str = 'imap.example.com'
    port: int = 993
    username: str = 'user'
    password: str = 'password'
    use_ssl: bool = False

@dataclass
class ConfigSchema:
    """My configuration schema

    Docstrings are used as comments in the generated yaml file!
    """
    transport: Transport

# Loaded from memory only
config = {
    "transport": {
        "host": "custom.example.com",
        "port": 993,
        "username": "custom_user",
        "password": "custom_password",
        "use_ssl": True,
    },
}
config = EYConfBase(data=config, schema=ConfigSchema)
```

## Dict style access

While we do not recommend using dict style access to configuration values, as you lose type safety and autocompletion, it is still possible to access configuration values using dict style access if you 
really need or want to.

To do so you can either use our utility decorator `@dict_access` or create a `__getitem__` method in your dataclass to convert your dataclass schema into a dictionary-like object:


::::{tab-set}

:::{tab-item} `@dict_access` decorator

```python
from eyconf.utils import dict_access

@dict_access
@dataclass
class ConfigSchema:
    fortytwo: int = 42

```
:::

:::{tab-item} `__getitem__` method

```python
@dataclass
class ConfigSchema:
    fortytwo: int = 42

    def __getitem__(self, item):
        return getattr(self, item)

```
:::

::::

This now allows you to access configuration values using dict style access:

```python
from eyconf import EYConf
from eyconf.utils import DictAccess
config = EYConf(ConfigSchema)

assert isinstance(config.data, DictAccess)
print(config.data["fortytwo"])  # Outputs: 42
```


## Typer integration

The `eyconf.cli` module provides a convenient way to create a command-line interface (CLI) for managing configuration files using the [typer library](https://typer.tiangolo.com/). This can be particularly useful when you want to provide users with the ability to interact and modify configuration files via the terminal.

You need to install the `cli` additions to use this feature. You can install it using pip:

```bash
pip install eyconf[cli]
```

### Integrating the CLI into Your Project

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


### The CLI Commands

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

