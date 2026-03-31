import unittest
import os
from enum import Enum
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from validkit import v, validate, ValidationError

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

class TestAdvancedFeatures(unittest.TestCase):
    def test_secret(self):
        schema = {"password": v.str().min(8).secret()}
        
        # 正常系
        res = validate({"password": "supersecret"}, schema)
        self.assertEqual(res["password"], "supersecret")
        
        # 異常系 (例外のエラーメッセージから値がマスクされるか)
        with self.assertRaises(ValidationError) as ctx:
            validate({"password": "short"}, schema)
        
        self.assertEqual(ctx.exception.value, "***")
        # デフォルトメッセージ自体に含まれるかを防ぐため、valueが例外に含まれないかは確認しづらいですが、
        # validator.py 側で err_val を "***" に置換して投げていることを確認します。
        
        # collect_errors=True の場合もマスクされるか
        result = validate({"password": 123}, schema, collect_errors=True)
        self.assertEqual(result.errors[0].value, "***")

    def test_env(self):
        schema = {"token": v.str().env("TEST_TOKEN")}
        
        # 値がある場合は入力値が優先される
        os.environ["TEST_TOKEN"] = "env_value"
        res1 = validate({"token": "input_value"}, schema)
        self.assertEqual(res1["token"], "input_value")
        
        # 値がない場合は環境変数が使われる
        res2 = validate({}, schema)
        self.assertEqual(res2["token"], "env_value")

        # 入力値も環境変数もない場合は必須エラー
        del os.environ["TEST_TOKEN"]
        with self.assertRaises(ValidationError):
            validate({}, schema)

        # decryptor のテスト
        schema_decrypt = {"api_secret": v.str().env("MY_SECRET", decryptor=lambda x: x[::-1])} # 逆順にする簡易復号
        os.environ["MY_SECRET"] = "terces"
        res_decrypt = validate({}, schema_decrypt)
        self.assertEqual(res_decrypt["api_secret"], "secret")
        
        # decryptor がエラーを投げた場合
        def bad_decryptor(x):
            raise ValueError("Decryption failed!")
        schema_bad_decrypt = {"api_secret": v.str().env("MY_SECRET", decryptor=bad_decryptor)}
        with self.assertRaises(ValidationError) as ctx_err:
            validate({}, schema_bad_decrypt)
        self.assertIn("Failed to decrypt env var", ctx_err.exception.message)

    def test_error_msg(self):
        custom_msg = "ちゃんと入力してね！"
        schema = {"age": v.int().range(20, 100).error_msg(custom_msg)}
        
        with self.assertRaises(ValidationError) as ctx:
            validate({"age": 10}, schema)
        
        self.assertEqual(ctx.exception.message, custom_msg)

    def test_url_validator(self):
        schema = {"webhook": v.url().schemes(["https"]).domains(["discord.com"]).paths(["/api/webhooks"])}
        
        # 正常系
        valid_url = "https://discord.com/api/webhooks?token=123"
        self.assertEqual(validate({"webhook": valid_url}, schema)["webhook"], valid_url)
        
        # スキームエラー
        with self.assertRaises(ValidationError):
            validate({"webhook": "http://discord.com/api/webhooks"}, schema)
            
        # ドメインエラー
        with self.assertRaises(ValidationError):
            validate({"webhook": "https://evil.com/api/webhooks"}, schema)
            
        # パスエラー
        with self.assertRaises(ValidationError):
            validate({"webhook": "https://discord.com/api/other"}, schema)

        # サブドメイン制約
        schema2 = {"url": v.url().subdomains(["api"])}
        self.assertEqual(validate({"url": "https://api.example.com"}, schema2)["url"], "https://api.example.com")
        with self.assertRaises(ValidationError):
            validate({"url": "https://www.example.com"}, schema2)

        # クエリパラメータ制約
        schema3 = {"url": v.url().query_keys(["id", "hash"])}
        self.assertEqual(validate({"url": "https://example.com?id=1&hash=abc"}, schema3)["url"], "https://example.com?id=1&hash=abc")
        with self.assertRaises(ValidationError):
            validate({"url": "https://example.com?id=1"}, schema3)

    def test_enum_validator(self):
        schema = {"theme": v.enum(Color).coerce()}
        
        # Enum直接
        self.assertEqual(validate({"theme": Color.RED}, schema)["theme"], Color.RED)
        
        # coerceによる文字列からEnumへの変換 (値)
        self.assertEqual(validate({"theme": "green"}, schema)["theme"], Color.GREEN)

        # coerceによる文字列からEnumへの変換 (名前)
        self.assertEqual(validate({"theme": "BLUE"}, schema)["theme"], Color.BLUE)

        # 無効な値
        with self.assertRaises(ValidationError):
            validate({"theme": "yellow"}, schema)

if __name__ == "__main__":
    unittest.main()
