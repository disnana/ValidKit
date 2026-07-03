import pytest
import os
import dataclasses
from validkit import compile, v, ValidationError, ValidationResult

def test_compile_basic():
    schema = compile({
        "id": v.int(),
        "name": v.str().min(3),
        "active": v.bool()
    })
    
    data = {"id": 1, "name": "Alice", "active": True}
    res = schema.validate(data)
    assert res == data
    
    # Validation failure
    with pytest.raises(ValidationError) as excinfo:
        schema.validate({"id": "not-an-int", "name": "Al", "active": True})
    # Fast path verification
    assert "Expected int" in str(excinfo.value) or "String length" in str(excinfo.value)

def test_compile_optional_and_default():
    schema = compile({
        "required_val": v.int(),
        "optional_val": v.str().optional(),
        "defaulted_val": v.int().default(42),
    })
    
    # Missing optional and defaulted
    res = schema.validate({"required_val": 10})
    assert res == {"required_val": 10, "defaulted_val": 42}
    
    # Missing optional but base dict has value
    res = schema.validate({"required_val": 10}, base={"optional_val": "hello"})
    assert res == {"required_val": 10, "optional_val": "hello", "defaulted_val": 42}

def test_compile_nested_dict():
    schema = compile({
        "user": {
            "name": v.str(),
            "profile": {
                "age": v.int().range(0, 150)
            }
        }
    })
    
    data = {"user": {"name": "Bob", "profile": {"age": 30}}}
    assert schema.validate(data) == data
    
    with pytest.raises(ValidationError) as excinfo:
        schema.validate({"user": {"name": "Bob", "profile": {"age": 200}}})
    assert "user.profile.age" in excinfo.value.path

def test_compile_list_and_dict_validators():
    schema = compile({
        "tags": v.list(v.str().min(2)),
        "scores": v.dict(str, v.int()),
    })
    
    data = {
        "tags": ["python", "validkit"],
        "scores": {"math": 95, "science": 100}
    }
    assert schema.validate(data) == data
    
    with pytest.raises(ValidationError):
        schema.validate({"tags": ["a"], "scores": {"math": 95}})

def test_compile_collect_errors():
    schema = compile({
        "id": v.int(),
        "name": v.str().min(5),
    })
    
    result = schema.validate({"id": "wrong", "name": "abc"}, collect_errors=True)
    assert isinstance(result, ValidationResult)
    assert len(result.errors) == 2
    paths = {err.path for err in result.errors}
    assert "id" in paths
    assert "name" in paths

def test_compile_when_condition():
    schema = compile({
        "is_admin": v.bool(),
        "admin_key": v.str().when(lambda data: data.get("is_admin") is True),
    })
    
    # When is_admin is False, admin_key is not required
    assert schema.validate({"is_admin": False}) == {"is_admin": False}
    
    # When is_admin is True, admin_key is required
    with pytest.raises(ValidationError):
        schema.validate({"is_admin": True})

def test_compile_env_vars():
    schema = compile({
        "db_port": v.int().coerce().env("TEST_DB_PORT").default(5432)
    })
    
    # No env var, should fall back to default
    assert schema.validate({}) == {"db_port": 5432}
    
    # Set env var
    os.environ["TEST_DB_PORT"] = "8080"
    try:
        assert schema.validate({}) == {"db_port": 8080}
    finally:
        del os.environ["TEST_DB_PORT"]

def test_compile_dataclass():
    @dataclasses.dataclass
    class UserModel:
        name: str
        age: int = 18

    schema = compile(UserModel)
    
    # Validates input dict and builds dataclass instance
    res = schema.validate({"name": "Charlie"})
    assert isinstance(res, UserModel)
    assert res.name == "Charlie"
    assert res.age == 18

def test_compile_migration():
    schema = compile({
        "username": v.str(),
        "age": v.int()
    })
    
    # Rename 'user_name' to 'username'
    migrate = {"user_name": "username"}
    res = schema.validate({"user_name": "Dave", "age": 25}, migrate=migrate)
    assert res == {"username": "Dave", "age": 25}
