"""
tests/test_class_schema.py
クラス記法によるスキーマ定義のテスト:
  - 型アノテーション (str / int / float / bool) からのスキーマ生成
  - typing モジュールのアノテーション (Optional / List / Dict / Union)
  - Python 3.9+ 組み込みジェネリクス (list[T] / dict[K, V])
  - カスタム型 (original class) の isinstance バリデーション
  - クラス属性をデフォルト値として使用
  - Validator インスタンスをクラス属性として使用
  - v.instance() ビルダー
  - partial / base / collect_errors との組み合わせ
  - Schema.generate_sample() との組み合わせ
"""

import datetime
from typing import Dict, List, Optional
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from validkit import v, validate, ValidationError, Schema, ValidationResult


# ---------------------------------------------------------------------------
# カスタム型の準備
# ---------------------------------------------------------------------------

class Timezone:
    """テスト用オリジナルタイムゾーン型"""
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"Timezone({self.name!r})"


UTC = Timezone("UTC")
JST = Timezone("Asia/Tokyo")


# ---------------------------------------------------------------------------
# 基本的なクラス記法のテスト
# ---------------------------------------------------------------------------

class TestClassSchemaBasic:
    def test_basic_annotations_pass(self):
        """str / int / float / bool のアノテーションで辞書データを検証できる"""
        class Profile:
            name: str
            age: int
            score: float
            active: bool

        data = {"name": "Alice", "age": 30, "score": 9.5, "active": True}
        result = validate(data, Profile)
        assert result == data

    def test_missing_required_field_raises(self):
        """必須フィールドが欠けている場合は ValidationError を送出する"""
        class Profile:
            name: str
            age: int

        with pytest.raises(ValidationError) as exc_info:
            validate({"name": "Alice"}, Profile)
        assert exc_info.value.path == "age"

    def test_wrong_type_raises(self):
        """型が一致しない場合は ValidationError を送出する"""
        class Profile:
            name: str
            age: int

        with pytest.raises(ValidationError):
            validate({"name": 123, "age": 30}, Profile)

    def test_extra_keys_are_ignored(self):
        """スキーマに定義されていない余分なキーは無視される"""
        class Profile:
            name: str

        result = validate({"name": "Alice", "extra": 99}, Profile)
        assert result == {"name": "Alice"}

    def test_empty_class_schema(self):
        """アノテーションなしのクラスは空のスキーマとして扱われる"""
        class Empty:
            pass

        result = validate({}, Empty)
        assert result == {}


# ---------------------------------------------------------------------------
# カスタム型 (original) のテスト
# ---------------------------------------------------------------------------

class TestClassSchemaCustomType:
    def test_custom_type_instance_passes(self):
        """アノテーションにカスタム型を使い、正しいインスタンスで検証が通る"""
        class Config:
            name: str
            timezone: Timezone

        result = validate({"name": "server1", "timezone": UTC}, Config)
        assert result["name"] == "server1"
        assert result["timezone"] is UTC

    def test_custom_type_wrong_instance_raises(self):
        """カスタム型のアノテーションで、型が違う値を渡すとエラーになる"""
        class Config:
            name: str
            timezone: Timezone

        with pytest.raises(ValidationError) as exc_info:
            validate({"name": "server1", "timezone": "UTC"}, Config)
        assert exc_info.value.path == "timezone"

    def test_stdlib_custom_type(self):
        """datetime.datetime のような標準ライブラリのカスタム型もサポートする"""
        class Event:
            title: str
            timestamp: datetime.datetime

        now = datetime.datetime.now()
        result = validate({"title": "Launch", "timestamp": now}, Event)
        assert result["timestamp"] == now

    def test_stdlib_custom_type_wrong_value_raises(self):
        """datetime.datetime 型に str を渡すとエラーになる"""
        class Event:
            title: str
            timestamp: datetime.datetime

        with pytest.raises(ValidationError):
            validate({"title": "Launch", "timestamp": "2026-01-01"}, Event)


# ---------------------------------------------------------------------------
# デフォルト値のテスト
# ---------------------------------------------------------------------------

