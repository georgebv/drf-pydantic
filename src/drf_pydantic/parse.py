import datetime
import decimal
import inspect
import typing
import uuid

import pydantic
import pydantic.fields

from pydantic_core import PydanticUndefined, Url
from rest_framework import serializers

from drf_pydantic.errors import FieldConversionError, ModelConversionError
from drf_pydantic.utils import get_union_members, is_scalar

# Cache Serializer classes to ensure that there is a one-to-one relationship
# between pydantic models and DRF Serializer classes
# Example: reuse Serializer for nested models
SERIALIZER_REGISTRY: dict[type, type[serializers.Serializer]] = {}

# https://pydantic-docs.helpmanual.io/usage/types
# https://www.django-rest-framework.org/api-guide/fields
# Maps python types supported by padantic to DRF serializer Fields
FIELD_MAP: dict[type, type[serializers.Field]] = {
    # Boolean fields
    bool: serializers.BooleanField,
    # String fields
    str: serializers.CharField,
    pydantic.EmailStr: serializers.EmailField,
    # Regex implemented as a special case
    # WARN This is what pydantic converts pydantic.HttpUrl to
    Url: serializers.URLField,
    uuid.UUID: serializers.UUIDField,
    # Numeric fields
    int: serializers.IntegerField,
    float: serializers.FloatField,
    # Decimal implemented as a special case
    # Date and time fields
    datetime.datetime: serializers.DateTimeField,
    datetime.date: serializers.DateField,
    datetime.time: serializers.TimeField,
    datetime.timedelta: serializers.DurationField,
}


def create_serializer_from_model(
    pydantic_model: typing.Type[pydantic.BaseModel],
) -> type[serializers.Serializer]:
    """
    Create DRF Serializer from a pydantic model.

    Parameters
    ----------
    pydantic_model : type[pydantic.BaseModel]
        Pydantic model class.

    Returns
    -------
    type[rest_framework.serializers.Serializer]
        DRF Serializer class.

    """
    if pydantic_model not in SERIALIZER_REGISTRY:
        errors: dict[str, str] = {}
        fields: dict[str, type[serializers.Field]] = {}
        for field_name, field in pydantic_model.model_fields.items():
            try:
                fields[field_name] = _convert_field(field)
            except FieldConversionError as error:
                errors[field_name] = str(error)
        if len(errors) > 0:
            raise ModelConversionError(
                "\n".join(
                    [
                        f"Error when converting model: {pydantic_model.__name__}",
                        *[
                            "\n".join(
                                [
                                    f"  {field_name}",
                                    f"    {error}",
                                ]
                            )
                            for field_name, error in errors.items()
                        ],
                    ]
                )
            )
        assert len(fields) == len(pydantic_model.model_fields)
        SERIALIZER_REGISTRY[pydantic_model] = type(
            f"{pydantic_model.__name__}Serializer",
            (serializers.Serializer,),
            fields,
        )
    return SERIALIZER_REGISTRY[pydantic_model]


def _convert_field(
    field: pydantic.fields.FieldInfo,
) -> serializers.Field:
    """
    Convert pydantic field to DRF serializer Field.

    Parameters
    ----------
    field : pydantic.fields.FieldInfo
        Field to convert.

    Returns
    -------
    rest_framework.serializers.Field
        Django REST framework serializer Field instance.

    """
    assert field.annotation is not None
    drf_field_kwargs: dict[str, typing.Any] = {
        "required": field.is_required(),
    }
    _default_value = field.get_default(call_default_factory=True)
    if _default_value is not PydanticUndefined:
        drf_field_kwargs["default"] = _default_value

    # Process constraints
    regex_patterns: list[str] = []
    for item in field.metadata:
        if isinstance(item, pydantic.StringConstraints):
            drf_field_kwargs["min_length"] = (
                max(
                    drf_field_kwargs.get("min_length", float("-inf")),
                    item.min_length,
                )
                if item.min_length is not None
                else drf_field_kwargs.get("min_length", None)
            )
            drf_field_kwargs["max_length"] = (
                min(
                    drf_field_kwargs.get("max_length", float("inf")),
                    item.max_length,
                )
                if item.max_length is not None
                else drf_field_kwargs.get("max_length", None)
            )
            if item.pattern is not None:
                regex_patterns.append(item.pattern)
    if len(regex_patterns) > 1:
        raise FieldConversionError(
            f"Field has multiple regex patterns: {regex_patterns}"
        )
    elif len(regex_patterns) == 1:
        return serializers.RegexField(regex=item.pattern, **drf_field_kwargs)

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

    return _convert_type(field.annotation, **drf_field_kwargs)


