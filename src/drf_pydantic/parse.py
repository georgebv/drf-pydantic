import datetime
import decimal
import enum
import inspect
import re
import typing
import uuid
import warnings

import annotated_types
import pydantic
import pydantic.fields
import pydantic_core

from annotated_types import MaxLen, MinLen
from pydantic._internal._fields import PydanticMetadata
from rest_framework import serializers  # type: ignore
from typing_extensions import TypeAliasType

import drf_pydantic

from drf_pydantic.base_serializer import DrfPydanticSerializer
from drf_pydantic.config import DrfConfigDict
from drf_pydantic.errors import FieldConversionError, ModelConversionError
from drf_pydantic.utils import get_union_members, is_scalar

# Cache Serializer classes to ensure that there is a one-to-one relationship
# between pydantic models and DRF Serializer classes
# Example: reuse Serializer for nested models
SERIALIZER_REGISTRY: dict[type, type[DrfPydanticSerializer]] = {}

# https://pydantic-docs.helpmanual.io/usage/types
# https://www.django-rest-framework.org/api-guide/fields
# Maps python types supported by padantic to DRF serializer Fields
FIELD_MAP: dict[type, type[serializers.Field]] = {
    # Boolean fields
    bool: serializers.BooleanField,
    # String fields
    str: serializers.CharField,
    pydantic.EmailStr: serializers.EmailField,  # type: ignore
    # * Regex implemented as a special case
    # WARN (legacy) pydantic converts pydantic.HttpUrl to pydantic_core.Url
    pydantic_core.Url: serializers.URLField,
    pydantic.HttpUrl: serializers.URLField,
    uuid.UUID: serializers.UUIDField,
    # Numeric fields
    int: serializers.IntegerField,
    float: serializers.FloatField,
    # * Decimal implemented as a special case
    # Date and time fields
    datetime.datetime: serializers.DateTimeField,
    datetime.date: serializers.DateField,
    datetime.time: serializers.TimeField,
    datetime.timedelta: serializers.DurationField,
    # Scalar collections
    list: serializers.ListField,
    tuple: serializers.ListField,
    dict: serializers.DictField,
}


def create_serializer_from_model(
    pydantic_model: typing.Type[pydantic.BaseModel],
    drf_config: typing.Optional[DrfConfigDict] = None,
) -> type[DrfPydanticSerializer]:
    """
    Create DRF Serializer from a pydantic model.

    Parameters
    ----------
    pydantic_model : type[pydantic.BaseModel]
        Pydantic model class.
    drf_config : DrfConfigDict, optional
        Config to set on the created serializer.
        If None (default), assumed to be present on 'pydantic_model'.

    Returns
    -------
    type[DrfPydanticSerializer]
        DRF Serializer class.

    """
    if pydantic_model not in SERIALIZER_REGISTRY:
        drf_config = drf_config or getattr(pydantic_model, "drf_config")
        assert drf_config is not None

        errors: dict[str, str] = {}
        fields: dict[str, serializers.Field] = {}
        for field_name, field in pydantic_model.model_fields.items():
            try:
                fields[field_name] = _convert_field(field, drf_config=drf_config)
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
            (DrfPydanticSerializer,),
            {
                "_pydantic_model": pydantic_model,
                "_drf_config": drf_config,
                **fields,
            },
        )
    return SERIALIZER_REGISTRY[pydantic_model]


