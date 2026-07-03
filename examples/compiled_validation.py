"""
ValidKit - スキーマ事前コンパイル機能 (compile) の網羅的サンプルコード

このサンプルコードでは、事前コンパイル機能 (`compile()`) を用いた
さまざまなバリデーションパターンと高度な使用方法を網羅的に解説します。

事前コンパイルを使用することで、都度スキーマを解析するオーバーヘッドを排除し、
ネイティブな Python の比較式と同等の速度（約 3x 以上高速）で検証を実行できます。
"""

import os
import sys
import time
import dataclasses
from typing import TypedDict

# プロジェクト内の validkit をインポートするためのパス調整
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from validkit import compile, v, ValidationError, ValidationResult, Schema


def section(title: str):
    print(f"\n--- {title} ---")


# =====================================================================
# 1. 基本的なコンパイルとバリデーション
# =====================================================================
section("1. 基本的なコンパイルとバリデーション")

# 辞書スキーマを事前にコンパイルします
basic_schema = compile({
    "user_id": v.int().range(1000, 9999),
    "username": v.str().regex(r"^[a-zA-Z0-9_]{3,15}$"),
    "active": v.bool()
})

# 正しいデータの検証
valid_data = {
    "user_id": 1234,
    "username": "alice_dev",
    "active": True
}
result = basic_schema.validate(valid_data)
print("検証成功:", result)

# 不正なデータの検証 (例外の発生)
invalid_data = {
    "user_id": 99,           # 範囲外 (1000-9999)
    "username": "ab",        # 長さ不足
    "active": "not-a-bool"   # 型不一致
}

try:
    basic_schema.validate(invalid_data)
except ValidationError as e:
    print(f"検証失敗箇所: {e.path}")
    print(f"エラー内容: {e.message}")


# =====================================================================
# 2. ネストされた構造 (Dict, List) の検証
# =====================================================================
section("2. ネストされた辞書やリストの検証")

nested_schema = compile({
    "group_name": v.str().min(1),
    "members": v.list({
        "name": v.str(),
        "age": v.int().min(0)
    }),
    "metadata": v.dict(str, v.str())  # キーが str, 値が str の任意の辞書
})

group_data = {
    "group_name": "Developers",
    "members": [
        {"name": "Bob", "age": 30},
        {"name": "Charlie", "age": 25}
    ],
    "metadata": {
        "env": "production",
        "region": "ap-northeast-1"
    }
}
print("ネスト検証成功:", nested_schema.validate(group_data))


# =====================================================================
# 3. 部分更新 (partial) と デフォルト値マージ (base)
# =====================================================================
section("3. 部分更新 (partial) とデフォルト値マージ (base)")

# デフォルト値の設定が含まれるスキーマ
config_schema = compile({
    "host": v.str().default("localhost"),
    "port": v.int().default(8080),
    "timeout": v.int().default(30)
})

# 空のデータを与えても、デフォルト値が自動補完されます
default_applied = config_schema.validate({})
print("デフォルト補完結果:", default_applied)

# partial=True による一部の更新と base によるマージ
# (既存の設定 DEFAULT_SETTINGS をベースにして、一部のパラメータのみを更新・検証します)
DEFAULT_SETTINGS = {
    "host": "production.db",
    "port": 5432,
    "timeout": 60
}
partial_input = {"timeout": 120}  # timeout のみ更新

merged_result = config_schema.validate(
    partial_input,
    partial=True,
    base=DEFAULT_SETTINGS
)
print("マージ結果 (timeoutのみ更新):", merged_result)


# =====================================================================
# 4. 環境変数フォールバック (env) と条件付き検証 (when)
# =====================================================================
section("4. 環境変数フォールバック (env) と条件付き検証 (when)")

complex_schema = compile({
    # データに欠損がある場合、環境変数 'APP_PORT' から文字列を読み取って int に自動変換 (coerce) します
    "port": v.int().coerce().env("APP_PORT").default(3000),
    
    # "is_premium" が True の場合のみ、"premium_key" フィールドが必須になります
    "is_premium": v.bool(),
    "premium_key": v.str().min(10).when(lambda data: data.get("is_premium") is True)
})

# 環境変数を設定して検証を実行
os.environ["APP_PORT"] = "9000"
try:
    res = complex_schema.validate({"is_premium": False})
    print("環境変数 & 非プレミアム検証成功:", res)
finally:
    del os.environ["APP_PORT"]

# プレミアムなのにキーが欠損している場合のエラー確認
try:
    complex_schema.validate({"is_premium": True})
except ValidationError as e:
    print(f"プレミアム条件付きエラー: {e.path} -> {e.message}")


# =====================================================================
# 5. クラスアノテーション (Dataclass) スキーマのコンパイル
# =====================================================================
section("5. Dataclass スキーマのコンパイルとインスタンス化")

@dataclasses.dataclass
class User:
    name: str
    age: int = 18
    roles: list[str] = dataclasses.field(default_factory=lambda: ["user"])

# Dataclass から高速バリデータスキーマをコンパイル
dataclass_schema = compile(User)

# 辞書データを検証すると、自動的に User クラスのインスタンスになって返されます
user_instance = dataclass_schema.validate({
    "name": "David",
    "roles": ["admin"]
})
print("生成されたインスタンス:", user_instance)
print("型チェック:", type(user_instance))


# =====================================================================
# 6. 複数エラーの一括収集 (collect_errors)
# =====================================================================
section("6. 複数エラーの一括収集 (collect_errors)")

user_schema = compile({
    "username": v.str().min(5),
    "age": v.int().range(0, 150),
    "email": v.str().regex(r"@")
})

bad_input = {
    "username": "jack",  # 短すぎる
    "age": -5,          # 範囲外
    "email": "invalid"  # 正規表現不適合
}

# collect_errors=True を指定すると、全てのエラーを ValidationResult に収集します
res_result = user_schema.validate(bad_input, collect_errors=True)
if res_result.errors:
    print(f"合計 {len(res_result.errors)} 件のエラーを検出しました:")
    for err in res_result.errors:
        print(f"  - [{err.path}]: {err.message} (入力値: {err.value})")


# =====================================================================
# 7. データマイグレーション (migrate)
# =====================================================================
section("7. データマイグレーション (migrate)")

migration_schema = compile({
    "login_name": v.str(),
    "level": v.int()
})

# 旧バージョンのデータ
old_data = {
    "old_username": "nana",
    "level": "10" # 文字列になっている
}

# 旧キーの改名と、型変換やデータ加工を同時に行いながら検証します
migrated = migration_schema.validate(
    old_data,
    migrate={
        "old_username": "login_name",
        "level": lambda val: int(val) # 文字列から整数に変換
    }
)
print("マイグレーション完了データ:", migrated)
