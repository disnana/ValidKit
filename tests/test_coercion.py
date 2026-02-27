import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from validkit import v, validate, ValidationError

def test_string_coercion():
    schema = {"val": v.str().coerce()}
    
    # int to str
    result = validate({"val": 123}, schema)
    assert result["val"] == "123"
    
    # float to str
    result = validate({"val": 12.3}, schema)
    assert result["val"] == "12.3"
    
    # bool to str
    result = validate({"val": True}, schema)
    assert result["val"] == "True"

def test_int_coercion():
    schema = {"val": v.int().coerce()}
    
    # str to int
    result = validate({"val": "123"}, schema)
    assert result["val"] == 123
    
    # float to int
    result = validate({"val": 12.3}, schema)
    assert result["val"] == 12
    
    # invalid str
    with pytest.raises(ValidationError):
        validate({"val": "abc"}, schema)

def test_float_coercion():
    schema = {"val": v.float().coerce()}
    
    # str to float
    result = validate({"val": "12.3"}, schema)
    assert result["val"] == 12.3
    
    # int to float
    result = validate({"val": 123}, schema)
    assert result["val"] == 123.0

def test_bool_coercion():
    schema = {"val": v.bool().coerce()}
    
    # str to bool (truthy)
    for truthy in ["true", "True", "1", "yes", "on"]:
        assert validate({"val": truthy}, schema)["val"] is True
        
    # str to bool (falsy)
    for falsy in ["false", "False", "0", "no", "off"]:
        assert validate({"val": falsy}, schema)["val"] is False
        
    # int to bool
    assert validate({"val": 1}, schema)["val"] is True
    assert validate({"val": 0}, schema)["val"] is False
    
    # invalid
    with pytest.raises(ValidationError):
        validate({"val": "maybe"}, schema)

def test_no_coercion_by_default():
    schema = {"val": v.int()}
    with pytest.raises(ValidationError):
        validate({"val": "123"}, schema)
