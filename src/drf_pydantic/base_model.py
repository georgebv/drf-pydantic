from typing import Any, ClassVar, Literal, Optional, TypedDict

import pydantic

from pydantic._internal._model_construction import (
    ModelMetaclass as PydanticModelMetaclass,
)
from pydantic._internal._model_construction import (
    PydanticGenericMetadata,  # type: ignore
)
from typing_extensions import dataclass_transform

from drf_pydantic.base_serializer import DrfPydanticSerializer
from drf_pydantic.parse import create_serializer_from_model


@dataclass_transform(kw_only_default=True, field_specifiers=(pydantic.Field,))
class ModelMetaclass(PydanticModelMetaclass, type):
    def __new__(
        mcs,
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

        # Set drf_config by merging properties with the following priority:
        # 1. Pydanitc model itself (cls)
        # 2. Parent class of the pydantic model (cls)
        # 3. Default values
        drf_config = DrfConfigDict(validate_pydantic=False, validation_error="drf")
        for base in cls.__mro__[:2][::-1]:
            drf_config.update(getattr(base, "drf_config", DrfConfigDict()))
        setattr(cls, "drf_config", drf_config)

        return cls


class DrfConfigDict(TypedDict, total=False):
    validate_pydantic: bool
    """
    Whether to validate parent pydantic model on drf_serializer validation.

    By default is False.

    """
    validation_error: Literal["drf", "pydantic"]
    """
    What error to raise if pydantic model validation raises its ValidationError.

    By default 'drf'.

    """


class BaseModel(pydantic.BaseModel, metaclass=ModelMetaclass):
    # Populated by the metaclass or manually set by the user
    drf_serializer: ClassVar[type[DrfPydanticSerializer]]
    drf_config: ClassVar[DrfConfigDict]
