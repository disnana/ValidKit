import re
import builtins
from typing import Any, Callable, Dict, List, Union, Type, Optional, cast

class Validator:
    def __init__(self) -> None:
        self._optional = False
        self._custom_checks: List[Callable[[Any], Any]] = []
        self._when_condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    def optional(self) -> "Validator":
        self._optional = True
        return self

    def custom(self, func: Callable[[Any], Any]) -> "Validator":
        self._custom_checks.append(func)
        return self

    def when(self, condition: Callable[[Dict[str, Any]], bool]) -> "Validator":
        self._when_condition = condition
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Any:
        """Base validate method. Subclasses should override this."""
        return self._validate_base(value, data)

    def _validate_base(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Any:
        # if condition is not met, this validator might be skipped or handled by caller
        for check in self._custom_checks:
            value = check(value)
        return value

class StringValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._regex: Optional[re.Pattern[str]] = None

    def regex(self, pattern: str) -> "StringValidator":
        self._regex = re.compile(pattern)
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__}")
        if self._regex and not self._regex.match(value):
            raise ValueError(f"Value '{value}' does not match regex '{self._regex.pattern}'")
        return cast(str, self._validate_base(value, data))

class NumberValidator(Validator):
    def __init__(self, type_cls: Union[Type[int], Type[float]]) -> None:
        super().__init__()
        self._type_cls = type_cls
        self._min: Optional[float] = None
        self._max: Optional[float] = None

    def range(self, min_val: float, max_val: float) -> "NumberValidator":
        self._min = min_val
        self._max = max_val
        return self

    def min(self, min_val: float) -> "NumberValidator":
        self._min = min_val
        return self

    def max(self, max_val: float) -> "NumberValidator":
        self._max = max_val
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Union[int, float]:
        if not isinstance(value, self._type_cls):
            raise TypeError(f"Expected {self._type_cls.__name__}, got {type(value).__name__}")
        if self._min is not None and value < self._min:
            raise ValueError(f"Value {value} is less than minimum {self._min}")
        if self._max is not None and value > self._max:
            raise ValueError(f"Value {value} is greater than maximum {self._max}")
        return cast(Union[int, float], self._validate_base(value, data))

class BoolValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {type(value).__name__}")
        return cast(bool, self._validate_base(value, data))

class ListValidator(Validator):
    def __init__(self, item_validator: Union[Validator, Dict[builtins.str, Any], Type[Any]]) -> None:
        super().__init__()
        self._item_validator = item_validator

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> List[Any]:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list, got {type(value).__name__}")
        from .validator import validate_internal
        result = []
        root_data = data if data is not None else {}
        for i, item in enumerate(value):
            try:
                result.append(validate_internal(item, self._item_validator, root_data, path_prefix=f"[{i}]"))
            except Exception:
                # Re-raise or collect will be handled by validate_internal/caller
                raise
        return cast(List[Any], self._validate_base(result, data))

class DictValidator(Validator):
    def __init__(self, key_type: Type[Any], value_validator: Union[Validator, Dict[str, Any], Type[Any]]) -> None:
        super().__init__()
        self._key_type = key_type
        self._value_validator = value_validator

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Dict[Any, Any]:
        if not isinstance(value, dict):
            raise TypeError(f"Expected dict, got {type(value).__name__}")
        from .validator import validate_internal
        result = {}
        root_data = data if data is not None else {}
        for k, v in value.items():
            if not isinstance(k, self._key_type):
                raise TypeError(f"Expected key type {self._key_type.__name__}, got {type(k).__name__}")
            try:
                result[k] = validate_internal(v, self._value_validator, root_data, path_prefix=f"{k}")
            except Exception:
                raise
        return cast(Dict[Any, Any], self._validate_base(result, data))

class OneOfValidator(Validator):
    def __init__(self, choices: List[Any]) -> None:
        super().__init__()
        self._choices = choices

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Any:
        if value not in self._choices:
            raise ValueError(f"Value '{value}' is not one of {self._choices}")
        return self._validate_base(value, data)

class VBuilder:
    def str(self) -> StringValidator:
        return StringValidator()

    def int(self) -> NumberValidator:
        return NumberValidator(int)

    def float(self) -> NumberValidator:
        return NumberValidator(float)

    def bool(self) -> BoolValidator:
        return BoolValidator()

    def list(self, item_validator: Union[Validator, Dict[builtins.str, Any], Type[Any]]) -> ListValidator:
        return ListValidator(item_validator)

    def dict(self, key_type: Type[Any], value_validator: Union[Validator, Dict[builtins.str, Any], Type[Any]]) -> DictValidator:
        return DictValidator(key_type, value_validator)

    def oneof(self, choices: List[Any]) -> OneOfValidator:
        return OneOfValidator(choices)

v = VBuilder()
