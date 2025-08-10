import json
import warnings

from typing import Any, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import pydantic

from rest_framework import serializers  # type: ignore
from rest_framework.settings import api_settings  # type: ignore

from drf_pydantic.config import DrfConfigDict

T = TypeVar("T", bound=Dict[str, Any])
P = TypeVar("P", bound=pydantic.BaseModel)


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
                    if isinstance(pydantic_value, pydantic.BaseModel):
                        pydantic_value = pydantic_value.model_dump()
                    return_value[key] = pydantic_value
                except AttributeError:  # pragma: no cover
                    warnings.warn(
                        f"Failed to set attribute `{key}` when validating instance "
                        f"of type `{self._pydantic_model.__name__}`"
                    )
                    continue

        self.__pydantic_instance = validated_pydantic_model

        return return_value
