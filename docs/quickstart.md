# Quickstart

## Installation

You can install EYConf from [PyPI](https://pypi.org/project/eyconf/) using pip.

```bash
pip install eyconf
```

## Using as a Configuration Manager

First of define a configuration schema using dataclasses.

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

config = EYConf(ConfigSchema)
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


### Change Configuration File Path

To change the path of the configuration file, you can set the `EYCONF_CONFIG_FILE` environment variable to the desired path before creating the `EYConf` instance.

```bash
export EYCONF_CONFIG_FILE="/path/to/your/config.yaml"
```

Alternatively, you can pass override the `get_file` method in a subclass of `EYConf`:

```python
from eyconf import EYConf
class CustomConfig(EYConf):
    @staticmethod
    def get_file() -> Path:
        return Path("/path/to/your/config.yaml").expanduser().resolve()
config = CustomConfig(ConfigSchema)
```

{ref}`Why can I not just provide a path to the constructor? <faq:why-can-i-not-just-provide-a-path-to-the-constructor>`



## Using as validation layer

If you already have a configuration as dictionary (e.g. loaded from a another source or you dont want to create a yaml file) you can use the `validate_config` function to validate and parse the configuration according to a defined schema.

```python
from dataclasses import dataclass
from typing import Optional

from eyconf import validation

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

config = {
    "transport": {
        "host": "custom.example.com",
        "port": 993,
        "username": "custom_user",
        "password": "custom_password",
        "use_ssl_s": True,
    },
}

validation.validate(
    config, validation.to_json_schema(ConfigSchema, allow_additional=False)
)
# Raises
# MultiConfigurationError:
# 'use_ssl' is a required property in section 'transport'
# Additional properties are not allowed ('use_ssl_s' was unexpected) in section 'transport'
```

### Create default configuration as python dict

```python
from dataclasses import asdict

config = asdict(ConfigSchema())

validation.validate(
    config, validation.to_json_schema(ConfigSchema, allow_additional=False)
)
# Pass
```
