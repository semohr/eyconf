# 📦 Changelog

All notable changes to this project will be documented in this file.

## [0.4.0]

* Moved some of the getting-started information into the advanced-usage guide.
* Added information on how to use the `@dict_access` decorator for dict-style access to configuration values.

## [0.3.3]

* Empty AttributeDicts are no longer considered truthy. An AttributeDict with no keys will evaluate to False.

## [0.3.2]

* Added repr and str methods to AttributeDict for better debugging and logging.
* Fixed issue where attribute access on EYConfExtraFields would populate data with empty AttributeDicts for missing extra fields.

## [0.3.1]

* Fixed an issue with updates not beeing applied to dataclasses if given a nested dict. E.g. `dict[str, Class]` was interpreted as `dict[str, dict]` and not converted to the target dataclass.

## [0.3.0]

* Added support for extra fields in configuration schemas. Additional fields are not typed but can be retrieved. Use `EYConfExtraFields` for even more flexibility.
* Modularized config.py file into multiple modules for better maintainability.
* Added `update` method to `EYConfBase` for updating configuration data programmatically.
* Improved tests and test coverage, especially for edge cases in the update function.
* Default `__getattr__` behavior is removed in favor of explicit access methods to avoid confusion with extra fields. Use `config.data.field_name` to access fields!
* Repo is no typed with `pyrefly`.
* Improved documentation with more examples and clearer explanations.

## [0.2.1]

### Fixed

* Using `from __future__ import annotations` caused issues with dataclass field type resolution. This has been fixed to ensure compatibility.
* Generation of yaml for dictionary types with arbitrary keys and typed values now working.

### Changed

* Moved `Primitives` and `primitive_types` to `eyconf.constants` for better modularity.

### Added

* More examples in the quickstart guide.


## [0.2.0] - 2025-10-23

### Added

* Now supports patternProperties for nested types, where they key can be arbitrary but its content should still adhere to a specific type.
* Added support for validating mixed type literals.
* Added functionality to disallow or allow additional properties in configuration schemas.

### Changed

* The `NoneType` type has been added to to literals and represents `null` values in YAML.

## [0.1.0] - 2025-08-07

### Added

* Added changelog
* Added `eyconf.cli` module for CLI commands.
   * Automatically generates a CLI for configuration management.

### Changed

* remove path from constructor in favour for get_file method.

## [0.0.7] - 2025-08-07

### Added

* Logo and basic usage example.
* Moved quickstart guide into documentation.


### Changed

* Adjusted string formatting.

---

## [0.0.6] - 2025-07-10

### Fixed

* Default values for lists were not generated correctly.

---

## [0.0.5] - 2025-07-09

> Version bump only. No functional changes listed.

---

## [0.0.4] - 2025-07-05

### Added

* FAQ section to documentation.
* Test for derived classes.

### Changed

* Default YAML API to allow custom default values.

---

## [0.0.3] - 2025-07-01

### Changed

* Fixed typos in README.

---

## [0.0.2] - 2025-06-28

### Fixed

* `issubclass()` errors when non-class types were used.
* Renamed `validate` function to `validation`.
* Minor formatting issues in documentation.

---

## [0.0.1] - 2025-06-26 (Inferred)

### Added

* Python package initialization.
* YAML-based config generation, validation, and creation.
* GitHub publish workflow.
* Python version checks and compatibility for 3.12.
* Initial tests and release scaffolding.
