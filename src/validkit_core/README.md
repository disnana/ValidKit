# validkit-py-core

Experimental Rust validation core for ValidKit.

The Python distribution is published as `validkit-py-core` and exposes the
native module as `validkit_core`.

This crate is intentionally isolated from the Python package for now. The first
goal is to prove and test the Rust validation engine without changing the public
Python API or the current pure-Python build.

Current scope:

- Validate a borrowed value tree against a compact schema tree.
- Preserve ValidKit-compatible path strings such as `user.tags[1]`.
- Ignore unknown object keys, matching the current non-strict ValidKit behavior.
- Avoid Python packaging changes until the core behavior is stable.

Next step:

- Add a PyO3 bridge that converts a compiled ValidKit schema into a Rust schema
  once, then sends each payload through the Rust validator in one call.
- Keep the bridge optional. If the native module is unavailable, ValidKit should
  continue using the existing Python compiled validator.
