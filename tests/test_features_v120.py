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


# ============================================================
# v.auto_infer() のテスト
# ============================================================

class TestAutoInfer:
    def test_primitive_str(self):
        """str 値から StringValidator が生成される"""
        from validkit.v import StringValidator
        schema = v.auto_infer("hello")
        assert isinstance(schema, StringValidator)

    def test_primitive_int(self):
        """int 値から NumberValidator(int) が生成される"""
        from validkit.v import NumberValidator
        schema = v.auto_infer(42)
        assert isinstance(schema, NumberValidator)
        assert schema._type_cls is int

    def test_primitive_float(self):
        """float 値から NumberValidator(float) が生成される"""
        from validkit.v import NumberValidator
        schema = v.auto_infer(3.14)
        assert isinstance(schema, NumberValidator)
        assert schema._type_cls is float

    def test_primitive_bool(self):
        """bool 値から BoolValidator が生成される (int の前に評価される)"""
        from validkit.v import BoolValidator
        schema = v.auto_infer(True)
        assert isinstance(schema, BoolValidator)

    def test_bool_not_confused_with_int(self):
        """bool は int のサブクラスだが、NumberValidator ではなく BoolValidator が返る"""
        from validkit.v import BoolValidator, NumberValidator
        schema_true = v.auto_infer(True)
        schema_false = v.auto_infer(False)
        assert isinstance(schema_true, BoolValidator)
        assert isinstance(schema_false, BoolValidator)
        # False (== 0) が int と誤認されないことを確認
        assert not isinstance(schema_false, NumberValidator)

    def test_list_with_str_elements(self):
        """str 要素のリストから v.list(v.str()) が生成される"""
        from validkit.v import ListValidator, StringValidator
        schema = v.auto_infer(["a", "b", "c"])
        assert isinstance(schema, ListValidator)
        assert isinstance(schema._item_validator, StringValidator)

    def test_list_with_int_elements(self):
        """int 要素のリストから v.list(v.int()) が生成される"""
        from validkit.v import ListValidator, NumberValidator
        schema = v.auto_infer([1, 2, 3])
        assert isinstance(schema, ListValidator)
        assert isinstance(schema._item_validator, NumberValidator)
        assert schema._item_validator._type_cls is int

    def test_empty_list_defaults_to_str(self):
        """空リストは v.list(v.str()) にデフォルトされる"""
        from validkit.v import ListValidator, StringValidator
        schema = v.auto_infer([])
        assert isinstance(schema, ListValidator)
        assert isinstance(schema._item_validator, StringValidator)

    def test_flat_dict(self):
        """フラットな dict から対応するバリデータを持つ dict スキーマが生成される"""
        from validkit.v import StringValidator, NumberValidator, BoolValidator
        data = {"name": "Alice", "age": 30, "active": True}
        schema = v.auto_infer(data)
        assert isinstance(schema, dict)
        assert isinstance(schema["name"], StringValidator)
        assert isinstance(schema["age"], NumberValidator)
        assert schema["age"]._type_cls is int
        assert isinstance(schema["active"], BoolValidator)

    def test_nested_dict(self):
        """ネストした dict は再帰的にスキーマ化される"""
        from validkit.v import StringValidator, NumberValidator
        data = {"user": {"id": 1, "name": "Bob"}}
        schema = v.auto_infer(data)
        assert isinstance(schema, dict)
        assert isinstance(schema["user"], dict)
        assert isinstance(schema["user"]["id"], NumberValidator)
        assert isinstance(schema["user"]["name"], StringValidator)

    def test_dict_with_list_value(self):
        """dict 内の list フィールドも正しく推論される"""
        from validkit.v import ListValidator, StringValidator
        data = {"tags": ["python", "java"]}
        schema = v.auto_infer(data)
        assert isinstance(schema, dict)
        assert isinstance(schema["tags"], ListValidator)
        assert isinstance(schema["tags"]._item_validator, StringValidator)

    def test_inferred_schema_can_validate_original_data(self):
        """auto_infer で生成したスキーマで元データをバリデーションできる"""
        data = {"name": "Alice", "age": 30, "score": 9.5, "active": True}
        schema = v.auto_infer(data)
        result = validate(data, schema)
        assert result["name"] == "Alice"
        assert result["age"] == 30
        assert result["score"] == 9.5
        assert result["active"] is True

    def test_inferred_nested_schema_can_validate_original_data(self):
        """ネスト付き auto_infer スキーマで元データをバリデーションできる"""
        data = {"user": {"id": 1, "tags": ["admin", "editor"]}}
        schema = v.auto_infer(data)
        result = validate(data, schema)
        assert result["user"]["id"] == 1
        assert result["user"]["tags"] == ["admin", "editor"]

    def test_none_returns_optional_validator(self):
        """None 値から optional な基底 Validator が生成される"""
        from validkit.v import Validator
        schema = v.auto_infer(None)
        assert isinstance(schema, Validator)
        assert schema._optional is True

    def test_dict_with_none_field_is_optional(self):
        """dict 内の None フィールドは optional なバリデータになる"""
        from validkit.v import Validator
        data = {"name": "Alice", "nickname": None}
        schema = v.auto_infer(data)
        assert isinstance(schema["nickname"], Validator)
        assert schema["nickname"]._optional is True

    def test_dict_with_none_field_validates_with_none(self):
        """auto_infer した None フィールドは None 値でバリデーションが通る"""
        data = {"name": "Alice", "nickname": None}
        schema = v.auto_infer(data)
        result = validate(data, schema)
        assert result["name"] == "Alice"
        assert result.get("nickname") is None

    def test_unsupported_type_raises_type_error(self):
        """サポートされていない型 (カスタムクラスなど) は TypeError を送出する"""
        import datetime
        with pytest.raises(TypeError, match="auto_infer: unsupported type"):
            v.auto_infer(datetime.datetime.now())

    def test_dict_with_unsupported_type_raises_type_error(self):
        """dict 内にサポートされていない型が含まれると TypeError を送出する"""
        import datetime
        data = {"name": "Alice", "created_at": datetime.date(2024, 1, 1)}
        with pytest.raises(TypeError, match="auto_infer: unsupported type"):
            v.auto_infer(data)

    def test_type_map_with_validator_instance(self):
        """type_map にバリデータインスタンスを渡すとカスタム型を処理できる"""
        import datetime
        from validkit.v import StringValidator
        schema = v.auto_infer(
            datetime.datetime(2024, 1, 1),
            type_map={datetime.datetime: v.str()},
        )
        assert isinstance(schema, StringValidator)

    def test_type_map_with_callable(self):
        """type_map に呼び出し可能オブジェクトを渡すと値を受けて Validator を返せる"""
        import datetime
        from validkit.v import StringValidator
        dt = datetime.datetime(2024, 6, 15, 12, 0, 0)
        schema = v.auto_infer(
            dt,
            type_map={datetime.datetime: lambda val: v.str().description(str(val))},
        )
        assert isinstance(schema, StringValidator)
        assert schema._description == str(dt)

    def test_type_map_in_dict_field(self):
        """dict 内のカスタム型フィールドも type_map で処理される"""
        import datetime
        from validkit.v import StringValidator
        data = {"name": "Alice", "created_at": datetime.date(2024, 1, 1)}
        schema = v.auto_infer(data, type_map={datetime.date: v.str()})
        assert isinstance(schema["name"], StringValidator)
        assert isinstance(schema["created_at"], StringValidator)

    def test_type_map_in_list_element(self):
        """list 内のカスタム型も type_map で処理される"""
        import datetime
        from validkit.v import ListValidator, StringValidator
        data = [datetime.date(2024, 1, 1), datetime.date(2024, 2, 1)]
        schema = v.auto_infer(data, type_map={datetime.date: v.str()})
        assert isinstance(schema, ListValidator)
        assert isinstance(schema._item_validator, StringValidator)

    def test_type_map_with_custom_class(self):
        """ユーザー定義のカスタムクラスも type_map で処理できる"""
        from validkit.v import StringValidator

        class MyModel:
            def __init__(self, name: str) -> None:
                self.name = name

        schema = v.auto_infer(MyModel("test"), type_map={MyModel: v.str()})
        assert isinstance(schema, StringValidator)

    def test_type_map_without_match_still_raises_type_error(self):
        """type_map に対象型がなければ依然として TypeError が送出される"""
        import datetime

        class Unrelated:
            pass

        with pytest.raises(TypeError, match="auto_infer: unsupported type"):
            v.auto_infer(
                Unrelated(),
                type_map={datetime.date: v.str()},  # Unrelated は含まれない
            )

    # ---- type_map 自動変換 (callable がプリミティブを返す) ---

    def test_type_map_callable_returning_str_re_infers(self):
        """type_map の callable が str を返す場合 → StringValidator として再推論される"""
        import datetime
        from validkit.v import StringValidator
        schema = v.auto_infer(
            datetime.date(2024, 1, 1),
            type_map={datetime.date: lambda val: val.isoformat()},
        )
        assert isinstance(schema, StringValidator)

    def test_type_map_callable_returning_int_re_infers(self):
        """type_map の callable が int を返す場合 → NumberValidator(int) として再推論される"""
        import datetime
        from validkit.v import NumberValidator
        schema = v.auto_infer(
            datetime.date(2024, 1, 1),
            type_map={datetime.date: lambda val: val.toordinal()},
        )
        assert isinstance(schema, NumberValidator)
        assert schema._type_cls is int

    def test_type_map_callable_returning_dict_re_infers(self):
        """type_map の callable が dict を返す場合 → ネスト dict スキーマとして再推論される"""
        import datetime
        from validkit.v import StringValidator, NumberValidator
        schema = v.auto_infer(
            datetime.date(2024, 6, 15),
            type_map={
                datetime.date: lambda val: {"year": val.year, "month": val.month, "day": val.day}
            },
        )
        assert isinstance(schema, dict)
        assert isinstance(schema["year"], NumberValidator)
        assert isinstance(schema["month"], NumberValidator)
        assert isinstance(schema["day"], NumberValidator)

    def test_type_map_callable_returning_validator_used_directly(self):
        """type_map の callable が Validator を返す場合はそのまま使用される (再推論なし)"""
        import datetime
        from validkit.v import StringValidator
        dt = datetime.datetime(2024, 6, 15, 12, 0, 0)
        schema = v.auto_infer(
            dt,
            type_map={datetime.datetime: lambda val: v.str().description(str(val))},
        )
        assert isinstance(schema, StringValidator)
        assert schema._description == str(dt)

    def test_type_map_auto_convert_in_dict_field(self):
        """dict フィールドの auto-convert callable も正しく re-infer される"""
        import datetime
        from validkit.v import StringValidator, NumberValidator
        data = {"name": "Alice", "created_at": datetime.date(2024, 1, 1)}
        schema = v.auto_infer(
            data,
            type_map={datetime.date: lambda val: val.isoformat()},
        )
        assert isinstance(schema["name"], StringValidator)
        assert isinstance(schema["created_at"], StringValidator)

    # ---- schema_overrides -----------------------------------------------

    def test_schema_overrides_replaces_inferred_field(self):
        """schema_overrides で指定したフィールドは推論をスキップして指定バリデータを使う"""
        from validkit.v import NumberValidator
        data = {"name": "Alice", "score": 9.5}
        schema = v.auto_infer(
            data,
            schema_overrides={"score": v.float().range(0.0, 10.0)},
        )
        assert isinstance(schema["score"], NumberValidator)
        assert schema["score"]._min == 0.0
        assert schema["score"]._max == 10.0

    def test_schema_overrides_optional_field(self):
        """schema_overrides で .optional() を付けると optional フィールドになる"""
        from validkit.v import StringValidator
        data = {"name": "Alice", "bio": "some text"}
        schema = v.auto_infer(
            data,
            schema_overrides={"bio": v.str().optional()},
        )
        assert isinstance(schema["bio"], StringValidator)
        assert schema["bio"]._optional is True

    def test_schema_overrides_handles_unsupported_type_field(self):
        """schema_overrides があれば推論できない型のフィールドもエラーにならない"""
        import datetime
        from validkit.v import StringValidator
        data = {"name": "Alice", "created_at": datetime.date(2024, 1, 1)}
        schema = v.auto_infer(
            data,
            schema_overrides={"created_at": v.str()},
        )
        assert isinstance(schema["name"], StringValidator)
        assert isinstance(schema["created_at"], StringValidator)

    def test_schema_overrides_does_not_affect_non_dict_data(self):
        """schema_overrides は dict 以外のデータに渡しても影響しない (str を推論する)"""
        from validkit.v import StringValidator
        schema = v.auto_infer("hello", schema_overrides={"hello": v.int()})
        assert isinstance(schema, StringValidator)

    def test_schema_overrides_unmentioned_fields_still_inferred(self):
        """schema_overrides に含まれないフィールドは通常どおり推論される"""
        from validkit.v import StringValidator, NumberValidator
        data = {"name": "Alice", "age": 30}
        schema = v.auto_infer(
            data,
            schema_overrides={"name": v.str().description("表示名")},
        )
        assert schema["name"]._description == "表示名"
        assert isinstance(schema["age"], NumberValidator)

    def test_schema_overrides_combined_with_type_map(self):
        """schema_overrides と type_map を同時に使うと両方有効になる"""
        import datetime
        from validkit.v import StringValidator, NumberValidator
        data = {
            "name": "Alice",
            "score": 9.5,
            "created_at": datetime.date(2024, 1, 1),
        }
        schema = v.auto_infer(
            data,
            type_map={datetime.date: v.str()},
            schema_overrides={"score": v.float().range(0.0, 10.0)},
        )
        assert isinstance(schema["name"], StringValidator)
        assert isinstance(schema["score"], NumberValidator)
        assert schema["score"]._min == 0.0
        assert isinstance(schema["created_at"], StringValidator)

    def test_schema_overrides_round_trip_validation(self):
        """schema_overrides を含むスキーマで元データをバリデーションできる"""
        data = {"name": "Alice", "score": 8.5, "bio": "developer"}
        schema = v.auto_infer(
            data,
            schema_overrides={
                "score": v.float().range(0.0, 10.0),
                "bio": v.str().optional(),
            },
        )
        result = validate(data, schema)
        assert result["name"] == "Alice"
        assert result["score"] == 8.5
        assert result["bio"] == "developer"
