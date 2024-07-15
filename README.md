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

If you develop DRF APIs and rely on pydantic for data validation/(de)serialization ,
then `drf-pydantic` is for you 😍.

> ℹ️ **INFO**<br> > `drf_pydantic` supports `pydantic` v2. Due to breaking API changes in `pydantic`
> v2 support for `pydantic` v1 is available only in `drf_pydantic` 1.\*.\*.

## Performance

Translation between `pydantic` models and `DRF` serializers is done during class
creation (e.g., when you first import the model). This means that there will be
zero impact on the performance of your application
(server instance or serverless session)
when using `drf_pydantic` while your application is running.

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

> ℹ️ **INFO**<br>
> Models created using `drf_pydantic` are fully idenditcal to those created by
> `pydantic`. The only change is the addition of the `drf_serializer` attribute.

## Existing Models

If you have an existing code base and you would like to add the `drf_serializer`
attribute only to some of your models, then I have great news 🥳 - you can easily
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

> ⚠️ **ATTENTION**<br>
> Inheritance order is important: `drf_pydantic.BaseModel` must always go before
> the `pydantic.BaseModel` class.

## Nested Models

If you have nested models and you want to generate serializer only from one of them,
you don't have to update all models - only update the model you need, `drf_pydantic`
will generate serializers for all normal nested `pydantic` models for free 🥷.

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

> ⚠️ **WARNING**<br>
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

Additional field properties are set according to the following mapping (`pydantic` -> `drf`):

- `description` -> `help_text`
- `title` -> `label`
- `StringConstraints` -> `min_length` and `max_length` attributes are set
- `pattern` -> uses special serializer field `RegexField`
- `max_digits` and `decimal_places` attributes are carried over as is
  (used for `Decimal` type). By default uses current decimal context precision.
- `ge` / `gt` -> `min_value`
- `le` / `lt` -> `max_value`
