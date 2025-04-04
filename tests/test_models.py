import datetime
import typing

import pydantic
import pytest

from rest_framework import serializers

from drf_pydantic import BaseModel, DrfPydanticSerializer


def test_model_with_multiple_fields():
    class Person(BaseModel):
        name: str
        email: pydantic.EmailStr
        age: int
        height: float
        address: typing.Optional[str]
        date_of_birth: datetime.date
        nationality: str = "USA"
        friends: list[str]

    serializer = Person.drf_serializer()

    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 8

    field: serializers.Field

    # Regular fields
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["email"], serializers.EmailField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["height"], serializers.FloatField)
    assert isinstance(serializer.fields["date_of_birth"], serializers.DateField)
    assert isinstance(serializer.fields["friends"], serializers.ListField)
    for name in ["name", "email", "age", "height", "date_of_birth", "friends"]:
        field = serializer.fields[name]
        assert field.required is True
        assert field.default is serializers.empty
        assert field.allow_null is False

    # Optional
    optional_field = serializer.fields["address"]
    assert isinstance(optional_field, serializers.CharField)
    assert optional_field.required is True
    assert optional_field.default is serializers.empty
    assert optional_field.allow_null is True

    # With default
    field_with_default = serializer.fields["nationality"]
    assert isinstance(field_with_default, serializers.CharField)
    assert field_with_default.required is False
    assert field_with_default.default == "USA"
    assert field_with_default.allow_null is False


def test_inheritance():
    class Person(BaseModel, pydantic.BaseModel):
        name: str
        age: int

    class Employee(Person):
        title: str
        salary: float

    serializer = Employee.drf_serializer()

    assert serializer.__class__.__name__ == "EmployeeSerializer"
    assert len(serializer.fields) == 4

    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["salary"], serializers.FloatField)
    assert isinstance(serializer.fields["title"], serializers.CharField)


def test_iheritance_from_non_drf_model():
    class Person(pydantic.BaseModel):
        name: str
        age: int

    class Employee(BaseModel, Person):
        title: str
        salary: float

    serializer = Employee.drf_serializer()

    assert serializer.__class__.__name__ == "EmployeeSerializer"
    assert len(serializer.fields) == 4

    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["age"], serializers.IntegerField)
    assert isinstance(serializer.fields["salary"], serializers.FloatField)
    assert isinstance(serializer.fields["title"], serializers.CharField)


def test_nested_model():
    class Job(BaseModel):
        title: str
        salary: float

    class Person(BaseModel):
        name: str
        job: Job

    serializer = Person.drf_serializer()

    # Parent model
    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 2
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["job"], serializers.Serializer)

    # Nested model
    job: serializers.Serializer = serializer.fields["job"]
    assert job.__class__.__name__ == "JobSerializer"
    assert len(job.fields) == 2
    assert isinstance(job.fields["title"], serializers.CharField)
    assert isinstance(job.fields["salary"], serializers.FloatField)


def test_list_of_nested_models():
    class Apartment(BaseModel):
        floor: int
        owner: str

    class Building(BaseModel):
        address: str
        apartments: list[Apartment]

    serializer = Building.drf_serializer()

    # Parent model
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


def test_non_drf_nested_model():
    class Apartment(pydantic.BaseModel):
        floor: int
        owner: str

    class Building(BaseModel):
        address: str
        apartments: list[Apartment]

    serializer = Building.drf_serializer()

    # Parent model
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


def test_manual_serializer():
    class MyCustomSerializer(DrfPydanticSerializer):
        gender = serializers.ChoiceField(choices=["male", "female"])
        title = serializers.CharField()
        peers = serializers.ListField(child=serializers.IntegerField())

    class Person(BaseModel):
        name: str
        age: int

        drf_serializer = MyCustomSerializer

    serializer = Person.drf_serializer()
    assert serializer.__class__.__name__ == "MyCustomSerializer"
    assert len(serializer.fields) == 3
    assert isinstance(serializer.fields["gender"], serializers.ChoiceField)
    assert isinstance(serializer.fields["title"], serializers.CharField)
    assert isinstance(serializer.fields["peers"], serializers.ListField)


def test_invalid_manual_serializer():
    with pytest.raises(TypeError, match=r"must be a class"):

        class Person1(BaseModel):
            name: str
            age: int

            drf_serializer = object()

    with pytest.raises(TypeError, match=r"is not a valid type"):

        class Person2(BaseModel):
            name: str
            age: int

            drf_serializer = object


