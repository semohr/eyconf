from collections.abc import Sequence
from typing import Annotated
import pytest
from eyconf.decorators import DictAccess, dict_access
from eyconf.type_utils import (
    iter_dataclass_type,
)
from dataclasses import dataclass, field

from eyconf.asdict import asdict_with_aliases

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035

from eyconf.utils import merge_dicts  # noqa: UP035


@dict_access
@dataclass
class Nested:
    str_field: str = "FortyTwo"


@dict_access
@dataclass
class Config42:
    int_field: int = 42
    nested: Nested = field(default_factory=Nested)


class TestDictStyleAccess:
    """Test the @dict_access decorator functionality."""

    def test_get_data(self):
        config = Config42()

        # Note that placing `assert isinstance(config, DictAccess)` here
        # will make some runtime type checkers error about the attribute access
        # Once you place the assert, better stick to dict-style access
        # for the rest of the scope
        assert isinstance(config, DictAccess)
        assert isinstance(config["nested"], DictAccess)

        assert config.int_field == 42
        assert config.nested.str_field == "FortyTwo"

        assert config["int_field"] == 42
        assert config["nested"]["str_field"] == "FortyTwo"


@dataclass
class ConfigWithProperty:
    int_field: int = 42

    @property
    def computed_property(self) -> str:
        return f"int_filed={self.int_field}"


class TestAsDict:
    """Test our customized asdict_with_aliases function.

    Besides the alias resolution, it also supports extracting
    properties and non-field attributes.

    Alias resolution is tested in test_alias.py
    """

    @pytest.mark.parametrize(
        "include_properties, include_attributes, expected_keys",
        [
            (False, False, {"int_field"}),
            (True, False, {"int_field", "computed_property"}),
            (False, True, {"int_field", "non_field_attr"}),
            (True, True, {"int_field", "computed_property", "non_field_attr"}),
        ],
    )
    def test_asdict(self, include_properties, include_attributes, expected_keys):
        config = ConfigWithProperty()
        config.non_field_attr = 100  # type: ignore
        dump = asdict_with_aliases(
            config,
            include_properties=include_properties,
            include_attributes=include_attributes,
        )
        assert set(dump.keys()) == expected_keys


@dataclass
class Item:
    id: int


class TestIterDataclassType:
    def test_iter_dataclass_type_basic(self):
        """Test basic dataclass iteration."""

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner
            name: str

        result = list(iter_dataclass_type(Outer))
        assert len(result) == 2
        assert Outer in result
        assert Inner in result

    def test_iter_dataclass_type_nested(self):
        """Test deeply nested dataclass structures."""

        @dataclass
        class Level3:
            value: int

        @dataclass
        class Level2:
            level3: Level3

        @dataclass
        class Level1:
            level2: Level2

        result = list(iter_dataclass_type(Level1))
        assert len(result) == 3
        assert Level1 in result
        assert Level2 in result
        assert Level3 in result

    @pytest.mark.parametrize(
        "collection_type",
        [
            list[Item],
            tuple[Item, Item],
            set[Item],
            Sequence[Item],
            TypingSequence[Item],
            Item | None,
            Annotated[Item, "Some metadata"],
            dict[str, Item],
        ],
    )
    def test_iter_dataclass_type_collections(self, collection_type):
        """Test dataclass iteration with collection types."""

        @dataclass
        class Container:
            items: collection_type  # type: ignore

        result = list(iter_dataclass_type(Container))
        assert len(result) == 2
        assert Container in result
        assert Item in result

    def test_iter_dataclass_type_duplicates(self):
        """Test that duplicate types are handled correctly."""

        @dataclass
        class Shared:
            value: int

        @dataclass
        class Container:
            first: Shared
            second: Shared
            items: list[Shared]

        result = list(iter_dataclass_type(Container))
        # Should only get each type once, despite multiple references
        assert len(result) == 2
        assert Container in result
        assert Shared in result
        # Verify Shared appears only once in the result
        assert result.count(Shared) == 1

    def test_iter_dataclass_type_self_reference(self):
        """Test handling of self-referential dataclasses."""

        @dataclass
        class TreeNode:
            value: int
            children: list["TreeNode"]

        result = list(iter_dataclass_type(TreeNode))
        # Should only get TreeNode once despite self-reference
        assert len(result) == 1
        assert TreeNode in result

    def test_iter_dataclass_type_mixed_types(self):
        """Test complex scenario with mixed type annotations."""

        @dataclass
        class Inner:
            id: int

        @dataclass
        class Middle:
            inner: Inner
            option: Inner | None
            items: list[Inner]

        @dataclass
        class Outer:
            middle: Middle
            direct: Inner
            mapping: dict[str, Middle]

        result = list(iter_dataclass_type(Outer))
        # Should get Outer, Middle, Inner (each only once)
        assert len(result) == 3
        assert Outer in result
        assert Middle in result
        assert Inner in result


class TestMergeDicts:
    def test_merge_simple_dicts(self):
        """Test merging two simple dictionaries without conflicts."""
        a = {"x": 1, "y": 2}
        b = {"z": 3}
        result = merge_dicts(a, b)
        expected = {"x": 1, "y": 2, "z": 3}
        assert result == expected

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries without conflicts."""
        a = {"database": {"host": "localhost", "port": 5432}}
        b = {"database": {"name": "mydb"}, "cache": {"enabled": True}}
        result = merge_dicts(a, b)
        expected = {
            "database": {"host": "localhost", "port": 5432, "name": "mydb"},
            "cache": {"enabled": True},
        }
        assert result == expected

    def test_merge_with_conflict_raises_exception(self):
        """Test that conflicting values raise an exception."""
        a = {"key": "value1"}
        b = {"key": "value2"}
        with pytest.raises(Exception, match="Conflict at key"):
            merge_dicts(a, b)

    def test_merge_nested_conflict_raises_exception(self):
        """Test that nested conflicting values raise an exception with correct path."""
        a = {"level1": {"level2": {"key": "old_value"}}}
        b = {"level1": {"level2": {"key": "new_value"}}}
        with pytest.raises(Exception, match="Conflict at level1.level2.key"):
            merge_dicts(a, b)

    def test_merge_empty_dicts(self):
        """Test merging with empty dictionaries."""
        a: dict = {}
        b = {"key": "value"}
        result = merge_dicts(a, b)
        assert result == {"key": "value"}

        a = {"key": "value"}
        b = {}
        result = merge_dicts(a, b)
        assert result == {"key": "value"}

    def test_merge_identical_dicts(self):
        """Test merging dictionaries with identical values."""
        a = {"key": "same_value"}
        b = {"key": "same_value"}
        result = merge_dicts(a, b)
        assert result == {"key": "same_value"}

    def test_merge_modifies_first_dict_in_place(self):
        """Test that the first dictionary is modified in place."""
        a = {"original": "value"}
        b = {"new": "data"}
        result = merge_dicts(a, b)
        assert a is result  # Should be the same object
        assert "new" in a  # Should have modified the original

    def test_merge_with_priority_a(self):
        a = {"key": "value1"}
        b = {"key": "value2"}
        result = merge_dicts(a, b, priority="a")
        assert result == {"key": "value1"}

    def test_merge_with_priority_b(self):
        a = {"key": "value1"}
        b = {"key": "value2"}
        result = merge_dicts(a, b, priority="b")
        assert result == {"key": "value2"}
