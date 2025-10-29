from dataclasses import asdict
from typing import TYPE_CHECKING, TypeVar

from eyconf.utils import AccessProxy, AttributeDict, merge_dicts

from .base import EYConfBase

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# Needs the string escaping to work at runtime as _typeshed is not a real module
D = TypeVar("D", bound="DataclassInstance")


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
        super().__init__(data, schema=schema, allow_additional_properties=True)
        self._extra_data = AttributeDict()

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
