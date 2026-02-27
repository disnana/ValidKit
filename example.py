import sys
import os
from typing import TypedDict

# Add src to path to import validkit
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from validkit import v, validate, ValidationError, Schema, ValidationResult

# ==========================================
# 1. v1.0.0 の基本機能 (Basic Features)
# ==========================================
print("--- 1. v1.0.0 基本機能 ---")

# スキーマ定義：辞書の形がそのままバリデーション構造になります
BASIC_SCHEMA = {
    "ユーザー名": v.str().regex(r"^\w{3,15}$"),
    "レベル": v.int().range(1, 100),
    "スキル": v.list(v.oneof(["火", "水", "風"])),
    "設定": {
        "通知": v.bool(),
        "言語": v.oneof(["日本語", "English"]).optional()
    }
}

data = {
    "ユーザー名": "nana_kit",
    "レベル": 50,
    "スキル": ["火", "風"],
    "設定": {"通知": True}  # 言語は optional なので省略可能
}

try:
    validated = validate(data, BASIC_SCHEMA)
    print(f"検証成功！ユーザー: {validated['ユーザー名']}, レベル: {validated['レベル']}")
except ValidationError as e:
    print(f"エラー発生箇所: {e.path} - {e.message}")


# ==========================================
# 2. v1.1.0 の高度な機能 (Advanced Features)
# ==========================================
print("\n--- 2. v1.1.0 高度な機能 ---")

# --- 2.1 Schema[T] による型推論と IDE 補完 ---
class UserConfig(TypedDict):
    name: str
    volume: int
    dark_mode: bool

# Schema[T] でラップすることで、戻り値に型情報が付与されます
CONFIG_SCHEMA: Schema[UserConfig] = Schema({
    "name": v.str(),
    "volume": v.int().range(0, 100),
    "dark_mode": v.bool()
})

config_data = {"name": "Player1", "volume": 80, "dark_mode": True}
result = validate(config_data, CONFIG_SCHEMA)
# IDE 上で result["name"] や result["volume"] が補完されます
print(f"型安全な検証結果: {result['name']} (音量: {result['volume']})")


# --- 2.2 partial=True と base によるデフォルト値マージ ---
print("\n--- 2.2 部分更新とデフォルト値マージ ---")
DEFAULT_CONFIG = {"name": "Guest", "volume": 50, "dark_mode": False}
user_patch = {"volume": 90}  # 音量だけ変更したい

# partial=True で不足キーを許容し、base でデフォルトを補完
merged = validate(user_patch, CONFIG_SCHEMA, partial=True, base=DEFAULT_CONFIG)
print(f"マージ後の設定: {merged}")


# --- 2.3 migrate によるデータ変換 ---
print("\n--- 2.3 データ移行 (Migration) ---")
legacy_data = {"old_name": "LegacyUser", "sound_level": 40, "dark_mode": "on"}

# キー名の変更や、値の変換を移行時に行います
migrated = validate(
    legacy_data,
    CONFIG_SCHEMA,
    migrate={
        "old_name": "name",           # キーのリネーム
        "sound_level": "volume",      # キーのリネーム
        "dark_mode": lambda v: v == "on"  # 値の変換
    }
)
print(f"移行後のデータ: {migrated}")


# --- 2.4 collect_errors=True によるエラーの一括取得 ---
print("\n--- 2.4 エラーの一括収集 ---")
invalid_data = {
    "name": 123,      # 文字列であるべき
    "volume": 150,    # 100以下であるべき
    "dark_mode": "no" # boolであるべき
}

res: ValidationResult = validate(invalid_data, CONFIG_SCHEMA, collect_errors=True)
if res.errors:
    print(f"合計 {len(res.errors)} 件のエラーが見つかりました:")
    for err in res.errors:
        print(f"  - [{err.path}]: {err.message} (値: {err.value})")


# --- 2.5 .when() による条件付きバリデーション ---
print("\n--- 2.5 条件付きバリデーション ---")
ADVANCED_SCHEMA = {
    "enable_logging": v.bool(),
    "log_path": v.str().when(lambda d: d.get("enable_logging") is True)
}

# ログ有効時は log_path が必須
try:
    validate({"enable_logging": True}, ADVANCED_SCHEMA)
except ValidationError as e:
    print(f"条件付きエラー: {e.path} - {e.message} (enable_logging が True なので log_path が必要)")

# ログ無効時は log_path は不要
success = validate({"enable_logging": False}, ADVANCED_SCHEMA)
print(f"成功 (ログ無効時は log_path 不要): {success}")
