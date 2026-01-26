# Contribution Guide

Thank you for your interest in contributing to our project! Please follow these guidelines to ensure a smooth contribution process.

## Prerequisites

- Python 3.10 or higher
- Git
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setting Up the Development Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/semohr/eyconf.git
   cd eyconf
   ```

2. **Install the dependencies with uv:**

   ```bash
   # Install with development dependencies
   uv sync --all-extras

   # Or if you prefer pip:
   pip install -e .[dev]
   ```

3. **Activate environemnt (if uv):**

   ```bash
   source .venv/env/activate
   ```

## Install pre-commit hooks

We automatically check for code style and formatting issues using pre-commit hooks. To install the hooks, run the following command:

```bash
pre-commit install
```

## Before Submitting a Pull Request

Verify that your code follows the project's coding standards and conventions. Run [Ruff](https://docs.astral.sh/ruff/) manually or use the pre-commit hooks to check for any issues. Additionally, run the tests to ensure that your changes do not break any existing functionality.

```bash
# Run Ruff manually
ruff check
# Run the tests
pytest
# Run type checking
pyrefly check
```

## Docs

To build the documentation locally, run:

```bash
cd docs
make html
```
