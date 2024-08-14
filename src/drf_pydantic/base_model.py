from typing import Any, ClassVar, Optional

import pydantic

from pydantic._internal._model_construction import (
    ModelMetaclass as PydanticModelMetaclass,
)
from pydantic._internal._model_construction import PydanticGenericMetadata
from rest_framework import serializers
from typing_extensions import dataclass_transform

from drf_pydantic.parse import SERIALIZER_REGISTRY, create_serializer_from_model


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

    @classmethod
    def model_rebuild(
        cls,
        *,
        force: bool = False,
        raise_errors: bool = True,
        _parent_namespace_depth: int = 2,
        _types_namespace: Optional[dict[str, Any]] = None,
    ) -> bool | None:
        ret = super().model_rebuild(
            force=force,
            raise_errors=raise_errors,
            _parent_namespace_depth=_parent_namespace_depth,
            _types_namespace=_types_namespace,
        )

        if cls in SERIALIZER_REGISTRY:
            SERIALIZER_REGISTRY.pop(cls)
            cls.drf_serializer = create_serializer_from_model(cls)

        return ret
