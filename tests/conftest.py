import pytest

from drf_pydantic.parse import SERIALIZER_REGISTRY


@pytest.fixture(autouse=True, scope="function")
def reset_serializers():
    SERIALIZER_REGISTRY.clear()
    assert len(SERIALIZER_REGISTRY) == 0