def _convert_field(
    field: pydantic.fields.FieldInfo,
    drf_config: DrfConfigDict,
) -> serializers.Field:
    """
    Convert pydantic field to DRF serializer Field.

    Parameters
    ----------
    field : pydantic.fields.FieldInfo
        Field to convert.
    drf_config : DrfConfigDict
        Config to set on the created serializer or nested serializers,
        if 'field' or its members/nested fields are pydantic models.

    Returns
    -------
    rest_framework.serializers.Field
        Django REST framework serializer Field instance.

    """
    # Check if DRF field was explicitly set
    manual_drf_fields: list[serializers.Field] = []
    for item in field.metadata:
        if isinstance(item, serializers.Field):
            manual_drf_fields.append(item)
    if len(manual_drf_fields) == 1:
        return manual_drf_fields[0]
    if len(manual_drf_fields) > 1:
        raise FieldConversionError(
            "Field has multiple conflicting DRF serializer fields. "
            "Only one DRF serializer field can be provided per field."
        )

    assert field.annotation is not None
    drf_field_kwargs: dict[str, typing.Any] = {
        "required": field.is_required(),
    }
    _default_value = field.get_default(call_default_factory=True)
    if _default_value is not pydantic_core.PydanticUndefined:
        drf_field_kwargs["default"] = _default_value

    # Adding description as help_text
    if (
        field.description is not pydantic_core.PydanticUndefined
        and field.description is not None
    ):
        drf_field_kwargs["help_text"] = field.description

    # Adding label as title
    if field.title is not pydantic_core.PydanticUndefined and field.title is not None:
        drf_field_kwargs["label"] = field.title

    # Process constraints
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
        elif isinstance(item, MinLen):
            drf_field_kwargs["min_length"] = max(
                drf_field_kwargs.get("min_length", float("-inf")),
                item.min_length,
            )
        elif isinstance(item, MaxLen):
            drf_field_kwargs["max_length"] = min(
                drf_field_kwargs.get("max_length", float("inf")),
                item.max_length,
            )
        # pydantic.Field constraints
        elif isinstance(item, PydanticMetadata):
            # Decimal constraints
            if (
                drf_field_kwargs.get("max_digits", None) is not None
                and getattr(item, "max_digits", None) is not None
            ) or (
                drf_field_kwargs.get("decimal_places", None) is not None
                and getattr(item, "decimal_places", None) is not None
            ):
                raise FieldConversionError(
                    "Field has multiple max_digits or decimal_places "
                    "conflicting constraints."
                )
            if getattr(item, "max_digits", None) is not None:
                drf_field_kwargs["max_digits"] = getattr(item, "max_digits")
            if getattr(item, "decimal_places", None) is not None:
                drf_field_kwargs["decimal_places"] = getattr(item, "decimal_places")
        # Numeric constraints (in DRF min/max_value is only supported for numeric types)
        elif isinstance(item, annotated_types.Ge):
            if drf_field_kwargs.get("min_value", None) is not None:
                raise FieldConversionError(
                    "Field has multiple conflicting min_value constraints"
                )
            try:
                drf_field_kwargs["min_value"] = decimal.Decimal(item.ge)  # type: ignore
            except (TypeError, decimal.InvalidOperation):
                pass
        elif isinstance(item, annotated_types.Gt):
            if drf_field_kwargs.get("min_value", None) is not None:
                raise FieldConversionError(
                    "Field has multiple conflicting min_value constraints"
                )
            warnings.warn(
                "gt (>) is not supported by DRF, using ge (>=) instead",
                UserWarning,
            )
            try:
                drf_field_kwargs["min_value"] = decimal.Decimal(item.gt)  # type: ignore
            except (TypeError, decimal.InvalidOperation):
                pass
        elif isinstance(item, annotated_types.Le):
            if drf_field_kwargs.get("max_value", None) is not None:
                raise FieldConversionError(
                    "Field has multiple conflicting max_value constraints"
                )
            try:
                drf_field_kwargs["max_value"] = decimal.Decimal(item.le)  # type: ignore
            except (TypeError, decimal.InvalidOperation):
                pass
        elif isinstance(item, annotated_types.Lt):
            if drf_field_kwargs.get("max_value", None) is not None:
                raise FieldConversionError(
                    "Field has multiple conflicting max_value constraints"
                )
            warnings.warn(
                "lt (<) is not supported by DRF, using le (<=) instead",
                UserWarning,
            )
            try:
                drf_field_kwargs["max_value"] = decimal.Decimal(item.lt)  # type: ignore
            except (TypeError, decimal.InvalidOperation):
                pass

    return _convert_type(
        field.annotation,
        drf_config=drf_config,
        field=field,
        **drf_field_kwargs,
    )


