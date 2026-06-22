from dataclasses import dataclass, field
from typing import NamedTuple

import pytest

from validkit import Schema, ValidationError, v, validate


def test_list_constraints() -> None:
    schema = {"tags": v.list(v.str()).min(2).max(4)}
    assert validate({"tags": ["a", "b"]}, schema) == {"tags": ["a", "b"]}
    assert validate({"tags": ["a", "b", "c", "d"]}, schema) == {
        "tags": ["a", "b", "c", "d"]
    }

    with pytest.raises(ValidationError):
        validate({"tags": ["a"]}, schema)
    with pytest.raises(ValidationError):
        validate({"tags": ["a", "b", "c", "d", "e"]}, schema)

    fixed_schema = {"ids": v.list(v.int()).length(3)}
    assert validate({"ids": [1, 2, 3]}, fixed_schema) == {"ids": [1, 2, 3]}
    with pytest.raises(ValidationError):
        validate({"ids": [1, 2]}, fixed_schema)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: v.list(v.int()).min(-1),
        lambda: v.list(v.int()).max(-1),
        lambda: v.list(v.int()).length(-1),
        lambda: v.list(v.int()).min(3).max(2),
        lambda: v.list(v.int()).max(2).min(3),
    ],
)
def test_list_constraints_reject_invalid_definitions(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()  # type: ignore[operator]


def test_number_exclusive_bounds() -> None:
    assert validate(11, v.int().min(10, exclusive=True)) == 11
    assert validate(19, v.int().max(20, exclusive=True)) == 19
    assert validate(
        0.5,
        v.float().range(0.0, 1.0, exclusive_min=True, exclusive_max=True),
    ) == 0.5

    with pytest.raises(ValidationError):
        validate(10, v.int().min(10, exclusive=True))
    with pytest.raises(ValidationError):
        validate(20, v.int().max(20, exclusive=True))
    with pytest.raises(ValidationError):
        validate(0.0, v.float().range(0.0, 1.0, exclusive_min=True))
    with pytest.raises(ValidationError):
        validate(1.0, v.float().range(0.0, 1.0, exclusive_max=True))


def test_exclusive_equal_bounds_are_rejected() -> None:
    with pytest.raises(ValueError, match="equal bounds cannot be exclusive"):
        v.int().range(1, 1, exclusive_min=True)
    with pytest.raises(ValueError, match="equal bounds cannot be exclusive"):
        v.int().min(1, exclusive=True).max(1)
    with pytest.raises(ValueError, match="equal bounds cannot be exclusive"):
        v.int().max(1, exclusive=True).min(1)


def test_constrained_samples_are_valid() -> None:
    list_schema = Schema({"items": v.list(v.int()).min(3)})
    number_schema = Schema(
        {"score": v.int().range(0, 3, exclusive_min=True, exclusive_max=True)}
    )

    assert list_schema.generate_sample() == {"items": [0, 0, 0]}
    assert number_schema.generate_sample() == {"score": 1}


def test_dataclass_conversion_and_defaults() -> None:
    @dataclass
    class User:
        name: str
        tags: list[str] = field(default_factory=list)
        normalized: str = field(init=False, default="ready")

    result = validate({"name": "Alice"}, User)

    assert isinstance(result, User)
    assert result.name == "Alice"
    assert result.tags == []
    assert result.normalized == "ready"


def test_partial_dataclass_validation_returns_dict() -> None:
    @dataclass
    class User:
        name: str
        age: int

    assert validate({"name": "Alice"}, User, partial=True) == {"name": "Alice"}


def test_namedtuple_conversion() -> None:
    class Point(NamedTuple):
        x: int
        y: int

    result = validate({"x": 10, "y": 20}, Point)

    assert isinstance(result, Point)
    assert result == Point(10, 20)
