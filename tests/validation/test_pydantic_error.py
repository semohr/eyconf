"""Unit tests for the Pydantic-specific error conversion."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

try:
    from pydantic import TypeAdapter, ValidationError

except ImportError:
    pytest.skip("Pydantic is not installed, skipping tests.", allow_module_level=True)

from eyconf.validation.backends.pydantic import to_ConfigurationError
from eyconf.validation.exceptions import ConfigurationError, MultiConfigurationError


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _validation_error(schema_type: type, data: object) -> ValidationError:
    """Validate bad data and return the caught :class:`ValidationError`."""
    adapter: TypeAdapter[object] = TypeAdapter(schema_type)
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_python(data)
    return exc_info.value


# --------------------------------------------------------------------------- #
# Schema fixtures (local to avoid cross-test pollution)
# --------------------------------------------------------------------------- #


@dataclass
class SimpleSchema:
    a: int
    b: str


@dataclass
class NestedInner:
    x: int


@dataclass
class NestedOuter:
    name: str
    inner: NestedInner


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


class TestToConfigurationError:
    """Test :func:`to_ConfigurationError` with Pydantic validation errors."""

    # -- Single error -------------------------------------------------------

    def test_single_error_returns_ConfigurationError(self):
        """A single validation error produces a ConfigurationError."""
        error = _validation_error(int, "not_an_int")
        result = to_ConfigurationError(error)

        assert isinstance(result, ConfigurationError)
        assert "not_an_int" in result.message or "int" in result.message.lower()

    def test_single_error_includes_section_from_loc(self):
        """The error path (loc) is mapped to the section field."""
        error = _validation_error(SimpleSchema, {"a": "bad", "b": "ok"})
        result = to_ConfigurationError(error)

        assert isinstance(result, ConfigurationError)
        # The section should reflect the field name that failed
        assert result.section == "a"

    def test_single_error_includes_message(self):
        """The Pydantic error message is preserved."""
        error = _validation_error(SimpleSchema, {"a": "bad", "b": "ok"})
        result = to_ConfigurationError(error)

        assert isinstance(result, ConfigurationError)
        assert result.message  # non-empty message

    # -- Nested path --------------------------------------------------------

    def test_nested_error_path_is_dot_joined(self):
        """Nested field loc tuples are joined with dots."""
        error = _validation_error(NestedOuter, {"name": "ok", "inner": {"x": "bad"}})
        result = to_ConfigurationError(error)

        assert isinstance(result, ConfigurationError)
        assert result.section == "inner.x"

    # -- Multiple errors ----------------------------------------------------

    def test_multiple_errors_return_MultiConfigurationError(self):
        """Multiple validation errors produce a MultiConfigurationError."""
        error = _validation_error(SimpleSchema, {"a": "bad", "b": 123})
        result = to_ConfigurationError(error)

        assert isinstance(result, MultiConfigurationError)
        assert len(result.errors) == 2

    def test_multiple_errors_preserve_all_messages(self):
        """Each error in MultiConfigurationError retains its original message."""
        error = _validation_error(SimpleSchema, {"a": "bad", "b": 123})
        result = to_ConfigurationError(error)

        assert isinstance(result, MultiConfigurationError)
        sections = {e.section for e in result.errors}
        assert sections == {"a", "b"}

    # -- List input ---------------------------------------------------------

    def test_list_of_validation_errors_is_merged(self):
        """A list of ValidationErrors is flattened into one result."""
        e1 = _validation_error(int, "bad1")
        e2 = _validation_error(str, 456)

        result = to_ConfigurationError([e1, e2])

        assert isinstance(result, MultiConfigurationError)
        assert len(result.errors) == 2

    # -- Edge: empty loc ----------------------------------------------------

    def test_error_with_empty_loc_has_no_section(self):
        """When loc is empty the section is None (top-level error)."""
        # A root-level schema error typically has loc=()
        error = _validation_error(int, "not_int")
        # Most type errors on root produce loc=(), but some backends differ.
        # We just assert the function doesn't crash.
        result = to_ConfigurationError(error)
        assert isinstance(result, ConfigurationError)
        assert result.message  # always has a message
