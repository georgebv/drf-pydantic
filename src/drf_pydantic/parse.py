import datetime
import decimal
import inspect
import typing
import uuid

import pydantic
import pydantic.fields

from pydantic_core import PydanticUndefined
from rest_framework import serializers

from .utils import get_union_members, is_scalar

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
}


def create_serializer_from_model(
    model_class: typing.Type[pydantic.BaseModel],
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
        for field_name, field in model_class.model_fields.items():
            fields[field_name] = _convert_field(field_name, field)
        SERIALIZER_REGISTRY[model_class] = type(
            f"{model_class.__name__}Serializer",
            (serializers.Serializer,),
            fields,
        )
    return SERIALIZER_REGISTRY[model_class]


def _convert_field(
    field_name: str,
    field: pydantic.fields.FieldInfo,
) -> serializers.Field:
    """
    Convert pydantic field to Django REST framework serializer field.

    Parameters
    ----------
    field_name : str
        Field name.
    field : pydantic.fields.FieldInfo
        Field to convert.

    Returns
    -------
    rest_framework.serializers.Field
        Django REST framework serializer field instance.

    """
    field_annotation = field.annotation
    if field_annotation is None:
        raise TypeError(f"Field '{field_name}' is missing type annotation")
    field_union_members = get_union_members(field_annotation)
    if (
        field_union_members is not None
        and len(field_union_members) > 2
        and type(None) not in field_union_members
    ):
        raise TypeError(f"Union types are not supported. Field: '{field_name}'")

    drf_field_kwargs: dict[str, typing.Any] = {
        "required": field.is_required(),
    }
    _default_value = field.get_default(call_default_factory=True)
    if _default_value is not PydanticUndefined:
        drf_field_kwargs["default"] = _default_value
    if field_union_members is not None and type(None) in field_union_members:
        drf_field_kwargs["allow_null"] = True
        field_annotation = [t for t in field_union_members if t is not type(None)][0]
    else:
        drf_field_kwargs["allow_null"] = False

    # TODO Search field.metadata for constraints
    # # Numeric field with constraints
    # if isinstance(field_annotation, pydantic.types.ConstrainedNumberMeta):
    #     if field.type_.gt is not None:
    #         warnings.warn(
    #             "gt (>) is not supported by DRF, using ge (>=) instead",
    #             UserWarning,
    #         )
    #         drf_field_kwargs["min_value"] = field.type_.gt
    #     elif field.type_.ge is not None:
    #         drf_field_kwargs["min_value"] = field.type_.ge
    #     if field.type_.lt is not None:
    #         warnings.warn(
    #             "lt (<) is not supported by DRF, using le (<=) instead",
    #             UserWarning,
    #         )
    #         drf_field_kwargs["max_value"] = field.type_.lt
    #     elif field.type_.le is not None:
    #         drf_field_kwargs["max_value"] = field.type_.le

    # TODO Search field.metadata for constraints
    # # String field with constraints
    # if inspect.isclass(field.type_) and issubclass(
    #     field.type_, pydantic.types.ConstrainedStr
    # ):
    #     drf_field_kwargs["min_length"] = field.type_.min_length
    #     drf_field_kwargs["max_length"] = field.type_.max_length

    # Scalar field
    if is_scalar(field_annotation):
        # Normal class
        if inspect.isclass(field_annotation):
            return _convert_type(field_annotation)(**drf_field_kwargs)

        # Alias
        if field_annotation.__origin__ is typing.Literal:
            choices = field_annotation.__args__
            assert all(isinstance(choice, str) for choice in choices)
            return serializers.ChoiceField(choices=choices, **drf_field_kwargs)

        raise NotImplementedError(f"{field_annotation} is not yet supported")

    # Container field
    if (
        field_annotation.__origin__ in [list, tuple]
        and len(field_annotation.__args__) == 1
        and is_scalar(field_annotation.__args__[0])
    ):
        return serializers.ListField(
            child=_convert_type(field_annotation.__args__[0])(**drf_field_kwargs)
        )
    raise NotImplementedError(f"'{field_annotation}' is not yet supported")


def _convert_type(type_: typing.Type) -> typing.Type[serializers.Field]:
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
    raise NotImplementedError(f"{type_.__name__} is not supported")
