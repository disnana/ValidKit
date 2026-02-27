import re
import builtins
from typing import Any, Callable, Dict, List, Union, Type, Optional, cast

class Validator:
    """
    すべてのバリデータの基底クラス。

    各バリデータはチェーン形式でオプションを組み合わせることができます::

        v.str().default("anonymous").description("ユーザー名").examples(["alice", "bob"])
    """

    def __init__(self) -> None:
        self._optional = False
        self._custom_checks: List[Callable[[Any], Any]] = []
        self._when_condition: Optional[Callable[[Dict[str, Any]], bool]] = None
        self._coerce = False
        self._has_default = False
        self._default_value: Any = None
        self._examples: List[Any] = []
        self._description: Optional[str] = None

    def coerce(self) -> "Validator":
        """入力値を対象型に自動変換します (例: str "123" -> int 123)。"""
        self._coerce = True
        return self

    def optional(self) -> "Validator":
        """このフィールドを省略可能にします。"""
        self._optional = True
        return self

    def default(self, value: Any) -> "Validator":
        """
        フィールドが欠損している場合に使用するデフォルト値を設定します。
        .default() を設定したフィールドは自動的にオプショナル扱いになります。

        引数が与えられた場合は入力値が優先されます (後方互換)。

        Args:
            value: 欠損時に補完する値。

        Example::

            v.str().default("guest")
            v.int().range(1, 100).default(10)
        """
        self._has_default = True
        self._default_value = value
        self._optional = True
        return self

    def examples(self, examples_list: List[Any]) -> "Validator":
        """
        このフィールドに入り得る値の例をリストで指定します。
        generate_sample() 実行時や、ドキュメント生成時の補助情報として使用されます。

        Args:
            examples_list: 具体的な値の例のリスト。

        Example::

            v.str().examples(["ap-northeast-1", "us-west-2"])
            v.int().range(1, 65535).examples([80, 443, 8080])
        """
        self._examples = examples_list
        return self

    def description(self, desc: str) -> "Validator":
        """
        フィールドの説明文を設定します。
        generate_sample() の出力やスキーマドキュメント生成の補助情報として使用されます。

        Args:
            desc: フィールドの説明文。

        Example::

            v.str().description("ユーザーの表示名 (3〜30文字)")
        """
        self._description = desc
        return self

    def custom(self, func: Callable[[Any], Any]) -> "Validator":
        """カスタムのバリデーション/変換関数を追加します。"""
        self._custom_checks.append(func)
        return self

    def when(self, condition: Callable[[Dict[str, Any]], bool]) -> "Validator":
        """
        条件付き必須バリデーションを設定します。
        条件関数が True を返す場合のみ、このフィールドが必須になります。

        Args:
            condition: 親辞書全体を受け取り bool を返す関数。

        Example::

            v.str().when(lambda d: d.get("is_premium") is True)
        """
        self._when_condition = condition
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        """Base validate method. Subclasses should override this."""
        return self._validate_base(value, data)

    def _validate_base(self, value: Any, data: Optional[Dict[str, Any]] = None) -> Any:
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

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if self._coerce and not isinstance(value, str):
            value = str(value)
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

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Union[int, float]:
        if self._coerce and not isinstance(value, self._type_cls):
            try:
                value = self._type_cls(value)
            except (ValueError, TypeError):
                pass
        if not isinstance(value, self._type_cls):
            raise TypeError(f"Expected {self._type_cls.__name__}, got {type(value).__name__}")
        if self._min is not None and value < self._min:
            raise ValueError(f"Value {value} is less than minimum {self._min}")
        if self._max is not None and value > self._max:
            raise ValueError(f"Value {value} is greater than maximum {self._max}")
        return cast(Union[int, float], self._validate_base(value, data))

class BoolValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> bool:
        if self._coerce and not isinstance(value, bool):
            if isinstance(value, str):
                lower_val = value.lower()
                if lower_val in ("true", "1", "yes", "on"):
                    value = True
                elif lower_val in ("false", "0", "no", "off"):
                    value = False
            elif isinstance(value, (int, float)):
                if value == 1:
                    value = True
                elif value == 0:
                    value = False

        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {type(value).__name__}")
        return cast(bool, self._validate_base(value, data))

class ListValidator(Validator):
    def __init__(self, item_validator: Union[Validator, Dict[builtins.str, Any], Type[Any]]) -> None:
        super().__init__()
        self._item_validator = item_validator

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> List[Any]:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list, got {type(value).__name__}")
        from .validator import validate_internal
        result = []
        root_data = data if data is not None else {}
        for i, item in enumerate(value):
            # Use path_prefix to build nested path
            item_path = f"{path_prefix}[{i}]" if path_prefix else f"[{i}]"
            res = validate_internal(item, self._item_validator, root_data, path_prefix=item_path, collect_errors=collect_errors, errors=errors)
            result.append(res)
        return cast(List[Any], self._validate_base(result, data))

class DictValidator(Validator):
    def __init__(self, key_type: Type[Any], value_validator: Union[Validator, Dict[str, Any], Type[Any]]) -> None:
        super().__init__()
        self._key_type = key_type
        self._value_validator = value_validator

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Dict[Any, Any]:
        if not isinstance(value, dict):
            raise TypeError(f"Expected dict, got {type(value).__name__}")
        from .validator import validate_internal
        result = {}
        root_data = data if data is not None else {}
        for k, v in value.items():
            if not isinstance(k, self._key_type):
                raise TypeError(f"Expected key type {self._key_type.__name__}, got {type(k).__name__}")
            # Use path_prefix to build nested path
            item_path = f"{path_prefix}.{k}" if path_prefix else f"{k}"
            res = validate_internal(v, self._value_validator, root_data, path_prefix=item_path, collect_errors=collect_errors, errors=errors)
            result[k] = res
        return cast(Dict[Any, Any], self._validate_base(result, data))

class OneOfValidator(Validator):
    def __init__(self, choices: List[Any]) -> None:
        super().__init__()
        self._choices = choices

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
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
