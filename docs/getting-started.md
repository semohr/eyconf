# Getting started

## Installation

```{include} ../README.md
:start-after: <!-- start installation -->
:end-before: <!-- end installation -->
```

## Basic Usage

```{include} ../README.md
:start-after: <!-- start usage -->
:end-before: <!-- end usage -->
```

## Core concepts

The main idea of EYConf is to define your configuration schema using one or 
multiple strongly typed dataclasses.

### 1. Define Your Schema

Start by defining your configuration structure using dataclasses:

```python

from dataclasses import dataclass
from typing import Optional

@dataclass
class Transport:
    """Email transport configuration"""
    host: str = 'imap.example.com'
    port: int = 993
    username: str = 'user'
    password: str = 'password'
    use_ssl: bool = False

@dataclass
class Other:
    """Other configuration options"""
    bar: Optional[int]

@dataclass
class ConfigSchema:
    """My configuration schema

    Docstrings are used as comments in the generated yaml file!
    """
    transport: Transport
    other: Other
```

### 2. Create and Use Configuration

We can now create a configuration using the {py:class}`~eyconf.config.EYConf` class directly, if you need
more control it is also possible to extend the class or use the {py:class}`~eyconf.config.EYConfBase` base class.

```python
from eyconf import EYConf

config = EYConf(ConfigSchema)
```

This created the `config.yaml` file in your current working directory with the following content.
Notice that the docstrings are used as comments in the generated yaml file.

```yaml
# My configuration schema
# Docstrings are used as comments in the generated yaml file!

transport:
  # Email transport configuration

  host: imap.example.com
  port: 993
  username: user
  password: password
  use_ssl: false

other:
  # Other configuration options

  bar: null
```

### 3. Modify and Reload


Edit `config.yaml` and reload changes:

```yaml
database:
  host: production-db.example.com
  username: prod_user
```

```python
config.refresh()
print(config.data.database.host)  # "production-db.example.com"
```

Configuration errors will be caught during loading with detailed error messages:

```yaml
transport:
  host: imap.example.com
  port: not_a_number  # Invalid type
```

```python
config.refresh()
# Raises
# ConfigurationError:
# 'not_a_number' is not of type 'integer' in section 'transport.port'
```

## Advanced Usage


### Change Configuration File Path

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