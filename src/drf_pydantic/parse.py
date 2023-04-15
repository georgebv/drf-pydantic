import datetime
import decimal
import inspect
import types
import typing
import uuid
import warnings

import pydantic

from rest_framework import serializers

# Cache serializer classes to ensure that there is a one-to-one relationship
# between pydantic models and serializer classes
# This is useful during introspection in tools such as drf_spectacular, so that
# it doesn't pick the same serializer as distinct objects due to dynamic generation
SERIALIZER_REGISTRY: dict[type, type[serializers.Serializer]] = {}

# https://pydantic-docs.helpmanual.io/usage/types
# https://www.django-rest-framework.org/api-guide/fields
FIELD_MAP: dict[type, type[serializers.Field]] = {
    # Boolean fields
    bool: serializers.BooleanField,
    # String fields
    str: serializers.CharField,
    pydantic.EmailStr: serializers.EmailField,
    pydantic.HttpUrl: serializers.URLField,
    uuid.UUID: serializers.UUIDField,
    # Numeric fields
    int: serializers.IntegerField,
    float: serializers.FloatField,
    decimal.Decimal: serializers.DecimalField,
    # Date and time fields
    datetime.date: serializers.DateField,
    datetime.time: serializers.TimeField,
    datetime.datetime: serializers.DateTimeField,
    datetime.timedelta: serializers.DurationField,
    # Constraint fields
    pydantic.ConstrainedStr: serializers.CharField,
    pydantic.ConstrainedInt: serializers.IntegerField,
}


def create_serializer_from_model(
    model_class: type[pydantic.BaseModel],
) -> type[serializers.Serializer]:
    """
    Create serializer from a pydantic model.

    Parameters
    ----------
    model_class : type[pydantic.BaseModel]
        Pydantic model class (not instance!).

    Returns
    -------
    type[serializers.Serializer]
        Django REST framework serializer class.

    """
    if model_class not in SERIALIZER_REGISTRY:
        fields: dict[str, type[serializers.Field]] = {}
        for field_name, field in model_class.__fields__.items():
            fields[field_name] = _convert_field(field)
        SERIALIZER_REGISTRY[model_class] = type(
            f"{model_class.__name__}Serializer",
            (serializers.Serializer,),
            fields,
        )
    return SERIALIZER_REGISTRY[model_class]


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

    # Numeric field with constraints
    if isinstance(field.type_, pydantic.types.ConstrainedNumberMeta):
        if field.type_.gt is not None:
            warnings.warn(
                "gt (>) is not supported by DRF, using ge (>=) instead",
                UserWarning,
            )
            extra_kwargs["min_value"] = field.type_.gt
        elif field.type_.ge is not None:
            extra_kwargs["min_value"] = field.type_.ge
        if field.type_.lt is not None:
            warnings.warn(
                "lt (<) is not supported by DRF, using le (<=) instead",
                UserWarning,
            )
            extra_kwargs["max_value"] = field.type_.lt
        elif field.type_.le is not None:
            extra_kwargs["max_value"] = field.type_.le

    # String field with constraints
    if inspect.isclass(field.type_) and issubclass(
        field.type_, pydantic.types.ConstrainedStr
    ):
        extra_kwargs["min_length"] = field.type_.min_length
        extra_kwargs["max_length"] = field.type_.max_length

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
    assert isinstance(
        field.outer_type_,
        (
            types.GenericAlias,
            getattr(typing, "_GenericAlias"),
        ),
    ), f"Unsupported container type '{field.outer_type_.__name__}'"
    if field.outer_type_.__origin__ is list or field.outer_type_.__origin__ is tuple:
        return serializers.ListField(child=_convert_type(field.type_)(**extra_kwargs))
    raise NotImplementedError(
        f"Container type '{field.outer_type_.__origin__.__name__}' is not yet supported"
    )


def _convert_type(type_: type) -> type[serializers.Field]:
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
    type[serializers.Field]
        Serializer field class.

    """
    # Nested model
    if issubclass(type_, pydantic.BaseModel):
        try:
            return getattr(type_, "drf_serializer")
        except AttributeError:
            return create_serializer_from_model(type_)

    for key in [type_, type_.__base__]:
        try:
            return FIELD_MAP[key]
        except KeyError:
            continue
    raise NotImplementedError(f"{type_.__name__} is not yet supported")
