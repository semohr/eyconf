<p align="center">
    <h1 align="center">EYConf</h1>
</p>
<p align="center">
    <em><b>E</b>asy <b>Y</B>aml based <b>Conf</b>iguration for Python</em>
</p>


<p align="center">
     <a href="https://pypi.org/project/eyconf/">
        <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/eyconf?style=flat-square">
     </a>
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
- **Generate**: Automatically convert a schema to a yaml configuration file, including comments!
- **Validate**: Validate a given configuration file against your schema and raise human readable errors!
- **Extend**: Introduce custom logic by extending the `EYConf` class!
- **Reload**: Reload your configuration on the fly without restarting your application!
<!-- end features -->

## Installation

You can install EYConf from [PyPI](https://pypi.org/project/eyconf/) using pip.

```bash
pip install eyconf
```

## Example Usage

```python
from dataclasses import dataclass
from eyconf import EYConf

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


config = EYConf(ConfigSchema)
```

This generate the following `config.yaml` file in your current working directory:

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

Please refer to the [documentation](https://eyconf.readthedocs.io/en/latest/) for more information.
