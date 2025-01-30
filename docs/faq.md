# Frequently Asked Questions

## Do I need default values for my dataclass schema?

If you use the default implementation for the `EyConf` class you do need to provide default values for your dataclass schema. They are used in the generated yaml file. If you overwrite the `default_yaml` method you can provide your own default values and therefore do not need to provide them in the schema.

Example:

```python

from eyconf import EYConf

@dataclass
class ConfigSchema:
    foo: int


class MyConfing(EYConf):
    def __init__(self, config_file):
        super().__init__(ConfigSchema, config_file)
        
    def default_yaml(self):
        return """
        My configuration schema
        foo: 42
        """
```