from typing import TYPE_CHECKING, Any, Type, TypeVar

import pydantic

from rest_framework import serializers  # type: ignore

if TYPE_CHECKING:
    from drf_pydantic.base_model import BaseModel

T = TypeVar("T", bound=dict[str, Any])


class DrfPydanticSerializer(serializers.Serializer):
    _pydantic_model: "Type[BaseModel]"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore

    def validate(self, attrs: T) -> T:
        return_value = super().validate(attrs)  # type: ignore
        if self._pydantic_model.drf_config.get("validate_pydantic"):
            try:
                self._pydantic_model(**attrs)
            except pydantic.ValidationError as exc:
                if self._pydantic_model.drf_config.get("validation_error") == "drf":
                    raise serializers.ValidationError(exc) from exc
                assert (
                    self._pydantic_model.drf_config.get("validation_error")
                    == "pydantic"
                )
                raise exc
        return return_value