def _convert_type(type_: typing.Type, **kwargs) -> serializers.Field:  # noqa: PLR0911
    """
    Convert scalar type to serializer field class.

    Scalar field is any field that is not a pydantic model (this would be nested field)
    or a collection field (e.g., list[int]).
    Examples of scalar fields: int, float, datetime, pydantic.EmailStr

    Parameters
    ----------
    type_ : type
        Field class.
    kwargs : dict
        Additional keyword arguments used to instantiate the serializer Field class.

    Returns
    -------
    type[serializers.Field]
        Serializer field class.

    """
    field_union_members = get_union_members(type_)
    if field_union_members is not None and (
        len(field_union_members) > 2 or type(None) not in field_union_members
    ):
        raise FieldConversionError(
            f"Field has Union type which cannot be converted "
            f"to DRF Serializer: {type_}. "
            f"Only optional union (two types, one of which is None) is supported."
        )
    if field_union_members is not None and type(None) in field_union_members:
        kwargs["allow_null"] = True
        type_ = [  # noqa: RUF015
            type_ for type_ in field_union_members if type_ is not type(None)
        ][0]
    else:
        kwargs["allow_null"] = False

    # Scalar field
    if is_scalar(type_):
        # Nested model
        if issubclass(type_, pydantic.BaseModel):
            try:
                return getattr(type_, "drf_serializer")(**kwargs)
            except AttributeError:
                return create_serializer_from_model(type_)(**kwargs)

        # Normal class
        if inspect.isclass(type_):
            if type_ is decimal.Decimal:
                _context = decimal.getcontext()
                kwargs["max_digits"] = _context.prec
                kwargs["decimal_places"] = _context.prec
                return serializers.DecimalField(**kwargs)
            else:
                for key in [type_, type_.__base__]:
                    try:
                        return FIELD_MAP[key](**kwargs)
                    except KeyError:
                        continue

        # TODO Enum

        # TODO Literal
        # if type_.__origin__ is typing.Literal:
        #     choices = type_.__args__
        #     assert all(isinstance(choice, str) for choice in choices)
        #     return serializers.ChoiceField(choices=choices, **kwargs)

        raise FieldConversionError(f"{type_.__name__} is not a supported scalar type")

    # Composite field
    if type_.__origin__ is list:
        # Enforced by pydantic, check just in case
        assert len(type_.__args__) == 1
        return serializers.ListField(
            child=_convert_type(type_.__args__[0]),
            allow_empty=True,
            **kwargs,
        )
    elif type_.__origin__ is tuple:
        if (
            len(type_.__args__) == 2
            and (is_scalar(type_.__args__[0]) and type_.__args__[1] is Ellipsis)
            or (type_.__args__[0] is Ellipsis and is_scalar(type_.__args__[1]))
        ):
            return serializers.ListField(
                child=_convert_type(type_.__args__[0]),
                allow_empty=True,
                **kwargs,
            )
        elif (
            all(is_scalar(arg) for arg in type_.__args__)
            and len(set(type_.__args__)) == 1
        ):
            return serializers.ListField(
                child=_convert_type(type_.__args__[0]),
                allow_empty=True,
                **kwargs,
            )
        else:
            raise FieldConversionError(
                f"{type_} is not a supported tuple type. "
                f"Tuple annotation must meet one of the following conditions: "
                f"(a) single scalar and single Ellipsis (e.g., tuple[int, ...]) or "
                "(b) multiple scalars of the same type (e.g., tuple[int, int])."
            )
    elif type_.__origin__ is dict:
        # Enforced by pydantic, check just in case
        assert len(type_.__args__) == 2
        if type_.__args__[0] is not str:
            raise FieldConversionError(
                f"{type_} is not a supported dict type. "
                f"Dict annotation must look like dict[str, <annotation>]."
            )
        return serializers.DictField(
            child=_convert_type(type_.__args__[1]),
            allow_empty=True,
            **kwargs,
        )
    else:
        raise FieldConversionError(
            f"{type_.__origin__.__name__} is not a supported composite type"
        )
