import inspect
import logging
import sys
from typing import (
    Any,
    get_type_hints,
)

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
