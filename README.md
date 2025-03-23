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
creation (e.g., when you first import the model). This means that there will be
zero runtime impact when using `drf_pydantic` while your application is running.

# Installation

```shell
pip install drf-pydantic
```

# Usage

## General

Use `drf_pydantic.BaseModel` instead of `pydantic.BaseModel` when creating your
models:

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]
```

`MyModel.drf_serializer` would be equvalent to the following DRF Serializer class:

```python
class MyModelSerializer:
    name = CharField(allow_null=False, required=True)
    addresses = ListField(
        allow_empty=True,
        allow_null=False,
        child=CharField(allow_null=False),
        required=True,
    )
```

Whenever you need a DRF serializer you can get it from the model like this:

```python
my_value = MyModel.drf_serializer(data={"name": "Van", addresses: ["Gym"]})
my_value.is_valid(raise_exception=True)
```

> [!NOTE]
> Models created using `drf_pydantic` are fully idenditcal to those created by
> `pydantic`. The only change is the addition of the `drf_serializer`
> and `drf_config` attributes.

## Pydantic Validation

By default the generated serializer only uses DRF's validation; however, pydantic
models are often more complex and their numerous validation rules cannot be properly
translated to DRF. To enable pydantic validators to be run whenever the generated
DRF serializer validates its data (e.g., `.is_valid()`),
set `"validate_pydantic": True` within `drf_config` property of your model:

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    addresses: list[str]

    drf_config = {"validate_pydantic": True}


my_serializer = MyModel.drf_serializer(data={"name": "Van", "addresses": []})
my_serializer.is_valid()  # this will also validate MyModel
```

With this option enabled, any time validate data using your DRF serializer
its parent pydantic model will be validated too and, if it fails, its
`ValidationError` exception will be wrapped within DRF's `ValidationError`.
Per-field and per-object (non-field) errors will be appropriately wrapped in the same
way how DRF does it during its own validation.
This way your arbitrarily complex validation logic from your pydantic model
will be properly evaluated anywhere a DRF serializer is validated and your views
using DRF models generated by `drf_pydantic` will reap all benefits of pydantic.

> [!NOTE]
> All `drf_config` values are properly inherited by child classes, same way as
> pydantic's `model_config`.

### Updating Field Values

By default `drf_pydantic` will update values in the DRF serializer from the validated
pydantic model:

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
print(my_serializer.data)  # {"name": "Van Herrington", "addresses": []}
```

This is very useful when you dynamically modify field values within your
pydantic validators. You can disable this behavior by setting
`"backpopulate_after_validation": False`:

```python
class MyModel(BaseModel):
    ...

    drf_config = {"validate_pydantic": True, "backpopulate_after_validation": False}
```

### Validation Errors

By default pydantic's `ValidationError` is wrapped within DRF's `ValidationError`.
If you want to raise the pydantic's `ValidationError` directly, you should
set `"validation_error": "pydantic"` within `drf_config` property of your model:

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
> When a model would be invalid from both DRF's and pydantic's perspectives and
> and exceptions are enabled (`.is_valid(raise_exception=True)`),
> DRF's `ValueError` will be raised regardless of what `validation_error` is set to
> because DRF validation always runs first.

> [!CAUTION]
> Setting `validation_error` to `pydantic` will have several side effects:
>
> 1. It will break your views because they will no longer be able to
>    intelligently handle DRF's `ValidationError`.
> 2. Calling `.is_valid()` will always raise `pydantic.ValidationError` if the data
>    is invalid, even without setting `.is_valid(raise_exception=True)`.

## Existing Models

If you have an existing code base and you would like to add the `drf_serializer`
attribute only to some of your models, then I have great news - you can easily
extend your existing `pydantic` models by adding `drf_pydantic.BaseModel` to the list
of parent classes of the model you want to extend.

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
> Inheritance order is important: `drf_pydantic.BaseModel` must always go before
> the `pydantic.BaseModel` class.

## Nested Models

If you have nested models and you want to generate serializer only from one of them,
you don't have to update all models - only update the model you need, `drf_pydantic`
will generate serializers for all normal nested `pydantic` models for free!

```python
from drf_pydantic import BaseModel as DRFBaseModel
from pydantic import BaseModel

class Apartment(BaseModel):
    floor: int
    tenant: str

class Building(BaseModel):
    address: str
    aparments: list[Apartment]

class Block(DRFBaseModel):
    buildings: list[Buildind]

Block.drf_serializer
```

## Manual Serializer Configuration

If `drf_pydantic` does not generate the serializer you need, you can either granularly
configure which DRF serializer fields to use for each pydantic field, or you can
create a custom serializer for the model altogether.

> [!IMPORTANT]
> When manually configuring the serializer you are responsible for setting all
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

In example below, `Person` will use `MyCustomSerializer` as its drf serializer.
`Employee` will have its own serializer generated by `drf_pydantic` because it
does not have a user-defined `drf_serializer` attribute (it's never inherited).
`Company` will have its own serializer generated by `drf_pydantic` and it will use
`Person`'s manually-defined serializer for its `ceo` field.

```python
from drf_pydantic import BaseModel
from rest_framework.serializers import Serializer


class MyCustomSerializer(Serializer):
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

# Additional Properties

Additional field properties are set according
to the following mapping (`pydantic` -> `drf`):

- `description` -> `help_text`
- `title` -> `label`
- `StringConstraints` -> `min_length` and `max_length` attributes are set
- `pattern` -> uses special serializer field `RegexField`
- `max_digits` and `decimal_places` attributes are carried over as is
  (used for `Decimal` type). By default uses current decimal context precision.
- `ge` / `gt` -> `min_value`
- `le` / `lt` -> `max_value`