def _convert_type(  # noqa: PLR0911
    type_: typing.Union[typing.Type[typing.Any], TypeAliasType],
    drf_config: DrfConfigDict,
    field: typing.Optional[pydantic.fields.FieldInfo] = None,
    **kwargs: typing.Any,
) -> serializers.Field:
    """
    Convert type or type alias to DRF serializer Field.

    Parameters
    ----------
    type_ : type | TypeAliasType
        Field class.
    drf_config : DrfConfigDict, optional
        Config to set on the created serializer or nested serializers,
        if 'type_' or its members/nested fields are pydantic models.
    field : pydantic.fields.FieldInfo | None
        Pydantic field instance.
    kwargs : dict
        Additional keyword arguments used to instantiate the serializer Field class.

    Returns
    -------
    rest_framework.serializers.Field
        Django REST framework serializer Field instance.

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

    # Type alias
    if isinstance(type_, TypeAliasType):
        if type_ is pydantic.JsonValue:  # type: ignore
            return serializers.JSONField(**kwargs)
        raise FieldConversionError(
            f"{type_.__name__} is not a supported TypeAliasType."
        )

    # Scalar field
    if is_scalar(type_):
        if not inspect.isclass(type_):
            raise FieldConversionError(  # pragma: no cover
                f"{type_.__name__} is not a supported scalar type. "
                f"Only classes and TypeAliasType instances are supported."
            )
        # Nested model
        if issubclass(type_, drf_pydantic.BaseModel):
            return type_.drf_serializer(**kwargs)
        if issubclass(type_, pydantic.BaseModel):
            return create_serializer_from_model(type_, drf_config=drf_config)(**kwargs)
        # Decimal
        elif type_ is decimal.Decimal:
            _context = decimal.getcontext()
            kwargs["max_digits"] = kwargs.get("max_digits", None) or _context.prec
            kwargs["decimal_places"] = (
                kwargs.get("decimal_places", None) or _context.prec
            )
            return serializers.DecimalField(**kwargs)
        # Regex
        elif field is not None and any(
            isinstance(item, pydantic.StringConstraints) and item.pattern is not None
            for item in field.metadata
        ):
            regex_patterns: list[typing.Union[str, re.Pattern[str]]] = []
            for item in field.metadata:
                if (
                    isinstance(item, pydantic.StringConstraints)
                    and item.pattern is not None
                ):
                    regex_patterns.append(item.pattern)
            if len(regex_patterns) > 1:
                raise FieldConversionError(
                    f"Field has multiple regex patterns: {regex_patterns}"
                )
            elif len(regex_patterns) == 1:
                return serializers.RegexField(regex=regex_patterns[0], **kwargs)
        # Enum
        elif issubclass(type_, enum.Enum):
            return serializers.ChoiceField(
                choices=[item.value for item in type_], **kwargs
            )
        # Known mapped scalar field
        for key in getattr(type_, "__mro__", []):
            try:
                return FIELD_MAP[key](**kwargs)
            except KeyError:
                continue
        raise FieldConversionError(f"{type_.__name__} is not a supported scalar type.")

    # Composite field
    if type_.__origin__ is list:
        # Enforced by pydantic, check just in case
        assert len(type_.__args__) == 1
        return serializers.ListField(
            child=_convert_type(type_.__args__[0], drf_config=drf_config),
            allow_empty=True,
            **kwargs,
        )
    elif type_.__origin__ is tuple:
        if (
            len(type_.__args__) == 2
            and (is_scalar(type_.__args__[0]) and type_.__args__[1] is Ellipsis)
        ) or (type_.__args__[0] is Ellipsis and is_scalar(type_.__args__[1])):
            return serializers.ListField(
                child=_convert_type(type_.__args__[0], drf_config=drf_config),
                allow_empty=True,
                **kwargs,
            )
        elif (
            all(is_scalar(arg) for arg in type_.__args__)
            and len(set(type_.__args__)) == 1
        ):
            return serializers.ListField(
                child=_convert_type(type_.__args__[0], drf_config=drf_config),
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
            child=_convert_type(type_.__args__[1], drf_config=drf_config),
            allow_empty=True,
            **kwargs,
        )
    elif type_.__origin__ is typing.Literal:
        return serializers.ChoiceField(choices=type_.__args__, **kwargs)
    raise FieldConversionError(
        f"{type_.__origin__.__name__} is not a supported composite type."
    )
