import re
import builtins
import datetime as dt_module
import uuid as uuid_module
import ipaddress
from typing import Any, Callable, Dict, List, Union, Type, Optional, cast
import urllib.parse
from enum import Enum

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
        self._secret_val = False
        self._env_key: Optional[str] = None
        self._custom_error_msg: Optional[str] = None

    def secret(self) -> "Validator":
        """エラー時に値をマスク (***) します。"""
        self._secret_val = True
        return self

    def env(self, env_key: str) -> "Validator":
        """データが欠損している場合、指定した環境変数から値を取得します。"""
        self._env_key = env_key
        return self

    def error_msg(self, msg: str) -> "Validator":
        """デフォルトのエラーメッセージを上書きします。"""
        self._custom_error_msg = msg
        return self

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
        self._min_len: Optional[int] = None
        self._max_len: Optional[int] = None

    def min(self, min_length: int) -> "StringValidator":
        if min_length < 0:
            raise ValueError(f"Invalid range: minimum length {min_length} cannot be negative")
        if self._max_len is not None and min_length > self._max_len:
            raise ValueError(f"Invalid range: minimum length {min_length} cannot be greater than maximum length {self._max_len}")
        self._min_len = min_length
        return self

    def max(self, max_length: int) -> "StringValidator":
        if max_length < 0:
            raise ValueError(f"Invalid range: maximum length {max_length} cannot be negative")
        if self._min_len is not None and self._min_len > max_length:
            raise ValueError(f"Invalid range: minimum length {self._min_len} cannot be greater than maximum length {max_length}")
        self._max_len = max_length
        return self

    def range(self, min_length: int, max_length: int) -> "StringValidator":
        if min_length < 0 or max_length < 0:
            raise ValueError("Invalid range: length bounds cannot be negative")
        if min_length > max_length:
            raise ValueError(f"Invalid range: minimum length {min_length} cannot be greater than maximum length {max_length}")
        self._min_len = min_length
        self._max_len = max_length
        return self

    def regex(self, pattern: str) -> "StringValidator":
        self._regex = re.compile(pattern)
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if self._coerce and not isinstance(value, str):
            value = str(value)
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__}")
            
        # 1. 最小長チェック
        if self._min_len is not None and len(value) < self._min_len:
            raise ValueError(f"String length {len(value)} is shorter than minimum length {self._min_len}")
            
        # 2. 最大長チェック
        if self._max_len is not None and len(value) > self._max_len:
            raise ValueError(f"String length {len(value)} is longer than maximum length {self._max_len}")
            
        # 3. 正規表現チェック
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
        if min_val > max_val:
            raise ValueError(f"Invalid range: minimum {min_val} cannot be greater than maximum {max_val}")
        self._min = min_val
        self._max = max_val
        return self

    def min(self, min_val: float) -> "NumberValidator":
        if self._max is not None and min_val > self._max:
            raise ValueError(f"Invalid range: minimum {min_val} cannot be greater than maximum {self._max}")
        self._min = min_val
        return self

    def max(self, max_val: float) -> "NumberValidator":
        if self._min is not None and self._min > max_val:
            raise ValueError(f"Invalid range: minimum {self._min} cannot be greater than maximum {max_val}")
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

class InstanceValidator(Validator):
    """カスタム型（任意のクラス）の isinstance チェックを行うバリデータ。

    Usage::

        import pytz
        schema = {"tz": v.instance(pytz.BaseTzInfo)}
        validate({"tz": pytz.utc}, schema)
    """

    def __init__(self, type_cls: Type[Any]) -> None:
        super().__init__()
        self._instance_type = type_cls

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if not isinstance(value, self._instance_type):
            if self._coerce:
                try:
                    coerced_value = self._instance_type(value)
                except Exception as e:
                    raise TypeError(
                        f"Expected instance of {self._instance_type.__name__}, got {type(value).__name__}"
                    ) from e
                if not isinstance(coerced_value, self._instance_type):
                    raise TypeError(
                        f"Expected instance of {self._instance_type.__name__}, got {type(coerced_value).__name__}"
                    )
                value = coerced_value
            else:
                raise TypeError(
                    f"Expected instance of {self._instance_type.__name__}, got {type(value).__name__}"
                )
        return self._validate_base(value, data)

class DateTimeValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._after: Optional[dt_module.datetime] = None
        self._before: Optional[dt_module.datetime] = None
        self._after_now = False
        self._before_now = False

    def after(self, value: Union[dt_module.datetime, dt_module.date]) -> "DateTimeValidator":
        if isinstance(value, dt_module.date) and not isinstance(value, dt_module.datetime):
            value = dt_module.datetime.combine(value, dt_module.time.min)
        self._after = value
        return self

    def before(self, value: Union[dt_module.datetime, dt_module.date]) -> "DateTimeValidator":
        if isinstance(value, dt_module.date) and not isinstance(value, dt_module.datetime):
            value = dt_module.datetime.combine(value, dt_module.time.max)
        self._before = value
        return self

    def after_now(self) -> "DateTimeValidator":
        self._after_now = True
        return self

    def before_now(self) -> "DateTimeValidator":
        self._before_now = True
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if self._coerce and isinstance(value, str):
            try:
                value = dt_module.datetime.fromisoformat(value)
            except ValueError:
                pass

        if not isinstance(value, (dt_module.datetime, dt_module.date)):
            raise TypeError(f"Expected datetime or date, got {type(value).__name__}")
        
        check_val = value
        if isinstance(value, dt_module.date) and not isinstance(value, dt_module.datetime):
            check_val = dt_module.datetime.combine(value, dt_module.time.min)
        
        # タイムゾーン対応: どちらか一方が aware の場合、比較対象も合わせる
        now = dt_module.datetime.now(check_val.tzinfo if isinstance(check_val, dt_module.datetime) and check_val.tzinfo else None)
        
        def _get_cmp_val(val: Union[dt_module.datetime, dt_module.date], reference: dt_module.datetime) -> dt_module.datetime:
            if isinstance(val, dt_module.date) and not isinstance(val, dt_module.datetime):
                val = dt_module.datetime.combine(val, dt_module.time.min)
            if reference.tzinfo and not val.tzinfo:
                return val.replace(tzinfo=reference.tzinfo)
            if not reference.tzinfo and val.tzinfo:
                return val.replace(tzinfo=None)
            return cast(dt_module.datetime, val)

        if self._after_now and check_val <= now:
            raise ValueError(f"Datetime {value} must be after now ({now})")
        if self._before_now and check_val >= now:
            raise ValueError(f"Datetime {value} must be before now ({now})")
        
        if self._after:
            cmp_after = _get_cmp_val(self._after, check_val)
            if check_val <= cmp_after:
                raise ValueError(f"Datetime {value} must be after {self._after}")
        if self._before:
            cmp_before = _get_cmp_val(self._before, check_val)
            if check_val >= cmp_before:
                raise ValueError(f"Datetime {value} must be before {self._before}")
            
        return self._validate_base(value, data)

class UUIDValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._version: Optional[int] = None

    def version(self, v: int) -> "UUIDValidator":
        self._version = v
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if self._coerce and isinstance(value, str):
            try:
                value = uuid_module.UUID(value)
            except ValueError:
                pass

        if isinstance(value, str):
            try:
                u = uuid_module.UUID(value)
                if self._version and u.version != self._version:
                    raise ValueError(f"UUID version must be {self._version}, got {u.version}")
                return self._validate_base(value, data)
            except ValueError:
                raise ValueError(f"Invalid UUID string: {value}")
        elif isinstance(value, uuid_module.UUID):
            if self._version and value.version != self._version:
                raise ValueError(f"UUID version must be {self._version}, got {value.version}")
            return self._validate_base(value, data)
        else:
            raise TypeError(f"Expected UUID string or instance, got {type(value).__name__}")

class MACValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str for MAC address, got {type(value).__name__}")
        
        pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid MAC address format: {value}")
        return cast(str, self._validate_base(value, data))

class SIDValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str for SID, got {type(value).__name__}")
        
        # S-1-[0-5]-(?:\d+-){1,14}\d+
        pattern = r"^S-\d+-(?:\d+-){1,14}\d+$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid Windows SID format: {value}")
        return cast(str, self._validate_base(value, data))

class HWIDValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._length: Optional[int] = None
        self._hex_only = False

    def length(self, n: int) -> "HWIDValidator":
        self._length = n
        return self

    def hex(self) -> "HWIDValidator":
        self._hex_only = True
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str for HWID, got {type(value).__name__}")
        
        if self._length and len(value) != self._length:
            raise ValueError(f"HWID length must be {self._length}, got {len(value)}")
        
        if self._hex_only and not re.match(r"^[0-9A-Fa-f]+$", value):
            raise ValueError(f"HWID must be a hex string: {value}")
            
        return cast(str, self._validate_base(value, data))

class IPValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._v4_only = False
        self._v6_only = False

    def v4_only(self) -> "IPValidator":
        self._v4_only = True
        return self

    def v6_only(self) -> "IPValidator":
        self._v6_only = True
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if self._coerce and isinstance(value, str):
            try:
                value = ipaddress.ip_address(value)
            except ValueError:
                pass

        try:
            val_to_check = str(value) if not isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)) else value
            ip = ipaddress.ip_address(val_to_check)
            if self._v4_only and ip.version != 4:
                raise ValueError(f"IP address must be IPv4, got IPv{ip.version} ({value})")
            if self._v6_only and ip.version != 6:
                raise ValueError(f"IP address must be IPv6, got IPv{ip.version} ({value})")
            return self._validate_base(value, data)
        except ValueError as e:
            raise ValueError(f"Invalid IP address '{value}': {e}")

class SnowflakeValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Union[str, int]:
        if self._coerce and isinstance(value, str) and value.isdigit():
            value = int(value)

        # Discord Snowflake は 64bit 正の整数 (17〜20桁程度の数値または文字列)
        if isinstance(value, int):
            if value < 0 or value > (2**64 - 1):
                raise ValueError(f"Invalid Snowflake (out of 64-bit range): {value}")
        elif isinstance(value, str):
            if not value.isdigit():
                raise ValueError(f"Snowflake string must contains only digits: {value}")
            val_int = int(value)
            if val_int < 0 or val_int > (2**64 - 1):
                raise ValueError(f"Invalid Snowflake (out of 64-bit range): {value}")
        else:
            raise TypeError(f"Expected int or str for Snowflake, got {type(value).__name__}")
            
        return cast(Union[str, int], self._validate_base(value, data))

class VersionValidator(Validator):
    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Expected str for version, got {type(value).__name__}")
        
        # Simple SemVer regex
        pattern = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid Semantic Versioning format: {value}")
        return cast(str, self._validate_base(value, data))

class URLValidator(Validator):
    def __init__(self) -> None:
        super().__init__()
        self._allowed_schemes: Optional[List[str]] = None
        self._allowed_domains: Optional[List[str]] = None
        self._allowed_subdomains: Optional[List[str]] = None
        self._require_query_keys: Optional[List[str]] = None
        self._allowed_paths: Optional[List[str]] = None

    def schemes(self, schemes: List[str]) -> "URLValidator":
        self._allowed_schemes = schemes
        return self

    def domains(self, domains: List[str]) -> "URLValidator":
        self._allowed_domains = domains
        return self
        
    def subdomains(self, subdomains: List[str]) -> "URLValidator":
        self._allowed_subdomains = subdomains
        return self

    def paths(self, paths: List[str]) -> "URLValidator":
        self._allowed_paths = paths
        return self

    def query_keys(self, keys: List[str]) -> "URLValidator":
        self._require_query_keys = keys
        return self

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if not isinstance(value, str):
            raise TypeError(f"Expected str for URL, got {type(value).__name__}")
        
        try:
            parsed = urllib.parse.urlparse(value)
            
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Incomplete URL format.")
                
            if self._allowed_schemes and parsed.scheme not in self._allowed_schemes:
                raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed.")
                
            if self._allowed_domains:
                domain_parts = parsed.netloc.split(':')
                host = domain_parts[0]
                matched_domain = any(host == d or host.endswith('.' + d) for d in self._allowed_domains)
                if not matched_domain:
                    raise ValueError(f"URL domain '{host}' is not allowed.")
                    
            if self._allowed_subdomains:
                host = parsed.netloc.split(':')[0]
                matched_sub = any(host.startswith(sub + '.') for sub in self._allowed_subdomains)
                if not matched_sub:
                    raise ValueError(f"URL subdomain for '{host}' is not allowed.")

            if self._allowed_paths:
                if parsed.path not in self._allowed_paths:
                    raise ValueError(f"URL path '{parsed.path}' is not allowed.")
                    
            if self._require_query_keys:
                query_params = urllib.parse.parse_qs(parsed.query)
                for req_key in self._require_query_keys:
                    if req_key not in query_params:
                        raise ValueError(f"URL missing required query parameter '{req_key}'.")

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid URL string: {value}")
            
        return self._validate_base(value, data)

