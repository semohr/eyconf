# 📦 Changelog

All notable changes to this project will be documented in this file.

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
