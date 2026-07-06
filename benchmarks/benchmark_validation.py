#!/usr/bin/env python3
"""Benchmark Pydantic, regular ValidKit, and compiled ValidKit validation.

It prints elapsed seconds and speedup ratios for several common payload shapes.
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
from validkit._native import NATIVE_RUNTIME  # noqa: E402

try:
    from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
except ImportError as exc:  # pragma: no cover - exercised by local setup
    raise SystemExit(
        "pydantic is required for this benchmark. Install with: "
        "python -m pip install -e .[benchmark]"
    ) from exc

Case = tuple[str, Any, Any, dict[str, Any], int, dict[str, Any], bool]


class Account:
    name: str
    age: int = 18
    active: bool = True


class PydanticFlat(BaseModel):
    id: int
    name: str = Field(min_length=3)
    score: float = Field(ge=0.0, le=100.0)
    active: bool


class PydanticProfile(BaseModel):
    name: str = Field(min_length=3)
    tags: list[str]


class PydanticUser(BaseModel):
    id: int
    profile: PydanticProfile


class PydanticNested(BaseModel):
    user: PydanticUser
    metrics: dict[str, list[int]]


class PydanticErrorCase(BaseModel):
    id: int
    name: str = Field(min_length=5)
    enabled: bool


class PydanticAccount(BaseModel):
    name: str
    age: int = 18
    active: bool = True


def build_cases(iterations: int) -> list[Case]:
    return [
        (
            "flat_basic",
            PydanticFlat,
            {
                "id": v.int(),
                "name": v.str().min(3),
                "score": v.float().range(0.0, 100.0),
                "active": v.bool(),
            },
            {"id": 1, "name": "Alice", "score": 98.5, "active": True},
            iterations,
            {},
            False,
        ),
        (
            "nested_payload",
            PydanticNested,
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
            False,
        ),
        (
            "collect_errors",
            PydanticErrorCase,
            {"id": v.int(), "name": v.str().min(5), "enabled": v.bool()},
            {"id": "wrong", "name": "abc", "enabled": "yes"},
            max(1, iterations // 4),
            {"collect_errors": True},
            True,
        ),
        (
            "class_schema",
            PydanticAccount,
            Account,
            {"name": "Alice", "age": 30, "active": True},
            iterations,
            {},
            False,
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
    pydantic_model: type[BaseModel],
    schema: Any,
    payload: dict[str, Any],
    iterations: int,
    kwargs: dict[str, Any],
    pydantic_expects_error: bool,
    native_mode: str = "auto",
) -> dict[str, Any]:
    compiled_schema = compile(schema)
    force_python = native_mode == "python"

    def pydantic() -> None:
        for _ in range(iterations):
            try:
                pydantic_model.model_validate(payload)
            except PydanticValidationError:
                if not pydantic_expects_error:
                    raise

    def regular() -> None:
        for _ in range(iterations):
            validate(payload, schema, **kwargs)

    def compiled() -> None:
        for _ in range(iterations):
            compiled_schema.validate(payload, _force_python=force_python, **kwargs)

    def compiled_python() -> None:
        for _ in range(iterations):
            compiled_schema.validate(payload, _force_python=True, **kwargs)

    pydantic_seconds = time_call(pydantic)
    regular_seconds = time_call(regular)
    compiled_seconds = time_call(compiled)
    compiled_python_seconds = time_call(compiled_python) if native_mode == "both" else None
    compiled_vs_regular = regular_seconds / compiled_seconds if compiled_seconds else float("inf")
    regular_vs_pydantic = pydantic_seconds / regular_seconds if regular_seconds else float("inf")
    compiled_vs_pydantic = pydantic_seconds / compiled_seconds if compiled_seconds else float("inf")
    native_vs_python = (
        compiled_python_seconds / compiled_seconds
        if compiled_python_seconds is not None and compiled_seconds
        else None
    )

    return {
        "case": name,
        "iterations": iterations,
        "pydantic_seconds": pydantic_seconds,
        "regular_seconds": regular_seconds,
        "compiled_seconds": compiled_seconds,
        "compiled_python_seconds": compiled_python_seconds,
        "regular_vs_pydantic": regular_vs_pydantic,
        "compiled_vs_regular": compiled_vs_regular,
        "compiled_vs_pydantic": compiled_vs_pydantic,
        "native_vs_python": native_vs_python,
    }


def print_table(results: list[dict[str, Any]], native_mode: str) -> None:
    if native_mode == "both":
        print(
            "| case | iterations | pydantic | validkit | compiled auto | "
            "compiled forced python | validkit / pydantic | auto / pydantic | auto / forced python |"
        )
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for result in results:
            compiled_python = result["compiled_python_seconds"]
            compiled_python_text = (
                f"{compiled_python:.6f}s" if compiled_python is not None else "n/a"
            )
            native_ratio = result["native_vs_python"]
            native_ratio_text = f"{native_ratio:.2f}x" if native_ratio is not None else "n/a"
            print(
                "| {case} | {iterations} | {pydantic_seconds:.6f}s | "
                "{regular_seconds:.6f}s | {compiled_seconds:.6f}s | "
                "{compiled_python_text} | {regular_vs_pydantic:.2f}x | "
                "{compiled_vs_pydantic:.2f}x | {native_ratio_text} |".format(
                    compiled_python_text=compiled_python_text,
                    native_ratio_text=native_ratio_text,
                    **result,
                )
            )
        return

    print(
        "| case | iterations | pydantic | validkit | validkit compiled | "
        "validkit / pydantic | compiled / validkit | compiled / pydantic |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for result in results:
        print(
            "| {case} | {iterations} | {pydantic_seconds:.6f}s | "
            "{regular_seconds:.6f}s | {compiled_seconds:.6f}s | "
            "{regular_vs_pydantic:.2f}x | {compiled_vs_regular:.2f}x | "
            "{compiled_vs_pydantic:.2f}x |".format(**result)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ValidKit validation paths.")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--native-mode",
        choices=("auto", "python", "native", "both"),
        default="auto",
        help=(
            "Native accelerator mode: auto uses it when available, python forces the "
            "Python compiled path, native requires it, both compares auto and forced python."
        ),
    )
    args = parser.parse_args()

    if args.native_mode == "native" and not NATIVE_RUNTIME.available:
        raise SystemExit("native accelerator is not available")

    results = [
        run_case(
            name,
            pydantic_model,
            schema,
            payload,
            iterations,
            kwargs,
            pydantic_expects_error,
            args.native_mode,
        )
        for (
            name,
            pydantic_model,
            schema,
            payload,
            iterations,
            kwargs,
            pydantic_expects_error,
        ) in build_cases(args.iterations)
    ]

    if args.json:
        print(json.dumps({
            "native_available": NATIVE_RUNTIME.available,
            "native_disabled": NATIVE_RUNTIME.disabled,
            "native_mode": args.native_mode,
            "results": results,
        }, indent=2))
    else:
        print(f"native available: {NATIVE_RUNTIME.available} (disabled: {NATIVE_RUNTIME.disabled})")
        print_table(results, args.native_mode)


if __name__ == "__main__":
    main()
