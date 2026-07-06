# Performance and Benchmarks

Benchmarks live in `benchmarks/benchmark_validation.py`. They also compare against Pydantic, so install the benchmark extra before running them.

```bash
python -m pip install -e ".[benchmark]"
python benchmarks/benchmark_validation.py
python benchmarks/benchmark_validation.py --json
```

## Measured scenarios

- `flat_basic`: Flat schema with core validators
- `nested_payload`: Nested dictionaries and lists
- `collect_errors`: Multiple error collection mode
- `class_schema`: Class-style schema

## How to read results

`speedup` greater than 1 means compiled validation is faster. Specialized validators and custom callbacks reduce the gap.

## What compiled validation optimizes

`compile(schema)` uses separate generated functions for normal validation and `collect_errors=True`. Compile a schema once and reuse it on hot paths.

`collect_errors=True` returns a `ValidationResult`. Detailed `ErrorDetail` objects are created when `result.errors` is accessed, so use `result.has_errors` or `result.error_count` when callers only need a cheap error check. Prefer normal validation for high-volume valid payloads, and use `collect_errors=True` when callers need a full error list.
