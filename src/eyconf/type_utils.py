from __future__ import annotations

import inspect
import logging
import sys
from collections.abc import Iterator, Sequence
from dataclasses import is_dataclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeGuard,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

D = TypeVar("D", bound="DataclassInstance")

log = logging.getLogger(__name__)


def get_type_hints_resolve_namespace(obj, include_extras: bool = False):
    """Get type hints for an object, resolving namespaces for dataclasses.

    Workaround for when using `from __future__ import annotations`.

    This is needed because Types become strings, and native
    recursive resolution does not work on strings alone.
    To resolve types recursively in this case, the Dataclasses are needed
    and can be passed to `get_type_hints` via `globalns` and `localns`.
    """
    try:
        return get_type_hints(obj, include_extras=include_extras)
    except NameError:
        globalns, localns = _get_namespace(obj)
        return get_type_hints(
            obj,
            globalns=globalns,
            localns=localns,
            include_extras=include_extras,
        )


def _get_namespace(
    obj,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Get the global and local namespaces for a dataclass.

    I.e. where to find the dataclass definitions and possibly
    other types used in the dataclass.

    Workaround for when using `from __future__ import annotations`.

    This is needed because Types become strings, and native
    recursive resolution does not work on strings alone.
    To resolve types recursively in this case, the Dataclasses are needed
    and can be passed to `get_type_hints` via `globalns` and `localns`.
    """
    module = sys.modules.get(obj.__module__)
    globalns = getattr(module, "__dict__", {}) if module else {}

    # Get the caller's locals to handle locally defined classes
    frame = inspect.currentframe()
    localns = {}

    # Walk up the call stack to find local variables
    while frame:
        frame_locals = frame.f_locals

        # Merge locals that might contain our dataclass definitions
        for name, value in frame_locals.items():
            if inspect.isclass(value):
                localns[name] = value
                globalns[name] = value  # Also add to globals

        frame = frame.f_back

    return globalns, localns


def is_dataclass_type(obj: Any) -> TypeGuard[type]:
    """Check if an object is a dataclass type (class), not an instance."""
    return is_dataclass(obj) and isinstance(obj, type)


def is_dataclass_instance(obj: Any) -> TypeGuard[DataclassInstance]:
    """Check if an object is a dataclass instance."""
    return is_dataclass(obj) and not isinstance(obj, type)


def iter_dataclass_type(schema: type[D]) -> Iterator[type[DataclassInstance]]:
    """Iterate over all dataclass nested instances in the given dataclass type.

    Duplicate types are automatically handled by using a set to track visited types.

    Yields
    ------
    DataclassInstance
        Each nested dataclass instance found within the schema (also the root).
    """
    visited = set()
    stack = [schema]

    def _add_type_to_stack(*t: type[Any]) -> None:
        """Add type to stack if it is a dataclass and not yet visited."""
        for item in t:
            if is_dataclass_type(item) and id(item) not in visited:
                stack.append(item)

    while stack:
        current_type = stack.pop()
        type_id = id(current_type)
        # Skip if we've already visited this type
        if type_id in visited:
            continue

        visited.add(type_id)
        yield current_type

        # Process fields of the current dataclass
        type_hints = get_type_hints_resolve_namespace(current_type, include_extras=True)
        for _, field_type in type_hints.items():
            origin = get_origin(field_type)

            if origin is Annotated:
                # Unpack Annotated types
                field_type = get_args(field_type)[0]
                origin = get_origin(field_type)

            if origin in {UnionType, list, tuple, set, Sequence, TypingSequence, dict}:
                # Handle collection types
                _add_type_to_stack(*get_args(field_type))

            if is_dataclass_type(field_type):
                _add_type_to_stack(field_type)
