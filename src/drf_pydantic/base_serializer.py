import json

from typing import Any, ClassVar, Type, TypeVar

import pydantic

from rest_framework import serializers  # type: ignore
from rest_framework.settings import api_settings  # type: ignore

from drf_pydantic.config import DrfConfigDict

T = TypeVar("T", bound=dict[str, Any])


class DrfPydanticSerializer(serializers.Serializer):
    _pydantic_model: ClassVar[Type[pydantic.BaseModel]]
    _drf_config: ClassVar[DrfConfigDict]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore

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

            field_errors: dict[str, list[str]] = {}
            non_field_errors: list[str] = []
            for error in exc.errors():
                try:
                    message = json.dumps(
                        {
                            "loc": error["loc"],
                            "msg": error["msg"],
                            "type": error["type"],
                        }
                    )
                except:  # noqa pragma: no cover
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
                    return_value[key] = getattr(validated_pydantic_model, key)
                except AttributeError:  # pragma: no cover
                    continue

        return return_value
