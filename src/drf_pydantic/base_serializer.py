import inspect
import json
import warnings

from typing import Any, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import pydantic

from rest_framework import serializers  # type: ignore
from rest_framework.settings import api_settings  # type: ignore

from drf_pydantic.config import DrfConfigDict

# `by_name` was added to `model_validate` in pydantic 2.11
_MODEL_VALIDATE_SUPPORTS_BY_NAME = (
    "by_name" in inspect.signature(pydantic.BaseModel.model_validate).parameters
)

T = TypeVar("T", bound=Dict[str, Any])
P = TypeVar("P", bound=pydantic.BaseModel)


def _dump_nested_models(value: Any) -> Any:
    """Convert pydantic models to dicts, including inside lists/tuples/dicts.

    A container is rebuilt only when one of its items changed, so containers
    without models keep their original type (NamedTuple, OrderedDict, ...).
    A NamedTuple that does hold models is rebuilt as the same NamedTuple.
    """
    dumped: Any
    if isinstance(value, pydantic.BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        dumped = {key: _dump_nested_models(item) for key, item in value.items()}
        changed = any(dumped[key] is not item for key, item in value.items())
    elif isinstance(value, (list, tuple)):
        dumped = [_dump_nested_models(item) for item in value]
        changed = any(new is not old for new, old in zip(dumped, value))
        if changed and isinstance(value, tuple):
            if hasattr(value, "_fields"):
                dumped = type(value)._make(dumped)  # type: ignore[attr-defined]
            else:
                dumped = tuple(dumped)
    else:
        return value
    return dumped if changed else value


class DrfPydanticSerializer(serializers.Serializer, Generic[P]):
    _pydantic_model: Type[P]
    _drf_config: ClassVar[DrfConfigDict]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.__pydantic_instance: Optional[P] = None

    @property
    def pydantic_instance(self) -> P:
        if not self._drf_config.get("validate_pydantic"):
            raise AssertionError(
                "You must enable pydantic validation with `validate_pydantic` "
                "before accessing `.pydantic_instance`."
            )
        if self.__pydantic_instance is None:
            raise AssertionError(
                "You must call `.is_valid()` before accessing `.pydantic_instance`."
            )
        return self.__pydantic_instance

    def validate(self, attrs: T) -> T:
        return_value = super().validate(attrs)  # type: ignore
        if not self._drf_config.get("validate_pydantic"):
            return return_value

        try:
            if _MODEL_VALIDATE_SUPPORTS_BY_NAME:
                # DRF field names are pydantic field names, not aliases
                validated_pydantic_model = self._pydantic_model.model_validate(
                    attrs, by_name=True
                )
            else:  # pragma: no cover
                validated_pydantic_model = self._pydantic_model(**attrs)
        except pydantic.ValidationError as exc:
            if self._drf_config.get("validation_error") == "pydantic":
                raise exc
            assert self._drf_config.get("validation_error") == "drf"

            field_errors: Dict[str, List[str]] = {}
            non_field_errors: List[str] = []
            for error in exc.errors():
                try:
                    message = json.dumps(
                        {
                            "loc": error["loc"],
                            "msg": error["msg"],
                            "type": error["type"],
                        }
                    )
                except Exception:  # pragma: no cover
                    message = f"{error['msg']} (type={error['type']})"
                if (
                    len(error["loc"]) == 0
                    or not isinstance(error["loc"][0], str)
                    or error["loc"][0] not in self.fields
                ):
                    non_field_errors.append(message)
                else:
                    field_errors.setdefault(error["loc"][0], []).append(message)

            raise serializers.ValidationError(
                {
                    getattr(
                        api_settings,
                        "NON_FIELD_ERRORS_KEY",
                        "non_field_errors",
                    ): non_field_errors,
                    **field_errors,
                }
            ) from exc

        if self._drf_config.get("backpopulate_after_validation"):
            for key in return_value:
                try:
                    pydantic_value = getattr(validated_pydantic_model, key)
                    return_value[key] = _dump_nested_models(pydantic_value)
                except AttributeError:  # pragma: no cover
                    warnings.warn(
                        f"Failed to set attribute `{key}` when validating instance "
                        f"of type `{self._pydantic_model.__name__}`"
                    )
                    continue

        self.__pydantic_instance = validated_pydantic_model

        return return_value
