from enum import Enum
from types import NoneType
from typing import Any, List, Type, Optional, Union

from rest_framework.fields import empty
from rest_framework.serializers import ChoiceField, Field


class EnumField(ChoiceField):
    """
    Custom DRF field that restricts accepted values to that of a defined enum
    """

    default_error_messages = {"invalid": "No matching enum type"}

    def __init__(self, enum: Type[Enum], **kwargs):
        self.enum = enum
        kwargs.setdefault("choices", [(x, x.name) for x in self.enum])
        super().__init__(**kwargs)

    def run_validation(
        self, data: Optional[Union[Enum, str, empty]] = empty
    ) -> Optional[Enum]:
        if data and data != empty and not isinstance(data, self.enum):
            match_found = False
            for x in self.enum:
                if x.value == data:
                    match_found = True
                    break

            if not match_found:
                self.fail("invalid")

        return super().run_validation(data)

    def to_internal_value(self, data: Optional[Union[Enum, str]]) -> Enum:
        for choice in self.enum:
            if choice == data or choice.name == data or choice.value == data:
                return choice
        self.fail("invalid")

    def to_representation(self, value: Optional[Union[Enum, str]]) -> Optional[str]:
        if isinstance(value, self.enum):
            return value.value

        return value


#: Define shortcut for scalar types
ScalarTypes = int | float | str | bool | NoneType


class UnionField(Field):
    """
    Custom DRF field that supports union fields of scalar values.
    """

    default_error_messages = {"invalid": "No match in type union"}

    #: The allowed types
    types: List[type]

    def __init__(self,
                 types: List[type],
                 **kwargs):
        super().__init__(**kwargs)
        self._check_all_types_scalar(types)
        self.types = types
        self.allow_null = NoneType in types

    def _check_all_types_scalar(self, types: List[type]):
        for type_ in types:
            if not any(type_ is t for t in (int, float, str, bool, NoneType)):
                raise ValueError(f"UnionField only supports scalar types but found: {type_}")

    def run_validation(self, data: Any) -> ScalarTypes:
        if type(data) not in self.types:
            self.fail("invalid")
        return super().run_validation(data)

    def to_internal_value(self, data: Any) -> ScalarTypes:
        if type(data) in self.types:
            return data
        self.fail("invalid")

    def to_representation(self, data: Any) -> ScalarTypes:
        if type(data) in self.types:
            return data
        self.fail("invalid")
