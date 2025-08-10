import inspect
import warnings

from typing import Any, ClassVar, Dict, Optional, Tuple, Type, cast

import pydantic

from pydantic._internal._model_construction import (
    ModelMetaclass as PydanticModelMetaclass,
)
from pydantic._internal._model_construction import (
    PydanticGenericMetadata,  # type: ignore
)
from rest_framework import serializers  # type: ignore
from typing_extensions import Self, dataclass_transform

from drf_pydantic.base_serializer import DrfPydanticSerializer
from drf_pydantic.config import DrfConfigDict
from drf_pydantic.parse import create_serializer_from_model
from drf_pydantic.utils import get_attr_owner


@dataclass_transform(kw_only_default=True, field_specifiers=(pydantic.Field,))
class ModelMetaclass(PydanticModelMetaclass, type):
    def __new__(
        mcs,
        cls_name: str,
        bases: Tuple[Type[Any], ...],
        namespace: Dict[str, Any],
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

        # Set drf_config by merging properties with the following priority:
        # 1. Pydanitc model itself (cls)
        # 2. Parent class of the pydantic model (cls)
        # 3. Default values
        drf_config = DrfConfigDict(
            validate_pydantic=False,
            validation_error="drf",
            backpopulate_after_validation=True,
        )
        for base in cls.__mro__[:2][::-1]:
            drf_config.update(getattr(base, "drf_config", DrfConfigDict()))
        setattr(cls, "drf_config", drf_config)

        # Serializer was set by the user (is already present and is not inherited)
        if hasattr(cls, "drf_serializer") and cls is get_attr_owner(
            cls, "drf_serializer"
        ):
            drf_serializer = getattr(cls, "drf_serializer")
            if not inspect.isclass(drf_serializer):
                raise TypeError(
                    f"drf_serializer must be a class, check class {cls.__name__}"
                )
            if not issubclass(drf_serializer, serializers.Serializer):
                raise TypeError(
                    f"{drf_serializer.__name__} is not a valid type "
                    f"for drf_serializer. Check class {cls.__name__}"
                )
            if not issubclass(drf_serializer, DrfPydanticSerializer):
                warnings.warn(
                    (
                        f"custom drf_serializer on model {cls.__name__} "
                        f"should be replaced with an instace of "
                        f"drf_pydantic.DrfPydanticSerializer "
                        f"(currently is {drf_serializer.__name__})"
                    ),
                    UserWarning,
                )
            drf_serializer = cast(Type[DrfPydanticSerializer[Any]], drf_serializer)
            if getattr(drf_serializer, "_pydantic_model", cls) is not cls:
                warnings.warn(
                    (
                        f"_pydantic_model on model {cls.__name__} doesn't match "
                        f"expected class {cls.__name__}: "
                        f"{getattr(drf_serializer, '_pydantic_model').__name__}"
                    ),
                    UserWarning,
                )
            setattr(drf_serializer, "_pydantic_model", cls)
            if not hasattr(drf_serializer, "_drf_config"):
                setattr(drf_serializer, "_drf_config", drf_config)
        # Serializer not declared on cls directly (missing or inherited)
        else:
            setattr(
                cls,
                "drf_serializer",
                create_serializer_from_model(cls, drf_config),
            )

        return cls


class BaseModel(pydantic.BaseModel, metaclass=ModelMetaclass):
    # Populated by the metaclass or manually set by the user
    drf_serializer: ClassVar[Type[DrfPydanticSerializer[Self]]]
    drf_config: ClassVar[DrfConfigDict]
