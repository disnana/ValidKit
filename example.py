import sys
import os
from typing import TypedDict
import io

# Handle UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path to import validkit
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from validkit import v, validate, ValidationError, Schema, ValidationResult

def header(text: str):
    print(f"\n{'='*20} {text} {'='*20}")

def log_success(msg: str):
    print(f"✅ SUCCESS: {msg}")

# ==========================================
# 1. v1.0.0 の基本機能 (Basic Features)
# ==========================================
header("1. v1.0.0 基本機能 (基本バリデーション)")

BASIC_SCHEMA = {
    "user_id": v.int().range(1000, 9999),
    "username": v.str().regex(r"^[a-z0-9_]{3,10}$"),
    "tags": v.list(v.oneof(["admin", "user", "guest"])),
    "profile": {
        "bio": v.str().optional(),
        "age": v.int().min(18)
    }
}

data = {
    "user_id": 1234,
    "username": "nana_kit",
    "tags": ["user", "guest"],
    "profile": {"age": 25}
}

validated = validate(data, BASIC_SCHEMA)
assert validated["user_id"] == 1234
assert validated["profile"]["age"] == 25
log_success("基本バリデーションとネスト構造の検証に成功しました。")

# ==========================================
# 2. v1.1.0 高度な機能 (Advanced Features)
# ==========================================
header("2. v1.1.0 高度な機能")

# --- 2.1 Schema[T] による型情報の付与 ---
print("[2.1 Schema[T] と TypedDict]")

class UserConfig(TypedDict):
    display_name: str
    theme: str
    notifications: bool

# Schema[T] を使うことで Python の型ヒントとして機能します
CONFIG_SCHEMA: Schema[UserConfig] = Schema({
    "display_name": v.str(),
    "theme": v.oneof(["light", "dark"]),
    "notifications": v.bool()
})

config_info = {"display_name": "Antigravity", "theme": "dark", "notifications": True}
# result は UserConfig 型として扱われます
result: UserConfig = validate(config_info, CONFIG_SCHEMA)
assert result["display_name"] == "Antigravity"
log_success("Schema[T] による型安全な検証に成功。")


# --- 2.2 partial=True と base によるマージ ---
print("\n[2.2 部分更新とデフォルト値マージ]")
DEFAULT_SETTINGS = {
    "display_name": "Anonymous",
    "theme": "light",
    "notifications": False
}
user_input = {"display_name": "NewName"}

# partial=True で不足キーを許容し、base でデフォルト値を補完
merged: UserConfig = validate(user_input, CONFIG_SCHEMA, partial=True, base=DEFAULT_SETTINGS)

assert merged["display_name"] == "NewName"
assert merged["theme"] == "light" # デフォルトから継承
log_success(f"デフォルト値とのマージ結果: {merged}")


# --- 2.3 柔軟なデータ移行 (Migration) ---
print("\n[2.3 柔軟なデータ移行 (Migration)]")
old_data = {
    "old_id": "999",
    "user_theme": "DARK",
    "extra": "ignore"
}

# リネーム + 値の変換を同時に行う例 (タプルを返すとリネーム＋変換)
migrated = validate(
    old_data,
    CONFIG_SCHEMA,
    partial=True,
    migrate={
        "old_id": "display_name",
        "user_theme": lambda v: ("theme", v.lower())
    }
)

assert migrated["display_name"] == "999"
assert migrated["theme"] == "dark"
log_success(f"移行後のデータ: {migrated}")


# --- 2.4 collect_errors=True による一括検知 ---
print("\n[2.4 エラーの網羅的収集]")
bad_data = {
    "display_name": 123,       # 型エラー
    "theme": "pink",           # oneofエラー
    "notifications": "True"    # 型エラー (str ではなく bool が必要)
}

res: ValidationResult = validate(bad_data, CONFIG_SCHEMA, collect_errors=True)
print(f"検知された不備 ({len(res.errors)}件):")
for err in res.errors:
    print(f"  ❌ {err.path}: {err.message} (入力値: {err.value})")

assert len(res.errors) == 3
log_success("すべての不備を一度に捕捉しました。")


# --- 2.5 when() による条件付き必須バリデーション ---
print("\n[2.5 条件付きバリデーション (.when)]")
# 「プレミアム会員の場合のみ、有効期限が必須」というスキーマ
SUBSCRIPTION_SCHEMA = {
    "is_premium": v.bool(),
    "expiry_date": v.str().regex(r"^\d{4}-\d{2}-\d{2}$").when(lambda d: d.get("is_premium") is True)
}

# 1. プレミアムでない場合 -> expiry_date は不要
v1 = validate({"is_premium": False}, SUBSCRIPTION_SCHEMA)
assert "expiry_date" not in v1
log_success("非プレミアム: expiry_date は要求されません。")

# 2. プレミアムである場合 -> expiry_date がないとエラー
try:
    validate({"is_premium": True}, SUBSCRIPTION_SCHEMA)
    assert False, "Should have raised ValidationError"
except ValidationError as e:
    assert e.path == "expiry_date"
    log_success("プレミアム: expiry_date がない場合に正しくエラーを検知。")

# 3. プレミアムで正しい日付がある場合
v3 = validate({"is_premium": True, "expiry_date": "2026-12-31"}, SUBSCRIPTION_SCHEMA)
assert v3["expiry_date"] == "2026-12-31"
log_success("プレミアム: 正しい形式の日付で検証通過。")

# --- 2.6 自動変換 (.coerce) ---
print("\n[2.6 自動変換 (.coerce)]")
# 文字列の "123" を数値に、1 を真偽値に変換する例
COERCE_SCHEMA = {
    "user_id": v.int().coerce(),
    "is_active": v.bool().coerce(),
    "score": v.float().coerce()
}

input_data = {
    "user_id": "9999",
    "is_active": 1,
    "score": "95.5"
}

coerced = validate(input_data, COERCE_SCHEMA)
assert coerced["user_id"] == 9999
assert coerced["is_active"] is True
assert coerced["score"] == 95.5
log_success(f"自動変換後のデータ: {coerced}")

header("すべての検証デモが正常に終了しました。")
