<p align="center">
  <a href="https://github.com/georgebv/drf-pydantic/actions/workflows/cicd.yml" target="_blank">
    <img src="https://github.com/georgebv/drf-pydantic/actions/workflows/cicd.yml/badge.svg?branch=main" alt="CI/CD Status">
  </a>
  <a href="https://codecov.io/gh/georgebv/drf-pydantic" target="_blank">
    <img src="https://codecov.io/gh/georgebv/drf-pydantic/branch/main/graph/badge.svg?token=GN9rxzIFMc" alt="Test Coverage"/>
  </a>
  <a href="https://badge.fury.io/py/drf-pydantic" target="_blank">
    <img src="https://badge.fury.io/py/drf-pydantic.svg" alt="PyPI version" height="18">
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
  - [Custom Base Models](#custom-base-models)
- [Roadmap](#roadmap)

# Introduction

[Pydantic](https://pydantic-docs.helpmanual.io) is a great Python library to perform
data serialization and validation.

[Django REST framework](https://www.django-rest-framework.org) is a framework built
on top of [Django](https://www.djangoproject.com/) which allows writing REST APIs.

If like me you develop DRF APIs and you like pydantic , `drf-pydantic` is for you 😍.

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

Whenever you need a DRF serializer you can get it from the model like this:

```python
MyModel.drf_serializer
```

> ℹ️ **INFO**<br>
> Models created using `drf_pydantic` are fully idenditcal to those created by
> `pydantic` and only the `drf_serializer` attribute is added on class creation.

## Custom Base Models

You can also use it as a mixin with your existing pydantic models (no need to change
your existing code 🥳):

```python
from drf_pydantic import BaseModel as DRFBaseModel
from pydantic import BaseModel

class MyBaseModel(BaseModel):
  value: int

class MyModel(DRFBaseModel, MyBaseModel):
  name: str
  addresses: list[str]
```

> ⚠️ **ATTENTION**<br>
> Inheritance order is important: `drf_pydantic.BaseModel` must always go before
> the `pydantic.BaseModel` class.

# Roadmap

- Add `ENUM` support
- Add option to create custom serializer for complex models
