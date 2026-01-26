"""Test coverage for validation exceptions."""

from jsonschema import ValidationError
from eyconf.validation.exceptions import (
    ConfigurationError,
    MultiConfigurationError,
)


class TestConfigurationError:
    """Test the ConfigurationError exception class."""

    def test_str_without_section(self):
        """Test __str__ when no section is provided."""
        error = ConfigurationError("Simple error")
        assert str(error) == "Simple error"

    def test_str_with_section(self):
        """Test __str__ when section is provided."""
        error = ConfigurationError("Complex error", section="api.config")
        assert str(error) == "Complex error in section 'api.config'"

    def test_fromValidationError(self):
        """Test that original_error is stored correctly."""
        error = ConfigurationError.from_ValidationErrors(ValidationError("Foo"))
        assert isinstance(error, ConfigurationError)
        assert not isinstance(error, MultiConfigurationError)

    def test_fromValidationErrorsr(self):
        error = ConfigurationError.from_ValidationErrors(
            [ValidationError("Foo"), ValidationError("Bar")]
        )
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, MultiConfigurationError)


class TestMultiConfigurationError:
    def test_str_without_section(self):
        """Test __str__ when no section is provided."""
        error = MultiConfigurationError(
            [
                ConfigurationError("Simple error"),
                ConfigurationError("Another simple error"),
            ]
        )
        assert len(error) == 2
        assert "Found 2 configuration error(s)" in str(error)
        assert "Simple error" in str(error)
        assert "Another simple error" in str(error)

        assert str(error[0]) == "Simple error"

        # Can iter
        for err in error:
            assert isinstance(err, ConfigurationError)

    def test_empty_error(self):
        error = MultiConfigurationError([])
        assert str(error) == "No configuration errors"
