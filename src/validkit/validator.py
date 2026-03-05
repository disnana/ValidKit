from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
    TYPE_CHECKING,
    Literal,
    cast,
)
import types as _types
from .v import (
    Validator,
    v,
    InstanceValidator,
    StringValidator,
    NumberValidator,
    BoolValidator,
    ListValidator,
    DictValidator,
    OneOfValidator,
)

T = TypeVar("T")

# Python 3.10+ introduced types.UnionType for PEP 604 (T | None) syntax.
# On Python 3.9, types.UnionType does not exist; capture it once at module
# load time so that _type_hint_to_validator() never accesses it at call time.
# Note: the annotation uses Optional[type] (not `type | None`) so the line
# itself is valid on Python 3.9 where PEP 604 runtime unions don't exist.
_UnionType: Optional[type] = getattr(_types, "UnionType", None)

# Basic Python types supported as schema shorthand (str, int, float, bool)
_BASIC_TYPES = (str, int, float, bool)


def _is_class_schema(schema: Any) -> bool:
    """Return True if *schema* is a class that should be treated as a class-based schema.

    A class qualifies when it:
    - is a plain class (not one of the basic shorthand types),
    - is not a Validator subclass, and
    - either declares own ``__annotations__`` (non-empty) or has at least one Validator
      class attribute in its own ``__dict__``.

    Using ``cls.__dict__.get("__annotations__", {})`` (rather than ``hasattr``) ensures that
    inherited annotations from parent classes or stdlib types (e.g. ``datetime.datetime``,
    ``pathlib.Path``) do not cause false positives.
    """
    if not isinstance(schema, type):
        return False
    if schema in _BASIC_TYPES:
        return False
    if issubclass(schema, Validator):
        return False
    # Check only the class's OWN annotations — not those inherited from base classes.
    # This prevents stdlib classes (datetime.datetime, pathlib.Path, etc.) from being
    # mistakenly detected as class schemas when their parent classes carry annotations.
    own_annotations = schema.__dict__.get("__annotations__", {})
    if own_annotations:
        return True
    # Also accept classes whose only schema fields are Validator instances.
    return any(
        isinstance(val, Validator)
        for k, val in schema.__dict__.items()
        if not k.startswith("_")
    )


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

def _type_hint_to_validator(
    hint: Any,
    has_default: bool = False,
    default_val: Any = None,
) -> Validator:
    """Python 型ヒントを Validator に変換します。

    対応する型ヒント:

    * ``str``, ``int``, ``float``, ``bool`` — 各型の基本バリデータ
    * ``Optional[T]`` / ``Union[T, None]`` — 内部型のバリデータに ``.optional()`` を付与
    * ``list[T]`` / ``List[T]`` — ``v.list()`` ラッパー (要素型を再帰的に変換)
    * ``dict[K, V]`` / ``Dict[K, V]`` — ``v.dict()`` ラッパー (値型を再帰的に変換)
    * 任意のクラス — ``InstanceValidator`` による isinstance チェック
    * ``Any`` / 不明な型 — すべての値を通過させる基底 Validator

    Args:
        hint: 変換元の Python 型ヒント。
        has_default: デフォルト値を付与するかどうか。
        default_val: ``has_default=True`` のときに使用するデフォルト値。

    Returns:
        対応する Validator インスタンス。
    """
    val: Validator
    optional_flag = False

    origin = get_origin(hint)
    args = get_args(hint)

    # --- Optional[T] / Union[T, None] and PEP 604 T | None / T1 | T2 ---
    # Also handles Python 3.10+ types.UnionType (PEP 604); _UnionType is None
    # on Python 3.9 where types.UnionType doesn't exist (module-level guard).
    if origin is Union or (_UnionType is not None and isinstance(hint, _UnionType)):
        non_none_args = [a for a in args if a is not type(None)]
        if type(None) in args:
            optional_flag = True
        if len(non_none_args) == 1:
            # True Optional[T]: recurse with the single inner type
            val = _type_hint_to_validator(non_none_args[0])
        else:
            # Union with multiple non-None members is not supported: fail fast instead of silently
            # disabling type checking. (This also covers Union[T1, T2, None] where None is present
            # but there are still multiple non-None members and no single target type can be inferred.
            # Applies equally to PEP 604 syntax: int | str | None raises the same error.)
            raise TypeError(
                f"typing.Union with multiple non-None members is not supported as schema annotations: {hint!r}. "
                "Use Optional[T] (Union[T, None]) with a single non-None type, or a plain type instead."
            )

    # --- list[T] / List[T] ---
    elif origin is list:
        item_hint: Any = args[0] if args else Any
        # For basic types use the shorthand; for others build a Validator
        if isinstance(item_hint, type) and item_hint in _BASIC_TYPES:
            item_validator: Any = item_hint
        else:
            item_validator = _type_hint_to_validator(item_hint)
        val = ListValidator(item_validator)

    # --- dict[K, V] / Dict[K, V] ---
    elif origin is dict:
        key_type: Any = args[0] if args else str
        val_hint: Any = args[1] if len(args) > 1 else Any
        if isinstance(val_hint, type) and val_hint in _BASIC_TYPES:
            val_validator: Any = val_hint
        else:
            val_validator = _type_hint_to_validator(val_hint)
        # Key type must be a concrete type; fall back to str for generics
        if not isinstance(key_type, type):
            key_type = str
        val = DictValidator(key_type, val_validator)

    # --- Basic shorthand types ---
    elif hint is str:
        val = StringValidator()
    elif hint is int:
        val = NumberValidator(int)
    elif hint is float:
        val = NumberValidator(float)
    elif hint is bool:
        val = BoolValidator()

    # --- Arbitrary concrete class → isinstance check ---
    elif isinstance(hint, type):
        val = InstanceValidator(hint)

    # --- Any / Unknown (e.g. typing.Any, forward references) → passthrough ---
    else:
        val = Validator()

    if has_default:
        # Apply default value via public API; defaulted fields are effectively optional.
        val = val.default(default_val)
    elif optional_flag:
        # Mark field as optional via public API.
        val = val.optional()

    return val


