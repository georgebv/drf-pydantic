<p align="center">
  <a href="https://github.com/georgebv/drf-pydantic/actions/workflows/test.yml" target="_blank">
    <img src="https://github.com/georgebv/drf-pydantic/actions/workflows/test.yml/badge.svg?event=pull_request" alt="Test Status">
  </a>
  <a href="https://codecov.io/gh/georgebv/drf-pydantic" target="_blank">
    <img src="https://codecov.io/gh/georgebv/drf-pydantic/branch/main/graph/badge.svg?token=GN9rxzIFMc" alt="Test Coverage"/>
  </a>
  <a href="https://badge.fury.io/py/drf-pydantic" target="_blank">
    <img src="https://badge.fury.io/py/drf-pydantic.svg" alt="PyPI version" height="20">
  </a>
</p>

<p align="center">
  <i>
    Use pydantic with Django REST framework
  </i>
</p>

- [Introduction](#introduction)
  - [Performance](#performance)
- [Installation](#installation)
- [Usage](#usage)
  - [General](#general)
  - [Pydantic Validation](#pydantic-validation)
    - [Updating Field Values](#updating-field-values)
    - [Validation Errors](#validation-errors)
    - [Accessing the Validated Pydantic Instance](#accessing-the-validated-pydantic-instance)
  - [Existing Models](#existing-models)
  - [Nested Models](#nested-models)
  - [Manual Serializer Configuration](#manual-serializer-configuration)
    - [Per-Field Configuration](#per-field-configuration)
    - [Custom Serializer](#custom-serializer)
- [Additional Properties](#additional-properties)

# Introduction

[Pydantic](https://pydantic-docs.helpmanual.io) is a Python library used to perform
data serialization and validation.

[Django REST framework](https://www.django-rest-framework.org) is a framework built
on top of [Django](https://www.djangoproject.com/) used to write REST APIs.

If you develop DRF APIs and rely on pydantic for data validation/(de)serialization,
then `drf-pydantic` is for you :heart_eyes:.

> [!NOTE]
> The latest version of `drf_pydantic` only supports `pydantic` v2.
> Support for `pydantic` v1 is available in the `1.*` version.

## Performance

Translation between `pydantic` models and `DRF` serializers is done during class
creation (e.g., when you first import the model). This means there will be
zero runtime impact when using `drf_pydantic` in your application.

> [!NOTE]
> There will be a minor penalty if `validate_pydantic` is set to `True` due to pydantic
> model validation. This is minimal compared to an already-present overhead of DRF
> itself because pydantic runs its validation in rust while DRF is pure python.

# Installation

```shell
pip install drf-pydantic
```

# Usage

## General

Use `drf_pydantic.BaseModel` instead of `pydantic.BaseModel` when creating your models:

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]
```

`MyModel.drf_serializer` is equivalent to the following DRF Serializer class:

```python
class MyModelSerializer:
    name = CharField(allow_null=False, required=True, allow_blank=True)
    addresses = ListField(
        allow_empty=True,
        allow_null=False,
        child=CharField(allow_null=False, allow_blank=True),
        required=True,
    )
```

Whenever you need a DRF serializer, you can get it from the model like this:

```python
my_value = MyModel.drf_serializer(data={"name": "Van", "addresses": ["Gym"]})
my_value.is_valid(raise_exception=True)
```

> [!NOTE]
> Models created using `drf_pydantic` are fully identical to those created by
> `pydantic`. The only change is the addition of the `drf_serializer`
> and `drf_config` attributes.

## Pydantic Validation

By default, the generated serializer only uses DRF's validation; however, pydantic
models are often more complex and their numerous validation rules cannot be fully
translated to DRF. To enable pydantic validators to run whenever the generated
DRF serializer validates its data (e.g., via `.is_valid()`),
set `"validate_pydantic": True` within the `drf_config` property of your model:

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]

    drf_config = {"validate_pydantic": True}


my_serializer = MyModel.drf_serializer(data={"name": "Van", "addresses": []})
my_serializer.is_valid()  # this will also validate MyModel
```

With this option enabled, every time you validate data using your DRF serializer,
the parent pydantic model is also validated. If it fails, its
`ValidationError` exception will be wrapped within DRF's `ValidationError`.
Per-field and non-field (object-level) errors are wrapped
similarly to how DRF handles them. This ensures your complex pydantic validation logic
is properly evaluated wherever a DRF serializer is used.

> [!NOTE]
> All `drf_config` values are properly inherited by child classes,
> just like pydantic's `model_config`.

### Updating Field Values

By default, `drf_pydantic` updates values in the DRF serializer
with those from the validated pydantic model:

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]

    @pydantic.field_validator("name")
    @classmethod
    def validate_name(cls, v):
        assert isinstance(v, str)
        return v.strip().title()

    drf_config = {"validate_pydantic": True}


my_serializer = MyModel.drf_serializer(data={"name": "van herrington", "addresses": []})
my_serializer.is_valid()
print(my_serializer.validated_data)  # {"name": "Van Herrington", "addresses": []}
```

This is handy when you dynamically modify field values within your
pydantic validators. You can disable this behavior by setting
`"backpopulate_after_validation": False`:

```python
class MyModel(BaseModel):
    ...

    drf_config = {"validate_pydantic": True, "backpopulate_after_validation": False}
```

### Validation Errors

By default, pydantic's `ValidationError` is wrapped within DRF's `ValidationError`.
If you want to raise pydantic's `ValidationError` directly,
set `"validation_error": "pydantic"` in the `drf_config` property of your model:

```python
import pydantic

from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]

    @pydantic.field_validator("name")
    @classmethod
    def validate_name(cls, v):
        assert isinstance(v, str)
        if v != "Billy":
            raise ValueError("Wrong door")
        return v

    drf_config = {"validate_pydantic": True, "validation_error": "pydantic"}


my_serializer = MyModel.drf_serializer(data={"name": "Van", "addresses": []})
my_serializer.is_valid()  # this will raise pydantic.ValidationError
```

> [!NOTE]
> When a model is invalid from both DRF's and pydantic's perspectives and
> exceptions are enabled (`.is_valid(raise_exception=True)`),
> DRF's `ValidationError` will be raised regardless of the `validation_error` setting,
> because DRF validation always runs first.

> [!CAUTION]
> Setting `validation_error` to `pydantic` has side effects:
>
> 1. It may break your views because they expect DRF's `ValidationError`.
> 2. Calling `.is_valid()` will always raise `pydantic.ValidationError` if the data
>    is invalid, even without setting `.is_valid(raise_exception=True)`.

### Accessing the Validated Pydantic Instance

When `validate_pydantic` is enabled and `.is_valid()` has been called successfully,
the generated serializer exposes the fully validated Pydantic model instance via the
`pydantic_instance` property:

```python
serializer = MyModel.drf_serializer(data={"name": "Van", "addresses": []})
serializer.is_valid(raise_exception=True)
print(serializer.pydantic_instance)  # MyModel(name='Van', addresses=[])
```

This lets you work directly with your original Pydantic model (including any
mutations applied in validators) instead of DRF’s `validated_data` dictionary.

> [!WARNING]
>
> - Accessing `pydantic_instance` before calling `.is_valid()` will raise an error.
> - If `validate_pydantic` is disabled, accessing it will also raise an error.

## Existing Models

If you have an existing code base and want to add the `drf_serializer`
attribute only to some of your models, you can extend your existing pydantic models
by adding `drf_pydantic.BaseModel` as a parent class to the models you want to extend.

Your existing pydantic models:

```python
from pydantic import BaseModel

class Pet(BaseModel):
    name: str

class Dog(Pet):
    breed: str
```

Update your `Dog` model and get serializer via the `drf_serializer`:

```python
from drf_pydantic import BaseModel as DRFBaseModel
from pydantic import BaseModel

class Pet(BaseModel):
    name: str

class Dog(DRFBaseModel, Pet):
    breed: str

Dog.drf_serializer
```

> [!IMPORTANT]
> Inheritance order is important: `drf_pydantic.BaseModel` must always come before
> `pydantic.BaseModel`.

## Nested Models

If you have nested models and want to generate a serializer for only one of them,
you don't need to update all models. Simply update the model you need,
and `drf_pydantic` will automatically generate serializers
for all standard nested pydantic models:

```python
from drf_pydantic import BaseModel as DRFBaseModel
from pydantic import BaseModel

class Apartment(BaseModel):
    floor: int
    tenant: str

class Building(BaseModel):
    address: str
    apartments: list[Apartment]

class Block(DRFBaseModel):
    buildings: list[Building]

Block.drf_serializer
```

## Manual Serializer Configuration

If `drf_pydantic` doesn't generate the serializer you need,
you can configure the DRF serializer fields for each pydantic field manually,
or create a custom serializer for the model altogether.

> [!IMPORTANT]
> When manually configuring the serializer, you are responsible for setting all
> properties of the fields (e.g., `allow_null`, `required`, `default`, etc.).
> `drf_pydantic` does not perform any introspection for fields that are manually
> configured or for any fields if a custom serializer is used.

### Per-Field Configuration

```python
from typing import Annotated

from drf_pydantic import BaseModel
from rest_framework.serializers import IntegerField


class Person(BaseModel):
    name: str
    age: Annotated[float, IntegerField(min_value=0, max_value=100)]
```

### Custom Serializer

In the example below, `Person` will use `MyCustomSerializer` as its DRF serializer.
`Employee` will have its own serializer generated by `drf_pydantic` since it doesn't
inherit a user-defined `drf_serializer` attribute.
`Company` will use `Person`'s manually defined serializer for its `ceo` field.

```python
from drf_pydantic import BaseModel, DrfPydanticSerializer
from rest_framework.serializers import CharField, IntegerField


class MyCustomSerializer(DrfPydanticSerializer):
    name = CharField(allow_null=False, required=True)
    age = IntegerField(allow_null=False, required=True)


class Person(BaseModel):
    name: str
    age: float

    drf_serializer = MyCustomSerializer


class Employee(Person):
    salary: float


class Company(BaseModel):
    ceo: Person
```

> [!IMPORTANT]
> Added in version `v2.6.0`
>
> Manual `drf_serializer` must have base class of `DrfPydanticSerializer`
> in order for [Pydantic Validation](#pydantic-validation) to work properly.
> You can still use standard `Serializer` from `rest_framework`, but automatic
> pydantic model validation will not work consistently and you will get a warning.

# Additional Properties

Additional field properties are mapped as follows (`pydantic` -> `DRF`):

- `description` -> `help_text`
- `title` -> `label`
- `StringConstraints` -> `min_length` and `max_length` and `allow_blank`
- `pattern` -> Uses the specialized `RegexField` serializer field
- `max_digits` and `decimal_places` are carried over
  (used for `Decimal` types, with the current decimal context precision)
- `ge` / `gt` -> `min_value` (only for numeric types)
- `le` / `lt` -> `max_value` (only for numeric types)
