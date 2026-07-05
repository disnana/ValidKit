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


def test_compile_copies_pure_list_and_dict_validator_inputs():
    schema = compile({
        "tags": v.list(v.str().min(2)),
        "scores": v.dict(str, v.int().range(0, 100)),
    })

    data = {
        "tags": ["python", "validkit"],
        "scores": {"math": 95, "science": 100},
    }

    result = schema.validate(data)
    assert result == data
    assert result is not data
    assert result["tags"] is not data["tags"]
    assert result["scores"] is not data["scores"]

    result["tags"].append("new")
    result["scores"]["english"] = 80
    assert data == {
        "tags": ["python", "validkit"],
        "scores": {"math": 95, "science": 100},
    }


def test_compile_copies_nested_pure_collection_inputs():
    schema = compile({
        "user": {
            "id": v.int(),
            "profile": {
                "name": v.str().min(3),
                "tags": v.list(v.str().min(2)),
            },
        },
        "metrics": v.dict(str, v.list(v.int())),
    })

    data = {
        "user": {"id": 1, "profile": {"name": "Alice", "tags": ["py", "vk"]}},
        "metrics": {"daily": [1, 2, 3]},
    }
    result = schema.validate(data)

    assert result == data
    assert result["user"] is not data["user"]
    assert result["user"]["profile"] is not data["user"]["profile"]
    assert result["user"]["profile"]["tags"] is not data["user"]["profile"]["tags"]
    assert result["metrics"] is not data["metrics"]
    assert result["metrics"]["daily"] is not data["metrics"]["daily"]


def test_compile_does_not_preserve_transforming_list_inputs():
    schema = compile({"items": v.list(v.int().coerce())})
    data = {"items": ("1", "2")}

    result = schema.validate(data)

    assert result == {"items": [1, 2]}
    assert result is not data


def test_compile_pure_tuple_list_input_still_returns_list():
    schema = compile({"items": v.list(v.int())})
    data = {"items": (1, 2)}

    result = schema.validate(data)

    assert result == {"items": [1, 2]}
    assert isinstance(result["items"], list)
    assert result is not data


def test_compile_nested_tuple_list_inputs_still_return_lists():
    schema = compile({"matrix": v.list(v.list(v.int()))})
    data = {"matrix": [(1, 2), (3,)]}

    result = schema.validate(data)

    assert result == {"matrix": [[1, 2], [3]]}
    assert all(isinstance(row, list) for row in result["matrix"])


def test_compile_dict_tuple_list_values_still_return_lists():
    schema = compile({"metrics": v.dict(str, v.list(v.int()))})
    data = {"metrics": {"daily": (1, 2, 3)}}

    result = schema.validate(data)

    assert result == {"metrics": {"daily": [1, 2, 3]}}
    assert isinstance(result["metrics"]["daily"], list)

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


def test_compile_nested_list_validator_does_not_reuse_temp_names():
    schema = compile({
        "matrix": v.list(v.list(v.int()))
    })

    data = {"matrix": [[1, 2], [3]]}
    assert schema.validate(data) == data


def test_compile_nested_dict_validator_does_not_reuse_temp_names():
    schema = compile({
        "groups": v.dict(str, v.dict(str, v.int()))
    })

    data = {"groups": {"a": {"x": 1}, "b": {"y": 2}}}
    assert schema.validate(data) == data


def test_compile_env_decryptor_collect_errors_compiles_and_collects(monkeypatch):
    def bad_decryptor(value):
        raise ValueError("bad decrypt")

    monkeypatch.setenv("TEST_BAD_SECRET", "encrypted")
    schema = compile({
        "secret": v.str().env("TEST_BAD_SECRET", decryptor=bad_decryptor)
    })

    result = schema.validate({}, collect_errors=True)
    assert isinstance(result, ValidationResult)
    assert len(result.errors) == 1
    assert "Failed to decrypt env var" in result.errors[0].message


def test_compile_fallback_validator_custom_runs_once():
    calls = []

    def track(value):
        calls.append(value)
        return value

    schema = compile({
        "dt": v.datetime().custom(track)
    })

    import datetime

    schema.validate({"dt": datetime.datetime(2024, 1, 1)})
    assert len(calls) == 1


def test_compile_nested_base_is_passed_to_child_schema():
    schema = compile({
        "user": {
            "name": v.str().optional(),
            "age": v.int(),
        }
    })

    result = schema.validate(
        {"user": {"age": 30}},
        partial=True,
        base={"user": {"name": "Alice"}},
    )

    assert result == {"user": {"name": "Alice", "age": 30}}


def test_compile_when_condition_uses_field_base_when_skipped():
    schema = compile({
        "enabled": v.bool(),
        "token": v.str().when(lambda data: data.get("enabled") is True),
    })

    result = schema.validate(
        {"enabled": False},
        base={"token": "from-base"},
    )

    assert result == {"enabled": False, "token": "from-base"}
