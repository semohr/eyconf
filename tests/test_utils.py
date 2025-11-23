from collections.abc import Sequence
from typing import Annotated
import pytest
from eyconf.config.extra_fields import AccessProxy
from eyconf.config.extra_fields import AttributeDict
from eyconf.decorators import DictAccess, dict_access
from eyconf.type_utils import (
    iter_dataclass_type,
)
from dataclasses import dataclass, field

from eyconf.asdict import asdict_with_aliases

# for some reason typing  Sequence and abc sequence are not the same type
from typing import Sequence as TypingSequence  # noqa: UP035


@dict_access
@dataclass
class Nested:
    str_field: str = "FortyTwo"


@dict_access
@dataclass
class Config42:
    int_field: int = 42
    nested: Nested = field(default_factory=Nested)


class TestAttributeDict:
    def test_init(self):
        attr_dict = AttributeDict(**{"foo": "bar", "nested": {"level": 42}})
        assert isinstance(attr_dict, AttributeDict)
        assert attr_dict.foo == "bar"

        assert isinstance(attr_dict.nested, AttributeDict)
        assert attr_dict.nested.level == 42

    def test_set_get(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore

        assert attr_dict.foo == "bar"

    def test_nested(self):
        attr_dict = AttributeDict()
        attr_dict.nested.level = 42

        assert attr_dict.nested.level == 42

    def test_as_dict(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore
        attr_dict.nested.level = 42  # type: ignore

        expected = {
            "foo": "bar",
            "nested": {
                "level": 42,
            },
        }

        assert attr_dict.as_dict() == expected

    def test_bool_conversion(self):
        attr_dict = AttributeDict()
        attr_dict.foo = "bar"  # type: ignore

        assert bool(attr_dict) is True

        empty_attr_dict = AttributeDict()
        assert bool(empty_attr_dict) is False


class TestAccessProxy:
    def test_access_fails(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        assert proxy.int_field == 42

    def test_set(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.int_field = 100

        assert proxy.int_field == 100
        assert config_data.int_field == 100

    def test_del(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )

        assert proxy.int_field == 42

        del proxy.int_field
        del proxy._data

    def test_set_extra(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"  # type: ignore

        assert proxy.int_field == 42
        assert proxy.foo == "bar"

        # make sure it actually sits in _additional_data
        assert proxy._extra_data.foo == "bar"  # type: ignore

    def test_del_extra(self):
        config_data = Config42()
        extra_data = AttributeDict()
        proxy = AccessProxy(
            config_data,
            extra_data,
        )
        proxy.foo = "bar"  # type: ignore

        assert proxy.foo == "bar"

        del proxy.foo  # type: ignore


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
