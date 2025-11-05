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
multiple strongly typed dataclasses. This is similar to how Pydantic works, but
way less heavy weight. EYConf uses Python's built-in dataclasses and the jsonschema
library to perform validation.

### 1. Define Your Schema

Start by defining your configuration structure using dataclasses:

```python

from dataclasses import dataclass

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
    bar: int | None = None

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

:::{dropdown} Full example

For a minimal working example, see below:

```python
# your_project/config.py
from eyconf import EYConf
from dataclasses import dataclass

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

config = EYConf(ConfigSchema)

```
:::
