import pytest

from drf_pydantic.utils import get_attr_owner


class TestGetAttrOwner:
    def test_no_attr(self):
        class Person: ...

        with pytest.raises(AttributeError, match=r"doesn't have"):
            get_attr_owner(Person, "name")

    def test_has_itself(self):
        class Person:
            name: str = "Van"

        assert get_attr_owner(Person, "name") is Person

    def test_has_parent(self):
        class Parent:
            name: str = "Van"

        class Child(Parent):
            age: int = 69

        assert get_attr_owner(Child, "name") is Parent
        assert get_attr_owner(Child, "age") is Child
