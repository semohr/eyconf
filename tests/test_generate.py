# In CI: We run this without `from __future__ import annotations` to ensure compatibility.
# from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, Optional

import logging
import pytest
import yaml

from eyconf.generate_yaml import dataclass_to_yaml

log = logging.getLogger(__name__)


class TestGenerateDefault:
    """Test the generation of default yaml from a dataclass."""

    def test_basic(self):
        """Test the basic functionality."""

        @dataclass
        class Basic:
            int_field: int = 42
            str_field: str = "Hello, World!"
            bool_field: bool = True
            float_field: float = 3.14

        yaml_str = dataclass_to_yaml(Basic)
        assert (
            yaml_str
            == "int_field: 42\nstr_field: Hello, World!\nbool_field: true\nfloat_field: 3.14"
        )
        assert yaml.safe_load(yaml_str) == {
            "int_field": 42,
            "str_field": "Hello, World!",
            "bool_field": True,
            "float_field": 3.14,
        }

    def test_optional(self):
        @dataclass
        class Optionals:
            int_field: int | None
            str_field: str | None
            other_field: str | None

        yaml_str = dataclass_to_yaml(Optionals)
        print(yaml_str)
        assert yaml_str == "int_field: null\nstr_field: null\nother_field: null"
        assert yaml.safe_load(yaml_str) == {
            "int_field": None,
            "str_field": None,
            "other_field": None,
        }

    def test_optional_with_default(self):
        @dataclass
        class OptionalsWithDefault:
            int_field: int | None = 42
            str_field: str | None = "test"
            other_field: str | None = None

        yaml_str = dataclass_to_yaml(OptionalsWithDefault)
        assert yaml_str == "int_field: 42\nstr_field: test\nother_field: null"
        assert yaml.safe_load(yaml_str) == {
            "int_field": 42,
            "str_field": "test",
            "other_field": None,
        }

    def test_nested(self):
        """Nested dataclasses should raise an error."""

        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Nested
            other_field: str = "Hello, World!"

        yaml_str = dataclass_to_yaml(Parent)
        print(yaml_str)
        assert (
            yaml_str
            == "nested:\n  int_field: 42\n  str_field: Hello, World!\n\nother_field: Hello, World!"
        )
        assert yaml.safe_load(yaml_str) == {
            "nested": {"int_field": 42, "str_field": "Hello, World!"},
            "other_field": "Hello, World!",
        }

    def test_deep_nested(self):
        @dataclass
        class Nested:
            int_field: int = 42
            str_field: str = "Hello, World!"

        @dataclass
        class Parent:
            nested: Nested
            other_field: str = "Hello, World!"

        @dataclass
        class GrandParent:
            parent: Parent
            other_field: str = "Hello, World!"

        yaml_str = dataclass_to_yaml(GrandParent)
        print(yaml_str)
        assert (
            yaml_str
            == "parent:\n  nested:\n    int_field: 42\n    str_field: Hello, World!\n\n  other_field: Hello, World!\n\nother_field: Hello, World!"
        )
        assert yaml.safe_load(yaml_str) == {
            "parent": {
                "nested": {"int_field": 42, "str_field": "Hello, World!"},
                "other_field": "Hello, World!",
            },
            "other_field": "Hello, World!",
        }

    def test_list(self):
        """Test a list of dataclasses."""

        @dataclass
        class Lists:
            int_list: list[int] | None
            str_list: list[str] = field(default_factory=lambda: ["a", "b", "c"])
            str_list_2: list[str] = field(default_factory=lambda: [])

        yaml_str = dataclass_to_yaml(Lists)
        print(yaml_str)
        assert yaml_str == "int_list: null\nstr_list:\n  - a\n  - b\n  - c"
        assert yaml.safe_load(yaml_str) == {
            "int_list": None,
            "str_list": ["a", "b", "c"],
        }

    def test_dict(self):
        """Test a dict of dataclasses."""

        @dataclass
        class DictSchema:
            empty: dict[str, str]
            int_dict: dict[str, int] = field(
                default_factory=lambda: {"one": 1, "two": 2, "three": 3}
            )
            str_dict: dict[str, str] | None = None

        yaml_str = dataclass_to_yaml(DictSchema)
        print(yaml_str)
        assert yaml_str == (
            "empty: {}\nint_dict:\n  one: 1\n  two: 2\n  three: 3\nstr_dict: null"
        )

        with pytest.raises(
            ValueError, match="Only string keys are supported in dict types"
        ):

            @dataclass
            class InvalidDictSchema:
                invalid_dict: dict[int, str] = field(
                    default_factory=lambda: {1: "one", 2: "two"}
                )

            yaml_str = dataclass_to_yaml(InvalidDictSchema)

    def test_list_union(self):
        @dataclass
        class Lists:
            int_list: list[int] | int = field(default_factory=lambda: [1, 2, 3])
            str_list: list[str] | str = "test"

        yaml_str = dataclass_to_yaml(Lists)
        print(yaml_str)
        assert yaml_str == "int_list:\n  - 1\n  - 2\n  - 3\nstr_list: test"

    def test_complex(self):
        """Test a more complex dataclass."""

        @dataclass
        class Movie:
            title: str = "Jurassic Park"
            year: int = 1993

        @dataclass
        class Director:
            name: str = "Steven Spielberg"
            movies: list[Movie] = field(
                default_factory=lambda: [
                    Movie(title="Jurassic Park", year=1993),
                    Movie(title="Indiana Jones", year=1981),
                ]
            )

        yaml_str = dataclass_to_yaml(Director)
        yaml_parsed = yaml.safe_load(yaml_str)

        assert yaml_parsed == {
            "name": "Steven Spielberg",
            "movies": [
                {"title": "Jurassic Park", "year": 1993},
                {"title": "Indiana Jones", "year": 1981},
            ],
        }

    def test_recursive(self):
        """Test a recursive dataclass."""

        @dataclass
        class Recursive:
            next: Optional["Recursive"] = None

        yaml_str = dataclass_to_yaml(Recursive)
        print(yaml_str)
        assert yaml_str == "next: null"
        assert yaml.safe_load(yaml_str) == {"next": None}

    def test_derived(self):
        """Test a dataclass with derived fields."""

        @dataclass
        class Base:
            enabled: bool = False

        @dataclass
        class Derived(Base):
            name: str = "Test"

        yaml_str = dataclass_to_yaml(Derived)
        print(yaml_str)
        assert yaml_str == "enabled: false\nname: Test"
        assert yaml.safe_load(yaml_str) == {"enabled": False, "name": "Test"}

    def test_advanced_deep_nested(self):
        @dataclass
        class InboxFolder:
            name: str
            path: str
            auto_threshold: float | None = None
            autotag: Literal["auto", "preview", "bootleg", False] = False
            # the `no` -> False option will need tweaking

        @dataclass
        class LibrarySection:
            readonly: bool = False
            artist_separators: list[str] = field(
                default_factory=lambda: [",", ";", "&"]
            )

        @dataclass
        class TerminalSection:
            start_path: str = "/repo"

        @dataclass
        class InboxSection:
            ignore: list[str] | Literal["_use_beets_ignore"] = "_use_beets_ignore"
            debounce_before_autotag: int = 30
            folders: dict[str, InboxFolder] = field(default_factory=dict)

        @dataclass
        class BeetsFlaskSchema:
            inbox: InboxSection = field(default_factory=lambda: InboxSection())
            library: LibrarySection = field(default_factory=lambda: LibrarySection())
            terminal: TerminalSection = field(default_factory=lambda: TerminalSection())
            num_preview_workers: int = 4

        @dataclass
        class BeetsSchema:
            gui: BeetsFlaskSchema

        yaml_str = dataclass_to_yaml(BeetsSchema)
        print(yaml_str)
        assert True

    def test_optional_nested(self):
        @dataclass
        class Nested:
            foo: str = "bar"

        @dataclass
        class Schema:
            nested: Nested | None = field(default_factory=Nested)

        yaml_str = dataclass_to_yaml(Schema)
        assert yaml_str == "nested:\n  foo: bar\n"

    def test_no_default(self):
        @dataclass
        class SchemaStrict:
            foo: str

        with pytest.raises(ValueError, match="has no default value!"):
            dataclass_to_yaml(SchemaStrict)


