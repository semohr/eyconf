class ConfigurationError(Exception):
    """Exception raised for configuration validation errors."""

    def __init__(self, message="Configuration error", section=None):
        self.message = message
        self.section = section
        super().__init__(self.message)

    def __str__(self):
        """Return the error message."""
        return (
            f"{self.message} in section '{self.section}'"
            if self.section
            else self.message
        )


class MultiConfigurationError(Exception):
    """Exception raised for multiple configuration validation errors."""

    def __init__(self, errors: list[ConfigurationError]):
        self.errors = errors
        super().__init__("Multiple configuration errors")

    def __str__(self):
        """Return the error message."""
        return "\n".join([str(e) for e in self.errors])
