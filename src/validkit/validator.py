from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
    TYPE_CHECKING,
    Literal,
    cast,
)
from .v import Validator, v

T = TypeVar("T")


class Schema(Generic[T]):
    """
    型情報を持つスキーマの薄いラッパーです。IDE による型補完を有効にするために使用します。

    Usage::

        from typing import TypedDict
        from validkit import v, validate, Schema

        class UserDict(TypedDict):
            name: str
            age: int

        SCHEMA: Schema[UserDict] = Schema({"name": v.str(), "age": v.int()})

        data: UserDict = {"name": "Alice", "age": 30}
        result = validate(data, SCHEMA)  # IDE は UserDict として推論します
        print(result["name"])            # IDE による "name" / "age" の補完が有効

    各フィールドのバリデータに `.default()`, `.examples()`, `.description()` を設定することで、
    より豊かなスキーマ定義が可能になります。
    """

    def __init__(self, schema: Dict[str, Any]) -> None:
        self._schema = schema

    def generate_sample(self) -> Dict[str, Any]:
        """
        スキーマ定義から代表的なサンプルデータ (dict) を自動生成します。

        値の優先順位:

        1. `.default(value)` が設定されている場合 → そのデフォルト値
        2. `.examples([...])` が設定されている場合 → リストの最初の要素
        3. どちらも設定されていない場合 → 型に応じたダミー値 (str: "example", int: 0 など)

        ネストされた辞書スキーマやリストスキーマも再帰的に処理されます。

        Returns:
            Dict[str, Any]: サンプルデータの辞書。

        Example::

            SCHEMA = Schema({
                "host": v.str().default("localhost"),
                "port": v.int().default(5432).examples([3306, 5432, 5433]),
                "ssl":  v.bool().default(False),
            })

            sample = SCHEMA.generate_sample()
            # -> {"host": "localhost", "port": 5432, "ssl": False}
        """
        return cast(Dict[str, Any], _generate_sample(self._schema))

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
            return schema.validate(value, root_data, path_prefix=path_prefix, collect_errors=collect_errors, errors=errors)
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
                    # base 引数が優先
                    result[key] = sub_base
                    continue

                # .default() が設定されている場合はデフォルト値を補完
                if isinstance(sub_schema, Validator) and sub_schema._has_default:
                    result[key] = sub_schema._default_value
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


# --- サンプルデータ生成ヘルパー ---

# 型ごとのデフォルトのダミー値
_TYPE_DUMMY: Dict[Any, Any] = {
    str: "example",
    int: 0,
    float: 0.0,
    bool: False,
}

def _generate_sample(schema: Any) -> Any:
    """
    スキーマ定義を再帰的に走査し、サンプルデータを生成します。
    Schema.generate_sample() の内部実装です。

    Args:
        schema: dict スキーマ、Validator インスタンス、または Python 型。

    Returns:
        生成されたサンプル値。
    """
    # 1. Python 型のショートハンド
    if isinstance(schema, type) and schema in _TYPE_DUMMY:
        return _TYPE_DUMMY[schema]

    # 2. Validator オブジェクト
    if isinstance(schema, Validator):
        # 優先順位: default > examples の先頭 > 型ダミー
        if schema._has_default:
            return schema._default_value
        if schema._examples:
            return schema._examples[0]
        # 型ダミーを型名から推定
        from .v import StringValidator, NumberValidator, BoolValidator, ListValidator, DictValidator, OneOfValidator
        if isinstance(schema, StringValidator):
            return "example"
        if isinstance(schema, NumberValidator):
            return 0 if schema._type_cls is int else 0.0
        if isinstance(schema, BoolValidator):
            return False
        if isinstance(schema, OneOfValidator):
            return schema._choices[0] if schema._choices else None
        if isinstance(schema, ListValidator):
            inner = _generate_sample(schema._item_validator)
            return [inner]
        if isinstance(schema, DictValidator):
            inner = _generate_sample(schema._value_validator)
            return {"key": inner}
        return None

    # 3. dict スキーマ → 再帰的に走査
    if isinstance(schema, dict):
        return {key: _generate_sample(sub) for key, sub in schema.items()}

    return None

if TYPE_CHECKING:
    # Overload definitions are used by type checkers only and skipped at runtime
    @overload
    def validate(
        data: Any,
        schema: Schema[T],
        partial: bool = ...,
        base: Any = ...,
        migrate: Optional[Dict[str, Any]] = ...,
        *,
        collect_errors: Literal[True],
    ) -> ValidationResult: ...

    @overload
    def validate(
        data: Any,
        schema: Schema[T],
        partial: bool = ...,
        base: Any = ...,
        migrate: Optional[Dict[str, Any]] = ...,
        *,
        collect_errors: Literal[False] = ...,  # default
    ) -> T: ...

    @overload
    def validate(
        data: Any,
        schema: Any,
        partial: bool = ...,
        base: Any = ...,
        migrate: Optional[Dict[str, Any]] = ...,
        *,
        collect_errors: Literal[True],
    ) -> ValidationResult: ...

    @overload
    def validate(
        data: Any,
        schema: Any,
        partial: bool = ...,
        base: Any = ...,
        migrate: Optional[Dict[str, Any]] = ...,
        *,
        collect_errors: Literal[False] = ...,  # default
    ) -> Any: ...


def validate(
    data: Any,
    schema: Any,
    partial: bool = False,
    base: Any = None,
    migrate: Optional[Dict[str, Any]] = None,
    collect_errors: bool = False,
) -> Union[Any, "ValidationResult"]:
    
    # Unwrap Schema[T] to its underlying dict schema
    if isinstance(schema, Schema):
        schema = schema._schema

    # Apply migration if any
    if migrate and isinstance(data, dict):
        data = data.copy()
        for old_key, action in migrate.items():
            if old_key in data:
                val = data.pop(old_key)
                if isinstance(action, str):
                    data[action] = val
                elif callable(action):
                    result_action = action(val)
                    if isinstance(result_action, tuple) and len(result_action) == 2:
                        new_key, new_val = result_action
                        data[new_key] = new_val
                    else:
                        data[old_key] = result_action
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