class TestClassSchemaDefaults:
    def test_class_attribute_as_default(self):
        """クラス属性のデフォルト値が欠損キーの補完に使われる"""
        class Config:
            host: str = "localhost"
            port: int = 5432

        result = validate({}, Config)
        assert result["host"] == "localhost"
        assert result["port"] == 5432

    def test_input_overrides_class_default(self):
        """入力値はクラス属性のデフォルト値より優先される"""
        class Config:
            host: str = "localhost"
            port: int = 5432

        result = validate({"host": "db.example.com", "port": 3306}, Config)
        assert result["host"] == "db.example.com"
        assert result["port"] == 3306

    def test_falsy_defaults(self):
        """False / 0 などの falsy なデフォルト値も正しく機能する"""
        class Settings:
            ssl: bool = False
            timeout: int = 0
            ratio: float = 0.0

        result = validate({}, Settings)
        assert result["ssl"] is False
        assert result["timeout"] == 0
        assert result["ratio"] == 0.0

    def test_custom_type_with_default(self):
        """カスタム型アノテーションのフィールドにもデフォルト値が機能する"""
        class Config:
            timezone: Timezone = UTC

        result = validate({}, Config)
        assert result["timezone"] is UTC

    def test_required_field_without_default_still_raises(self):
        """デフォルトなし必須フィールドが欠損すれば従来どおりエラー"""
        class Config:
            host: str = "localhost"
            port: int  # デフォルトなし必須

        with pytest.raises(ValidationError) as exc_info:
            validate({"host": "example.com"}, Config)
        assert exc_info.value.path == "port"


# ---------------------------------------------------------------------------
# Validator クラス属性のテスト
# ---------------------------------------------------------------------------

class TestClassSchemaValidatorAttributes:
    def test_validator_as_class_attribute(self):
        """Validator インスタンスをクラス属性として定義したフィールドが正しく動作する"""
        class Profile:
            name = v.str().regex(r"^\w{3,10}$")
            age = v.int().range(0, 150)

        result = validate({"name": "alice", "age": 25}, Profile)
        assert result == {"name": "alice", "age": 25}

    def test_validator_attribute_with_annotation(self):
        """アノテーション付きでも Validator クラス属性が優先される"""
        class Profile:
            name: str = v.str().regex(r"^\w+$")  # type: ignore[assignment]

        result = validate({"name": "alice"}, Profile)
        assert result["name"] == "alice"

    def test_validator_class_attribute_invalid_value(self):
        """Validator クラス属性のルールに違反するとエラーになる"""
        class Profile:
            name = v.str().regex(r"^\w{3,10}$")
            age = v.int().range(0, 150)

        with pytest.raises(ValidationError):
            validate({"name": "x", "age": 25}, Profile)  # name が短すぎる

    def test_validator_with_default_via_class_attribute(self):
        """Validator クラス属性に .default() を付けるとデフォルト補完が効く"""
        class Config:
            role = v.str().default("worker")
            active = v.bool().default(True)

        result = validate({}, Config)
        assert result["role"] == "worker"
        assert result["active"] is True

    def test_mixed_annotations_and_validator_attributes(self):
        """アノテーションとValidatorクラス属性の混在が正しく動作する"""
        class Profile:
            name: str               # アノテーション型ショートハンド
            age = v.int().min(0)    # Validator クラス属性

        result = validate({"name": "Bob", "age": 20}, Profile)
        assert result == {"name": "Bob", "age": 20}


# ---------------------------------------------------------------------------
# typing モジュールのアノテーション (Optional / List / Dict / Union)
# ---------------------------------------------------------------------------

