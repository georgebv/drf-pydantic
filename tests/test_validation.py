import typing

import pydantic
import pytest

from rest_framework import serializers

from drf_pydantic import BaseModel


@pytest.fixture(
    scope="function",
    params=[False, True],
    ids=["without_pydantic", "with_pydantic"],
)
def validate_pydantic(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture(
    scope="function",
    params=[False, True],
    ids=["raise_drf", "raise_pydantic"],
)
def raise_pydantic_error(request: pytest.FixtureRequest) -> bool:
    return request.param


def test_simple_model(
    validate_pydantic: bool,
    raise_pydantic_error: bool,
):
    class Person(BaseModel):
        name: str
        age: int

        drf_config = {
            "validate_pydantic": validate_pydantic,
            "validation_error": "pydantic" if raise_pydantic_error else "drf",
        }

    valid_serializer = Person.drf_serializer(data={"name": "Van", "age": 69})
    assert valid_serializer.is_valid(raise_exception=True)

    invalid_serializer = Person.drf_serializer(data={"name": 69, "age": "Van"})
    assert not invalid_serializer.is_valid()
    with pytest.raises(serializers.ValidationError):
        invalid_serializer.is_valid(raise_exception=True)


def test_pydantic_only_validation(
    validate_pydantic: bool,
    raise_pydantic_error: bool,
):
    class Person(BaseModel):
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any) -> str:
            assert isinstance(v, str)
            if v != "Billy":
                raise ValueError("Wrong door")
            return v

        drf_config = {
            "validate_pydantic": validate_pydantic,
            "validation_error": "pydantic" if raise_pydantic_error else "drf",
        }

    maybe_valid_serializer = Person.drf_serializer(data={"name": "Van", "age": 69})
    if validate_pydantic:
        if raise_pydantic_error:
            with pytest.raises(pydantic.ValidationError):
                maybe_valid_serializer.is_valid()
            with pytest.raises(pydantic.ValidationError):
                maybe_valid_serializer.is_valid(raise_exception=True)
        else:
            assert not maybe_valid_serializer.is_valid()
            with pytest.raises(serializers.ValidationError):
                maybe_valid_serializer.is_valid(raise_exception=True)
    else:
        # Without pydantic DRF doesn't know about field_validator
        assert maybe_valid_serializer.is_valid()
        assert maybe_valid_serializer.is_valid(raise_exception=True)