class EnumValidator(Validator):
    def __init__(self, enum_cls: Type[Enum]) -> None:
        super().__init__()
        self._enum_cls = enum_cls

    def validate(self, value: Any, data: Optional[Dict[str, Any]] = None, path_prefix: str = "", collect_errors: bool = False, errors: Optional[List[Any]] = None) -> Any:
        if self._coerce:
            try:
                value = self._enum_cls(value)
            except ValueError:
                try:
                    value = self._enum_cls[str(value)]
                except KeyError:
                    pass

        if not isinstance(value, self._enum_cls):
            raise TypeError(f"Expected {self._enum_cls.__name__}, got {type(value).__name__}")
            
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

    def instance(self, type_cls: Type[Any]) -> InstanceValidator:
        """カスタム型（任意のクラス）の isinstance チェックを行うバリデータを返します。

        Args:
            type_cls: バリデーション対象の型。

        Example::

            import datetime
            schema = {"ts": v.instance(datetime.datetime)}
            validate({"ts": datetime.datetime.now()}, schema)
        """
        return InstanceValidator(type_cls)

    def datetime(self) -> DateTimeValidator:
        return DateTimeValidator()

    def uuid(self) -> UUIDValidator:
        return UUIDValidator()

    def mac(self) -> MACValidator:
        return MACValidator()

    def sid(self) -> SIDValidator:
        return SIDValidator()

    def hwid(self) -> HWIDValidator:
        return HWIDValidator()

    def ip(self) -> IPValidator:
        return IPValidator()

    def snowflake(self) -> SnowflakeValidator:
        return SnowflakeValidator()

    def version(self) -> VersionValidator:
        return VersionValidator()

    def url(self) -> URLValidator:
        return URLValidator()

    def enum(self, enum_cls: Type[Enum]) -> EnumValidator:
        return EnumValidator(enum_cls)
    @staticmethod
    def auto_infer(
        data: Any,
        type_map: Optional[Dict[type, Any]] = None,
        schema_overrides: Optional[Dict[builtins.str, Any]] = None,
    ) -> Any:
        """
        渡されたデータから ValidKit スキーマを逆生成します。

        各値の型を再帰的に解析し、対応するバリデータを返します。
        dict を渡すとネストしたスキーマ (dict) を返します。

        Args:
            data: スキーマを推論する元データ。
            type_map: カスタム型とバリデータのマッピング (省略可能)。
                キーに Python の型、値に以下のいずれかを指定します。組み込み型より先に
                評価されるため、組み込み型の挙動を上書きすることもできます。

                - :class:`Validator` インスタンス: そのまま使用します。
                - ``(value) -> Validator`` 形式の呼び出し可能オブジェクト:
                  値を受け取り :class:`Validator` を返す関数。
                - ``(value) -> primitive`` 形式の呼び出し可能オブジェクト:
                  値をプリミティブ値 (``str``, ``int``, ``float``, ``bool``, ``list``,
                  ``dict``, ``None``) に変換する関数。変換後の値で ``auto_infer`` を
                  再帰呼び出しします (オプション自動変換)。

            schema_overrides: フィールドごとに推論を手動で上書きするマッピング
                (省略可能)。キーにフィールド名 (文字列)、値に :class:`Validator`
                インスタンスを指定します。``data`` が dict の場合のみ有効です。
                指定されたフィールドは型推論をスキップし、指定のバリデータをそのまま
                使用します。``.optional()`` をチェーンすることでフィールドを任意にも
                できます。ネストした dict やリスト内の要素には適用されません
                (トップレベルの dict のキーのみ対象)。

        Returns:
            データ構造に対応する ValidKit スキーマ。

            - ``schema_overrides`` に一致するキー → 対応するバリデータ (推論をスキップ)
            - ``type_map`` に一致する型 → 対応するバリデータ (または呼び出し結果)
            - ``None``  → :class:`Validator` に ``.optional()`` を付けたもの (型不明のため optional 扱い)
            - ``dict``  → 各キーに対応するバリデータを含む dict スキーマ
            - ``list``  → :class:`ListValidator` (要素が存在する場合は最初の要素から推論)
            - ``bool``  → :class:`BoolValidator`  (int より先に評価)
            - ``int``   → :class:`NumberValidator` (int)
            - ``float`` → :class:`NumberValidator` (float)
            - ``str``   → :class:`StringValidator`

        Raises:
            TypeError: ``type_map`` に一致せず、かつサポートされていない型が渡された場合。

        Example::

            data = {"name": "Alice", "age": 30, "active": True}
            schema = v.auto_infer(data)
            # -> {"name": v.str(), "age": v.int(), "active": v.bool()}

            nested = {"user": {"id": 1, "tags": ["admin"]}}
            schema = v.auto_infer(nested)
            # -> {"user": {"id": v.int(), "tags": v.list(v.str())}}

            # None フィールドは optional なバリデータになる
            data = {"name": "Alice", "nickname": None}
            schema = v.auto_infer(data)
            # -> {"name": v.str(), "nickname": Validator().optional()}

            # カスタム型は type_map で対応できる (バリデータインスタンス)
            import datetime
            schema = v.auto_infer(
                {"ts": datetime.datetime(2024, 1, 1)},
                type_map={datetime.datetime: v.str()},
            )
            # -> {"ts": StringValidator}

            # type_map の callable がプリミティブを返す場合は再帰推論 (オプション自動変換)
            schema = v.auto_infer(
                {"ts": datetime.datetime(2024, 1, 1)},
                type_map={datetime.datetime: lambda val: val.isoformat()},
            )
            # isoformat() -> str -> auto_infer("2024-01-01T00:00:00") -> StringValidator

            # schema_overrides でフィールドを手動補完 (optional 指定も可能)
            schema = v.auto_infer(
                {"name": "Alice", "score": 9.5, "note": ""},
                schema_overrides={
                    "score": v.float().range(0.0, 10.0),
                    "note": v.str().optional(),
                },
            )
            # -> {"name": StringValidator, "score": NumberValidator(float, 0..10),
            #     "note": StringValidator(optional)}
        """
        # schema_overrides only applies at the dict level; handled inside dict branch below
        # User-supplied type_map is checked first so custom types (and overrides) are handled
        if type_map:
            for custom_type, handler in type_map.items():
                if isinstance(data, custom_type):
                    if callable(handler) and not isinstance(handler, Validator):
                        result = handler(data)
                        # If the callable returned a Validator, use it directly.
                        # Otherwise treat the result as a converted primitive and re-infer.
                        # Do not propagate schema_overrides: the converted value is not the
                        # original dict, so top-level overrides must not bleed into it.
                        if isinstance(result, Validator):
                            return result
                        return VBuilder.auto_infer(result, type_map, schema_overrides=None)
                    return handler
        # None: type cannot be inferred, mark as optional with no type constraint
        if data is None:
            return Validator().optional()
        # bool must be checked before int because bool is a subclass of int
        if isinstance(data, bool):
            return BoolValidator()
        if isinstance(data, int):
            return NumberValidator(int)
        if isinstance(data, float):
            return NumberValidator(float)
        if isinstance(data, str):
            return StringValidator()
        if isinstance(data, list):
            item_schema: Union[Validator, Dict[str, Any]] = (
                VBuilder.auto_infer(data[0], type_map) if data else StringValidator()
            )
            return ListValidator(item_schema)
        if isinstance(data, dict):
            result_schema: Dict[str, Any] = {}
            for key, value in data.items():
                if schema_overrides and key in schema_overrides:
                    result_schema[key] = schema_overrides[key]
                else:
                    result_schema[key] = VBuilder.auto_infer(value, type_map)
            return result_schema
        raise TypeError(
            f"auto_infer: unsupported type '{type(data).__name__}'. "
            "Pass a type_map to handle custom types, or use one of the built-in "
            "supported types: None, bool, int, float, str, list, dict."
        )

v = VBuilder()