class TestClassSchemaTypingAnnotations:
    def test_optional_field_can_be_omitted(self):
        """Optional[T] アノテーションのフィールドは省略可能"""
        class Profile:
            name: str
            nickname: Optional[str]

        result = validate({"name": "Alice"}, Profile)
        assert result["name"] == "Alice"
        assert "nickname" not in result

    def test_optional_field_accepts_value(self):
        """Optional[T] アノテーションのフィールドは値が渡されれば検証を通る"""
        class Profile:
            name: str
            nickname: Optional[str]

        result = validate({"name": "Alice", "nickname": "Ally"}, Profile)
        assert result["nickname"] == "Ally"

    def test_optional_field_rejects_wrong_type(self):
        """Optional[T] で型が違う値を渡すとエラーになる"""
        class Profile:
            name: str
            age: Optional[int]

        with pytest.raises(ValidationError):
            validate({"name": "Alice", "age": "thirty"}, Profile)

    def test_optional_with_default(self):
        """Optional[T] + クラス属性のデフォルト値が正しく機能する"""
        class Config:
            host: str
            timeout: Optional[int] = 30

        result = validate({"host": "example.com"}, Config)
        assert result["timeout"] == 30

    def test_list_annotation(self):
        """List[T] アノテーションで list の各要素が検証される"""
        class Report:
            scores: List[int]

        result = validate({"scores": [10, 20, 30]}, Report)
        assert result["scores"] == [10, 20, 30]

    def test_list_annotation_rejects_wrong_element_type(self):
        """List[int] に文字列要素が含まれるとエラーになる"""
        class Report:
            scores: List[int]

        with pytest.raises(ValidationError):
            validate({"scores": [10, "bad", 30]}, Report)

    def test_dict_annotation(self):
        """Dict[K, V] アノテーションで辞書の各値が検証される"""
        class Metrics:
            values: Dict[str, int]

        result = validate({"values": {"a": 1, "b": 2}}, Metrics)
        assert result["values"] == {"a": 1, "b": 2}

    def test_dict_annotation_rejects_wrong_value_type(self):
        """Dict[str, int] に文字列値が含まれるとエラーになる"""
        class Metrics:
            values: Dict[str, int]

        with pytest.raises(ValidationError):
            validate({"values": {"a": "one"}}, Metrics)

    def test_optional_custom_type(self):
        """Optional[CustomType] でカスタム型がオプショナルになる"""
        class Config:
            name: str
            timezone: Optional[Timezone]

        result = validate({"name": "srv"}, Config)
        assert "timezone" not in result

        result2 = validate({"name": "srv", "timezone": UTC}, Config)
        assert result2["timezone"] is UTC

    def test_list_of_custom_type(self):
        """List[CustomType] でカスタム型のリストを検証できる"""
        class Config:
            zones: List[Timezone]

        result = validate({"zones": [UTC, JST]}, Config)
        assert result["zones"] == [UTC, JST]

    def test_list_of_custom_type_rejects_wrong(self):
        """List[Timezone] に str が含まれるとエラーになる"""
        class Config:
            zones: List[Timezone]

        with pytest.raises(ValidationError):
            validate({"zones": [UTC, "NOT_A_TZ"]}, Config)

    def test_complex_class_with_all_types(self):
        """str / int / Optional / List / Dict / CustomType が混在するクラス"""
        class ServerConfig:
            host: str
            port: int
            ssl: bool
            tags: Optional[List[str]]
            metadata: Dict[str, int]
            timezone: Timezone

        data = {
            "host": "example.com",
            "port": 443,
            "ssl": True,
            "tags": ["web", "prod"],
            "metadata": {"requests": 1000},
            "timezone": UTC,
        }
        result = validate(data, ServerConfig)
        assert result["host"] == "example.com"
        assert result["port"] == 443
        assert result["ssl"] is True
        assert result["tags"] == ["web", "prod"]
        assert result["metadata"] == {"requests": 1000}
        assert result["timezone"] is UTC

    def test_complex_class_optional_list_omitted(self):
        """Optional[List[str]] フィールドを省略しても通る"""
        class ServerConfig:
            host: str
            port: int
            ssl: bool
            tags: Optional[List[str]]
            metadata: Dict[str, int]
            timezone: Timezone

        data = {
            "host": "example.com",
            "port": 80,
            "ssl": False,
            "metadata": {},
            "timezone": JST,
        }
        result = validate(data, ServerConfig)
        assert "tags" not in result


# ---------------------------------------------------------------------------
# Python 3.9+ 組み込みジェネリクス (list[T] / dict[K, V])
# ---------------------------------------------------------------------------

