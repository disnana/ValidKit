# Performance and Benchmarks

Benchmarks live in `benchmarks/benchmark_validation.py`. They compare normal and compiled validation without external dependencies.

```bash
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
