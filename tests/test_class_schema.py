"""
tests/test_class_schema.py
クラス記法によるスキーマ定義のテスト:
  - 型アノテーション (str / int / float / bool) からのスキーマ生成
  - typing モジュールのアノテーション (Optional / List / Dict)
  - Python 3.9+ 組み込みジェネリクス (list[T] / dict[K, V])
  - カスタム型 (original class) の isinstance バリデーション
  - クラス属性をデフォルト値として使用
  - Validator インスタンスをクラス属性として使用
  - v.instance() ビルダー
  - partial / base / collect_errors との組み合わせ
  - Schema.generate_sample() との組み合わせ
  - 空クラスのスキーマとしての動作
  - サポート外の型 (non-optional Union) の明示的エラー
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
        """アノテーションなしのクラスはスキーマとして認識されない。
        validate() はデータをそのまま返す（パススルー）。"""
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


# ---------------------------------------------------------------------------
# Fix 5: 非 Optional の Union[T1, T2] は明示的 TypeError を送出する
# ---------------------------------------------------------------------------

class TestNonOptionalUnionRaisesError:
    """非 Optional な Union[T1, T2,...] は _type_hint_to_validator() / _class_to_schema() で
    TypeError を送出し、サイレントパススルーにならないことを検証するテスト群。"""

    def test_non_optional_union_raises_type_error_via_class_to_schema(self):
        """Union[int, str] アノテーションはクラス記法スキーマ生成時に TypeError を送出する"""
        from typing import Union
        from validkit.validator import _class_to_schema

        class BadSchema:
            value: Union[int, str]

        with pytest.raises(TypeError, match="multiple non-None members"):
            _class_to_schema(BadSchema)

    def test_non_optional_union_raises_type_error_via_type_hint_to_validator(self):
        """_type_hint_to_validator() に直接 Union[int, str] を渡しても TypeError が送出される"""
        from typing import Union
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(Union[int, str])

    def test_optional_t_does_not_raise(self):
        """Optional[T] (= Union[T, None]) は正常に動作し TypeError を送出しない"""
        from validkit.validator import _type_hint_to_validator
        from typing import Optional

        val = _type_hint_to_validator(Optional[str])
        assert val._optional is True

    def test_union_with_none_only_as_non_none_still_raises(self):
        """Union[int, str, float] (None なし) でも TypeError を送出する"""
        from typing import Union
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(Union[int, str, float])

    def test_validate_with_class_with_non_optional_union_raises(self):
        """validate() にクラス記法スキーマを渡したとき Union[T1,T2] フィールドが TypeError になる"""
        from typing import Union

        class Config:
            host: Union[str, bytes]

        with pytest.raises(TypeError, match="multiple non-None members"):
            validate({"host": "db"}, Config)


# ---------------------------------------------------------------------------
# 空クラスの動作（注: 空クラスはスキーマと認識されず、validate() でパススルーになる）
# ---------------------------------------------------------------------------

class TestEmptyClassSchema:
    """空クラス (アノテーションも Validator 属性もない) は _is_class_schema() で False になり、
    クラス記法スキーマとしては扱われないことを検証するテスト群。
    空クラスを validate() に渡すと、スキーマ処理をバイパスしてデータをそのまま返す（パススルー）。
    アノテーションや Validator 属性を持つクラスのみがスキーマとして認識される。"""

    def test_empty_class_is_not_detected_as_class_schema(self):
        """_is_class_schema() が空クラスを False と判定する（スキーマではない）"""
        from validkit.validator import _is_class_schema

        class Empty:
            pass

        assert _is_class_schema(Empty) is False

    def test_empty_class_produces_empty_dict_schema(self):
        """_class_to_schema() に空クラスを渡しても空辞書を返す（内部的には安全）"""
        from validkit.validator import _class_to_schema

        class Empty:
            pass

        assert _class_to_schema(Empty) == {}

    def test_validate_with_empty_class_passes_through_data(self):
        """空クラスはスキーマではないので validate() はデータをそのまま返す（パススルー）"""
        class Empty:
            pass

        # Empty class is NOT a class schema; validate() passes the value through unchanged.
        result = validate({"foo": 1, "bar": "baz"}, Empty)
        assert result == {"foo": 1, "bar": "baz"}

    def test_validate_with_empty_class_passes_through_empty_data(self):
        """空クラスをスキーマとして validate() に渡すと、空辞書もそのまま返す"""
        class Empty:
            pass

        result = validate({}, Empty)
        assert result == {}

    def test_validate_with_empty_class_passes_through_list_input(self):
        """空クラスはスキーマではないので、リストを渡してもそのまま返す（パススルー）"""
        class Empty:
            pass

        result = validate([1, 2, 3], Empty)
        assert result == [1, 2, 3]

    def test_validate_with_empty_class_passes_through_none_input(self):
        """空クラスはスキーマではないので None を渡してもそのまま返す（パススルー）"""
        class Empty:
            pass

        result = validate(None, Empty)
        assert result is None

    def test_basic_types_are_not_class_schemas(self):
        """基本型 (str / int / float / bool) は _is_class_schema() で False になる"""
        from validkit.validator import _is_class_schema

        for t in (str, int, float, bool):
            assert _is_class_schema(t) is False, f"{t} should not be a class schema"

    def test_validator_subclass_is_not_class_schema(self):
        """Validator のサブクラスは _is_class_schema() で False になる"""
        from validkit.validator import _is_class_schema
        from validkit.v import StringValidator

        assert _is_class_schema(StringValidator) is False

    def test_generate_sample_from_empty_class_returns_empty_dict(self):
        """空クラスを Schema でラップした generate_sample() は空辞書を返す"""
        from validkit.validator import _class_to_schema

        class Empty:
            pass

        schema = Schema(_class_to_schema(Empty))
        assert schema.generate_sample() == {}


# ---------------------------------------------------------------------------
# _is_class_schema() の過剰検出リグレッション防止テスト
# ---------------------------------------------------------------------------

class TestIsClassSchemaTooBroad:
    """_is_class_schema() が標準ライブラリクラスや任意クラスを
    誤ってクラス記法スキーマと判定しないことを検証するテスト群。

    これらのテストは「すべての非基本・非 Validator クラスを True にする」修正の
    リグレッション（後退）を防ぐために作成した。
    正しい動作: own __annotations__ または Validator 属性を持つクラスのみを True とする。
    """

    def test_datetime_datetime_is_not_a_class_schema(self):
        """datetime.datetime はスキーマではなく型として使われるべきなので False"""
        import datetime
        from validkit.validator import _is_class_schema

        assert _is_class_schema(datetime.datetime) is False

    def test_datetime_date_is_not_a_class_schema(self):
        """datetime.date も同様に False"""
        import datetime
        from validkit.validator import _is_class_schema

        assert _is_class_schema(datetime.date) is False

    def test_pathlib_path_is_not_a_class_schema(self):
        """pathlib.Path もスキーマと誤認されてはならない"""
        import pathlib
        from validkit.validator import _is_class_schema

        assert _is_class_schema(pathlib.Path) is False

    def test_empty_class_is_not_a_class_schema(self):
        """アノテーションも Validator 属性もない空クラスはクラス記法スキーマと見なさない"""
        from validkit.validator import _is_class_schema

        class Empty:
            pass

        assert _is_class_schema(Empty) is False

    def test_annotated_class_is_a_class_schema(self):
        """型アノテーションを持つユーザー定義クラスはクラス記法スキーマとして認識される"""
        from validkit.validator import _is_class_schema

        class Profile:
            name: str
            age: int

        assert _is_class_schema(Profile) is True

    def test_validator_attr_class_is_a_class_schema(self):
        """Validator 属性のみを持つクラスはクラス記法スキーマとして認識される"""
        from validkit.validator import _is_class_schema

        class Config:
            role = v.str()

        assert _is_class_schema(Config) is True

    def test_validate_with_datetime_class_does_not_treat_as_empty_schema(self):
        """validate() で datetime.datetime を schema に渡しても誤って {} スキーマで処理されない"""
        import datetime
        from validkit.validator import _is_class_schema

        # With the overly-broad _is_class_schema(), validate(data, datetime.datetime) would
        # try to validate data as an empty dict schema, stripping all keys to {}.
        # The correct behavior is to NOT treat datetime.datetime as a class schema,
        # so validate() passes the data through unchanged (passthrough path).
        assert _is_class_schema(datetime.datetime) is False

        data = {"year": 2024, "month": 1, "day": 15}
        result = validate(data, datetime.datetime)
        # Must NOT silently strip all keys to {}
        assert result == data


# ---------------------------------------------------------------------------
# TDD Cycle 2: 新しいレビュー指摘への対応
# ---------------------------------------------------------------------------

class TestUnionWithNoneErrorMessage:
    """Union 型のエラーメッセージが正確であることを検証するテスト群。
    複数の非 None メンバーを持つ Union アノテーションは TypeError を送出し、
    エラーメッセージは正確に問題を説明しなければならない。"""

    def test_union_with_none_and_multiple_non_none_raises_with_accurate_message(self):
        """Union[int, str, None] は非 None メンバーが複数あるため TypeError を送出する"""
        from typing import Union
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(Union[int, str, None])

    def test_union_without_none_still_raises_type_error(self):
        """Union[int, str] (None なし) は引き続き TypeError を送出する"""
        from typing import Union
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(Union[int, str])

    def test_union_int_str_none_error_message_contains_type_repr(self):
        """エラーメッセージはどの型アノテーションが問題かを repr で含む"""
        from typing import Union
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError) as exc_info:
            _type_hint_to_validator(Union[int, str, None])

        # The hint repr (e.g. "typing.Union[int, str, NoneType]") must be in the message
        assert "typing.Union" in str(exc_info.value), (
            "Error message should include the exact hint repr so users know what failed"
        )


class TestInstanceValidatorExceptionChaining:
    """InstanceValidator.coerce() が元の例外を正しくチェーンすることを検証。"""

    def test_coercion_failure_chains_original_exception(self):
        """coerce() が失敗したとき、送出される TypeError は元の例外を __cause__ に持つ"""
        from validkit import v

        class StrictType:
            def __init__(self, value: str) -> None:
                raise ValueError(f"Cannot construct from {value!r}")

        validator = v.instance(StrictType).coerce()

        with pytest.raises(TypeError) as exc_info:
            validator.validate("bad_value")

        assert exc_info.value.__cause__ is not None, (
            "TypeError raised by coerce() should chain the original exception via 'raise ... from e'"
        )
        assert isinstance(exc_info.value.__cause__, ValueError), (
            "The chained exception should be the original ValueError from the constructor"
        )

    def test_coercion_failure_chain_preserves_original_message(self):
        """チェーンされた例外は元のコンストラクタのメッセージを保持する"""
        from validkit import v

        class StrictType:
            def __init__(self, value: str) -> None:
                raise ValueError("original error message")

        validator = v.instance(StrictType).coerce()

        with pytest.raises(TypeError) as exc_info:
            validator.validate("bad_value")

        assert "original error message" in str(exc_info.value.__cause__)


class TestClassSchemaAnnotationInheritance:
    """_class_to_schema() が継承されたアノテーションを含めず、
    クラス自身の __dict__ からのみアノテーションを読み取ることを検証。"""

    def test_class_to_schema_uses_own_annotations_only(self):
        """_class_to_schema() は cls.__dict__ のアノテーションのみ処理する"""
        from validkit.validator import _class_to_schema

        class Base:
            x: int

        class ChildWithValidatorAttr(Base):
            role = v.str()  # Validator attr → treated as schema

        schema = _class_to_schema(ChildWithValidatorAttr)
        # Only own fields should appear; 'x' is inherited from Base, not declared on Child
        assert "role" in schema, "'role' (Validator attr) must be in schema"
        assert "x" not in schema, "'x' (inherited from Base) must NOT be in schema"

    def test_validate_with_child_schema_excludes_parent_annotations(self):
        """validate() でも親クラスのアノテーションは引き継がれない"""
        from validkit.validator import validate
        from validkit import v

        class Base:
            x: int

        class ChildSchema(Base):
            role = v.str()  # Only this is owned

        # 'role' is required; 'x' (from Base) should NOT be required
        result = validate({"role": "admin"}, ChildSchema)
        assert result == {"role": "admin"}
        assert "x" not in result


# ---------------------------------------------------------------------------
# TDD Cycle 3: PEP 604 ユニオン記法 (T | None, T1 | T2) のサポート
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="PEP 604 union syntax (T | None) creates types.UnionType only on Python 3.10+",
)
class TestPEP604UnionSyntax:
    """Python 3.10+ の PEP 604 パイプ記法 (T | None, T1 | T2) が
    typing.Optional / typing.Union と同等に処理されることを検証するテスト群。

    PEP 604 の T | None 記法は Python 3.10+ でのみ有効なため、
    このテストクラスは Python 3.10 未満では自動的にスキップされる。
    """

    # ---- Optional-like: T | None ----

    def test_str_or_none_is_optional(self):
        """str | None は Optional[str] と同等に扱われ、省略可能フィールドになる"""
        from validkit.validator import _type_hint_to_validator
        val = _type_hint_to_validator(str | None)
        assert val._optional is True, "str | None validator must be optional"

    def test_str_or_none_passes_string_value(self):
        """str | None アノテーションのフィールドは文字列値を受け入れる"""
        from validkit import validate

        class Schema:
            nickname: str | None

        result = validate({"nickname": "Alice"}, Schema)
        assert result == {"nickname": "Alice"}

    def test_str_or_none_allows_missing_field(self):
        """str | None アノテーションのフィールドは省略可能"""
        from validkit import validate

        class Schema:
            nickname: str | None

        result = validate({}, Schema)
        assert "nickname" not in result or result.get("nickname") is None

    def test_int_or_none_is_optional(self):
        """int | None は Optional[int] と同等に扱われ、省略可能フィールドになる"""
        from validkit.validator import _type_hint_to_validator
        val = _type_hint_to_validator(int | None)
        assert val._optional is True

    def test_none_or_str_is_optional(self):
        """None | str も str | None と同等に扱われる"""
        from validkit.validator import _type_hint_to_validator
        val = _type_hint_to_validator(None | str)
        assert val._optional is True

    def test_pep604_optional_rejects_wrong_type(self):
        """str | None フィールドに非文字列を渡すと ValidationError が送出される"""
        from validkit import validate, ValidationError

        class Schema:
            label: str | None

        with pytest.raises((TypeError, ValidationError)):
            validate({"label": 123}, Schema)

    # ---- Multi-member: T1 | T2 (should raise TypeError) ----

    def test_int_or_str_raises_type_error(self):
        """int | str は複数の非 None メンバーを持つため TypeError を送出する"""
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(int | str)

    def test_int_or_str_or_none_raises_type_error(self):
        """int | str | None も複数の非 None メンバーを持つため TypeError を送出する"""
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError, match="multiple non-None members"):
            _type_hint_to_validator(int | str | None)

    def test_validate_with_class_using_multi_member_pep604_raises(self):
        """クラスアノテーションに int | str を使うと validate() が TypeError を送出する"""
        from validkit import validate

        class BadSchema:
            value: int | str

        with pytest.raises(TypeError, match="multiple non-None members"):
            validate({"value": 1}, BadSchema)

    # ---- Validator type (inner type) is correct ----

    def test_str_or_none_inner_validator_is_string_validator(self):
        """str | None から生成される内部バリデータは StringValidator であるべき"""
        from validkit.validator import _type_hint_to_validator
        from validkit.v import StringValidator
        val = _type_hint_to_validator(str | None)
        assert isinstance(val, StringValidator), (
            f"Expected StringValidator, got {type(val).__name__}"
        )

    def test_int_or_none_inner_validator_is_int_validator(self):
        """int | None から生成される内部バリデータは NumberValidator であるべき"""
        from validkit.validator import _type_hint_to_validator
        from validkit.v import NumberValidator
        val = _type_hint_to_validator(int | None)
        assert isinstance(val, NumberValidator), (
            f"Expected NumberValidator, got {type(val).__name__}"
        )

    def test_list_or_none_produces_optional_list_validator(self):
        """list[str] | None は省略可能な ListValidator を生成する"""
        from validkit.validator import _type_hint_to_validator
        from validkit.v import ListValidator
        val = _type_hint_to_validator(list[str] | None)
        assert isinstance(val, ListValidator)
        assert val._optional is True

    def test_pep604_error_message_contains_hint_repr(self):
        """TypeError のメッセージはヒントの repr を含む"""
        from validkit.validator import _type_hint_to_validator

        with pytest.raises(TypeError) as exc_info:
            _type_hint_to_validator(int | str)

        assert "int" in str(exc_info.value) or "str" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TDD Cycle 4: Python 3.9 互換性 (types.UnionType ガード)
# ---------------------------------------------------------------------------

class TestPEP604Python39Compatibility:
    """Python 3.9 では types.UnionType が存在しない。
    _type_hint_to_validator() がモジュールレベルの _UnionType ガード変数を使用し、
    呼び出し時に _types.UnionType を直接参照しないことを検証する。
    (呼び出し時直接参照は Python 3.9 で AttributeError を発生させる)"""

    def test_module_has_union_type_guard(self):
        """validkit.validator モジュールは _UnionType モジュールレベル変数を持つ必要がある。
        Python 3.10+ では types.UnionType に設定され、Python 3.9 では None になる。"""
        import validkit.validator as vmod
        assert hasattr(vmod, '_UnionType'), (
            "_UnionType module-level guard not found in validkit.validator. "
            "This is required for Python 3.9 compatibility where types.UnionType "
            "does not exist."
        )

    def test_non_union_hints_work_when_union_type_guard_is_none(self):
        """_UnionType を None に設定した状態 (Python 3.9 シミュレーション) でも
        基本型ヒントが AttributeError を発生させない。"""
        import validkit.validator as vmod

        original = vmod._UnionType
        try:
            vmod._UnionType = None  # Simulate Python 3.9: no types.UnionType
            val_str = vmod._type_hint_to_validator(str)
            val_int = vmod._type_hint_to_validator(int)
            val_float = vmod._type_hint_to_validator(float)
            val_bool = vmod._type_hint_to_validator(bool)
            assert val_str is not None
            assert val_int is not None
            assert val_float is not None
            assert val_bool is not None
        except AttributeError as e:
            pytest.fail(
                f"AttributeError raised on non-union hint when _UnionType=None "
                f"(Python 3.9 incompatibility): {e}"
            )
        finally:
            vmod._UnionType = original

    def test_optional_hint_works_when_union_type_guard_is_none(self):
        """typing.Optional[str] は _UnionType=None でも正しく処理される。"""
        from typing import Optional
        import validkit.validator as vmod

        original = vmod._UnionType
        try:
            vmod._UnionType = None  # Simulate Python 3.9
            val = vmod._type_hint_to_validator(Optional[str])
            assert val is not None
            assert val._optional is True
        except AttributeError as e:
            pytest.fail(
                f"AttributeError raised on Optional[str] when _UnionType=None: {e}"
            )
        finally:
            vmod._UnionType = original

    def test_list_hint_works_when_union_type_guard_is_none(self):
        """List[str] は _UnionType=None でも正しく処理される。"""
        from typing import List
        import validkit.validator as vmod

        original = vmod._UnionType
        try:
            vmod._UnionType = None  # Simulate Python 3.9
            val = vmod._type_hint_to_validator(List[str])
            assert val is not None
        except AttributeError as e:
            pytest.fail(
                f"AttributeError raised on List[str] when _UnionType=None: {e}"
            )
        finally:
            vmod._UnionType = original

    def test_validate_with_class_schema_works_when_union_type_guard_is_none(self):
        """validate() でクラススキーマを使っても _UnionType=None で動作する。"""
        from typing import Optional
        from validkit import validate
        import validkit.validator as vmod

        class Schema:
            name: str
            age: Optional[int]

        original = vmod._UnionType
        try:
            vmod._UnionType = None  # Simulate Python 3.9
            result = validate({"name": "Alice", "age": 30}, Schema)
            assert result["name"] == "Alice"
            assert result["age"] == 30
        except AttributeError as e:
            pytest.fail(
                f"AttributeError raised in validate() when _UnionType=None: {e}"
            )
        finally:
            vmod._UnionType = original

    def test_union_type_guard_value_on_current_python(self):
        """現在の Python バージョンに応じた _UnionType の値を検証する。"""
        import types
        import validkit.validator as vmod

        if sys.version_info >= (3, 10):
            assert vmod._UnionType is types.UnionType, (
                "On Python 3.10+, _UnionType must be types.UnionType"
            )
        else:
            assert vmod._UnionType is None, (
                "On Python < 3.10, _UnionType must be None"
            )


# ---------------------------------------------------------------------------
# TDD Cycle 5: _UnionType annotation must not use PEP 604 (T | None) syntax
# ---------------------------------------------------------------------------

class TestUnionTypeAnnotationPython39Safe:
    """_UnionType の型アノテーション `type | None` は Python 3.9 で
    `TypeError` を発生させる (PEP 604 は実行時注釈としては 3.10+ のみ対応)。
    正しくは `Optional[type]` を使う必要がある。"""

    def test_union_type_annotation_does_not_use_pep604_syntax(self):
        """validator.py の _UnionType アノテーションが PEP 604 記法でないことを検証する。
        `type | None` は Python 3.9 の import 時に TypeError を発生させる。"""
        import ast
        import pathlib
        import validkit.validator as vmod

        # Locate the source file dynamically so this test works in any environment
        validator_src = pathlib.Path(vmod.__file__).read_text(encoding="utf-8")

        tree = ast.parse(validator_src)

        pep604_union_annotations: List[str] = []
        for node in ast.walk(tree):
            # AnnAssign: variable: annotation = value
            if not isinstance(node, ast.AnnAssign):
                continue
            # Check if the target is _UnionType
            if not (isinstance(node.target, ast.Name) and node.target.id == "_UnionType"):
                continue
            # BinOp with BitOr is the AST form of PEP 604 T | U
            if isinstance(node.annotation, ast.BinOp) and isinstance(
                node.annotation.op, ast.BitOr
            ):
                pep604_union_annotations.append(ast.unparse(node))

        assert not pep604_union_annotations, (
            f"_UnionType uses PEP 604 (T | None) syntax in its annotation, "
            f"which causes TypeError on Python 3.9: {pep604_union_annotations}. "
            f"Use Optional[type] instead."
        )

    def test_validator_module_importable_when_union_type_is_none(self):
        """_UnionType が None のときでも validkit.validator が正常にインポートできる。
        (Python 3.9 シミュレーション)"""
        import validkit.validator as vmod

        original = vmod._UnionType
        try:
            vmod._UnionType = None
            # Re-accessing module attributes must not raise
            assert hasattr(vmod, "_is_class_schema")
            assert hasattr(vmod, "_class_to_schema")
            assert hasattr(vmod, "_type_hint_to_validator")
        finally:
            vmod._UnionType = original