def test_manual_serializer_warnings():
    with pytest.warns(UserWarning, match=r"should be replaced"):

        class MySerializer1(serializers.Serializer):
            name = serializers.CharField()
            age = serializers.IntegerField()

        class Person1(BaseModel):
            name: str
            age: int

            drf_serializer = MySerializer1

    with pytest.warns(UserWarning, match=r"doesn't match expected class"):

        class MySerializer2(DrfPydanticSerializer):
            name = serializers.CharField()
            age = serializers.IntegerField()

            _pydantic_model = BaseModel

        class Person2(BaseModel):
            name: str
            age: int

            drf_serializer = MySerializer2


def test_manual_serializer_inheritance():
    """Ensure that manual serializer is not inherited from the parent class."""

    class MyCustomSerializer(DrfPydanticSerializer):
        gender = serializers.ChoiceField(choices=["male", "female"])
        title = serializers.CharField()
        peers = serializers.ListField(child=serializers.IntegerField())

    class Person(BaseModel):
        name: str
        age: int

        drf_serializer = MyCustomSerializer

    class Employee(Person):
        salary: float
        office: str

    person_serializer = Person.drf_serializer()
    assert person_serializer.__class__.__name__ == "MyCustomSerializer"
    assert len(person_serializer.fields) == 3
    assert isinstance(person_serializer.fields["gender"], serializers.ChoiceField)
    assert isinstance(person_serializer.fields["title"], serializers.CharField)
    assert isinstance(person_serializer.fields["peers"], serializers.ListField)

    employee_serializer = Employee.drf_serializer()
    assert employee_serializer.__class__.__name__ == "EmployeeSerializer"
    assert len(employee_serializer.fields) == 4
    assert isinstance(employee_serializer.fields["name"], serializers.CharField)
    assert isinstance(employee_serializer.fields["age"], serializers.IntegerField)
    assert isinstance(employee_serializer.fields["salary"], serializers.FloatField)
    assert isinstance(employee_serializer.fields["office"], serializers.CharField)


def test_nested_manual_serializer():
    class MyCustomSerializer(DrfPydanticSerializer):
        gender = serializers.ChoiceField(choices=["male", "female"])
        title = serializers.CharField()
        peers = serializers.ListField(child=serializers.IntegerField())

    class Job(BaseModel):
        title: str
        salary: float

        drf_serializer = MyCustomSerializer

    class Person(BaseModel):
        name: str
        job: Job

    serializer = Person.drf_serializer()
    assert serializer.__class__.__name__ == "PersonSerializer"
    assert len(serializer.fields) == 2
    assert isinstance(serializer.fields["name"], serializers.CharField)
    assert isinstance(serializer.fields["job"], serializers.Serializer)

    job_serializer = serializer.fields["job"]
    assert job_serializer.__class__.__name__ == "MyCustomSerializer"
    assert len(job_serializer.fields) == 3
    assert isinstance(job_serializer.fields["gender"], serializers.ChoiceField)
    assert isinstance(job_serializer.fields["title"], serializers.CharField)
    assert isinstance(job_serializer.fields["peers"], serializers.ListField)


def test_drf_config_inheritance():
    class Grandparent(pydantic.BaseModel):
        name: str
        age: int

    class Parent(BaseModel, Grandparent):
        drf_config = {"validate_pydantic": True}

    class Child(Parent):
        drf_config = {"validation_error": "pydantic"}

    class Grandchild(Child):
        drf_config = {
            "validate_pydantic": False,
            "backpopulate_after_validation": False,
        }

    assert not hasattr(Grandparent, "drf_config")

    assert Parent.drf_config.get("validate_pydantic", False)
    assert Parent.drf_config.get("validation_error", "") == "drf"
    assert Parent.drf_config.get("backpopulate_after_validation", False)

    assert Child.drf_config.get("validate_pydantic", False)
    assert Child.drf_config.get("validation_error", "") == "pydantic"
    assert Child.drf_config.get("backpopulate_after_validation", False)

    assert not Grandchild.drf_config.get("validate_pydantic", True)
    assert Grandchild.drf_config.get("validation_error", "") == "pydantic"
    assert not Grandchild.drf_config.get("backpopulate_after_validation", True)


def test_drf_config_nested():
    class Name(BaseModel):
        first: str
        last: str

        drf_config = {"validate_pydantic": True}

    class Person(BaseModel):
        name: Name
        age: int

    assert Name.drf_config.get("validate_pydantic", False)
    assert Name.drf_config.get("validation_error", "") == "drf"

    assert not Person.drf_config.get("validate_pydantic", True)
    assert Person.drf_config.get("validation_error", "") == "drf"
