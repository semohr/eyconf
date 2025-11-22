from dataclasses import dataclass
from eyconf.decorators import (
    allow_additional,
    check_allows_additional,
    dict_access,
    DictAccess,
    check_dict_access,
)


@dataclass
class SchemaUndercorated:
    foo: int = 1


@dict_access
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
    def test_dict_access_basic(self):
        config1 = SchemaWithDictAcecess()
        config2 = SchemaWithBoth()
        assert check_dict_access(SchemaWithDictAcecess)
        assert check_dict_access(config1)
        assert isinstance(config1, DictAccess)

        assert check_dict_access(SchemaWithBoth)
        assert check_dict_access(config2)
        assert isinstance(config2, DictAccess)

    def test_no_dict_access(self):
        config = SchemaUndercorated()
        assert not check_dict_access(SchemaUndercorated)
        assert not check_dict_access(config)
