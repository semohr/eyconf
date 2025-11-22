from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

from eyconf.type_utils import is_dataclass_type

T = TypeVar("T")
D = TypeVar("D", bound="DataclassInstance")


@runtime_checkable
class DictAccess(Protocol):
    """Protocol for dict-like access."""

    def __getitem__(self, key: str) -> Any: ...  # noqa: D105


def dict_access(cls: type[T]) -> type[T]:
    """Class decorator to add dict-like access to class attributes.

    Can be used to add `dict`-like access to any class, allowing
    attribute access via the `obj['attribute']` syntax.

    Use with care, dict-style access does not provide any type safety
    and will not be checked by static type checkers.

    Usage:

    ```python
    @dict_access
    class MySchema:
        forty_two: int = 42

    obj = MySchema()
    assert isinstance(obj, DictAccess)
    print(obj['forty_two'])  # Outputs: 42
    ```
    """

    def __getitem__(self, key: str) -> Any:
        # for dict access we _only_ want to allow the aliases,
        # not the attribute names!
        aliases = {
            f.metadata["alias"]: f.name for f in fields(self) if "alias" in f.metadata
        }
        if key in aliases.keys():
            return getattr(self, aliases[key])
        elif key in aliases.values():
            _suggestion = next((k for k, v in aliases.items() if v == key), None)
            raise KeyError(
                "If an alias is defined, subscripting is only allowed "
                + f"using the alias. Use ['{_suggestion}'] instead of ['{key}']!"
            )

        return getattr(self, key)

    setattr(cls, "__getitem__", __getitem__)
    return cls


def check_dict_access(schema: D | type[D]) -> bool:
    """Whether the dataclass allows access via dict-like syntax."""
    if is_dataclass_type(schema):
        return issubclass(schema, DictAccess)
    elif is_dataclass(schema) and not isinstance(schema, type):
        return isinstance(schema, DictAccess)
    return False


def allow_additional(cls: type[T]) -> type[T]:
    """Class decorator to allow additional attributes in dataclass.

    This prevent validation errors if a dataclass instance holds an attribute
    that is not defined in the dataclass schema.

    Usage:

    ```python
    @allow_additional
    @dataclass
    class MySchema:
        forty_two: int = 42

    obj = MySchema()
    obj.extra_attr = "I am extra"
    validate(obj, MySchema)  # Does not raise
    ```
    """
    mangled = f"_{cls.__name__}__allow_additional"
    setattr(cls, mangled, True)
    return cls


def check_allows_additional(schema: D | type[D]) -> bool:
    """Whether the dataclass allows additional properties."""
    if is_dataclass_type(schema):
        return getattr(schema, f"_{schema.__name__}__allow_additional", False)
    elif is_dataclass(schema) and not isinstance(schema, type):
        return getattr(schema, f"_{schema.__class__.__name__}__allow_additional", False)
    return False
