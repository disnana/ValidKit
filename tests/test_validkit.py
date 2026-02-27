import pytest
import sys
import os
from typing import TypedDict

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from validkit import v, validate, ValidationError, Schema, ValidationResult

def test_basic_types():
    assert validate("hello", v.str()) == "hello"
    assert validate(123, v.int()) == 123
    assert validate(1.23, v.float()) == 1.23
    assert validate(True, v.bool()) == True
    
    with pytest.raises(ValidationError):
        validate(123, v.str())
    with pytest.raises(ValidationError):
        validate("123", v.int())

def test_string_regex():
    validator = v.str().regex(r"^\d{3}-\d{4}$")
    assert validate("123-4567", validator) == "123-4567"
    with pytest.raises(ValidationError):
        validate("123-456", validator)

def test_number_range():
    validator = v.int().range(10, 20)
    assert validate(15, validator) == 15
    with pytest.raises(ValidationError):
        validate(9, validator)
    with pytest.raises(ValidationError):
        validate(21, validator)

def test_list_validation():
    validator = v.list(v.int())
    assert validate([1, 2, 3], validator) == [1, 2, 3]
    with pytest.raises(ValidationError):
        validate([1, "2", 3], validator)

def test_dict_validation():
    validator = v.dict(str, v.int())
    assert validate({"a": 1, "b": 2}, validator) == {"a": 1, "b": 2}
    with pytest.raises(ValidationError):
        validate({"a": "1"}, validator)
    with pytest.raises(ValidationError):
        validate({1: 1}, validator)

def test_nested_dict():
    schema = {
        "user": {
            "name": v.str(),
            "age": v.int().min(0)
        }
    }
    data = {"user": {"name": "Alice", "age": 20}}
    assert validate(data, schema) == data
    
    with pytest.raises(ValidationError) as excinfo:
        validate({"user": {"name": "Alice", "age": -1}}, schema)
    assert excinfo.value.path == "user.age"
    # Use 'in' and be less specific about .0 to be flexible
    assert "is less than minimum" in str(excinfo.value)

def test_optional_fields():
    schema = {
        "name": v.str(),
        "age": v.int().optional()
    }
    assert validate({"name": "Alice"}, schema) == {"name": "Alice"}
    assert validate({"name": "Alice", "age": 20}, schema) == {"name": "Alice", "age": 20}

def test_partial_validation():
    schema = {"a": v.int(), "b": v.int()}
    assert validate({"a": 1}, schema, partial=True) == {"a": 1}

def test_base_merge():
    schema = {"a": v.int(), "b": v.int()}
    base = {"b": 2}
    assert validate({"a": 1}, schema, base=base) == {"a": 1, "b": 2}

def test_migration_advanced():
    schema = {"new_key": v.str(), "val": v.int()}
    migrate = {
        "old_key": "new_key",
        "val": lambda v: int(v) if isinstance(v, str) else v
    }
    # Test rename + value transform
    assert validate({"old_key": "hello", "val": "100"}, schema, migrate=migrate) == {"new_key": "hello", "val": 100}
    
    # Test with partial and missing key in migration
    assert validate({"val": 50}, schema, partial=True, migrate=migrate) == {"val": 50}

def test_when_condition_complex():
    schema = {
        "mode": v.str(),
        "threshold": v.int().when(lambda d: d.get("mode") == "strict"),
        "factor": v.float().optional()
    }
    # Mode is normal, threshold is NOT required
    assert validate({"mode": "normal"}, schema) == {"mode": "normal"}
    # Mode is strict, threshold IS required
    with pytest.raises(ValidationError) as exc:
        validate({"mode": "strict"}, schema)
    assert exc.value.path == "threshold"
    assert validate({"mode": "strict", "threshold": 10}, schema) == {"mode": "strict", "threshold": 10}

def test_error_collection_details():
    schema = {
        "users": v.list({
            "id": v.int(),
            "name": v.str()
        })
    }
    data = {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": "two", "name": 2}
        ]
    }
    result = validate(data, schema, collect_errors=True)
    assert isinstance(result, ValidationResult)
    assert len(result.errors) == 2
    
    # Check paths
    paths = {e.path: e for e in result.errors}
    assert "users[1].id" in paths
    assert "users[1].name" in paths
    assert "Expected int" in paths["users[1].id"].message
    assert "Expected str" in paths["users[1].name"].message

def test_custom_validator_chaining():
    def strip_str(s): return s.strip()
    def uppercase_str(s): return s.upper()
    
    validator = v.str().custom(strip_str).custom(uppercase_str)
    assert validate("  hello  ", validator) == "HELLO"

def test_oneof_with_int():
    validator = v.oneof([1, 2, 3])
    assert validate(2, validator) == 2
    with pytest.raises(ValidationError):
        validate(4, validator)

def test_list_of_nested_dicts_and_errors():
    schema = v.list({"meta": {"code": v.int()}})
    data = [{"meta": {"code": 200}}, {"meta": {"code": "404"}}]
    
    result = validate(data, schema, collect_errors=True)
    assert len(result.errors) == 1
    # Check if path contains [1] and meta.code
    assert "[1].meta.code" in result.errors[0].path or result.errors[0].path == "[1].meta.code"

def test_schema_generic_full_lifecycle():
    class MyDict(TypedDict):
        id: int
        data: str
    
    schema: Schema[MyDict] = Schema({"id": v.int(), "data": v.str()})
    
    # Valid
    res = validate({"id": 1, "data": "ok"}, schema)
    assert res["id"] == 1
    
    # Invalid
    with pytest.raises(ValidationError):
        validate({"id": "1", "data": "ok"}, schema)
    
    # Partial + Base
    res_partial = validate({"id": 2}, schema, partial=True, base={"data": "default"})
    assert res_partial == {"id": 2, "data": "default"}

def test_validate_none_with_optional_and_base():
    schema = {"a": v.int().optional()}
    # Optional field with value None: result should reflect input or base
    assert validate({"a": None}, schema) == {"a": None}
    assert validate({"a": None}, schema, base={"a": 10}) == {"a": 10}

def test_shorthand_types():
    schema = {"name": str, "age": int}
    data = {"name": "Alice", "age": 30}
    assert validate(data, schema) == data
    with pytest.raises(ValidationError):
        validate({"name": 123, "age": 30}, schema)

def test_collect_errors_without_exception():
    """Ensure collect_errors still returns a result even if no errors."""
    schema = {"a": v.int()}
    result = validate({"a": 1}, schema, collect_errors=True)
    assert isinstance(result, ValidationResult)
    assert result.data == {"a": 1}
    assert result.errors == []
