from types import NoneType
from typing import TYPE_CHECKING, Sequence, Union

from typing_extensions import Final

if TYPE_CHECKING:
    Primitives = Union[int, float, str, bool, type(None), NoneType]


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
