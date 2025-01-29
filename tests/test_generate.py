from dataclasses import dataclass, field
from typing import Annotated, Optional, Union

import logging
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

    def test_docstring(self):
        """Test the basic functionality."""

        @dataclass
        class SingleLineDocstring:
            """This is a docstring."""

            pass

        yaml_str = dataclass_to_yaml(SingleLineDocstring)
        assert yaml_str == "# This is a docstring.\n"
        assert yaml.safe_load(yaml_str) == None

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

    def test_optional(self):

        @dataclass
        class Optionals:
            int_field: Optional[int]
            str_field: str | None
            other_field: Union[str, None]

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
            int_field: Optional[int] = 42
            str_field: str | None = "test"
            other_field: Union[str, None] = None

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
            int_list: Optional[list[int]]
            str_list: list[str] = field(default_factory=lambda: ["a", "b", "c"])

        yaml_str = dataclass_to_yaml(Lists)
        print(yaml_str)
        assert yaml_str == "int_list: null\nstr_list:\n  - a\n  - b\n  - c"
        assert yaml.safe_load(yaml_str) == {
            "int_list": None,
            "str_list": ["a", "b", "c"],
        }

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
