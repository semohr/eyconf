from __future__ import annotations

import copy
import logging
import types
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

log = logging.getLogger(__name__)

D = TypeVar("D", bound="DataclassInstance")


@dataclass
class AttributeDict:
    """A generic dataclass for holding dynamic attributes."""

    def __init__(self, **kwargs: Any):
        """Initialize the AttributeDict with given keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        """Get attribute dynamically. If it does not exist, we create it."""
        if name.startswith("_"):
            raise AttributeError(f"{name} not found")

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            n = AttributeDict()
            setattr(self, name, n)
            return n

    def __setattr__(self, name: str, value: Any):
        """Set attribute dynamically."""
        if isinstance(value, dict):
            value = AttributeDict(**value)
        object.__setattr__(self, name, value)

    def __getitem__(self, key: str) -> Any:
        """Get item dynamically."""
        return self.__getattr__(key)

    def as_dict(self) -> dict:
        """Convert the AttributeDict to a standard dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, AttributeDict):
                result[key] = value.as_dict()
            else:
                result[key] = value
        return result

    def __deepcopy__(self, memo: dict) -> AttributeDict:
        """Create a deep copy of the AttributeDict."""
        # Avoid infinite recursion with memo
        if id(self) in memo:
            return memo[id(self)]

        # Create new instance
        new_instance = AttributeDict()
        memo[id(self)] = new_instance

        # Deep copy all attributes
        for key, value in self.__dict__.items():
            # Use copy.deepcopy for nested objects, but handle AttributeDict specially
            if isinstance(value, AttributeDict):
                setattr(new_instance, key, deepcopy(value, memo))
            else:
                setattr(new_instance, key, deepcopy(value, memo))

        return new_instance

    def __repr__(self) -> str:
        """Representation of the AttributeDict."""
        return f"AttributeDict({self.as_dict()})"

    def __str__(self) -> str:
        """Use the dict string representation."""
        return str(self.as_dict())

    def __bool__(self) -> bool:
        """Return False if the AttributeDict is empty, True otherwise."""
        return bool(self.__dict__)


