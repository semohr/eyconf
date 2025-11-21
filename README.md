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
    <a href="https://codecov.io/github/semohr/eyconf" > 
        <img src="https://codecov.io/github/semohr/eyconf/graph/badge.svg?token=JJVCY9H6QR"/> 
    </a>
</p>


## Why EYConf?

<!-- start features -->
- **Schema-First Configuration**: Define your config structure with Python dataclasses, get automatic YAML generation with comments
- **Type-Safe Access**: Access nested configuration values with full IDE support and runtime type checking
- **Validation First**: Catch configuration errors early with detailed, human-readable validation messages
- **Zero Boilerplate**: No manual YAML parsing, no dictionary access - just clean attribute access to your configuration
<!-- end features -->

## Installation

<!-- start installation -->
You can install EYConf from [PyPI](https://pypi.org/project/eyconf/) using pip.

```bash
pip install eyconf
```
<!-- end installation -->

## Example Usage

<!-- start usage -->

```python
from dataclasses import dataclass
from eyconf import EYConf

@dataclass
class AppConfig:
    """Application configuration"""
    database_url: str = "sqlite:///app.db"
    debug: bool = False

# Creates/loads config.yaml automatically
config = EYConf(AppConfig)

# Use your config
print(config.data.debug)  # False
```

This will create a `config.yaml` file in your current working directory with the following content:

```yaml
# Application configuration

database_url: sqlite:///app.db
debug: false
```
<!-- end usage -->

Please refer to the [documentation](https://eyconf.readthedocs.io/en/latest/) for more examples and detailed usage instructions.
