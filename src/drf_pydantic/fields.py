from enum import Enum
from typing import Type, Optional

from rest_framework.fields import empty
from rest_framework.serializers import ChoiceField


class EnumField(ChoiceField):
    """
    Custom DRF field that restricts accepted values to that of a defined enum
    """

    def __init__(self, enum: Type[Enum], **kwargs):
        self.enum = enum
        kwargs.setdefault('choices', [(x, x.name) for x in self.enum])
        super().__init__(**kwargs)

    def run_validation(self, data=empty) -> Optional[Enum]:
        if data and data != empty and not isinstance(data, self.enum):
            match_found = False
            for x in self.enum:
                if x.value == data:
                    match_found = True
                    break

            if not match_found:
                self.fail('invalid_choice')

        return super().run_validation(data)

    def to_internal_value(self, data):
        if data is None:
            return data

        if not isinstance(data, self.enum):
            data = self.enum(data)

        return data.value

    def to_representation(self, value):
        if value is None:
            return value

        return self.enum(value)
