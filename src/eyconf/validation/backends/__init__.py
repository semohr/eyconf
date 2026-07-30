from typing import Literal

from .interface import Validator

__all__ = [
    "Validator",
]


def _get_default_validator(allow_additional: bool = False) -> Validator:
    """Get the default validation backend.

    Returns
    -------
    Validator
        The default validation backend instance.

    Raises
    ------
    ValueError
        If no supported validation backend is found.
    """
    try:
        from .pydantic import PydanticValidator

        return PydanticValidator()
    except ImportError:
        pass

    try:
        from .json_schema import JsonSchemaValidator

        return JsonSchemaValidator()
    except ImportError:
        pass

    raise ValueError(
        "No supported validation backend found. Please install one of: "
        "msgspec, pydantic, or jsonschema."
    )


def get_validator(
    backend: Literal["jsonschema"] | Literal["pydantic"] | None = None,
    allow_additional: bool = False,
) -> Validator:
    """Get a validation backend.

    Parameters
    ----------
    backend : Literal["jsonschema", "pydantic"], optional
        The validation backend to use. If None, defaults to first one installed.

    Returns
    -------
    Validator
        The validation backend instance.

    Raises
    ------
    ValueError
        If the specified backend is not supported.
    """
    if backend is None:
        return _get_default_validator(allow_additional)

    elif backend == "pydantic":
        try:
            from .pydantic import PydanticValidator

            return PydanticValidator(allow_additional)
        except ImportError as e:
            raise ValueError(
                "pydantic backend requested but pydantic is not installed."
            ) from e
    elif backend == "jsonschema":
        try:
            from .json_schema import JsonSchemaValidator

            return JsonSchemaValidator(allow_additional)
        except ImportError as e:
            raise ValueError(
                "jsonschema backend requested but jsonschema is not installed."
            ) from e

    raise ValueError(f"Unsupported validation backend: {backend}")
