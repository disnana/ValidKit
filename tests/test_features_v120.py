"""
tests/test_features_v120.py
v1.2.0 新機能のテスト:
  - .default() によるデフォルト値補完
  - .examples() によるサンプル情報の保持
  - .description() による説明文の保持
  - Schema.generate_sample() によるサンプルデータ生成 (ネスト対応)
  - 後方互換性の保証
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from validkit import v, Schema, validate, ValidationError


# ============================================================
# .default() のテスト
# ============================================================

class TestDefault:
    def test_default_is_used_when_key_is_missing(self):
        """キーが欠損した場合にデフォルト値が補完される"""
        schema = Schema({"name": v.str().default("anonymous"), "age": v.int()})
        result = validate({"age": 25}, schema)
        assert result["name"] == "anonymous"
        assert result["age"] == 25

    def test_input_value_takes_priority_over_default(self):
        """明示的に入力した値はデフォルト値より優先される (後方互換)"""
        schema = Schema({"region": v.str().default("ap-northeast-1")})
        result = validate({"region": "us-west-2"}, schema)
        assert result["region"] == "us-west-2"  # デフォルト値 ap-northeast-1 に上書きされない

    def test_default_makes_field_optional_automatically(self):
        """.default() を設定したフィールドは省略可能になる"""
        schema = Schema({"host": v.str().default("localhost"), "port": v.int()})
        # port のみ渡した場合、host が欠損してもエラーにならない
        result = validate({"port": 5432}, schema)
        assert result["host"] == "localhost"

    def test_required_field_without_default_still_raises(self):
        """デフォルトなしの必須フィールドが欠損した場合はエラー (後方互換)"""
        schema = Schema({"username": v.str(), "email": v.str().default("none@example.com")})
        with pytest.raises(ValidationError) as exc_info:
            validate({"email": "user@example.com"}, schema)
        assert exc_info.value.path == "username"

    def test_default_with_bool_false(self):
        """False や 0 などの falsy なデフォルト値も正しく機能する"""
        schema = Schema({
            "ssl": v.bool().default(False),
            "timeout": v.int().default(0),
        })
        result = validate({}, schema)
        assert result["ssl"] is False
        assert result["timeout"] == 0

    def test_default_in_nested_list(self):
        """ネストしたリスト内の辞書スキーマでもデフォルト値が補完される"""
        schema = Schema({
            "nodes": v.list({
                "ip": v.str(),
                "role": v.str().default("worker"),
            })
        })
        result = validate({"nodes": [{"ip": "10.0.0.1"}]}, schema)
        assert result["nodes"][0]["role"] == "worker"

    def test_default_with_validate_partial_and_base_still_work(self):
        """partial=True / base= は引き続き動作し、デフォルト値と共存できる"""
        schema = Schema({
            "theme": v.str().default("light"),
            "lang": v.str(),
        })
        base = {"lang": "ja"}
        result = validate({}, schema, partial=True, base=base)
        assert result["lang"] == "ja"      # base から補完
        assert result["theme"] == "light"  # default から補完


# ============================================================
# .examples() のテスト
# ============================================================

class TestExamples:
    def test_examples_stored_correctly(self):
        """.examples() に渡したリストが保持される"""
        validator = v.str().examples(["alice", "bob", "charlie"])
        assert validator._examples == ["alice", "bob", "charlie"]

    def test_examples_does_not_affect_validation(self):
        """.examples() はバリデーションに影響しない"""
        schema = Schema({"name": v.str().examples(["alice", "bob"])})
        # examples に含まれない値も通る
        result = validate({"name": "carol"}, schema)
        assert result["name"] == "carol"

    def test_examples_chained_with_other_options(self):
        """.examples() は他のオプションとチェーンできる"""
        validator = v.str().default("guest").examples(["alice", "bob"]).description("ユーザー名")
        assert validator._has_default is True
        assert validator._default_value == "guest"
        assert validator._examples[0] == "alice"
        assert validator._description == "ユーザー名"


# ============================================================
# .description() のテスト
# ============================================================

class TestDescription:
    def test_description_stored_correctly(self):
        """.description() に渡した文字列が保持される"""
        validator = v.int().description("接続ポート番号")
        assert validator._description == "接続ポート番号"

    def test_description_does_not_affect_validation(self):
        """.description() はバリデーションに影響しない"""
        schema = Schema({"port": v.int().range(1, 65535).description("ポート番号")})
        result = validate({"port": 8080}, schema)
        assert result["port"] == 8080


# ============================================================
# Schema.generate_sample() のテスト
# ============================================================

class TestGenerateSample:
    def test_default_value_used_in_sample(self):
        """generate_sample() で .default() の値が採用される"""
        schema = Schema({
            "host": v.str().default("localhost"),
            "ssl": v.bool().default(False),
        })
        sample = schema.generate_sample()
        assert sample["host"] == "localhost"
        assert sample["ssl"] is False

    def test_examples_first_element_used_when_no_default(self):
        """generate_sample() で default がない場合は examples の先頭が採用される"""
        schema = Schema({
            "region": v.str().examples(["ap-northeast-1", "us-west-2"]),
        })
        sample = schema.generate_sample()
        assert sample["region"] == "ap-northeast-1"

    def test_type_dummy_used_when_neither_default_nor_examples(self):
        """generate_sample() で default も examples もない場合は型ダミーが採用される"""
        schema = Schema({
            "name": v.str(),
            "count": v.int(),
            "score": v.float(),
            "active": v.bool(),
        })
        sample = schema.generate_sample()
        assert isinstance(sample["name"], str)
        assert isinstance(sample["count"], int)
        assert isinstance(sample["score"], float)
        assert isinstance(sample["active"], bool)

    def test_priority_default_over_examples(self):
        """generate_sample() での優先順位: default > examples"""
        schema = Schema({
            "port": v.int().default(5432).examples([3306, 8080]),
        })
        sample = schema.generate_sample()
        assert sample["port"] == 5432  # examples の先頭 (3306) より default が優先

    def test_nested_dict_schema_recursive(self):
        """generate_sample() はネストした dict スキーマを再帰的に処理する"""
        schema = Schema({
            "database": {
                "host": v.str().default("db.local"),
                "port": v.int().default(5432),
            }
        })
        sample = schema.generate_sample()
        assert sample["database"]["host"] == "db.local"
        assert sample["database"]["port"] == 5432

    def test_nested_list_validator_recursive(self):
        """generate_sample() はリスト内のネストスキーマも再帰的に処理する"""
        schema = Schema({
            "nodes": v.list({
                "ip": v.str().examples(["192.168.1.10"]),
                "role": v.str().default("worker"),
            })
        })
        sample = schema.generate_sample()
        assert isinstance(sample["nodes"], list)
        assert len(sample["nodes"]) == 1
        assert sample["nodes"][0]["ip"] == "192.168.1.10"
        assert sample["nodes"][0]["role"] == "worker"

    def test_oneof_validator_in_sample(self):
        """generate_sample() で oneof バリデータは選択肢の先頭を返す"""
        schema = Schema({
            "theme": v.oneof(["light", "dark"]),
        })
        sample = schema.generate_sample()
        assert sample["theme"] == "light"

    def test_generate_sample_does_not_modify_schema(self):
        """generate_sample() はスキーマオブジェクト自体を変更しない"""
        schema = Schema({"host": v.str().default("localhost")})
        sample1 = schema.generate_sample()
        sample2 = schema.generate_sample()
        assert sample1 == sample2
