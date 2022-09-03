import typing

import pydantic

from rest_framework import serializers

from drf_pydantic.parse import create_serializer_from_model


class ModelMetaclass(pydantic.main.ModelMetaclass, type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "drf_serializer", create_serializer_from_model(cls))
        return cls


class BaseModel(pydantic.BaseModel, metaclass=ModelMetaclass):
    if typing.TYPE_CHECKING:
        # populated by the metaclass, defined here to help IDEs only
        drf_serializer: type[serializers.Serializer]
