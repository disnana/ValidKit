# ValidKit Benchmarks

This folder contains small, dependency-free benchmarks for comparing regular
`validate()` calls with precompiled `compile(...).validate(...)` calls.

Run from the repository root:

```bash
python benchmarks/benchmark_validation.py
python benchmarks/benchmark_validation.py --json
```

The benchmark is intentionally simple and stable enough for local comparison.
It is not a substitute for production profiling on your own payloads.
