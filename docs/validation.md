# Validation Backends

EYConf supports multiple validation backends, allowing you to choose the one that
best fits your project's needs. All backends implement the same
{py:class}`~eyconf.validation.backends.interface.Validator` protocol, so switching
between them requires only a one-line change.

## Available Backends

### JsonSchemaValidator

```python
from eyconf.validation.backends.json_schema import JsonSchemaValidator

validator = JsonSchemaValidator(allow_additional=False)
```

The **default and first** backend. It uses the
[jsonschema](https://python-jsonschema.readthedocs.io/) library with
**Draft 2020-12** for schema generation and validation.

**Best for**

- Projects where you want to minimise dependencies
- When you need the most mature and tested backend
- When inline (non-`$ref`) JSON Schema output is preferred

---

### PydanticValidator

```python
from eyconf.validation.backends.pydantic import PydanticValidator

validator = PydanticValidator(allow_additional=False)
```

Leverages [Pydantic v2](https://docs.pydantic.dev/)'s
{py:class}`pydantic.TypeAdapter` for both runtime validation and JSON Schema
generation.

**Best for**

- Projects already using Pydantic in their stack
- When you prefer Pydantic's error message format
- When `$ref`-based JSON Schema output is preferred

### Quick Comparison

| Feature                         | JsonSchema   | Pydantic           |
| ------------------------------- | ------------ | ------------------ |
| **Dependency**                  | `jsonschema` | `pydantic` (heavy) |
| **Validation speed**            | Good         | Good               |
| **Schema output style**         | Inline       | `$ref`-based       |
| **`__allow_additional` marker** | Yes          | Yes                |
| **Error detail**                | Good         | Rich               |
| **Maturity in EYConf**          | Most tested  | Well tested        |

## Choosing a Backend

### Auto-detection

If you don't specify a backend, EYConf automatically picks the best available
one for you. It tries **Pydantic first**, then falls back to **JsonSchema**:

```python
from eyconf import Config

# No validator specified — EYConf auto-detects the best available backend
config = Config(data, MySchema)
```

You can also pass a backend by name:

```python
from eyconf.validation.backends import get_validator

config = Config(data, MySchema, validator=get_validator("pydantic"))
```

Or construct a validator instance directly for full control:

```python
from eyconf.validation.backends.pydantic import PydanticValidator

config = Config(data, MySchema, validator=PydanticValidator(allow_additional=True))
```

### Which one should I use?

:::{tip}
**Start with the default (auto-detection).** You get Pydantic if it's installed,
otherwise JsonSchema. Both are well-tested and fully supported.
:::

- **Pydantic** — best if you already use Pydantic in your project, or prefer
  richer error messages and `$ref`-based JSON Schema output.
- **JsonSchema** — best if you want minimal dependencies (only `jsonschema`
  is required) and prefer inline JSON Schema output.

Switching later is a one-line change — all backends implement the same
protocol, so no other code needs to change.

## Error Handling

Validation errors are surfaced through two exception types:

{py:class}`~eyconf.validation.exceptions.ConfigurationError`
: Raised when a single validation error occurs. Contains a human-readable
`message` and an optional `section` indicating which configuration path
failed (e.g. `"transport.port"`).

{py:class}`~eyconf.validation.exceptions.MultiConfigurationError`
: Raised when multiple validation errors occur. Wraps a list of
{py:class}`ConfigurationError` instances, one per failed field.

```python
from eyconf.validation import ConfigurationError, MultiConfigurationError

try:
    validator.validate(data, MySchema)
except MultiConfigurationError as e:
    for error in e.errors:
        print(f"{error.section}: {error.message}")
except ConfigurationError as e:
    print(f"{e.section}: {e.message}")
```
