import json
import typing

import pydantic
import pytest

from rest_framework import serializers  # type: ignore

from drf_pydantic import BaseModel, DrfPydanticSerializer


@pytest.fixture(
    scope="function",
    params=[False, True],
    ids=["no_validate_pydantic", "validate_pydantic"],
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

    assert valid_serializer._pydantic_model is Person
    if validate_pydantic:
        assert isinstance(valid_serializer.pydantic_instance, Person)
    else:
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            valid_serializer.pydantic_instance

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
    assert maybe_valid_serializer._pydantic_model is Person
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
        with pytest.raises(
            AssertionError,
            match=r"You must call `.is_valid\(\)` before",
        ):
            maybe_valid_serializer.pydantic_instance
    else:
        # Without pydantic DRF doesn't know about field_validator
        assert maybe_valid_serializer.is_valid()
        assert maybe_valid_serializer.is_valid(raise_exception=True)
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            maybe_valid_serializer.pydantic_instance


@pytest.mark.parametrize(
    ["base"],
    [(pydantic.BaseModel,), (BaseModel,)],
    ids=["pydantic_base", "drf_pydantic_base"],
)
def test_nested_model(
    validate_pydantic: bool,
    raise_pydantic_error: bool,
    base: type[pydantic.BaseModel],
):
    class Job(base):  # type: ignore
        title: str
        salary: float

        @pydantic.field_validator("salary")
        @classmethod
        def validate_salary(cls, v: typing.Any) -> float:
            assert isinstance(v, float)
            if v < 9000:
                raise ValueError("Too low")
            return v

    class Person(BaseModel):
        name: str
        job: Job

        drf_config = {
            "validate_pydantic": validate_pydantic,
            "validation_error": "pydantic" if raise_pydantic_error else "drf",
        }

    valid_serializer = Person.drf_serializer(
        data={"name": "Van", "job": {"title": "DM", "salary": 9000}},
    )
    assert valid_serializer.is_valid(raise_exception=True)
    if validate_pydantic:
        assert isinstance(valid_serializer.pydantic_instance, Person)
    else:
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            valid_serializer.pydantic_instance

    maybe_valid_serializer = Person.drf_serializer(
        data={"name": "Van", "job": {"title": "DM", "salary": 300}},
    )
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
        with pytest.raises(
            AssertionError,
            match=r"You must call `.is_valid\(\)` before",
        ):
            maybe_valid_serializer.pydantic_instance
    else:
        # Without pydantic DRF doesn't know about field_validator
        assert maybe_valid_serializer.is_valid()
        assert maybe_valid_serializer.is_valid(raise_exception=True)
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            maybe_valid_serializer.pydantic_instance


@pytest.mark.parametrize(
    ["base"],
    [(pydantic.BaseModel,), (BaseModel,)],
    ids=["pydantic_base", "drf_pydantic_base"],
)
def test_list_of_nested_models(
    validate_pydantic: bool,
    raise_pydantic_error: bool,
    base: type[pydantic.BaseModel],
):
    class Job(base):  # type: ignore
        title: str
        salary: float

        @pydantic.field_validator("salary")
        @classmethod
        def validate_salary(cls, v: typing.Any) -> float:
            assert isinstance(v, float)
            if v < 9000:
                raise ValueError("Too low")
            return v

    class Person(BaseModel):
        name: str
        jobs: list[Job]

        drf_config = {
            "validate_pydantic": validate_pydantic,
            "validation_error": "pydantic" if raise_pydantic_error else "drf",
        }

    valid_serializer = Person.drf_serializer(
        data={"name": "Van", "jobs": [{"title": "DM", "salary": 9000}]},
    )
    assert valid_serializer.is_valid(raise_exception=True)
    if validate_pydantic:
        assert isinstance(valid_serializer.pydantic_instance, Person)
    else:
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            valid_serializer.pydantic_instance

    maybe_valid_serializer = Person.drf_serializer(
        data={"name": "Van", "jobs": [{"title": "DM", "salary": 300}]},
    )
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
        # not available when invalid or when is_valid raised
        with pytest.raises(
            AssertionError, match=r"You must call `.is_valid\(\)` before"
        ):
            maybe_valid_serializer.pydantic_instance
    else:
        # Without pydantic DRF doesn't know about field_validator
        assert maybe_valid_serializer.is_valid()
        assert maybe_valid_serializer.is_valid(raise_exception=True)
        with pytest.raises(
            AssertionError, match=r"You must enable pydantic validation"
        ):
            maybe_valid_serializer.pydantic_instance


def test_inheritance():
    class Grandparent(pydantic.BaseModel):
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any) -> str:
            assert isinstance(v, str)
            if v != "Billy":
                raise ValueError("Wrong door")
            return v

    class Parent(BaseModel, Grandparent):
        drf_config = {"validate_pydantic": True}

    class Child(Parent):
        drf_config = {"validation_error": "pydantic"}

    class Grandchild(Child):
        drf_config = {"validate_pydantic": False}

    assert not hasattr(Grandparent, "drf_serializer")

    data: dict[str, typing.Any] = {"name": "Van", "age": 69}

    parent_serializer = Parent.drf_serializer(data={**data})
    assert not parent_serializer.is_valid()
    with pytest.raises(serializers.ValidationError):
        parent_serializer.is_valid(raise_exception=True)
    with pytest.raises(AssertionError, match=r"You must call `.is_valid\(\)` before"):
        parent_serializer.pydantic_instance
    child_serializer = Child.drf_serializer(data={**data})
    with pytest.raises(pydantic.ValidationError):
        child_serializer.is_valid()
    with pytest.raises(pydantic.ValidationError):
        child_serializer.is_valid(raise_exception=True)
    with pytest.raises(AssertionError, match=r"You must call `.is_valid\(\)` before"):
        child_serializer.pydantic_instance

    grandchild_serializer = Grandchild.drf_serializer(data={**data})
    assert grandchild_serializer.is_valid(raise_exception=True)
    with pytest.raises(AssertionError, match=r"You must enable pydantic validation"):
        grandchild_serializer.pydantic_instance


