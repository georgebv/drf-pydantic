import datetime
import decimal
import enum
import re
import sys
import typing
import uuid

import pydantic
import pytest

from drf_pydantic import BaseModel
from drf_pydantic.errors import ModelConversionError
from rest_framework import serializers


class TestScalar:
    def test_bool(self):
        class Person(BaseModel):
            is_active: bool

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["is_active"], serializers.BooleanField)

    def test_str(self):
        class Person(BaseModel):
            name: str

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["name"], serializers.CharField)

    def test_constrained_string(self):
        class Person(BaseModel):
            name: typing.Annotated[
                str,
                pydantic.StringConstraints(min_length=3, max_length=10),
            ]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["name"], serializers.CharField)
        assert serializer.fields["name"].min_length == 3
        assert serializer.fields["name"].max_length == 10

    def test_email(self):
        class Person(BaseModel):
            email: pydantic.EmailStr

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["email"], serializers.EmailField)

    def test_regex(self):
        pattern = r"^\+?[0-9]+$"

        class Person(BaseModel):
            phone_number: typing.Annotated[
                str,
                pydantic.StringConstraints(pattern=pattern),
            ]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["phone_number"], serializers.RegexField)
        assert serializer.fields["phone_number"].validators[-1].regex == re.compile(
            pattern
        )
        assert serializer.fields["phone_number"].allow_null is False

    def test_optional_regex(self):
        pattern = r"^\+?[0-9]+$"

        class Person(BaseModel):
            phone_number: typing.Annotated[
                typing.Optional[str],
                pydantic.StringConstraints(pattern=pattern),
            ]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["phone_number"], serializers.RegexField)
        assert serializer.fields["phone_number"].validators[-1].regex == re.compile(
            pattern
        )
        assert serializer.fields["phone_number"].allow_null is True

    def test_multiple_regex_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class Person(BaseModel):
                phone_number: typing.Annotated[
                    str,
                    pydantic.StringConstraints(pattern=r"123"),
                    pydantic.StringConstraints(pattern=r"456"),
                ]

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "Field has multiple regex patterns" in str(exc_info.value)

    def test_url(self):
        class Person(BaseModel):
            website: pydantic.HttpUrl

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["website"], serializers.URLField)

    def test_uuid(self):
        class Person(BaseModel):
            uuid: uuid.UUID

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["uuid"], serializers.UUIDField)

    def test_int(self):
        class Person(BaseModel):
            age: int

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["age"], serializers.IntegerField)

    @pytest.mark.filterwarnings("ignore:.*is not supported by DRF.*")
    def test_int_with_constraints(self):
        class Stock(BaseModel):
            price: typing.Annotated[
                int,
                pydantic.Field(gt=69, lt=420),
            ]

        serializer = Stock.drf_serializer()

        assert isinstance(serializer.fields["price"], serializers.IntegerField)
        assert serializer.fields["price"].min_value == 69
        assert serializer.fields["price"].max_value == 420

    def test_float(self):
        class Person(BaseModel):
            height: float

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["height"], serializers.FloatField)

    @pytest.mark.filterwarnings("ignore:.*is not supported by DRF.*")
    def test_float_with_constraints(self):
        class Person(BaseModel):
            height: typing.Annotated[
                float,
                pydantic.Field(gt=69, lt=420),
            ]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["height"], serializers.FloatField)
        assert serializer.fields["height"].min_value == 69
        assert serializer.fields["height"].max_value == 420

    def test_decimal(self):
        class Person(BaseModel):
            salary: decimal.Decimal

        serializer = Person.drf_serializer()

        decimal_context = decimal.getcontext()

        assert isinstance(serializer.fields["salary"], serializers.DecimalField)
        assert serializer.fields["salary"].max_digits == decimal_context.prec
        assert serializer.fields["salary"].decimal_places == decimal_context.prec

    @pytest.mark.filterwarnings("ignore:.*is not supported by DRF.*")
    def test_decimal_with_consraints(self):
        class Person(BaseModel):
            salary: typing.Annotated[
                decimal.Decimal,
                pydantic.Field(gt=69, lt=420),
            ]

        serializer = Person.drf_serializer()

        decimal_context = decimal.getcontext()

        assert isinstance(serializer.fields["salary"], serializers.DecimalField)
        assert serializer.fields["salary"].max_digits == decimal_context.prec
        assert serializer.fields["salary"].decimal_places == decimal_context.prec
        assert serializer.fields["salary"].min_value == 69
        assert serializer.fields["salary"].max_value == 420

    def test_decimal_with_digit_constraints(self):
        class Person(BaseModel):
            salary: typing.Annotated[
                decimal.Decimal,
                pydantic.Field(max_digits=420, decimal_places=69),
            ]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["salary"], serializers.DecimalField)
        assert serializer.fields["salary"].max_digits == 420
        assert serializer.fields["salary"].decimal_places == 69

    def test_decimal_with_conflicting_constraints_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class Person(BaseModel):
                salary: typing.Annotated[
                    decimal.Decimal,
                    pydantic.Field(max_digits=420, decimal_places=69),
                    pydantic.Field(max_digits=69, decimal_places=420),
                ]

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "Field has multiple max_digits or decimal_places" in str(exc_info.value)

    def test_datetime(self):
        class Person(BaseModel):
            created_at: datetime.datetime

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["created_at"], serializers.DateTimeField)

    def test_date(self):
        class Person(BaseModel):
            birthday: datetime.date

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["birthday"], serializers.DateField)

    def test_time(self):
        class Person(BaseModel):
            start_time: datetime.time

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["start_time"], serializers.TimeField)

    def test_timedelta(self):
        class Person(BaseModel):
            duration: datetime.timedelta

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["duration"], serializers.DurationField)

    def test_enum(self):
        class Gender(enum.Enum):
            MALE = 0
            FEMALE = 1

        class Person(BaseModel):
            gender: Gender

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["gender"], serializers.ChoiceField)
        assert serializer.fields["gender"].choices == {0: 0, 1: 1}

    # TODO
    @pytest.mark.skip(reason="Not implemented")
    def test_literal(self):
        ...

    def test_unsupported_type_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class CustomType:
                ...

            class Person(BaseModel):
                name: CustomType

                model_config = {
                    "arbitrary_types_allowed": True,
                }

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "CustomType is not a supported scalar" in str(exc_info.value)