class AccessProxy(Generic[D]):
    """Proxy to access attributes dynamically."""

    _data: D
    _extra_data: AttributeDict

    def __init__(self, data: D, extra_data: AttributeDict):
        self._data = data
        self._extra_data = extra_data

    def __getattr__(self, name: str) -> Any:
        """Get attribute from either the typed data or additional data."""
        try:
            ret = getattr(self._data, name)
            # We need to wrap nested dataclasses as well
            # Needed for accessing a mixed case, where we add an unknown property to
            # a nested schema. In this case, we need the same extra level in _extra_data.
            if is_dataclass(ret):
                return AccessProxy(ret, getattr(self._extra_data, name))  # type: ignore[arg-type]
            return getattr(self._data, name)
        except AttributeError:
            return getattr(self._extra_data, name)

    def __getitem__(self, key: str) -> Any:
        """Get item dynamically."""
        return self.__getattr__(key)

    def __setattr__(self, name: str, value: Any):
        """Set attribute on either the typed data or additional data."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            if hasattr(self._data, name):
                setattr(self._data, name, value)
            else:
                setattr(self._extra_data, name, value)

    def __delattr__(self, name: str):
        """Delete attribute from either the typed data or additional data."""
        if name.startswith("_"):
            object.__delattr__(self, name)
        else:
            if hasattr(self._data, name):
                delattr(self._data, name)
            else:
                delattr(self._extra_data, name)

    def as_dict(self) -> dict:
        """Convert the AccessProxy to a standard dictionary."""
        merged = deepcopy(self._extra_data.as_dict())
        data_dict = deepcopy(asdict(self._data))
        result = merge_dicts(data_dict, merged)
        return result


def merge_dicts(a: dict, b: dict, path=[]):
    """Merge dict b into dict a, raising an exception on conflicts."""
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                raise Exception("Conflict at " + ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def dataclass_from_dict(
    in_type: type[D], data: dict, allow_additional: bool = False
) -> D:
    """Convert a dict to a dataclass instance of the given type. Always returns a dataclass."""
    result = _dataclass_from_dict_inner(in_type, data, allow_additional)
    if result is None:
        raise ValueError(f"Could not parse data {data} with type {in_type}")
    return result


def _dataclass_from_dict_inner(
    target_type: type, data: Any, allow_additional: bool = False
) -> Any:
    """Inner function that handles Union types and may return None."""
    # Handle Union types
    origin = get_origin(target_type)
    if origin is Union or origin is types.UnionType:
        args = get_args(target_type)
        includes_none = any(arg is types.NoneType or arg is type(None) for arg in args)

        if data is None and includes_none:
            return None

        for arg in args:
            if arg is types.NoneType or arg is type(None):
                continue
            try:
                return _dataclass_from_dict_inner(arg, data, allow_additional)
            except (ValueError, TypeError, KeyError):
                continue
        return None

    # Handle dict data - convert to dataclass
    if isinstance(data, dict) and is_dataclass(target_type):
        field_types = get_type_hints(target_type, include_extras=False)
        found_fields = {}
        additional_fields = {}

        aliased_fields = {}  # alias to name, only aliased fields
        field_types_to_use = {}  # name to type, all fields
        for f in fields(target_type):
            if hasattr(f, "metadata"):
                aliased_fields[f.metadata.get("alias")] = f.name
            field_types_to_use[f.name] = field_types.get(f.name, f.type)

        for key, value in data.items():
            if key in aliased_fields.keys():
                key = aliased_fields[key]
                found_fields[key] = _dataclass_from_dict_inner(
                    field_types_to_use[key], value, allow_additional
                )
            elif key in field_types_to_use.keys():
                found_fields[key] = _dataclass_from_dict_inner(
                    field_types_to_use[key], value, allow_additional
                )
            else:
                additional_fields[key] = value

        try:
            res = target_type(**found_fields)  # type: ignore[bad-instantiation]
            if allow_additional:
                for key, value in additional_fields.items():
                    setattr(res, key, value)
            elif len(additional_fields) > 0:
                raise TypeError(
                    f"Found additional fields {list(additional_fields.keys())}. "
                    + "Consider setting `allow_additional=True`"
                )
            return res
        except TypeError as e:
            raise ValueError(f"Failed to create {target_type.__name__}: {e}")

    # Potentially nested dataclass in dicts
    if isinstance(data, dict) and get_origin(target_type) is dict:
        key_type, value_type = get_args(target_type)
        return {
            _dataclass_from_dict_inner(
                key_type, k, allow_additional
            ): _dataclass_from_dict_inner(value_type, v, allow_additional)
            for k, v in data.items()
        }

    # Handle sequence types (list, tuple)
    if isinstance(data, (list, tuple)):
        if hasattr(target_type, "__args__") and target_type.__args__:
            elem_type = target_type.__args__[0]
            return [
                _dataclass_from_dict_inner(elem_type, item, allow_additional)
                for item in data
            ]
        else:
            return data

    # Handle primitive types
    return data


T = TypeVar("T")


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


def asdict_with_aliases(obj: DataclassInstance | DataclassInstance) -> dict:
    """
    Convert a dataclass to a dict, applying aliases if present.

    Every attribute in the dataclass that has an `alias` defined in the metadata
    will use the alias as the key in the resulting dictionary (instead of the attribute name).

    This is pretty much a copy of the standard `dataclasses.asdict` function,
    but we had to modify it, because the dict_factory needs to access obj recursively.
    (previously dataclass obj not passed down)
    """
    if not hasattr(type(obj), "__dataclass_fields__"):
        raise TypeError("asdict_with_aliases() should be called on dataclass instances")

    return _asdict_inner(obj, dict_factory=_alias_dict_factory)  # type: ignore[arg-type]


# -------------- Slightly modified copy from dataclasses.asdict -------------- #

_ATOMIC_TYPES = frozenset(
    {
        # Common JSON Serializable types
        types.NoneType,
        bool,
        int,
        float,
        str,
        # Other common types
        complex,
        bytes,
        # Other types that are also unaffected by deepcopy
        types.EllipsisType,
        types.NotImplementedType,
        types.CodeType,
        types.BuiltinFunctionType,
        types.FunctionType,
        type,
        range,
        property,
    }
)


def _asdict_inner(obj, dict_factory):
    if type(obj) in _ATOMIC_TYPES:
        return obj
    elif hasattr(type(obj), "__dataclass_fields__"):
        # fast path for the common case
        if dict_factory is dict:
            return {
                f.name: _asdict_inner(getattr(obj, f.name), dict) for f in fields(obj)
            }
        else:
            result = []
            for f in fields(obj):
                value = _asdict_inner(getattr(obj, f.name), dict_factory)
                result.append((f.name, value))
            return dict_factory(obj, result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        # obj is a namedtuple.  Recurse into it, but the returned
        # object is another namedtuple of the same type.  This is
        # similar to how other list- or tuple-derived classes are
        # treated (see below), but we just need to create them
        # differently because a namedtuple's __init__ needs to be
        # called differently (see bpo-34363).

        # I'm not using namedtuple's _asdict()
        # method, because:
        # - it does not recurse in to the namedtuple fields and
        #   convert them to dicts (using dict_factory).
        # - I don't actually want to return a dict here.  The main
        #   use case here is json.dumps, and it handles converting
        #   namedtuples to lists.  Admittedly we're losing some
        #   information here when we produce a json list instead of a
        #   dict.  Note that if we returned dicts here instead of
        #   namedtuples, we could no longer call asdict() on a data
        #   structure where a namedtuple was used as a dict key.

        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        # Assume we can create an object of this type by passing in a
        # generator (which is not true for namedtuples, handled
        # above).
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))
            for k, v in obj.items():
                result[_asdict_inner(k, dict_factory)] = _asdict_inner(v, dict_factory)
            return result
        return type(obj)(
            (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
            for k, v in obj.items()
        )
    else:
        return copy.deepcopy(obj)


def _alias_dict_factory(obj, items):
    result = {}
    for key, value in items:
        # Find the field object for this key
        field_obj = next((f for f in fields(obj) if f.name == key), None)
        if field_obj and "alias" in field_obj.metadata:
            result[field_obj.metadata["alias"]] = value
        else:
            result[key] = value
    return result
