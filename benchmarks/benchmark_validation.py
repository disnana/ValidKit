#!/usr/bin/env python3
"""Benchmark regular and compiled ValidKit validation.

The script avoids third-party dependencies so it can run in a fresh checkout.
It prints elapsed seconds and a speedup ratio for several common payload shapes.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validkit import compile, v, validate  # noqa: E402


Case = tuple[str, dict[str, Any], dict[str, Any], int, dict[str, Any]]


class Account:
    name: str
    age: int = 18
    active: bool = True


def build_cases(iterations: int) -> list[Case]:
    return [
        (
            "flat_basic",
            {
                "id": v.int(),
                "name": v.str().min(3),
                "score": v.float().range(0.0, 100.0),
                "active": v.bool(),
            },
            {"id": 1, "name": "Alice", "score": 98.5, "active": True},
            iterations,
            {},
        ),
        (
            "nested_payload",
            {
                "user": {
                    "id": v.int(),
                    "profile": {
                        "name": v.str().min(3),
                        "tags": v.list(v.str().min(2)),
                    },
                },
                "metrics": v.dict(str, v.list(v.int().range(0, 1000))),
            },
            {
                "user": {"id": 1, "profile": {"name": "Alice", "tags": ["py", "vk"]}},
                "metrics": {"daily": [1, 2, 3], "weekly": [10, 20, 30]},
            },
            max(1, iterations // 2),
            {},
        ),
        (
            "collect_errors",
            {"id": v.int(), "name": v.str().min(5), "enabled": v.bool()},
            {"id": "wrong", "name": "abc", "enabled": "yes"},
            max(1, iterations // 4),
            {"collect_errors": True},
        ),
        (
            "class_schema",
            Account,
            {"name": "Alice", "age": 30, "active": True},
            iterations,
            {},
        ),
    ]


def time_call(func: Callable[[], Any], repeat: int = 5) -> float:
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def run_case(
    name: str,
    schema: Any,
    payload: dict[str, Any],
    iterations: int,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    compiled_schema = compile(schema)

    def regular() -> None:
        for _ in range(iterations):
            validate(payload, schema, **kwargs)

    def compiled() -> None:
        for _ in range(iterations):
            compiled_schema.validate(payload, **kwargs)

    regular_seconds = time_call(regular)
    compiled_seconds = time_call(compiled)
    speedup = regular_seconds / compiled_seconds if compiled_seconds else float("inf")

    return {
        "case": name,
        "iterations": iterations,
        "regular_seconds": regular_seconds,
        "compiled_seconds": compiled_seconds,
        "speedup": speedup,
    }


def print_table(results: list[dict[str, Any]]) -> None:
    print("| case | iterations | validate() | compiled | speedup |")
    print("|---|---:|---:|---:|---:|")
    for result in results:
        print(
            "| {case} | {iterations} | {regular_seconds:.6f}s | "
            "{compiled_seconds:.6f}s | {speedup:.2f}x |".format(**result)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ValidKit validation paths.")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    results = [
        run_case(name, schema, payload, iterations, kwargs)
        for name, schema, payload, iterations, kwargs in build_cases(args.iterations)
    ]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_table(results)


if __name__ == "__main__":
    main()