class TestClassSchemaBuiltinGenerics:
    def test_builtin_list_annotation(self):
        """Python 3.9+ の list[T] アノテーションが機能する"""
        class Report:
            scores: list[int]

        result = validate({"scores": [1, 2, 3]}, Report)
        assert result["scores"] == [1, 2, 3]

    def test_builtin_list_rejects_wrong_element(self):
        """list[int] に文字列要素が含まれるとエラーになる"""
        class Report:
            scores: list[int]

        with pytest.raises(ValidationError):
            validate({"scores": [1, "bad"]}, Report)

    def test_builtin_dict_annotation(self):
        """Python 3.9+ の dict[K, V] アノテーションが機能する"""
        class Metrics:
            values: dict[str, float]

        result = validate({"values": {"rate": 0.95}}, Metrics)
        assert result["values"]["rate"] == 0.95

    def test_builtin_dict_rejects_wrong_value(self):
        """dict[str, int] に整数でない値が含まれるとエラーになる"""
        class Metrics:
            values: dict[str, int]

        with pytest.raises(ValidationError):
            validate({"values": {"a": "bad"}}, Metrics)


# ---------------------------------------------------------------------------
# v.instance() ビルダーのテスト
# ---------------------------------------------------------------------------

class TestInstanceValidator:
    def test_instance_validator_pass(self):
        """v.instance() で正しい型のインスタンスが通る"""
        schema = {"tz": v.instance(Timezone)}
        result = validate({"tz": UTC}, schema)
        assert result["tz"] is UTC

    def test_instance_validator_fail(self):
        """v.instance() で型が違う値を渡すとエラーになる"""
        schema = {"tz": v.instance(Timezone)}
        with pytest.raises(ValidationError) as exc_info:
            validate({"tz": "UTC"}, schema)
        assert exc_info.value.path == "tz"
        assert "Expected instance of Timezone" in exc_info.value.message

    def test_instance_validator_optional(self):
        """v.instance().optional() で省略可能なカスタム型フィールドが機能する"""
        schema = {"tz": v.instance(Timezone).optional()}
        result = validate({}, schema)
        assert "tz" not in result

    def test_instance_validator_with_default(self):
        """v.instance().default() でデフォルト値補完が機能する"""
        schema = {"tz": v.instance(Timezone).default(UTC)}
        result = validate({}, schema)
        assert result["tz"] is UTC

    def test_instance_validator_stdlib_type(self):
        """v.instance() で標準ライブラリの型もサポートする"""
        schema = {"ts": v.instance(datetime.datetime)}
        now = datetime.datetime.now()
        result = validate({"ts": now}, schema)
        assert result["ts"] == now


# ---------------------------------------------------------------------------
# partial / base / collect_errors との組み合わせ
# ---------------------------------------------------------------------------

class TestClassSchemaOptions:
    def test_partial_validation(self):
        """partial=True でクラス記法スキーマの一部フィールドだけ検証できる"""
        class Config:
            host: str
            port: int

        result = validate({"host": "localhost"}, Config, partial=True)
        assert result == {"host": "localhost"}

    def test_base_merge(self):
        """base= でクラス記法スキーマに既定値をマージできる"""
        class Config:
            host: str
            port: int

        result = validate({"host": "db.local"}, Config, base={"port": 5432})
        assert result == {"host": "db.local", "port": 5432}

    def test_collect_errors(self):
        """collect_errors=True でクラス記法スキーマの複数エラーを一括収集できる"""
        class Profile:
            name: str
            age: int

        result = validate({"name": 123, "age": "thirty"}, Profile, collect_errors=True)
        assert isinstance(result, ValidationResult)
        assert len(result.errors) == 2

    def test_class_schema_with_schema_wrapper(self):
        """Schema() ラッパーはクラス記法スキーマを直接受け取れる（dict変換後に渡す）"""
        class Profile:
            name: str
            age: int

        from validkit.validator import _class_to_schema
        schema = Schema(_class_to_schema(Profile))
        result = validate({"name": "Alice", "age": 30}, schema)
        assert result == {"name": "Alice", "age": 30}


