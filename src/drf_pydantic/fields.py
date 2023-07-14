from enum import Enum
from typing import Type, Optional

from rest_framework.fields import empty
from rest_framework.serializers import ChoiceField


class EnumField(ChoiceField):
    """
    Custom DRF field that restricts accepted values to that of a defined enum
    """
    default_error_messages = {'invalid': 'No matching enum type'}

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
                self.fail('invalid')

        return super().run_validation(data)

    def to_internal_value(self, data):
        for choice in self.enum:
            if choice == data or choice.name == data or choice.value == data:
                return choice
        self.fail('invalid')
        # if data is None:
        #     return data
        #
        # if not isinstance(data, self.enum):
        #     try:
        #         data = self.enum(data)
        #     except ValueError:
        #         return None
        #
        # return data.value

    def to_representation(self, value):
        if isinstance(value, self.enum):
            return value.value

        return value
