from eyconf.utils import AttributeDict, AccessProxy
from dataclasses import dataclass, field


@dataclass
class Nested:
    str_field: str = "FortyTwo"


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
