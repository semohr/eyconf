"""Validating configuration data against schemas."""

from __future__ import annotations

import logging

from eyconf.validation.exceptions import ConfigurationError, MultiConfigurationError

log = logging.getLogger(__name__)

from ._to_json import to_json_schema
from .validate import validate, validate_json

__all__ = [
    "to_json_schema",
    "validate",
    "validate_json",
    "ConfigurationError",
    "MultiConfigurationError",
]
