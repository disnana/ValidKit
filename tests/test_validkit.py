import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from validkit import v, validate, ValidationError, Schema

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
    assert "user.age" in str(excinfo.value)

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

def test_migration():
    schema = {"new_key": v.str(), "val": v.str()}
    migrate = {
        "old_key": "new_key",
        "val": lambda v: f"prefix_{v}"
    }
    data = {"old_key": "hello", "val": "world"}
    expected = {"new_key": "hello", "val": "prefix_world"}
    assert validate(data, schema, migrate=migrate) == expected

def test_when_condition():
    schema = {
        "enabled": v.bool(),
        "config": v.str().when(lambda d: d.get("enabled", False))
    }
    # When enabled is False, config is NOT required (even if not marked optional, because condition fails)
    assert validate({"enabled": False}, schema) == {"enabled": False}
    # When enabled is True, config IS required
    with pytest.raises(ValidationError):
        validate({"enabled": True}, schema)
    assert validate({"enabled": True, "config": "some"}, schema) == {"enabled": True, "config": "some"}

def test_error_collection():
    schema = {
        "a": v.int().max(10),
        "b": v.str().regex(r"^\w+$")
    }
    data = {"a": 20, "b": "!!!"}
    result = validate(data, schema, collect_errors=True)
    assert len(result.errors) == 2
    paths = [e.path for e in result.errors]
    assert "a" in paths
    assert "b" in paths

def test_custom_validator():
    def must_be_even(n):
        if n % 2 != 0: raise ValueError("Must be even")
        return n
    
    validator = v.int().custom(must_be_even)
    assert validate(2, validator) == 2
    with pytest.raises(ValidationError):
        validate(3, validator)

def test_oneof():
    validator = v.oneof(["apple", "banana"])
    assert validate("apple", validator) == "apple"
    with pytest.raises(ValidationError):
        validate("orange", validator)

def test_chained_customs():
    validator = v.int().custom(lambda x: x * 2).custom(lambda x: x + 1)
    # (5 * 2) + 1 = 11
    assert validate(5, validator) == 11

def test_list_of_dicts():
    schema = v.list({"id": v.int(), "name": v.str()})
    data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    assert validate(data, schema) == data
    with pytest.raises(ValidationError):
        validate([{"id": 1, "name": 5}], schema)

def test_optional_with_none():
    schema = {"a": v.str().optional()}
    assert validate({"a": None}, schema) == {"a": None}
    assert validate({}, schema) == {}

def test_when_with_base():
    schema = {
        "use_default": v.bool(),
        "value": v.int().when(lambda d: d.get("use_default") == False)
    }
    base = {"value": 100}
    # When use_default is True, 'when' fails, so it should return base value
    assert validate({"use_default": True}, schema, base=base) == {"use_default": True, "value": 100}
    # When use_default is False, 'when' passes, it requires value
    assert validate({"use_default": False, "value": 10}, schema, base=base) == {"use_default": False, "value": 10}

def test_schema_generic_basic():
    """Schema[T] wraps a dict schema and validate works identically."""
    schema = Schema({"name": v.str(), "age": v.int()})
    data = {"name": "Alice", "age": 30}
    result = validate(data, schema)
    assert result == data

def test_schema_generic_validation_error():
    """Schema[T] still raises ValidationError on bad data."""
    schema = Schema({"name": v.str(), "level": v.int().range(1, 100)})
    with pytest.raises(ValidationError):
        validate({"name": "Bob", "level": 999}, schema)

def test_schema_generic_partial_and_base():
    """Schema[T] supports partial and base kwargs."""
    schema = Schema({"a": v.int(), "b": v.int()})
    base = {"b": 2}
    result = validate({"a": 1}, schema, base=base)
    assert result == {"a": 1, "b": 2}

def test_schema_generic_optional_field():
    """Schema[T] respects optional fields."""
    schema = Schema({"name": v.str(), "nickname": v.str().optional()})
    result = validate({"name": "Alice"}, schema)
    assert result == {"name": "Alice"}

def test_schema_exported():
    """Schema is exported from the top-level package."""
    # validkit is already imported above via 'from validkit import ...',
    # so it's present in sys.modules
    mod = sys.modules.get("validkit")
    assert mod is not None and hasattr(mod, "Schema")