class TestDocstringGeneration:
    """Test generation of docstrings from dataclass fields."""

    def test_simple(self):
        """Test the basic functionality."""

        @dataclass
        class SingleLineDocstring:
            """This is a docstring."""

            pass

        yaml_str = dataclass_to_yaml(SingleLineDocstring)
        assert yaml_str == "# This is a docstring.\n"
        assert yaml.safe_load(yaml_str) == None

    def test_multiline(self):
        @dataclass
        class MultiLineDocstring:
            """This is a docstring that is longer than 80 characters and should be split into multiple lines."""

            pass

        yaml_str = dataclass_to_yaml(MultiLineDocstring)
        assert (
            yaml_str
            == "# This is a docstring that is longer than 80 characters and should be split into\n# multiple lines.\n"
        )
        assert yaml.safe_load(yaml_str) == None

    def test_no_docstring(self):
        @dataclass
        class NoDocstring:
            pass

        yaml_str = dataclass_to_yaml(NoDocstring)
        assert yaml_str == ""
        assert yaml.safe_load(yaml_str) == None

    def test_annotation_docstring(self):
        """Test the basic functionality."""

        @dataclass
        class VariableDocstring:
            """This is a module docstring."""

            int_field: Annotated[int, "This is a docstring for the int field."] = 42

        yaml_str = dataclass_to_yaml(VariableDocstring)
        print(yaml_str)
        assert (
            yaml_str
            == "# This is a module docstring.\n\n# This is a docstring for the int field.\nint_field: 42"
        )

    def test_multiline_variable_docstring(self):
        """Test the basic functionality."""

        @dataclass
        class MultiLineVariableDocstring:
            """This is a module docstring."""

            int_field: Annotated[int, "This is a docstring", "Test"] = 42

        yaml_str = dataclass_to_yaml(MultiLineVariableDocstring)
        print(yaml_str)
        assert (
            yaml_str
            == "# This is a module docstring.\n\n# This is a docstring\n# Test\nint_field: 42"
        )
        assert yaml.safe_load(yaml_str) == {"int_field": 42}

    def test_nested_variable_docstring(self):
        """Test the basic functionality."""

        @dataclass
        class Inner:
            """This is a section docstring."""

            single: Annotated[int, "This is a docstring for the int field."] = 42
            multi: Annotated[int, "This is a docstring", "Test"] = 42

        @dataclass
        class Outer:
            """This is a module docstring."""

            inner: Annotated[Inner, "This is a docstring for the inner field."] = field(
                default_factory=lambda: Inner()
            )

        yaml_str = dataclass_to_yaml(Outer)
        expected_yaml = (
            "# This is a module docstring.\n\n"
            "# This is a docstring for the inner field.\n"
            "inner:\n"
            "  # This is a section docstring.\n\n"
            "  # This is a docstring for the int field.\n"
            "  single: 42\n"
            "  # This is a docstring\n"
            "  # Test\n"
            "  multi: 42\n"
        )
        print(yaml_str)
        assert yaml_str == expected_yaml
        assert yaml.safe_load(yaml_str) == {"inner": {"single": 42, "multi": 42}}
