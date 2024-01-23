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
- [Installation](#installation)
- [Usage](#usage)
  - [General](#general)
  - [Existing Models](#existing-models)
  - [Nested Models](#nested-models)
- [Roadmap](#roadmap)

# Introduction

[Pydantic](https://pydantic-docs.helpmanual.io) is a Python library used to perform
data serialization and validation.

[Django REST framework](https://www.django-rest-framework.org) is a framework built
on top of [Django](https://www.djangoproject.com/) used to write REST APIs.

If you develop DRF APIs and rely on pydantic for data validation/(de)serialization ,
then `drf-pydantic` is for you 😍.

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

# Roadmap

- Add support for custom field types (both for pydantic and DRF)
- Add option to create custom serializer for complex models
