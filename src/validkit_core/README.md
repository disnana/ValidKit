# validkit-py-core

Optional Rust/PyO3 native validation core for
[ValidKit](https://github.com/disnana/ValidKit).

`validkit-py-core` publishes the native Python module `validkit_core`. It is
used automatically by `validkit-py` when installed and when a compiled schema is
supported by the native fast path.

## Install

```bash
pip install validkit-py validkit-py-core
```

The main `validkit-py` package does not require this package. If
`validkit-py-core` is missing or disabled, ValidKit falls back to the pure Python
compiled validator.

## What It Accelerates

The native core is focused on hot compiled validation paths:

- `compile(...).validate(...)` for supported dict/list/str/int/float/bool
  schemas
- nested object and list traversal
- numeric range checks, including exclusive bounds
- string and list length checks
- some `collect_errors=True` paths, with lazy `ErrorDetail` materialization in
  `validkit-py`

The fast path validates borrowed Python objects directly and returns the input
object unchanged when the output shape does not need to change.

## Fallback Behavior

ValidKit automatically uses the Python path for unsupported features, including
custom Python callbacks, coercion, environment lookups, regex validators,
`partial`, `base`, and migrations. This keeps the public API compatible while
allowing the native core to prioritize performance.

You can force-disable the native core:

```bash
VALIDKIT_DISABLE_NATIVE=1 python app.py
```

## Import Name

The distribution name is `validkit-py-core`; the importable module is
`validkit_core`.
