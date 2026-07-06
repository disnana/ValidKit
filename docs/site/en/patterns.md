# Practical Patterns

## Class Schemas

Schemas can be written as classes. Type annotations become basic validators, and validator attributes add explicit constraints.

```python
from dataclasses import dataclass
from validkit import compile, v

@dataclass
class User:
    name: str
    age: int = v.int().range(0, 150)
    active: bool = True

schema = compile(User)
user = schema.validate({"name": "Alice", "age": 30})

assert isinstance(user, User)
```

With `partial=True`, ValidKit returns a dict because the constructor may not have enough required values.

## Using ValidKit with Pydantic

ValidKit is useful for fast boundary validation, configuration files, and plugin settings. In applications that already use Pydantic, ValidKit can validate incoming shapes first and Pydantic can still own the domain model.

```python
from pydantic import BaseModel
from validkit import compile, v

class UserModel(BaseModel):
    name: str
    age: int

incoming = compile({
    "name": v.str().min(3),
    "age": v.int().range(0, 150),
})

data = incoming.validate(payload)
user = UserModel(**data)
```

You can also validate Pydantic output before sending it to an external API.

## Custom Types

Use `v.instance(...)` when a field should accept an existing Python type.

```python
from pathlib import Path
from validkit import validate, v

schema = {"output": v.instance(Path)}
result = validate({"output": Path("dist")}, schema)
```

Use `.custom(...)` when validation should transform a value.

```python
from uuid import UUID
from validkit import validate, v

schema = {
    "id": v.str().custom(UUID),
}

result = validate({"id": "6f9619ff-8b86-d011-b42d-00cf4fc964ff"}, schema)
assert isinstance(result["id"], UUID)
```

`.custom(...)` and `v.instance(...)` run on the Python path because they execute Python objects or arbitrary functions.
