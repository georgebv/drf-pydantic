import pytest

from rest_framework.exceptions import ValidationError

from drf_pydantic import BaseModel


def test_simple_model():
    class Person(BaseModel):
        name: str
        age: int

    valid_serializer = Person.drf_serializer(data={"name": "Van", "age": 69})
    assert valid_serializer.is_valid(raise_exception=True)

    invalid_serializer = Person.drf_serializer(data={"name": 69, "age": "Van"})
    with pytest.raises(ValidationError):
        invalid_serializer.is_valid(raise_exception=True)