# ---------------------------------------------------------------------------
# generate_sample との組み合わせ
# ---------------------------------------------------------------------------

class TestClassSchemaGenerateSample:
    def test_generate_sample_from_class_schema(self):
        """_class_to_schema 経由で Schema.generate_sample() が動作する"""
        from validkit.validator import _class_to_schema

        class Config:
            host: str = "localhost"
            port: int = 5432
            ssl: bool = False

        schema = Schema(_class_to_schema(Config))
        sample = schema.generate_sample()
        assert sample["host"] == "localhost"
        assert sample["port"] == 5432
        assert sample["ssl"] is False

    def test_instance_validator_generates_none_sample(self):
        """InstanceValidator のサンプル値は None (型ダミーなし) になる"""
        schema = Schema({"tz": v.instance(Timezone)})
        sample = schema.generate_sample()
        assert sample["tz"] is None

    def test_instance_validator_with_default_generates_sample(self):
        """InstanceValidator に .default() があればサンプルにデフォルト値が使われる"""
        schema = Schema({"tz": v.instance(Timezone).default(UTC)})
        sample = schema.generate_sample()
        assert sample["tz"] is UTC


# ---------------------------------------------------------------------------
# Fix 1: InstanceValidator.coerce() 実装の検証
# ---------------------------------------------------------------------------

class TestInstanceValidatorCoerce:
    """v.instance(T).coerce() が型変換を試みることを検証するテスト群。"""

    def test_coerce_successful_construction(self):
        """coerce=True のとき type_cls(value) が成功すれば変換後の値が返る"""
        class Celsius:
            def __init__(self, value: float) -> None:
                self.value = float(value)
            def __repr__(self) -> str:
                return f"Celsius({self.value})"

        schema = {"temp": v.instance(Celsius).coerce()}
        # Pass a raw float → Celsius(float) should succeed
        result = validate({"temp": 36.6}, schema)
        assert isinstance(result["temp"], Celsius)
        assert result["temp"].value == 36.6

    def test_coerce_from_string(self):
        """coerce=True のとき str から型変換できる場合は成功する"""
        class Celsius:
            def __init__(self, value: float) -> None:
                self.value = float(value)

        schema = {"temp": v.instance(Celsius).coerce()}
        result = validate({"temp": "37.0"}, schema)
        assert isinstance(result["temp"], Celsius)
        assert result["temp"].value == 37.0

    def test_coerce_raises_when_construction_fails(self):
        """coerce=True でも type_cls(value) が例外を投げたらバリデーションエラー"""
        class StrictType:
            def __init__(self, value: object) -> None:
                if not isinstance(value, int):
                    raise ValueError("must be int")

        schema = {"x": v.instance(StrictType).coerce()}
        with pytest.raises(ValidationError) as exc_info:
            validate({"x": "not an int"}, schema)
        assert "Expected instance of StrictType" in exc_info.value.message

    def test_no_coerce_raises_on_wrong_type(self):
        """coerce=False (デフォルト) では型違いで即エラー"""
        schema = {"tz": v.instance(Timezone)}
        with pytest.raises(ValidationError) as exc_info:
            validate({"tz": "UTC"}, schema)
        assert "Expected instance of Timezone" in exc_info.value.message

    def test_coerce_already_correct_type_is_passthrough(self):
        """coerce=True でもすでに正しい型ならそのまま通る"""
        schema = {"tz": v.instance(Timezone).coerce()}
        result = validate({"tz": UTC}, schema)
        assert result["tz"] is UTC

    def test_coerce_with_stdlib_int(self):
        """coerce=True で int型に対して文字列数値が変換される (標準ライブラリ型)"""
        # Note: v.instance(int).coerce() does int("42") which succeeds
        schema = {"count": v.instance(int).coerce()}
        result = validate({"count": "42"}, schema)
        assert result["count"] == 42
        assert isinstance(result["count"], int)

    def test_coerce_with_optional_and_default(self):
        """coerce と optional / default の組み合わせが正しく動作する"""
        class Port:
            def __init__(self, n: int) -> None:
                self.n = int(n)

        schema = {"port": v.instance(Port).coerce().default(Port(80))}
        # value provided as raw int → coerced to Port
        r1 = validate({"port": 443}, schema)
        assert isinstance(r1["port"], Port)
        assert r1["port"].n == 443
        # value absent → default (already a Port) is returned
        r2 = validate({}, schema)
        assert isinstance(r2["port"], Port)
        assert r2["port"].n == 80


