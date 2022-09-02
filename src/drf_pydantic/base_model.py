import datetime
import decimal
import inspect
import types
import typing

import pydantic

from rest_framework import serializers

SERIALIZER_REGISTRY: dict[type, typing.Type[serializers.Serializer]] = {}

# Read this https://www.django-rest-framework.org/api-guide/fields/
FIELD_MAP: dict[type, typing.Type[serializers.Field]] = {
    # Boolean fields
    bool: serializers.BooleanField,
    # String fields
    str: serializers.CharField,
    pydantic.EmailStr: serializers.EmailField,
    pydantic.HttpUrl: serializers.URLField,
    # Numeric fields
    int: serializers.IntegerField,
    float: serializers.FloatField,
    decimal.Decimal: serializers.DecimalField,
    # Date and time fields
    datetime.date: serializers.DateField,
    datetime.time: serializers.TimeField,
    datetime.datetime: serializers.DateTimeField,
    datetime.timedelta: serializers.DurationField,
}


class ModelMetaclass(pydantic.main.ModelMetaclass, type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if cls not in SERIALIZER_REGISTRY:
            fields: dict[str, typing.Type[serializers.Field]] = {}
            for field_name, field in cls.__fields__.items():
                fields[field_name] = _convert_field(field)
            SERIALIZER_REGISTRY[cls] = type(
                f"{cls.__name__}Serializer",
                (serializers.Serializer,),
                fields,
            )

        setattr(cls, "drf_serializer", SERIALIZER_REGISTRY[cls])

        return cls


class BaseModel(pydantic.BaseModel, metaclass=ModelMetaclass):
    if typing.TYPE_CHECKING:
        # populated by the metaclass, defined here to help IDEs only
        drf_serializer: typing.Type[serializers.Serializer]


def _convert_field(field: pydantic.fields.ModelField) -> serializers.Field:
    """
    Convert pydantic field to Django REST framework serializer field.

    Parameters
    ----------
    field : pydantic.fields.ModelField
        Field to convert.

    Returns
    -------
    rest_framework.serializers.Field
        Django REST framework serializer field instance.

    """
    extra_kwargs: dict[str, typing.Any] = {}
    if isinstance(field.required, pydantic.fields.UndefinedType):
        extra_kwargs["required"] = True
    else:
        extra_kwargs["required"] = field.required
    if field.default is not None:
        extra_kwargs["default"] = field.default
    if field.allow_none:
        extra_kwargs["allow_null"] = True
        extra_kwargs["default"] = None

    # Scalar field
    if field.outer_type_ is field.type_:
        # Normal class
        if inspect.isclass(field.type_):
            return _convert_type(field.type_)(**extra_kwargs)

        # Alias
        if field.type_.__origin__ is typing.Literal:
            choices = field.type_.__args__
            assert all(isinstance(choice, str) for choice in choices)
            return serializers.ChoiceField(choices=choices, **extra_kwargs)
        raise NotImplementedError(f"{field.type_.__name__} is not yet supported")

    # Container field
    assert isinstance(field.outer_type_, types.GenericAlias)
    if field.outer_type_.__origin__ is list:
        return serializers.ListField(child=_convert_type(field.type_)(**extra_kwargs))
    raise NotImplementedError(
        f"Container type '{field.outer_type_.__origin__.__name__}' is not yet supported"
    )


def _convert_type(type_: type) -> typing.Type[serializers.Field]:
    """
    Convert scalar type to serializer field class.

    Scalar field is any field that is not a pydantic model (this would be nested field)
    or a collection field (e.g., list[int]).
    Examples of scalar fields: int, float, datetime, pydantic.EmailStr

    Parameters
    ----------
    type_ : type
        Field class.

    Returns
    -------
    typing.Type[serializers.Field]
        Serializer field class.

    """
    # Nested model
    if issubclass(type_, BaseModel):
        return type_.drf_serializer

    if issubclass(type_, pydantic.BaseModel):
        raise TypeError(
            " ".join(
                [
                    f"Model {type_.__name__} is a normal pydantic model.",
                    "All nested models must be inherited from drf_pydantic.BaseModel",
                ]
            )
        )

    try:
        return FIELD_MAP[type_]
    except KeyError as error:
        raise NotImplementedError(f"{type_.__name__} is not yet supported") from error
