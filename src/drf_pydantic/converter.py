from typing import Any, Type

from pydantic.fields import ModelField
from rest_framework import serializers

from drf_pydantic.base_model import BaseModel


def convert_field(field: ModelField) -> serializers.Field:
    serializer_field = convert_raw_type(field.type_)
    if field.outer_type_ is list:
        serializer_field = serializer_field(many=True)


def convert_raw_type(field: Any) -> Type[serializers.Serializer]:
    if isinstance(field, BaseModel):
        return field.drf_serializer()
