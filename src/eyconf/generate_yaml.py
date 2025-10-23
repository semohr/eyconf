"""Generate a default yaml file from a dataclass schema.

This is relatively dirty and not all edge cases might be covered. Works for most
simple cases though.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import _MISSING_TYPE, Field, fields, is_dataclass
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Dict,
    Union,
    get_args,
    get_origin,
)

from eyconf.constants import primitive_types
from eyconf.type_utils import get_type_hints_resolve_namespace

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from eyconf.constants import Primitives


class Line(ABC):
    """A line of yaml content."""

    is_comment: bool = False
    indent: int = 0

    def __init__(self, is_comment: bool = False, indent: int = 0):
        self.is_comment = is_comment
        self.indent = indent

    @property
    @abstractmethod
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        pass

    @property
    def content(self) -> str:
        """Return the formatted line."""
        return f"{'  ' * self.indent}{'# ' if self.is_comment else ''}{self._content}"


class EmptyLine(Line):
    """An empty line of yaml content."""

    def __init__(self):
        super().__init__(is_comment=False, indent=0)

    @property
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        return ""

    @property
    def content(self) -> str:
        """Return the formatted line."""
        return ""


class CommentLine(Line):
    """A comment line of yaml content."""

    def __init__(self, comment: str, indent: int = 0):
        super().__init__(is_comment=True, indent=indent)
        self.comment = comment

    @property
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        return self.comment.strip()


class MapLine(Line):
    """A map line of yaml content."""

    name: str
    default_value: Primitives

    def __init__(self, name: str, default_value: Primitives, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.default_value = default_value

    @property
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        value = self.default_value
        if value is None:
            value = "null"
        elif isinstance(value, bool):
            value = str(value).lower()
        return f"{self.name}: {value}"


class SequenceLine(Line):
    """A sequence line of yaml content."""

    default_value: Primitives

    def __init__(self, default_value: Primitives, **kwargs):
        super().__init__(**kwargs)
        self.default_value = default_value

    @property
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        return f"- {self.default_value}"


class SectionLine(Line):
    """A section line of yaml content."""

    name: str

    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    @property
    def _content(self) -> str:
        """Return the formatted line. Without indentation or comment."""
        return f"{self.name}:"


def dataclass_to_yaml(schema: type[DataclassInstance] | DataclassInstance) -> str:
    """Generate a yaml string from a dataclass schema."""
    lines = _dataclass_to_lines(schema)
    return "\n".join([line.content for line in lines])


def _dataclass_to_lines(
    schema: type[DataclassInstance] | DataclassInstance,
    indent: int = 0,
) -> list[Line]:
    """Generate yaml from a dataclass schema."""
    lines: list[Line] = []

    # Parse docstring
    if schema.__doc__ is not None and __is_custom_docstring(schema):
        lines += __split_docstring(schema.__doc__, indent=indent)
        lines.append(EmptyLine())

    # Handle dataclass instances
    if __is_dataclass_instance(schema):
        dict = schema.__dict__
        for key, value in dict.items():
            lines.append(MapLine(name=key, default_value=value, indent=indent))
        return lines

    # Handle dataclass types
    # by parsing type hint
    dataclass_types = get_type_hints_resolve_namespace(
        schema,
        include_extras=True,
    )
    all_fields = fields(schema)

    for field in all_fields:
        lines += __field_to_lines(field, dataclass_types[field.name], indent=indent)

    return lines


def __field_to_lines(field: Field[Any], field_type: type, indent=0) -> list[Line]:
    """Parse a primitive field and return a list of lines.

    Parameters
    ----------
    field : Field
        The field to parse.
    field_type : type
        The type of the field. Parsed here additionally
        to the included type in the field to support
        `from __future__ import annotations`. This is basically
        an overwrite of `field.type`.

    Returns
    -------
    list[str]
        A list of lines, each no longer than `l` characters.
    """
    lines = []
    origin = get_origin(field_type)
    args = get_args(field_type)

    if is_dataclass(field_type):
        # Add section
        lines.append(SectionLine(field.name, indent=indent))
        lines += _dataclass_to_lines(field_type, indent=indent + 1)
        lines.append(EmptyLine())
        return lines

    # Extract docstring from annotated
    if origin is Annotated:
        annotations = [arg for arg in args if isinstance(arg, str)]
        args = [arg for arg in args if not isinstance(arg, str)]
        for annotation in annotations:
            lines += __split_docstring(annotation, indent=indent)

    # Check if field is optional
    is_optional = False
    if origin is UnionType or origin is Union:
        is_optional = type(None) in args or NoneType in args
        args = [arg for arg in args if arg is not type(None) and arg is not NoneType]

    # Parse default
    default_missing = True
    default_value: Any = None
    if isinstance(field.default, _MISSING_TYPE):
        if isinstance(field.default_factory, _MISSING_TYPE):
            default_missing = True
        else:
            default_value = field.default_factory()
            default_missing = False
    else:
        default_value = field.default
        default_missing = False

    if origin in [dict, Dict] and default_missing:
        default_value = {}
        default_missing = False

    # No default value only allowed if the field is optional
    if default_missing and not is_optional:
        raise ValueError(
            f"Field '{field.name}' has no default value! You may set one using direct assignment or a default factory."
        )

    # Default value: Lists/Sequences
    if isinstance(default_value, list):
        if len(default_value) == 0:
            default_value = None
        else:
            """
            Stuff:
                - 1
                - 2
                - 3
            """
            lines.append(SectionLine(field.name, indent=indent))
            for value in default_value:
                if __is_primitive_instance(value):
                    lines.append(SequenceLine(default_value=value, indent=indent + 1))
                    continue

                if __is_dataclass_instance(value):
                    lines.append(SequenceLine("", indent=indent + 1))
                    lines += _dataclass_to_lines(value, indent=indent + 2)
                    continue

                raise NotImplementedError(
                    f"Field type {field.type} {args} {origin} is not supported."
                )

            return lines

    # Default value: dicts
    if isinstance(default_value, dict):
        if len(default_value) == 0:
            """
            Stuff: {}
            """
            lines.append(MapLine(name=field.name, default_value=r"{}", indent=indent))
            return lines
        else:
            """
            Stuff:
                key1: value1
                key2: value2
            """
            lines.append(SectionLine(field.name, indent=indent))
            for key, value in default_value.items():
                if not isinstance(key, str):
                    raise ValueError("Only string keys are supported in dict types")

                if __is_primitive_instance(value):
                    lines.append(
                        MapLine(name=key, default_value=value, indent=indent + 1)
                    )
                    continue

                if __is_dataclass_instance(value):
                    lines.append(MapLine(name=key, default_value="", indent=indent + 1))
                    lines += _dataclass_to_lines(value, indent=indent + 2)
                    continue

                raise NotImplementedError(
                    f"Field type {field.type} {args} {origin} is not supported."
                )

            return lines

    # Might not type check but it is a good enough heuristic
    # if default_value is set wrongly there are more issues anyways
    if __is_primitive_instance(default_value) or is_optional:
        lines.append(
            MapLine(name=field.name, default_value=default_value, indent=indent)
        )
        return lines

    raise NotImplementedError(
        f"Field type {field.type} {args} {origin} is not supported."
    )


def __split_docstring(docstring: str, l=80, indent=0) -> list[Line]:
    """Parse a docstring and return a list of lines.

    Tries to split full words if possible.

    Parameters
    ----------
    docstring : str
        The docstring to parse.

    l : int
        The line length.

    Returns
    -------
    list[str]
        A list of lines, each no longer than `l` characters.
    """
    lines = []
    for line in docstring.split("\n"):
        while len(line) > l:
            split_at = line.rfind(" ", 0, l)
            if split_at == -1:
                # If no space is found, split at the maximum length
                split_at = l
            lines.append(line[:split_at])
            line = line[split_at:].lstrip()
        lines.append(line)
    return [CommentLine(line.strip(), indent=indent) for line in lines if line.strip()]


def __is_custom_docstring(dataclass_obj):
    # Create a regex pattern to match the default docstring format
    default_docstring_pattern = r"^[^\(]+\([^\)]*\)(\w*|.*)$"

    # Check if the docstring matches the default pattern
    return re.match(default_docstring_pattern, dataclass_obj.__doc__) is None


def __is_primitive_type(t: Any) -> bool:
    """Check if the field type is supported.

    Parameters
    ----------
    field : Field
        The field to check.

    Returns
    -------
    bool
        True if the field type is supported, False otherwise.
    """
    if t in primitive_types:
        return True
    return False


def __is_primitive_instance(t: Any) -> bool:
    """Check if the field type is a primitive instance.

    Parameters
    ----------
    field : Field
        The field to check.

    Returns
    -------
    bool
        True if the field type is a primitive instance, False otherwise.
    """
    if isinstance(t, (*primitive_types,)):
        return True
    return False


def __is_dataclass_instance(t: Any) -> bool:
    """Check if the field type is a dataclass instance.

    Parameters
    ----------
    field : Field
        The field to check.

    Returns
    -------
    bool
        True if the field type is a dataclass instance, False otherwise.
    """
    return is_dataclass(t) and not isinstance(t, type)


__all__ = [
    "dataclass_to_yaml",
]
