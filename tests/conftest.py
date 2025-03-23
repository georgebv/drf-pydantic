import django
import pytest

from django.conf import settings

from drf_pydantic.parse import SERIALIZER_REGISTRY


@pytest.fixture(autouse=True, scope="function")
def reset_serializer_registry():
    """Purge cached serializers."""
    SERIALIZER_REGISTRY.clear()
    assert len(SERIALIZER_REGISTRY) == 0


@pytest.fixture(autouse=True, scope="session")
def django_setup():
    """Required to run serializer.is_valid()"""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="fake-key",  # noqa
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "rest_framework",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            MIDDLEWARE=[],
        )
    django.setup()
