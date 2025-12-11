from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import is_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeVar,
    overload,
    runtime_checkable,
)

from eyconf.type_utils import is_dataclass_type
from eyconf.utils import get_metadata

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar("T")
D = TypeVar("D", bound="DataclassInstance")


@runtime_checkable
class DictAccess(Protocol):
    """Protocol for dict-like access."""

    def __getitem__(self, key: str) -> Any: ...  # noqa: D105


@runtime_checkable
class DictSetAccess(Protocol):
    """Protocol for dict-like access with setting."""

    def __setitem__(self, key: str, value: Any) -> None: ...  # noqa: D105


def _aliases_map(cls: DataclassInstance) -> dict[str, str]:
    """Get mapping of aliases to field names for a dataclass."""
    return {m["alias"]: f.name for f, m in get_metadata(cls) if "alias" in m}


def _get_attr_resolve_alias(self: DataclassInstance, key: str) -> Any:
    """Get item resolving aliases."""
    aliases = _aliases_map(self)
    if key in aliases.keys():
        return getattr(self, aliases[key])
    elif key in aliases.values():
        _suggestion = next((k for k, v in aliases.items() if v == key), None)
        raise KeyError(
            "If an alias is defined, subscripting is only allowed "
            + f"using the alias. Use ['{_suggestion}'] instead of ['{key}']!"
        )

    return getattr(self, key)


def _set_attr_resolve_alias(self: DataclassInstance, key: str, value: Any) -> None:
    """Set item resolving aliases."""
    aliases = _aliases_map(self)
    if key in aliases.keys():
        return setattr(self, aliases[key], value)
    elif key in aliases.values():
        _suggestion = next((k for k, v in aliases.items() if v == key), None)
        raise KeyError(
            "If an alias is defined, subscripting is only allowed "
            + f"using the alias. Use ['{_suggestion}'] instead of ['{key}']!"
        )

    return setattr(self, key, value)


@overload
def dict_access(cls: type[T]) -> type[T]: ...
@overload
def dict_access(
    cls: None = None, getter: bool = True, setter: bool = False
) -> Callable[[type[T]], type[T]]: ...


def dict_access(
    cls: type[T] | None = None, getter: bool = True, setter: bool = False
) -> type[T] | Callable[[type[T]], type[T]]:
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

    #1 (cls) -> cls


    @dict_access(setter=True)
    class MySchema:

    #2 (args) -> (cls) -> cls

    obj = MySchema()
    assert isinstance(obj, DictAccess)
    print(obj['forty_two'])  # Outputs: 42
    ```
    """

    def _decorate(cls: type[T]) -> type[T]:
        @functools.wraps(cls)
        def wrap(target_cls: type[T]) -> type[T]:
            if getter:
                setattr(target_cls, "__getitem__", _get_attr_resolve_alias)
            if setter:
                setattr(target_cls, "__setitem__", _set_attr_resolve_alias)
            return target_cls

        return wrap(cls)

    if cls is None:
        return _decorate
    else:
        return _decorate(cls)


def allow_additional(cls: type[T]) -> type[T]:
    """Class decorator to allow additional attributes in dataclass.

    This prevent validation errors if a dataclass instance holds an attribute
    that is not defined in the dataclass schema.

    Note this will not automatically load additional (none-schema) fields from the yaml.
    To also load additional fields use `EyConfExtraFields` as base class for your
    configuration dataclass.
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
