import datetime
import typing

import pydantic

from rest_framework import serializers

from drf_pydantic import BaseModel


def test_simple_model():
    class Person(BaseModel):
        name: str
        email: pydantic.EmailStr
        age: int
        height: float
        address: typing.Optional[str]
        date_of_birth: datetime.date
        nationality: str = "USA"

    serializer = Person.drf_serializer()

    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 7

    # Regular fields
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["email"], serializers.EmailField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["height"], serializers.FloatField)
    assert isinstance(serializer.fields["date_of_birth"], serializers.DateField)
    for name in ["name", "email", "age", "height", "date_of_birth"]:
        field = serializer.fields[name]
        assert field.required is True, name
        assert field.default is serializers.empty, name
        assert field.allow_null is False, name

    # Optional
    field: serializers.Field = serializer.fields["address"]
    assert isinstance(field, serializers.CharField)
    assert field.allow_null is True
    assert field.default is None
    assert field.required is False

    # With default
    field: serializers.Field = serializer.fields["nationality"]
    assert isinstance(field, serializers.CharField)
    assert field.allow_null is False
    assert field.default == "USA"
    assert field.required is False


def test_model_with_literal():
    class Human(BaseModel):
        sex: typing.Literal["male", "female"]
        age: int

    serializer = Human.drf_serializer()

    assert serializer.__class__.__name__ == "HumanSerializer"
    assert len(serializer.fields) == 2

    # Normal field
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert not isinstance(serializer.fields["age"], serializers.CharField)

    # Literal field
    field: serializers.Field = serializer.fields["sex"]
    assert not isinstance(field, serializers.CharField)
    assert isinstance(field, serializers.ChoiceField)
    assert set(field.choices) == set(["male", "female"])


def test_model_with_list():
    class Team(BaseModel):
        name: str
        value: typing.Optional[float]
        members: list[str]

    serializer = Team.drf_serializer()

    assert serializer.__class__.__name__ == "TeamSerializer"
    assert len(serializer.fields) == 3

    # Normal fields
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["value"], serializers.FloatField)

    # List field
    field = serializer.fields["members"]
    assert isinstance(field, serializers.ListField)
    assert isinstance(field.child, serializers.CharField)
    assert field.default is serializers.empty
    assert field.allow_empty is True


def test_iheritance_future():
    class Person(pydantic.BaseModel):
        name: str
        age: int

    class Employee(BaseModel, Person):
        title: typing.Literal["grunt", "boss"]
        salary: float

    serializer = Employee.drf_serializer()

    assert serializer.__class__.__name__ == "EmployeeSerializer"
    assert len(serializer.fields) == 4

    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["salary"], serializers.FloatField)
    assert isinstance(serializer.fields["title"], serializers.ChoiceField)
    assert set(serializer.fields["title"].choices) == set(["boss", "grunt"])


def test_inheritance_past():
    class Person(BaseModel, pydantic.BaseModel):
        name: str
        age: int

    class Employee(Person):
        title: typing.Literal["grunt", "boss"]
        salary: float

    serializer = Employee.drf_serializer()

    assert serializer.__class__.__name__ == "EmployeeSerializer"
    assert len(serializer.fields) == 4

    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["salary"], serializers.FloatField)
    assert isinstance(serializer.fields["title"], serializers.ChoiceField)
    assert set(serializer.fields["title"].choices) == set(["boss", "grunt"])


def test_nested_model():
    class Job(BaseModel):
        title: typing.Literal["grunt", "boss"]
        salary: float

    class Person(BaseModel):
        name: str
        job: Job

    serializer = Person.drf_serializer()

    # Top model
    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 2
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["job"], serializers.Serializer)

    # Nested model
    job: serializers.Serializer = serializer.fields["job"]
    assert job.__class__.__name__ == "JobSerializer"
    assert len(job.fields) == 2
    assert isinstance(job.fields["title"], serializers.ChoiceField)
    assert isinstance(job.fields["salary"], serializers.FloatField)


def test_nested_model_list():
    class Apartment(BaseModel):
        floor: int
        owner: str

    class Building(BaseModel):
        address: str
        apartments: list[Apartment]

    serializer = Building.drf_serializer()

    # Top model
    assert serializer.__class__.__name__ == "BuildingSerializer"
    assert len(serializer.fields) == 2
    assert isinstance(serializer.fields["address"], serializers.CharField)
    assert isinstance(serializer.fields["apartments"], serializers.ListField)

    # Nested model
    apartment: serializers.Serializer = serializer.fields["apartments"].child
    assert apartment.__class__.__name__ == "ApartmentSerializer"
    assert len(apartment.fields) == 2
    assert isinstance(apartment.fields["floor"], serializers.IntegerField)
    assert isinstance(apartment.fields["owner"], serializers.CharField)


def test_nested_model_only_last():
    class Apartment(pydantic.BaseModel):
        floor: int
        owner: str

    class Building(BaseModel):
        address: str
        apartments: list[Apartment]

    serializer = Building.drf_serializer()

    # Top model
    assert serializer.__class__.__name__ == "BuildingSerializer"
    assert len(serializer.fields) == 2
    assert isinstance(serializer.fields["address"], serializers.CharField)
    assert isinstance(serializer.fields["apartments"], serializers.ListField)

    # Nested model
    apartment: serializers.Serializer = serializer.fields["apartments"].child
    assert apartment.__class__.__name__ == "ApartmentSerializer"
    assert len(apartment.fields) == 2
    assert isinstance(apartment.fields["floor"], serializers.IntegerField)
    assert isinstance(apartment.fields["owner"], serializers.CharField)