class TestComposite:
    def test_list(self):
        class Person(BaseModel):
            friends: list[str]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["friends"], serializers.ListField)
        assert isinstance(serializer.fields["friends"].child, serializers.CharField)
        assert serializer.fields["friends"].allow_null is False

    def test_optional_list_with_optional(self):
        class Person(BaseModel):
            friends: typing.Optional[list[str]]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["friends"], serializers.ListField)
        assert isinstance(serializer.fields["friends"].child, serializers.CharField)
        assert serializer.fields["friends"].allow_null is True

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
    def test_optional_list_with_pipe(self):
        class Person(BaseModel):
            friends: list[str] | None  # type: ignore

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["friends"], serializers.ListField)
        assert isinstance(serializer.fields["friends"].child, serializers.CharField)
        assert serializer.fields["friends"].allow_null is True

    def test_tuple_with_ellipsis(self):
        class Person(BaseModel):
            friends: tuple[str, ...]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["friends"], serializers.ListField)
        assert isinstance(serializer.fields["friends"].child, serializers.CharField)

    def test_tuple_with_multiple(self):
        class Person(BaseModel):
            friends: tuple[str, str]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["friends"], serializers.ListField)
        assert isinstance(serializer.fields["friends"].child, serializers.CharField)

    def test_tuple_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class Person(BaseModel):
                friends: tuple[int, str]

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "is not a supported tuple type" in str(exc_info.value)

    def test_dict(self):
        class Person(BaseModel):
            value: dict[str, int]

        serializer = Person.drf_serializer()

        assert isinstance(serializer.fields["value"], serializers.DictField)
        assert isinstance(serializer.fields["value"].child, serializers.IntegerField)

    def test_dict_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class Person(BaseModel):
                value: dict[int, str]

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "is not a supported dict type" in str(exc_info.value)

    def test_unsupported_type_error(self):
        with pytest.raises(ModelConversionError) as exc_info:
            T = typing.TypeVar("T")

            class CustomCollection(typing.Generic[T]):
                ...

            class Person(BaseModel):
                name: CustomCollection[str]

                model_config = {
                    "arbitrary_types_allowed": True,
                }

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "CustomCollection is not a supported composite type" in str(
            exc_info.value
        )


class TestUnion:
    def test_optional_type_with_optional(self):
        class Person(BaseModel):
            name: typing.Optional[str]

        serializer = Person.drf_serializer()

        field: serializers.Field = serializer.fields["name"]
        assert isinstance(field, serializers.CharField)
        assert field.allow_null is True

    def test_optional_type_with_union(self):
        class Person(BaseModel):
            name: typing.Union[str, None]

        serializer = Person.drf_serializer()

        field: serializers.Field = serializer.fields["name"]
        assert isinstance(field, serializers.CharField)
        assert field.allow_null is True

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
    def test_optional_type_with_pipe(self):
        class Person(BaseModel):
            name: str | None  # type: ignore

        serializer = Person.drf_serializer()

        field: serializers.Field = serializer.fields["name"]
        assert isinstance(field, serializers.CharField)
        assert field.allow_null is True

    def test_union_field_error(self):
        with pytest.raises(ModelConversionError) as exc_info:

            class Person(BaseModel):
                name: typing.Union[str, int]

            Person.drf_serializer()

        assert "Error when converting model: Person" in str(exc_info.value)
        assert "Field has Union type which cannot be converted" in str(exc_info.value)


def test_drf_field_kwargs():
    class Person(BaseModel):
        field_1: str
        field_2: str = "default"
        field_3: typing.Annotated[str, pydantic.Field("default")]
        field_4: typing.Annotated[
            str,
            pydantic.Field(default_factory=lambda: "default"),
        ]
        field_5: typing.Optional[str]
        field_6: typing.Optional[str] = "default"
        field_7: typing.Optional[str] = None

    serializer = Person.drf_serializer()

    assert serializer.fields["field_1"].required is True
    assert serializer.fields["field_2"].required is False
    assert serializer.fields["field_3"].required is False
    assert serializer.fields["field_4"].required is False
    assert serializer.fields["field_5"].required is True
    assert serializer.fields["field_6"].required is False
    assert serializer.fields["field_7"].required is False

    assert serializer.fields["field_1"].default is serializers.empty
    assert serializer.fields["field_2"].default == "default"
    assert serializer.fields["field_3"].default == "default"
    assert serializer.fields["field_4"].default == "default"
    assert serializer.fields["field_5"].default is serializers.empty
    assert serializer.fields["field_6"].default == "default"
    assert serializer.fields["field_7"].default is None

    assert serializer.fields["field_1"].allow_null is False
    assert serializer.fields["field_2"].allow_null is False
    assert serializer.fields["field_3"].allow_null is False
    assert serializer.fields["field_4"].allow_null is False
    assert serializer.fields["field_5"].allow_null is True
    assert serializer.fields["field_6"].allow_null is True
    assert serializer.fields["field_7"].allow_null is True
