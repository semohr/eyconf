from __future__ import annotations

from collections.abc import Sequence
from types import NoneType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    Primitives = int | float | str | bool | None


primitive_types: Final[Sequence[type[object]]] = [
    int,
    float,
    str,
    bool,
    type(None),
    NoneType,
]

primitive_type_mapping: Final[dict[type[object], str]] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    type(None): "null",
    NoneType: "null",
}
