<p align="center">
    <h1 align="center">EYConf</h1>
</p>
<p align="center">
    <em>Easy yaml based configuration for Python</em>
</p>


<p align="center">
    <a href="https://github.com/semohr/eyconf/actions">
        <img alt="build status" src="https://img.shields.io/github/actions/workflow/status/semohr/eyconf/workflow.yml?style=flat-square" />
    </a>
    <a href="https://eyconf.readthedocs.io/en/latest/">
        <img alt="docs" src="https://img.shields.io/readthedocs/eyconf?style=flat-square" />
    </a>
    <a href="https://github.com/semohr/eyconf/blob/main/LICENSE">
        <img alt="License: GPL v3" src="https://img.shields.io/badge/License-GPL%20v3-blue.svg?style=flat-square" />
    </a>
</p>


## Features

<!-- start features -->
- **Generate**: Automatically convert your schema to a yaml configuration file, including comments!
- **Validate**: Validate your a given configuration file against your schema and raise human readable errors!
- **Extend**: Introduce custom logic by extending the `EYConf` class!
- **Reload**: Reload your configuration on the fly without restarting your application!
<!-- end features -->

## Installation

You can install EYConf from git directly using pip:

```bash
pip install git+https://github.com/semohr/eyconf.git
```

## Quickstart

Define a configuration schema

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

We can now create a configuration using the `EYConf` class directly, if you need
more control it is also possible to extend the class.

```python
# Using create_config_class helper function
from eyconf import EYConf

config = EYConf(ConfigSchema,'config.yaml')
```

This created the `config.yaml` file in your current working directory with the following content. Notice that the
docstrings are used as comments in the generated yaml file.

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

You can access your configuration directly as attributes of the `config` object.

```python
assert type(config.transport) == Transport
assert config.transport.host == "imap.example.com"
```

If you want to change the configuration, you can do so by editing the `config.yaml` file directly and reloading the configuration.

```yaml
...
transport:
  host: changed.example.com
```

```python
config.refresh()
assert config.transport.host == "changed.example.com"
```
