from dataclasses import dataclass, field

import pytest
from eyconf.decorators import (
    DictSetAccess,
    allow_additional,
    check_allows_additional,
    dict_access,
    DictAccess,
)


@dataclass
class SchemaUndercorated:
    foo: int = 1


@dict_access(
    getter=True,
    setter=True,
)
@dataclass
class SchemaWithDictAcecess:
    foo: int = 1


@allow_additional
@dataclass
class SchemaWithAllowAdditional:
    foo: int = 1


@allow_additional
@dict_access
@dataclass
class SchemaWithBoth:
    foo: int = 1


class TestAllowsAdditional:
    def test_allow_additional_sets_flag(self):
        config1 = SchemaWithAllowAdditional()
        assert check_allows_additional(SchemaWithAllowAdditional)
        assert check_allows_additional(config1)

        config2 = SchemaWithBoth()
        assert check_allows_additional(SchemaWithBoth)
        assert check_allows_additional(config2)

    def test_no_allow_additional_flag(self):
        config = SchemaUndercorated()
        assert not check_allows_additional(SchemaUndercorated)
        assert not check_allows_additional(config)


class TestDictAccess:
    def test_item_assignment(self):
        """Test basic dict-style get access."""
        obj = SchemaWithDictAcecess()
        assert isinstance(obj, DictAccess)
        assert isinstance(obj, DictSetAccess)
        obj["foo"] = 10
        assert obj["foo"] == 10

    def test_attribute_assignment(self):
        """Test basic dict-style set access."""
        obj = SchemaWithDictAcecess()
        obj.foo = 20
        assert obj.foo == 20


class TestDictAccessWithAlias:
    @pytest.fixture(autouse=True)
    def alias_fixture(self):
        @dict_access(getter=True, setter=True)
        @dataclass
        class AliasConfig:
            attr_field: int = field(metadata={"alias": "dict_field"})
            str_field: str = "FortyTwo!"

        self.AliasConfig = AliasConfig

    def test_item_assignment_with_alias(self):
        """Test dict-style get/set access with alias resolution."""
        obj = self.AliasConfig(attr_field=42)
        assert isinstance(obj, DictAccess)
        assert isinstance(obj, DictSetAccess)

        # Access via alias
        assert obj["dict_field"] == 42

        # Set via alias
        obj["dict_field"] = 100
        assert obj["dict_field"] == 100

        # Access via attribute name should raise
        with pytest.raises(KeyError):
            _ = obj["attr_field"]

        with pytest.raises(KeyError):
            obj["attr_field"] = 150

    def test_attribute_assignment_with_alias(self):
        """Test attribute get/set access with alias resolution."""
        obj = self.AliasConfig(attr_field=42)

        # Access via attribute name ONLY
        assert obj.attr_field == 42

        # Set via attribute name ONLY
        obj.attr_field = 200
        assert obj.attr_field == 200

        with pytest.raises(AttributeError):
            _ = obj.dict_field  # type: ignore
