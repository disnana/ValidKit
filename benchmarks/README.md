# ValidKit Benchmarks

This folder contains small benchmarks for comparing:

- Pydantic `BaseModel.model_validate(...)`
- regular ValidKit `validate(...)`
- precompiled ValidKit `compile(...).validate(...)`

Run from the repository root:

```bash
python -m pip install -e .[benchmark]
python benchmarks/benchmark_validation.py
python benchmarks/benchmark_validation.py --json
```

The benchmark is intentionally simple and stable enough for local comparison.
It is not a substitute for production profiling on your own payloads.
