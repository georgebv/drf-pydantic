<p align="center">
  <a href="https://github.com/georgebv/drf-pydantic/actions/workflows/cicd.yml" target="_blank">
    <img src="https://github.com/georgebv/drf-pydantic/actions/workflows/cicd.yml/badge.svg?branch=main" alt="CI/CD Status">
  </a>
  <a href="https://codecov.io/gh/georgebv/drf-pydantic" target="_blank">
    <img src="https://codecov.io/gh/georgebv/drf-pydantic/branch/main/graph/badge.svg?token=GN9rxzIFMc" alt="Test Coverage"/>
  </a>
</p>

Use pydantic with the Django REST framework

# Installation

```shell
pip install drf-pydantic
```

# Usage

```python
from drf_pydantic import BaseModel

class MyModel(BaseModel):
  name: str
  addresses: list[str]

serializer = MyModel.drf_serializer

```
