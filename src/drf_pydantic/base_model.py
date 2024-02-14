from typing import Any, ClassVar, Optional

import pydantic

from pydantic._internal._model_construction import (
    ModelMetaclass as PydanticModelMetaclass,
)
from pydantic._internal._model_construction import PydanticGenericMetadata
from rest_framework import serializers
from typing_extensions import dataclass_transform

from drf_pydantic.parse import create_serializer_from_model


@dataclass_transform(kw_only_default=True, field_specifiers=(pydantic.Field,))
class ModelMetaclass(PydanticModelMetaclass, type):
    def __new__(
        mcs,  # noqa: N804
        cls_name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        __pydantic_generic_metadata__: Optional[PydanticGenericMetadata] = None,
        __pydantic_reset_parent_namespace__: bool = True,
        _create_model_module: Optional[str] = None,
        **kwargs: Any,
    ):
        cls = super().__new__(
            mcs,
            cls_name,
            bases,
            namespace,
            __pydantic_generic_metadata__,
            __pydantic_reset_parent_namespace__,
            _create_model_module,
            **kwargs,
        )
        # Create serializer only if it's not already set by the user
        # Serializer should never be inherited from the parent classes
        if not hasattr(cls, "drf_serializer") or getattr(cls, "drf_serializer") in (
            getattr(base, "drf_serializer", None) for base in cls.__mro__[1:]
        ):
            setattr(
                cls,
                "drf_serializer",
                create_serializer_from_model(cls),
            )
        return cls


class BaseModel(pydantic.BaseModel, metaclass=ModelMetaclass):
    # Populated by the metaclass or manually set by the user
    drf_serializer: ClassVar[type[serializers.Serializer]]