# ---------------------------------------------------------------------------
# Fix 2: _type_hint_to_validator が公開 API を使うことを検証するテスト群
# ---------------------------------------------------------------------------

class TestTypeHintToValidatorPublicAPI:
    """_type_hint_to_validator() が .optional() / .default() 公開メソッドを通じて
    validator の状態を設定することを、クラス記法経由で end-to-end に検証する。"""

    def test_optional_annotation_sets_optional_via_public_api(self):
        """Optional[T] アノテーションのフィールドは省略可能 (response に含まれない)"""
        class Config:
            host: str
            nickname: Optional[str]

        # nickname は省略しても Missing required key が出ない
        result = validate({"host": "db"}, Config)
        assert result["host"] == "db"
        assert "nickname" not in result

    def test_optional_annotation_passes_value_through(self):
        """Optional[T] で値を渡したときは検証してから応答に含まれる"""
        class Config:
            host: str
            nickname: Optional[str]

        result = validate({"host": "db", "nickname": "alias"}, Config)
        assert result["nickname"] == "alias"

    def test_optional_annotation_rejects_wrong_type(self):
        """Optional[int] に str を渡すとバリデーションエラー"""
        class Config:
            count: Optional[int]

        with pytest.raises(ValidationError):
            validate({"count": "bad"}, Config)

    def test_default_annotation_sets_default_via_public_api(self):
        """クラス属性デフォルト値がフィールド欠損時に応答に補完される"""
        class Config:
            host: str = "localhost"
            port: int = 5432

        result = validate({}, Config)
        assert result["host"] == "localhost"
        assert result["port"] == 5432

    def test_default_annotation_explicit_value_overrides_default(self):
        """入力値があればデフォルトより入力値が優先される"""
        class Config:
            port: int = 5432

        result = validate({"port": 9000}, Config)
        assert result["port"] == 9000

    def test_optional_with_default_annotation(self):
        """Optional[T] + クラス属性デフォルトの組み合わせ: 省略時はデフォルト、指定時は値"""
        class Config:
            timeout: Optional[int] = 30

        r_default = validate({}, Config)
        assert r_default["timeout"] == 30

        r_override = validate({"timeout": 60}, Config)
        assert r_override["timeout"] == 60

    def test_list_annotation_response_contains_all_elements(self):
        """List[T] アノテーションで応答がリスト全体を正確に含む"""
        class Report:
            scores: List[int]

        result = validate({"scores": [10, 20, 30]}, Report)
        assert result["scores"] == [10, 20, 30]

    def test_dict_annotation_response_contains_all_entries(self):
        """Dict[K, V] アノテーションで応答が辞書全体を正確に含む"""
        class Metrics:
            values: Dict[str, int]

        result = validate({"values": {"a": 1, "b": 2}}, Metrics)
        assert result["values"] == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# 網羅的な end-to-end レスポンス検証テスト群
# ---------------------------------------------------------------------------

