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


(faq:why-can-i-not-just-provide-a-path-to-the-constructor)=
## Why can I not just provide a path to the constructor?


This is a design choice: To enable our cli to find your configuration (which comes with great benefits), the path needs to be attached to a class — being attached to an instance is not sufficient.
This prevents a simpler pattern like `EYConf(ConfigSchema, path="/path/to/config.yaml")`.

We also do not want to create multiple ways to do the same thing.
Having both a path parameter and a way to override `get_file` would add unnecessary complexity to the class interface.
