import datetime
import typing

import pydantic

from rest_framework import serializers

from drf_pydantic import BaseModel
from drf_pydantic.test_utils import compare_serializers


class TestSuccesses:
    def test_model_with_scalar_fields(self):
        class User(BaseModel):
            username: str
            password: str
            age: int
            email: pydantic.EmailStr
            address: typing.Optional[str]
            birthdate: datetime.date

        class UserSerializer(serializers.Serializer):
            username = serializers.CharField()
            password = serializers.CharField()
            age = serializers.IntegerField()
            email = serializers.EmailField()
            address = serializers.CharField(
                allow_null=True, default=None, required=False
            )
            birthdate = serializers.DateField()

        assert compare_serializers(User.drf_serializer(), UserSerializer())

    def test_model_with_literal_field(self):
        class User(BaseModel):
            role: typing.Literal["admin", "developer", "user"]

        class UserSerializer(serializers.Serializer):
            role = serializers.ChoiceField(choices=["admin", "developer", "user"])

        assert compare_serializers(User.drf_serializer(), UserSerializer())

    def test_model_with_list_field(self):
        class User(BaseModel):
            addresses: list[str]

        class UserSerializer(serializers.Serializer):
            addresses = serializers.ListField(child=serializers.CharField())

        assert compare_serializers(User.drf_serializer(), UserSerializer())


class TestFailures:
    def test_model_with_scalar_fields(self):
        class User(BaseModel):
            username: str

        class UserSerializer(serializers.Serializer):
            username = serializers.IntegerField()

        assert not compare_serializers(User.drf_serializer(), UserSerializer())

    def test_model_with_literal_field(self):
        class User(BaseModel):
            role: typing.Literal["admin", "developer", "user"]

        class UserSerializer(serializers.Serializer):
            role = serializers.ChoiceField(choices=["admin", "developer", "boss"])

        assert not compare_serializers(User.drf_serializer(), UserSerializer())

    def test_model_with_list_field(self):
        class User(BaseModel):
            addresses: list[str]

        class UserSerializer(serializers.Serializer):
            addresses = serializers.ListField(child=serializers.IntegerField())

        assert not compare_serializers(User.drf_serializer(), UserSerializer())