class TestEndToEndClassSchemaResponse:
    """クラス記法スキーマ全体の応答値を網羅的に検証するテスト群。
    各フィールドの応答値が正確であることをアサートする。"""

    def test_full_response_with_all_basic_types(self):
        """str / int / float / bool の全フィールドが応答に正確に含まれる"""
        class Profile:
            name: str
            age: int
            score: float
            active: bool

        data = {"name": "Alice", "age": 30, "score": 9.85, "active": True}
        result = validate(data, Profile)
        assert result == {"name": "Alice", "age": 30, "score": 9.85, "active": True}

    def test_full_response_with_defaults_and_overrides(self):
        """デフォルト値と入力値が混在するときの応答全体を検証"""
        class Config:
            host: str
            port: int = 5432
            ssl: bool = False
            timeout: Optional[int] = 30

        result = validate({"host": "prod.example.com", "port": 443}, Config)
        assert result == {
            "host": "prod.example.com",
            "port": 443,
            "ssl": False,
            "timeout": 30,
        }

    def test_full_response_with_nested_list_and_dict(self):
        """List と Dict が混在するスキーマの応答全体を検証"""
        class Analytics:
            hits: List[int]
            labels: Dict[str, str]

        result = validate(
            {"hits": [100, 200, 300], "labels": {"env": "prod", "region": "us"}},
            Analytics,
        )
        assert result == {
            "hits": [100, 200, 300],
            "labels": {"env": "prod", "region": "us"},
        }

    def test_full_response_with_custom_type(self):
        """カスタム型フィールドがある応答全体を検証"""
        class Deployment:
            name: str
            timezone: Timezone

        result = validate({"name": "deploy-1", "timezone": UTC}, Deployment)
        assert result["name"] == "deploy-1"
        assert result["timezone"] is UTC

    def test_full_response_optional_fields_absent_when_not_provided(self):
        """省略可能フィールドは未指定時に応答に含まれない"""
        class UserProfile:
            username: str
            bio: Optional[str]
            website: Optional[str]

        result = validate({"username": "nana_kit"}, UserProfile)
        assert set(result.keys()) == {"username"}
        assert result["username"] == "nana_kit"

    def test_full_response_validator_attributes_respected(self):
        """Validator インスタンスをクラス属性として使ったときの応答全体を検証"""
        class Profile:
            role = v.str().default("guest")
            score = v.int().range(0, 100).default(0)

        r_defaults = validate({}, Profile)
        assert r_defaults == {"role": "guest", "score": 0}

        r_provided = validate({"role": "admin", "score": 99}, Profile)
        assert r_provided == {"role": "admin", "score": 99}

    def test_full_response_coerce_in_instance_validator(self):
        """coerce=True の InstanceValidator でのレスポンス全体を検証"""
        class Celsius:
            def __init__(self, val: float) -> None:
                self.val = float(val)

        class Reading:
            sensor: str
            temp = v.instance(Celsius).coerce()

        result = validate({"sensor": "S1", "temp": 36.6}, Reading)
        assert result["sensor"] == "S1"
        assert isinstance(result["temp"], Celsius)
        assert result["temp"].val == 36.6

    def test_full_response_collect_errors_returns_all_failures(self):
        """collect_errors=True のとき全エラーが ValidationResult.errors に収集される"""
        class Form:
            name: str
            age: int
            score: float

        result = validate(
            {"name": 42, "age": "thirty", "score": "high"},
            Form,
            collect_errors=True,
        )
        assert isinstance(result, ValidationResult)
        assert len(result.errors) >= 3

    def test_full_response_partial_validation_omits_unset_keys(self):
        """partial=True のとき不足フィールドはエラーにならず、送ったフィールドだけ応答に含まれる"""
        class Config:
            host: str
            port: int
            ssl: bool

        result = validate({"port": 8080}, Config, partial=True)
        assert result.get("port") == 8080
        assert "host" not in result

    def test_full_response_base_merge_fills_missing_fields(self):
        """base= のとき欠損フィールドがベース値でマージされる"""
        class Config:
            host: str
            port: int

        base = {"host": "old.host", "port": 5432}
        result = validate({"host": "new.host"}, Config, base=base, partial=True)
        assert result["host"] == "new.host"
        assert result["port"] == 5432

    def test_full_response_generate_sample_uses_defaults(self):
        """generate_sample() がデフォルト値をサンプルとして返す"""
        from validkit.validator import _class_to_schema

        class Config:
            host: str = "localhost"
            port: int = 5432
            ssl: bool = False
            timeout: Optional[int] = 30

        schema = Schema(_class_to_schema(Config))
        sample = schema.generate_sample()
        assert sample == {
            "host": "localhost",
            "port": 5432,
            "ssl": False,
            "timeout": 30,
        }
