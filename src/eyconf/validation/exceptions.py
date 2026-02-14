from __future__ import annotations

from jsonschema import ValidationError


class ConfigurationError(Exception):
    """Exception for configuration validation errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        section: str | None = None,
        original_error: ValidationError | None = None,
    ):
        self.message = message
        self.section = section
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self):
        """Return the error message."""
        if self.section:
            return f"{self.message} in section '{self.section}'"
        return self.message

    @classmethod
    def from_ValidationErrors(
        cls, error: ValidationError | list[ValidationError]
    ) -> ConfigurationError:
        """Create a ConfigurationError from a ValidationError or a list of ValidationErrors."""
        if isinstance(error, list):
            errors = []
            for e in error:
                path = [str(p) for p in e.path]
                errors.append(
                    ConfigurationError(
                        e.message,
                        ".".join(path) if path else None,
                        original_error=e,
                    )
                )
            return MultiConfigurationError(errors)
        else:
            path = [str(p) for p in error.path]
            return ConfigurationError(
                error.message,
                ".".join(path) if path else None,
                original_error=error,
            )


class MultiConfigurationError(ConfigurationError):
    """Exception for multiple configuration validation errors."""

    def __init__(self, errors: list[ConfigurationError]):
        self.errors = errors
        super().__init__("Multiple configuration errors")

    def __str__(self):
        """Return formatted error messages for all errors."""
        if not self.errors:
            return "No configuration errors"

        error_lines = []
        for i, error in enumerate(self.errors, 1):
            error_lines.append(f"{i}. {error}")

        return f"Found {len(self.errors)} configuration error(s):\n" + "\n".join(
            error_lines
        )

    def __len__(self):
        """Return the number of errors."""
        return len(self.errors)

    def __getitem__(self, index):
        """Get error by index."""
        return self.errors[index]

    def __iter__(self):
        """Iterate over errors."""
        return iter(self.errors)
