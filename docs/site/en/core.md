# Native Core

ValidKit works without native dependencies. If `validkit-py-core` is installed, supported `compile(...).validate(...)` paths and some `collect_errors=True` validations use the Rust/PyO3 native core.

```bash
pip install validkit-py validkit-py-core
```

```python
from validkit import compile, v

schema = compile({
    "user": {
        "id": v.int(),
        "profile": {
            "name": v.str().min(3),
            "tags": v.list(v.str().min(2)),
        },
    },
    "metrics": v.dict(str, v.list(v.int().range(0, 1000))),
})

validated = schema.validate(payload)
```

## When It Runs

The native runtime is detected once at startup. If it is not available, ValidKit uses the Python implementation automatically.

Supported shapes:

- dict schemas
- `v.str()`, `v.int()`, `v.float()`, `v.bool()`
- `v.list(...)`
- `v.dict(str, ...)`
- numeric `min` / `max` / `range`, including exclusive bounds
- string length `min` / `max`
- list length `min` / `max` / `length`

Fallback cases:

- `partial`, `base`, `migrate`
- `.optional()`, `.default()`, `.coerce()`, `.custom()`, `.when()`, `.env()`, `.regex()`
- tuple inputs that must be converted to lists
- unknown keys that must be removed from the output

## Performance Policy

The core is optional, so when it is installed the native path prioritizes speed. If a successful validation does not need to reshape the output, it returns the validated input object directly and avoids extra copies.

```python
schema = compile({"tags": v.list(v.str())})
data = {"tags": ["fast", "path"]}

assert schema.validate(data) is data  # when the native core is active
```

With `collect_errors=True`, ValidKit returns a `ValidationResult`, but `ErrorDetail` objects are created only when `result.errors` is accessed. Call paths that only need to carry the result forward avoid paying for detailed Python error objects.

```python
result = schema.validate(data, collect_errors=True)

if result.has_errors:
    for error in result.errors:
        print(error.path, error.message)
```

Use the Python path explicitly when copy-compatible behavior is required.

```python
schema.validate(data, _force_python=True)
```

## Disable It

```bash
VALIDKIT_DISABLE_NATIVE=1 python app.py
```

## Benchmark

```bash
python benchmarks/benchmark_validation.py --native-mode both
```
