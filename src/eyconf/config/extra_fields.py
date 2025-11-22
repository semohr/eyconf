import logging
from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

from eyconf.utils import AccessProxy, AttributeDict, iter_dataclass_type, merge_dicts
from eyconf.validation import validate
from eyconf.validation._to_json import to_json_schema

from .base import EYConfBase

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")


log = logging.getLogger(__name__)


class EYConfExtraFields(EYConfBase[D]):
    """Configuration class that supports extra fields explicitly.

    This class extends the base configuration functionality to allow
    for additional fields that are not defined in the original schema.

    This additional field is accessible via the `extra_data_as_dict` property.
    """

    _extra_data: AttributeDict

    def __init__(
        self,
        data: dict | D,
        schema: type[D] | None = None,
    ):
        if schema is not None:
            self._schema = schema
        else:
            if not is_dataclass(data):
                raise ValueError(
                    "If no schema is provided, data must be of the schema dataclass instance."
                )
            self._schema = type(data)

        # Automatically set __allow_additional to True in the schema(s) if not set
        for s in iter_dataclass_type(self._schema):
            if not hasattr(s, "__allow_additional"):
                setattr(s, "__allow_additional", True)
            else:
                log.debug(
                    f"Schema {s.__name__} already has __allow_additional set to "
                    f"{getattr(s, '__allow_additional')}."
                )

        # Create schema, raise if Schema is invalid
        self._json_schema = to_json_schema(self._schema)

        # Will raise ConfigurationError if the data does not comply with the schema
        validate(data, self._json_schema)

        self._extra_data = AttributeDict()

        if is_dataclass(data):
            self._data = cast(D, data)
        else:
            self._data = None  # type: ignore
            self.update(data)

    @property
    def data(self) -> D:
        """Get the configuration data wrapped in a dynamic accessor.

        Care: Instance checks will not work as expected on this property.
        """
        return AccessProxy(self._data, self._extra_data)  # type: ignore

    @property
    def extra_data(self) -> AttributeDict:
        """Get the extra data as an AttributeDict."""
        return self._extra_data

    def to_dict(self, include_additional: bool = True) -> dict:
        """Get the full configuration data as a dictionary, including extra fields."""
        data = asdict(self._data)
        if include_additional:
            data = merge_dicts(data, self.extra_data.as_dict())
        return data

    def _update_additional(self, target, key, value: Any, _current_path: list[str]):
        extra_data: AttributeDict = self._extra_data
        for path_part in _current_path:
            extra_data = getattr(extra_data, path_part)

        if isinstance(value, dict):
            setattr(extra_data, key, AttributeDict(**value))
        else:
            setattr(extra_data, key, value)