def test_manual_serializer(
    validate_pydantic: bool,
    raise_pydantic_error: bool,
):
    class MyCustomSerializer(DrfPydanticSerializer):
        gender = serializers.ChoiceField(choices=["male", "female"])
        name = serializers.CharField()
        age = serializers.IntegerField()

    class Person(BaseModel):
        gender: str
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any) -> str:
            assert isinstance(v, str)
            if v != "Billy":
                raise ValueError("Wrong door")
            return v

        drf_serializer = MyCustomSerializer
        drf_config = {
            "validate_pydantic": validate_pydantic,
            "validation_error": "pydantic" if raise_pydantic_error else "drf",
        }

    maybe_valid_serializer = Person.drf_serializer(
        data={"gender": "male", "name": "Van", "age": 69}
    )
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
        with pytest.raises(
            AssertionError,
            match=r"You must call `.is_valid\(\)` before",
        ):
            maybe_valid_serializer.pydantic_instance
    else:
        # Without pydantic DRF doesn't know about field_validator
        assert maybe_valid_serializer.is_valid()
        assert maybe_valid_serializer.is_valid(raise_exception=True)
        with pytest.raises(
            AssertionError,
            match=r"You must enable pydantic validation",
        ):
            maybe_valid_serializer.pydantic_instance


