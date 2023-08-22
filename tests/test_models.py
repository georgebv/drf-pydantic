import datetime
import typing
from enum import Enum

import pydantic
import pytest

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from drf_pydantic import BaseModel
from drf_pydantic.fields import EnumField


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


def test_int_constraint():

    with pytest.warns(UserWarning) as warninfo:

        class Person(BaseModel):
            name: str
            email: pydantic.EmailStr
            age: int = pydantic.Field(ge=0, le=100)
            salary: int = pydantic.Field(gt=0, lt=100)

        assert all("not supported by DRF" in str(wrn.message) for wrn in warninfo)

    serializer = Person.drf_serializer()

    assert isinstance(serializer.fields["age"], serializers.IntegerField)

    # With constraints
    field: serializers.Field = serializer.fields["age"]
    assert isinstance(field, serializers.IntegerField)
    assert field.allow_null is False
    assert field.required is True
    assert field.min_value == 0
    assert field.max_value == 100

    # With constraints
    field: serializers.Field = serializer.fields["salary"]
    assert isinstance(field, serializers.IntegerField)
    assert field.allow_null is False
    assert field.required is True
    assert field.min_value == 0
    assert field.max_value == 100


def test_str_constraint():
    class Person(BaseModel):
        name: str = pydantic.Field(min_length=3, max_length=10)
        email: pydantic.EmailStr
        age: int

    serializer = Person.drf_serializer()

    assert isinstance(serializer.fields["name"], serializers.CharField)

    field: serializers.Field = serializer.fields["name"]
    assert isinstance(field, serializers.CharField)
    assert field.allow_null is False
    assert field.required is True
    assert field.min_length == 3
    assert field.max_length == 10


def test_model_with_list_from_typing():
    class Item(BaseModel):
        name: str

    class Cart(BaseModel):
        items: typing.List[Item]

    serializer = Cart.drf_serializer()

    assert isinstance(serializer, serializers.Serializer)

    items_field: serializers.Field = serializer.fields["items"]
    assert isinstance(items_field, serializers.ListField)
    assert items_field.child.__class__.__name__ == "ItemSerializer"

    name_field: serializers.Field = items_field.child.fields["name"]
    assert isinstance(name_field, serializers.CharField)


def test_enum_model():
    class CountryEnum(Enum):
        US = "US"
        GB = "GB"
        FR = "FR"

    class NotificationPreferenceEnum(Enum):
        NONE = "no_notifications"
        SOME = "some_notifications"
        ALL = "all_notifications"

    class Person(BaseModel):
        name: str
        email: pydantic.EmailStr
        age: int
        height: float
        date_of_birth: datetime.date
        notification_preferences: NotificationPreferenceEnum
        original_nationality: typing.Optional[CountryEnum]
        nationality: CountryEnum = CountryEnum.GB

    serializer = Person.drf_serializer()

    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 8

    # Regular fields
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["email"], serializers.EmailField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["height"], serializers.FloatField)
    assert isinstance(serializer.fields["date_of_birth"], serializers.DateField)
    assert isinstance(serializer.fields["notification_preferences"], EnumField)
    for name in [
        "name",
        "email",
        "age",
        "height",
        "date_of_birth",
        "notification_preferences",
    ]:
        field = serializer.fields[name]
        assert field.required is True, name
        assert field.default is serializers.empty, name
        assert field.allow_null is False, name
        if name == "notification_preferences":
            assert field.choices == dict(
                [(x, x.name) for x in NotificationPreferenceEnum]
            )

    # Optional
    field: serializers.Field = serializer.fields["original_nationality"]
    assert isinstance(field, EnumField)
    assert field.allow_null is True
    assert field.default is None
    assert field.required is False
    assert field.choices == dict([(x, x.name) for x in CountryEnum])

    # With default
    field: serializers.Field = serializer.fields["nationality"]
    assert isinstance(field, EnumField)
    assert field.allow_null is False
    assert field.default == CountryEnum.GB
    assert field.required is False
    assert field.choices == dict([(x, x.name) for x in CountryEnum])


def test_enum_value():
    class SexEnum(Enum):
        MALE = "male"
        FEMALE = "female"
        OTHER = "other"

    class Human(BaseModel):
        sex: SexEnum
        age: int

    serializer = Human.drf_serializer

    normal_serializer = serializer(data={"sex": SexEnum.MALE, "age": 25})

    assert normal_serializer.is_valid()
    assert normal_serializer.validated_data["sex"] == SexEnum.MALE
    assert normal_serializer.validated_data["age"] == 25

    value_serializer = serializer(data={"sex": "male", "age": 25})

    assert value_serializer.is_valid()
    assert value_serializer.validated_data["sex"] == SexEnum.MALE
    assert value_serializer.validated_data["age"] == 25

    bad_value_serializer = serializer(data={"sex": "bad_value", "age": 25})

    assert bad_value_serializer.is_valid() is False


def test_allow_blank():
    class Human(BaseModel):
        name: str = pydantic.Field(min_length=3, max_length=10)
        bio: str = ""
        address: str = pydantic.Field(allow_blank=True)
        town: str = pydantic.Field(allow_blank=False)
        age: int

    serializer = Human.drf_serializer()

    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["bio"], serializers.CharField)
    assert isinstance(serializer.fields["address"], serializers.CharField)
    assert isinstance(serializer.fields["town"], serializers.CharField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert serializer.fields["name"].allow_blank is False
    assert serializer.fields["town"].allow_blank is False
    assert serializer.fields["bio"].allow_blank
    assert serializer.fields["bio"].default == ""
    assert serializer.fields["address"].allow_blank is True

    blank_serializer = Human.drf_serializer(
        data={"name": "Bob", "bio": "", "address": "", "town": "somewhere", "age": 25}
    )

    assert blank_serializer.is_valid()
    assert blank_serializer.validated_data["name"] == "Bob"
    assert blank_serializer.validated_data["bio"] == ""
    assert blank_serializer.validated_data["address"] == ""
    assert blank_serializer.validated_data["town"] == "somewhere"
    assert blank_serializer.validated_data["age"] == 25

    value_serializer = Human.drf_serializer(
        data={
            "name": "Bob",
            "bio": "This is my bio",
            "address": "1234, some road",
            "town": "somewhere",
            "age": 25,
        }
    )

    assert value_serializer.is_valid()
    assert value_serializer.validated_data["name"] == "Bob"
    assert value_serializer.validated_data["bio"] == "This is my bio"
    assert value_serializer.validated_data["address"] == "1234, some road"
    assert value_serializer.validated_data["town"] == "somewhere"
    assert value_serializer.validated_data["age"] == 25

    bad_value_serializer = Human.drf_serializer(
        data={
            "name": "Bob",
            "bio": "This is my bio",
            "address": "1234, some road",
            "town": "",
            "age": 25,
        }
    )

    assert bad_value_serializer.is_valid() is False
