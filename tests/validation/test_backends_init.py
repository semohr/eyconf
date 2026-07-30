"""Tests for backend discovery and instantiation in ``validation/backends/__init__.py``."""

from __future__ import annotations

import builtins
from typing import Any
from unittest.mock import patch

import pytest

from eyconf.validation.backends import _get_default_validator, get_validator
from eyconf.validation.backends.interface import Validator


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _import_blocker(blocked: str):
    """Return a side_effect that blocks imports of *blocked*."""
    _orig = builtins.__import__

    def _block(name: str, *a: Any, **kw: Any) -> Any:
        if name == blocked:
            raise ImportError(f"No module named '{blocked}'")
        return _orig(name, *a, **kw)

    return _block


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


class TestGetValidator:
    """Tests for :func:`get_validator` with both backends installed."""

    def test_none_returns_default(self) -> None:
        v = get_validator(None)
        assert isinstance(v, Validator)

    def test_pydantic_by_name(self) -> None:
        from eyconf.validation.backends.pydantic import PydanticValidator

        v = get_validator("pydantic")
        assert isinstance(v, PydanticValidator)

    def test_jsonschema_by_name(self) -> None:
        from eyconf.validation.backends.json_schema import JsonSchemaValidator

        v = get_validator("jsonschema")
        assert isinstance(v, JsonSchemaValidator)

    def test_allow_additional_is_forwarded_pydantic(self) -> None:
        v = get_validator("pydantic", allow_additional=True)
        assert v.allow_additional is True  # type: ignore[attr-defined]

    def test_allow_additional_is_forwarded_jsonschema(self) -> None:
        v = get_validator("jsonschema", allow_additional=True)
        assert v.allow_additional is True  # type: ignore[attr-defined]

    def test_allow_additional_defaults_to_false(self) -> None:
        v = get_validator("pydantic")
        assert v.allow_additional is False  # type: ignore[attr-defined]

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported validation backend"):
            get_validator("nonexistent")  # type: ignore[arg-type]


class TestGetValidatorMissingBackends:
    """Tests for :func:`get_validator` when a specific backend is *not* installed."""

    def test_pydantic_not_installed_raises(self) -> None:
        # Remove cached modules so the re-import is forced.
        with patch.dict(
            "sys.modules",
            {"eyconf.validation.backends.pydantic": None, "pydantic": None},
        ):
            with patch(
                "builtins.__import__",
                side_effect=_import_blocker("pydantic"),
            ):
                with pytest.raises(ValueError, match="pydantic backend"):
                    get_validator("pydantic")

    def test_jsonschema_not_installed_raises(self) -> None:
        with patch.dict(
            "sys.modules",
            {"eyconf.validation.backends.json_schema": None, "jsonschema": None},
        ):
            with patch(
                "builtins.__import__",
                side_effect=_import_blocker("jsonschema"),
            ):
                with pytest.raises(ValueError, match="jsonschema backend"):
                    get_validator("jsonschema")


class TestDefaultValidator:
    """Tests for :func:`_get_default_validator`."""

    def test_returns_validator(self) -> None:
        v = _get_default_validator()
        assert isinstance(v, Validator)

    def test_no_backend_installed_raises(self) -> None:
        with patch("builtins.__import__", side_effect=ImportError):
            with pytest.raises(
                ValueError, match="No supported validation backend found"
            ):
                _get_default_validator()
