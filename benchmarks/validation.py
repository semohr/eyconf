"""Benchmark validation backends.

Measures ``validate()`` and ``validate_and_construct()`` performance for
the JsonSchema and Pydantic backends across a realistic nested config.

Usage::

    python benchmarks/validation.py
"""

from __future__ import annotations

import statistics
import timeit
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# Realistic nested config schema
# --------------------------------------------------------------------------- #


@dataclass
class Database:
    host: str = "localhost"
    port: int = 5432
    name: str = "myapp"
    user: str = "admin"
    password: str = "secret"
    pool_size: int = 10
    timeout: float = 30.0
    ssl: bool = True


@dataclass
class Cache:
    backend: str = "redis"
    url: str = "redis://localhost:6379"
    ttl: int = 300
    max_entries: int = 1000


@dataclass
class Logging:
    level: str = "INFO"
    format: str = "json"
    file: str = "/var/log/app.log"
    max_size: int = 10_485_760
    backup_count: int = 5


@dataclass
class SMTP:
    host: str = "smtp.example.com"
    port: int = 587
    username: str = "noreply"
    password: str = "secret"
    use_tls: bool = True


@dataclass
class AppConfig:
    """Typical application configuration with 4 nested sections."""

    database: Database = field(default_factory=Database)
    cache: Cache = field(default_factory=Cache)
    logging: Logging = field(default_factory=Logging)
    smtp: SMTP = field(default_factory=SMTP)
    debug: bool = False
    secret_key: str = "change-me"
    allowed_hosts: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])


# --------------------------------------------------------------------------- #
# Valid data for benchmarks
# --------------------------------------------------------------------------- #

VALID_DICT: dict[str, Any] = {
    "database": {
        "host": "db.example.com",
        "port": 5432,
        "name": "production",
        "user": "app",
        "password": "s3cret",
        "pool_size": 20,
        "timeout": 60.0,
        "ssl": True,
    },
    "cache": {
        "backend": "redis",
        "url": "redis://cache:6379",
        "ttl": 600,
        "max_entries": 5000,
    },
    "logging": {
        "level": "WARNING",
        "format": "text",
        "file": "/var/log/prod.log",
        "max_size": 52_428_800,
        "backup_count": 10,
    },
    "smtp": {
        "host": "mail.example.com",
        "port": 465,
        "username": "app",
        "password": "s3cret",
        "use_tls": True,
    },
    "debug": False,
    "secret_key": "prod-secret",
    "allowed_hosts": ["example.com"],
}

INSTANCE = AppConfig()  # default-constructed instance


# --------------------------------------------------------------------------- #
# Benchmark helpers
# --------------------------------------------------------------------------- #

N = 10_000
REPEAT = 5


def _run(backend: str, label: str, stmt: str, setup: str, number: int = N) -> None:
    """Run the benchmark and print mean ± stdev in µs per call."""
    timings = timeit.repeat(stmt, setup, number=number, repeat=REPEAT)
    per_call = [t / number * 1e6 for t in timings]
    mean = statistics.mean(per_call)
    stdev = statistics.stdev(per_call) if len(per_call) > 1 else 0.0
    print(f"  {backend:12s} {label:30s} {mean:8.1f} ± {stdev:5.1f} µs")


def bench_validate_dict():
    """Validate a plain dict (normal path: external data comes in as dict)."""
    print("validate(dict)  — external data entering the system")
    for backend, import_path, class_name in [
        ("JsonSchema", "eyconf.validation.backends.json_schema", "JsonSchemaValidator"),
        ("Pydantic", "eyconf.validation.backends.pydantic", "PydanticValidator"),
    ]:
        setup = (
            f"from {import_path} import {class_name}; "
            f"from {__name__} import VALID_DICT, AppConfig; "
            f"v = {class_name}()"
        )
        _run(backend, "validate(dict)", "v.validate(VALID_DICT, AppConfig)", setup)


def bench_validate_instance():
    """Validate a dataclass instance (update() / in-place mutation path)."""
    print("\nvalidate(instance)  — after in-place mutation (update path)")
    for backend, import_path, class_name in [
        ("JsonSchema", "eyconf.validation.backends.json_schema", "JsonSchemaValidator"),
        ("Pydantic", "eyconf.validation.backends.pydantic", "PydanticValidator"),
    ]:
        setup = (
            f"from {import_path} import {class_name}; "
            f"from {__name__} import INSTANCE, AppConfig; "
            f"v = {class_name}()"
        )
        _run(backend, "validate(instance)", "v.validate(INSTANCE, AppConfig)", setup)


def bench_construct():
    """Validate and construct from dict (Config.__init__ path)."""
    print("\nvalidate_and_construct(dict)  — Config.__init__ path")
    for backend, import_path, class_name in [
        ("JsonSchema", "eyconf.validation.backends.json_schema", "JsonSchemaValidator"),
        ("Pydantic", "eyconf.validation.backends.pydantic", "PydanticValidator"),
    ]:
        setup = (
            f"from {import_path} import {class_name}; "
            f"from {__name__} import VALID_DICT, AppConfig; "
            f"v = {class_name}()"
        )
        _run(
            backend,
            "validate_and_construct(dict)",
            "v.validate_and_construct(VALID_DICT, AppConfig)",
            setup,
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print(f"Backend validation benchmark ({N:,} iterations each, lower is better)\n")
    bench_validate_dict()
    bench_validate_instance()
    bench_construct()