def test_validation_error_translation_field_errors():
    class Person(BaseModel):
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any):
            assert isinstance(v, str)
            if v == "Van":
                raise ValueError("Wrong door, Jabroni!")
            return v

        @pydantic.field_validator("age")
        @classmethod
        def validate_age(cls, v: typing.Any):
            assert isinstance(v, int)
            assert v == 69
            return v

        drf_config = {"validate_pydantic": True}

    serializer = Person.drf_serializer(data={"name": "Van", "age": 68})
    assert not serializer.is_valid()
    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as exc:
        assert len(exc.detail.keys()) == 3

        assert len(exc.detail["non_field_errors"]) == 0

        assert len(exc.detail["name"]) == 1
        name_error = json.loads(exc.detail["name"][0])
        assert name_error["loc"] == ["name"]
        assert "Wrong door, Jabroni!" in name_error["msg"]

        assert len(exc.detail["age"]) == 1
        age_error = json.loads(exc.detail["age"][0])
        assert age_error["loc"] == ["age"]
        assert "Assertion failed" in age_error["msg"]


def test_validation_error_translation_non_field_errors():
    class Person(BaseModel):
        name: str
        age: int

        @pydantic.model_validator(mode="after")
        def validate_person(self):
            if self.name == "Van":
                raise ValueError("Wrong door, Jabroni!")
            return self

        drf_config = {"validate_pydantic": True}

    serializer = Person.drf_serializer(data={"name": "Van", "age": 69})
    assert not serializer.is_valid()
    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as exc:
        assert len(exc.detail.keys()) == 1

        assert len(exc.detail["non_field_errors"]) == 1

        error = json.loads(exc.detail["non_field_errors"][0])
        assert error["loc"] == []
        assert "Wrong door, Jabroni!" in error["msg"]


def test_validation_backpopulation():
    class Person(BaseModel):
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any):
            assert isinstance(v, str)
            if v == "Van":
                return "Jabroni"
            return v

        @pydantic.model_validator(mode="after")
        def validate_person(self):
            self.age = 69
            return self

        drf_config = {"validate_pydantic": True}

    serializer = Person.drf_serializer(data={"name": "Van", "age": 68})
    assert serializer.is_valid(raise_exception=True)
    assert serializer.validated_data["name"] == "Jabroni"
    assert serializer.pydantic_instance.age == 69
    assert serializer.validated_data["age"] == 69


def test_validation_without_backpopulation():
    class Person(BaseModel):
        name: str
        age: int

        @pydantic.field_validator("name")
        @classmethod
        def validate_name(cls, v: typing.Any):
            assert isinstance(v, str)
            if v == "Van":
                return "Jabroni"
            return v

        @pydantic.model_validator(mode="after")
        def validate_person(self):
            self.age = 69
            return self

        drf_config = {"validate_pydantic": True, "backpopulate_after_validation": False}

    serializer = Person.drf_serializer(data={"name": "Van", "age": 68})
    assert serializer.is_valid(raise_exception=True)
    assert serializer.validated_data["name"] == "Van"
    assert serializer.pydantic_instance.age == 69
    assert serializer.validated_data["age"] == 68


def test_nested_backpopulation():
    class Salary(BaseModel):
        value: int
        currency: str

    class Job(BaseModel):
        title: str
        salary: Salary

        @pydantic.model_validator(mode="after")
        def adjust_salary(self):
            if self.title == "DM":
                self.salary = Salary(value=300, currency="bucks")
            return self

    class Person(BaseModel):
        name: str
        job: Job

        drf_config = {"validate_pydantic": True}

    s = Person.drf_serializer(
        data={
            "name": "Van",
            "job": {
                "title": "DM",
                "salary": {
                    "value": 1000,
                    "currency": "dollars",
                },
            },
        }
    )
    assert s.is_valid(raise_exception=True)
    assert isinstance(s.data["job"], dict)
    assert s.pydantic_instance.job.title == "DM"
    assert s.validated_data["job"]["title"] == "DM"
    assert isinstance(s.data["job"]["salary"], dict)
    assert s.pydantic_instance.job.salary.value == 300
    assert s.validated_data["job"]["salary"]["value"] == 300
    assert s.pydantic_instance.job.salary.currency == "bucks"
    assert s.validated_data["job"]["salary"]["currency"] == "bucks"
