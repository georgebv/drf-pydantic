from typing import Type

from pydantic import BaseModel as PydanticBaseModel
from rest_framework import serializers

from drf_pydantic.converter import convert_field


class BaseModel(PydanticBaseModel):
    @property
    def drf_serializer(self) -> Type[serializers.Serializer]:
        """
        Generate serializer compatible with Django REST framework.
        """
        fields: dict[str, serializers.Field] = {}
        for name, field in self.__fields__.items():
            fields[name] = convert_field(field)
