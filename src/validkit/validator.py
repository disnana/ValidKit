from typing import Any, Dict, List, Union, Optional
from .v import Validator, v

class ValidationError(Exception):
    def __init__(self, message: str, path: str = "", value: Any = None) -> None:
        self.message = message
        self.path = path
        self.value = value
        super().__init__(f"{path}: {message}" if path else message)

class ErrorDetail:
    def __init__(self, path: str, message: str, value: Any) -> None:
        self.path = path
        self.message = message
        self.value = value
    
    def __str__(self) -> str:
        return f"{self.path}: {self.message} (value: {self.value})"

class ValidationResult:
    def __init__(self, data: Any, errors: Optional[List[ErrorDetail]] = None) -> None:
        self.data = data
        self.errors = errors or []

def validate_internal(
    value: Any, 
    schema: Any, 
    root_data: Dict[str, Any], 
    path_prefix: str = "", 
    partial: bool = False,
    base: Any = None,
    collect_errors: bool = False,
    errors: Optional[List[ErrorDetail]] = None
) -> Any:
    # 1. Shorthand types
    if isinstance(schema, type) and schema in (str, int, float, bool):
        if schema is str:
            schema = v.str()
        elif schema is int:
            schema = v.int()
        elif schema is float:
            schema = v.float()
        elif schema is bool:
            schema = v.bool()

    # 2. Validator objects
    if isinstance(schema, Validator):
        # Allow None if optional
        if value is None and schema._optional:
            return base if base is not None else None

        # Check condition if any
        if schema._when_condition and not schema._when_condition(root_data):
            # If condition not met and we have a base value, use it, else return None (or skip)
            return base

        try:
            return schema.validate(value, root_data)
        except (TypeError, ValueError) as e:
            err_msg = str(e)
            if collect_errors and errors is not None:
                errors.append(ErrorDetail(path_prefix, err_msg, value))
                return value
            raise ValidationError(err_msg, path_prefix, value)

    # 3. Dict schemas
    if isinstance(schema, dict):
        if value is not None and not isinstance(value, dict):
            err_msg = f"Expected dict, got {type(value).__name__}"
            if collect_errors and errors is not None:
                errors.append(ErrorDetail(path_prefix, err_msg, value))
                return value
            raise ValidationError(err_msg, path_prefix, value)

        result = {}
        input_dict = value if value is not None else {}
        base_dict = base if isinstance(base, dict) else {}

        # All keys in schema
        if not partial:
            # Check for missing keys
            pass # We'll check individually

        for key, sub_schema in schema.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            val = input_dict.get(key)
            sub_base = base_dict.get(key)

            is_optional = False
            if isinstance(sub_schema, Validator) and sub_schema._optional:
                is_optional = True

            if key not in input_dict:
                if sub_base is not None:
                    # Use base value
                    result[key] = sub_base
                    continue
                
                # Check condition for requirement
                if isinstance(sub_schema, Validator) and sub_schema._when_condition:
                    if not sub_schema._when_condition(root_data):
                        # Condition not met, not required
                        continue

                if is_optional or partial:
                    # Skip or keep as None
                    if is_optional and sub_base is not None:
                        result[key] = sub_base
                    continue
                else:
                    err_msg = "Missing required key"
                    if collect_errors and errors is not None:
                        errors.append(ErrorDetail(current_path, err_msg, None))
                        continue
                    raise ValidationError(err_msg, current_path, None)
            
            # Key exists in input
            try:
                result[key] = validate_internal(
                    val, sub_schema, root_data, current_path, 
                    partial, sub_base, collect_errors, errors
                )
            except ValidationError:
                if collect_errors:
                    continue
                raise

        # Check for unknown keys? (Optional feature, not requested but good for strictness)
        # For now, we only process keys in schema.
        return result

    # 4. Literal / Pre-validated?
    return value

def validate(
    data: Any, 
    schema: Any, 
    partial: bool = False, 
    base: Any = None, 
    migrate: Optional[Dict[str, Any]] = None, 
    collect_errors: bool = False
) -> Union[Any, ValidationResult]:
    
    # Apply migration if any
    if migrate and isinstance(data, dict):
        data = data.copy()
        for old_key, action in migrate.items():
            if old_key in data:
                val = data.pop(old_key)
                if isinstance(action, str):
                    data[action] = val
                elif callable(action):
                    # We need to decide where the result goes. 
                    # If migrate says {"timeout": lambda v: f"{v}s"}, it modifies the value but keeps the key?
                    # Actual request: "timeout": lambda v: f"{v}s" -> value transformation.
                    # "旧キー名": "新キー名" -> key rename.
                    # Let's assume if it's a string, it's a rename. If it's a callable, it's a value transform of the SAME key (or should it be rename + transform?)
                    # Usually migration means "old format to new format".
                    # Let's support both.
                    data[old_key] = action(val)
                # Note: if it's a rename, we might want to transform too.
                # But the prompt example shows them separately.

    errors: List[ErrorDetail] = []
    try:
        validated_data = validate_internal(
            data, schema, root_data=data, 
            partial=partial, base=base, 
            collect_errors=collect_errors, errors=errors
        )
    except ValidationError:
        if not collect_errors:
            raise
        validated_data = data # fallback

    if collect_errors:
        return ValidationResult(validated_data, errors)
    return validated_data