def _class_to_schema(cls: type) -> Dict[str, Any]:
    """クラスのアノテーションとクラス属性からスキーマ辞書を生成します。

    優先順位:
    1. クラス属性が Validator インスタンスの場合、そのまま使用する。
    2. 型アノテーションを ``_type_hint_to_validator()`` で Validator に変換する:

       * ``str``, ``int``, ``float``, ``bool`` → 基本バリデータ
       * ``Optional[T]`` / ``Union[T, None]`` → 内部型バリデータ + ``.optional()``
       * ``list[T]`` / ``List[T]`` → ``ListValidator``
       * ``dict[K, V]`` / ``Dict[K, V]`` → ``DictValidator``
       * 任意クラス → ``InstanceValidator``
       * ``Any`` / 不明 → パススルー Validator

    クラス属性として Validator 以外のデフォルト値が定義されている場合、
    生成した Validator に自動的にデフォルト値を付与します。

    Args:
        cls: ``__annotations__`` を持つ任意のクラス。

    Returns:
        validkit のスキーマ辞書。
    """
    schema: Dict[str, Any] = {}

    # 1. Collect fields defined as Validator class attributes (with or without annotation)
    for key in vars(cls):
        if key.startswith("_"):
            continue
        attr = vars(cls)[key]
        if isinstance(attr, Validator):
            schema[key] = attr

    # 2. Process type annotations (only those declared directly on this class, not inherited)
    annotations: Dict[str, Any] = cls.__dict__.get("__annotations__", {})
    for key, type_hint in annotations.items():
        if key in schema:
            # Already have a Validator class attribute for this field — skip
            continue

        # Check for a non-Validator class attribute that acts as default value
        has_default = False
        default_val: Any = None
        if key in vars(cls) and not isinstance(vars(cls)[key], Validator):
            has_default = True
            default_val = vars(cls)[key]

        schema[key] = _type_hint_to_validator(type_hint, has_default=has_default, default_val=default_val)

    return schema


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

    # 1b. Class-based schema (class with __annotations__ or Validator class attributes)
    if _is_class_schema(schema):
        schema = _class_to_schema(schema)

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
        schema: dict スキーマ、Validator インスタンス、Python 型、またはクラス。

    Returns:
        生成されたサンプル値。
    """
    # 1. Python 型のショートハンド
    if isinstance(schema, type) and schema in _TYPE_DUMMY:
        return _TYPE_DUMMY[schema]

    # 1b. クラスベーススキーマ → dict スキーマに変換してから再帰処理
    if _is_class_schema(schema):
        return _generate_sample(_class_to_schema(schema))

    # 2. Validator オブジェクト
    if isinstance(schema, Validator):
        # 優先順位: default > examples の先頭 > 型ダミー
        if schema._has_default:
            return schema._default_value
        if schema._examples:
            return schema._examples[0]
        # 型ダミーを型名から推定
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
        if isinstance(schema, InstanceValidator):
            return None
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
