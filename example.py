import sys
import os
from typing import Dict, List, Optional, TypedDict
import io
import ipaddress
import datetime
import uuid
from enum import Enum

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

# ==========================================
# 3. v1.2.0 新機能: .default() / .examples() / .description() / generate_sample()
# ==========================================
header("3. v1.2.0 新機能 (デフォルト値・サンプル生成)")

class NodeConfig(TypedDict):
    ip: str
    role: str

class ClusterConfig(TypedDict):
    cluster_name: str
    region: str
    auto_scale: bool
    nodes: List[NodeConfig]

# --- 3.1 スキーマ定義 (.default / .examples / .description が使えるようになる) ---
print("[3.1 スキーマ定義]")

CLUSTER_SCHEMA: Schema[ClusterConfig] = Schema({
    # 必須フィールド: .examples() で「こんな値が入る」を提示
    "cluster_name": v.str().examples(["myapp-prod", "myapp-staging"]).description("クラスタの識別名"),

    # オプションフィールド: .default() でデフォルト値を設定
    "region": v.str().default("ap-northeast-1").examples(["ap-northeast-1", "us-west-2"]).description("デプロイ先リージョン"),
    "auto_scale": v.bool().default(True).description("オートスケールの有効化"),

    # ネスト構造にも同様に適用可能
    "nodes": v.list({
        "ip": v.str().examples(["192.168.1.10", "10.0.0.5"]).description("ノードのIPアドレス"),
        "role": v.str().default("worker").examples(["worker", "master"]).description("ノードのロール"),
    }).description("クラスタを構成するノードのリスト"),
})

log_success("スキーマ定義完了。")

# --- 3.2 generate_sample(): スキーマから仕様書代わりのサンプルデータを生成 ---
print("\n[3.2 generate_sample() によるサンプル自動生成]")
# 優先順位: .default() > .examples() の先頭 > 型のダミー値
sample = CLUSTER_SCHEMA.generate_sample()
print(f"  cluster_name = {sample['cluster_name']!r:20s} # .examples() の先頭")
print(f"  region       = {sample['region']!r:20s} # .default() 値")
print(f"  auto_scale   = {sample['auto_scale']!r:20s} # .default() 値")
print(f"  nodes[0].role= {sample['nodes'][0]['role']!r:20s} # .default() 値 (ネスト内部)")
assert sample["cluster_name"] == "myapp-prod"  # examples の先頭
assert sample["region"] == "ap-northeast-1"    # default 値
assert sample["auto_scale"] is True            # default 値
assert sample["nodes"][0]["role"] == "worker"  # ネスト内の default 値
log_success("generate_sample() によるサンプルデータの生成に成功 (ネスト含む)。")

# --- 3.3 .default() による自動補完のデモ (後方互換確認含む) ---
print("\n[3.3 .default() による欠損キーの自動補完]")

# ケース1: 通常入力 (既存コードと全く同じ動作 → 後方互換)
full_input: ClusterConfig = {
    "cluster_name": "full-cluster",
    "region": "us-west-2",        # 明示的に指定した場合は入力値が優先
    "auto_scale": False,
    "nodes": [{"ip": "10.0.0.1", "role": "master"}],
}
r1 = validate(full_input, CLUSTER_SCHEMA)
assert r1["region"] == "us-west-2"    # 入力値が優先、デフォルト値で上書きされない
assert r1["auto_scale"] is False      # 同上
log_success(f"[後方互換] 入力値が優先されること確認: region={r1['region']!r}")

# ケース2: 必須フィールドだけ入力し、残りはデフォルト補完
minimal_input = {
    "cluster_name": "minimal-cluster",
    "nodes": [{"ip": "192.168.0.10"}],  # role が欠損 → ネスト内もデフォルト補完
}
r2 = validate(minimal_input, CLUSTER_SCHEMA)
assert r2["region"] == "ap-northeast-1"  # デフォルト補完
assert r2["auto_scale"] is True          # デフォルト補完
assert r2["nodes"][0]["role"] == "worker"  # ネスト内部のデフォルト補完
log_success(f"欠損キーがデフォルト値で補完: region={r2['region']!r}, nodes[0].role={r2['nodes'][0]['role']!r}")

header("v1.2.0 の全デモが正常に終了しました。")

# ==========================================
# 4. クラス記法によるスキーマ定義
# ==========================================
header("4. クラス記法スキーマ (Class-based Schema)")

# --- 4.1 基本的なアノテーション ---
print("[4.1 基本的なアノテーション]")

class UserProfile:
    name: str
    age: int
    score: float
    active: bool

data = {"name": "Alice", "age": 30, "score": 9.5, "active": True}
result = validate(data, UserProfile)
assert result == data
log_success(f"基本アノテーション検証成功: {result}")

# 型不一致はエラー
try:
    validate({"name": 123, "age": 30, "score": 9.5, "active": True}, UserProfile)
    assert False
except ValidationError as e:
    log_success(f"型不一致を検知: path={e.path!r}, msg={e.message}")

# --- 4.2 Optional / List / Dict と typing モジュールの型 ---
print("\n[4.2 Optional / List / Dict]")

class ServerConfig:
    host: str
    port: int
    tags: Optional[List[str]]      # 省略可能なリスト
    metadata: Dict[str, int]       # 辞書

# tags は Optional なので省略してもエラーにならない
result = validate(
    {"host": "db.local", "port": 5432, "metadata": {"connections": 10}},
    ServerConfig,
)
assert result["host"] == "db.local"
assert result["port"] == 5432
assert "tags" not in result
log_success(f"Optional フィールドの省略が許容された: {result}")

# tags を明示的に指定した場合は検証される
result2 = validate(
    {"host": "db.local", "port": 5432, "metadata": {}, "tags": ["web", "api"]},
    ServerConfig,
)
assert result2["tags"] == ["web", "api"]
log_success(f"タグ付き: {result2['tags']}")

# --- 4.3 カスタム型 (isinstance チェック) ---
print("\n[4.3 カスタム型 (isinstance チェック)]")

class Timezone:
    def __init__(self, name: str) -> None:
        self.name = name
    def __repr__(self) -> str:
        return f"Timezone({self.name!r})"

UTC = Timezone("UTC")
JST = Timezone("Asia/Tokyo")

class Config:
    name: str
    age: int
    timezone: Timezone   # → isinstance(value, Timezone) で検証

result = validate({"name": "server1", "age": 5, "timezone": UTC}, Config)
assert result["timezone"] is UTC
log_success(f"カスタム型の isinstance チェック成功: timezone={result['timezone']!r}")

# 誤った型を渡すとエラー
try:
    validate({"name": "server1", "age": 5, "timezone": "UTC"}, Config)
    assert False
except ValidationError as e:
    log_success(f"カスタム型の型不一致を検知: {e.message}")

# --- 4.4 クラス属性をデフォルト値として使用 + Validator クラス属性 ---
print("\n[4.4 デフォルト値 + Validator クラス属性]")

class AppConfig:
    host: str                            # 必須
    port: int = 5432                     # デフォルト値 5432
    ssl: bool = False                    # デフォルト値 False
    timeout: Optional[int] = 30          # Optional + デフォルト
    role = v.str().default("worker")     # Validator で詳細に定義

result = validate({"host": "db.local"}, AppConfig)
assert result["host"] == "db.local"
assert result["port"] == 5432
assert result["ssl"] is False
assert result["timeout"] == 30
assert result["role"] == "worker"
log_success(f"デフォルト値が自動補完された: {result}")

# 明示的な値はデフォルトを上書きする
result2 = validate({"host": "db.local", "port": 3306, "role": "master"}, AppConfig)
assert result2["port"] == 3306
assert result2["role"] == "master"
log_success(f"明示的な値がデフォルトを上書き: port={result2['port']}, role={result2['role']!r}")

# --- 4.5 v.instance() — 辞書スキーマでの isinstance チェック ---
print("\n[4.5 v.instance() — 辞書スキーマでの isinstance チェック]")

schema = {
    "name": v.str(),
    "timezone": v.instance(Timezone).default(UTC),
}

# timezone を省略 → デフォルトの UTC が補完される
result = validate({"name": "server1"}, schema)
assert result["name"] == "server1"
assert result["timezone"] is UTC
log_success(f"v.instance() デフォルト補完: timezone={result['timezone']!r}")

# 正しい型を渡した場合も通る
result2 = validate({"name": "server2", "timezone": JST}, schema)
assert result2["timezone"] is JST
log_success(f"v.instance() 正常ケース: timezone={result2['timezone']!r}")

# 誤った型を渡した場合はエラー
try:
    validate({"name": "server3", "timezone": "JST"}, schema)
    assert False
except ValidationError as e:
    log_success(f"v.instance() 型不一致を検知: {e.message}")

# .coerce() で型変換も可能（コンストラクタで変換）
schema_coerce = {
    "name": v.str(),
    "timezone": v.instance(Timezone).coerce(),
}
result3 = validate({"name": "server4", "timezone": "Asia/Tokyo"}, schema_coerce)
assert isinstance(result3["timezone"], Timezone)
assert result3["timezone"].name == "Asia/Tokyo"
log_success(f"v.instance().coerce() 型変換成功: {result3['timezone']!r}")

# --- 4.6 Schema(MyClass) と generate_sample() ---
print("\n[4.6 Schema(MyClass) と generate_sample()]")

class SampleConfig:
    app_name: str
    debug: bool = False
    port = v.int().default(8080).description("待機ポート")

schema_obj = Schema(SampleConfig)
sample = schema_obj.generate_sample()
assert sample["debug"] is False      # クラス属性デフォルト
assert sample["port"] == 8080        # Validator デフォルト
log_success(f"generate_sample() 成功: {sample}")

# --- 4.7 collect_errors と partial の組み合わせ ---
print("\n[4.7 collect_errors / partial との組み合わせ]")

class Profile:
    name: str
    age: int

# collect_errors=True: 複数エラーを一度に収集
bad = {"name": 99, "age": "thirty"}
res = validate(bad, Profile, collect_errors=True)
assert len(res.errors) == 2
log_success(f"collect_errors: {len(res.errors)} 件のエラーを収集")

# partial=True: 欠損フィールドを許容
partial_result = validate({"name": "Bob"}, Profile, partial=True)
assert partial_result["name"] == "Bob"
assert "age" not in partial_result
log_success(f"partial=True: 欠損フィールドを許容: {partial_result}")

header("クラス記法スキーマのデモが正常に終了しました。")

# ==========================================
# 5. v1.3.0 新機能: ライセンス認証向けバリデータ
# ==========================================
header("5. v1.3.0 新機能 (ライセンス認証向けバリデータ)")

from datetime import datetime, timedelta

# --- 5.1 v.datetime() ---
print("[5.1 v.datetime() — 有効期限チェック]")
now = datetime.now()
LICENSE_SCHEMA = {
    "expiry": v.datetime().after_now().description("有効期限"),
    "issued_at": v.datetime().before(now).description("発行日")
}

# 正常系: 有効期限が未来、発行日が過去
valid_license = {
    "expiry": now + timedelta(days=365),
    "issued_at": now - timedelta(days=1)
}
res_dt = validate(valid_license, LICENSE_SCHEMA)
log_success(f"日付バリデーション成功: {res_dt}")

# --- 5.2 v.uuid() / v.mac() / v.sid() ---
print("\n[5.2 v.uuid() / v.mac() / v.sid() — 識別子チェック]")
IDENTIFIER_SCHEMA = {
    "key": v.uuid().version(4),
    "mac_address": v.mac(),
    "computer_sid": v.sid()
}

ident_data = {
    "key": "550e8400-e29b-41d4-a716-446655440000", # 固定値だが形式はOK
    "mac_address": "00:11:22:33:44:55",
    "computer_sid": "S-1-5-21-3623811015-3361044348-30300820-1013"
}
# UUID は version(4) を指定しているため、上記固定値（version 4ではない）はエラーになるはず
try:
    validate(ident_data, IDENTIFIER_SCHEMA)
except ValidationError as e:
    log_success(f"期待通りのエラー (UUID version 不一致): {e.message}")

# 正しい UUID v4 を使用
ident_data["key"] = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
res_ident = validate(ident_data, IDENTIFIER_SCHEMA)
log_success(f"識別子バリデーション成功: {res_ident}")

# --- 5.3 v.ip() / v.snowflake() / v.version() ---
print("\n[5.3 v.ip() / v.snowflake() / v.version() — その他]")
OTHER_SCHEMA = {
    "allowed_ip": v.ip().v4_only().coerce(),
    "discord_user_id": v.snowflake().coerce(),
    "app_version": v.version()
}

other_data = {
    "allowed_ip": "127.0.0.1",
    "discord_user_id": "123456789012345678",
    "app_version": "1.5.0-beta.1"
}
res_other = validate(other_data, OTHER_SCHEMA)
log_success(f"IP/Snowflake/Version バリデーション成功: {res_other}")
assert isinstance(res_other["allowed_ip"], ipaddress.IPv4Address)
assert isinstance(res_other["discord_user_id"], int)

header("v1.3.0 の全デモが正常に終了しました。")

# ==========================================
# 6. セキュリティ＆開発体験向上機能 (Secret, Env, URL, Enum)
# ==========================================
header("6. セキュリティ＆開発体験向上機能")

class Role(Enum):
    ADMIN = "admin"
    USER = "user"

# --- 6.1 .secret() / .error_msg() ---
print("[6.1 .secret() と .error_msg() — 機密情報とカスタムエラー]")
SEC_SCHEMA = {
    "password": v.str().min(8).secret().error_msg("パスワードは8文字以上にしてください"),
}

try:
    validate({"password": "short"}, SEC_SCHEMA)
except ValidationError as e:
    log_success(f"エラーメッセージの変更と値のマスクを確認: {e.message} (value: {e.value})")
    assert e.value == "***"

# --- 6.2 .env() ---
print("\n[6.2 .env() — 環境変数からの自動フォールバック]")
ENV_SCHEMA = {
    "api_key": v.str().env("MY_API_KEY"),
}

# 1. 入力がある場合は環境変数を無視
res_input = validate({"api_key": "input_val"}, ENV_SCHEMA)
log_success(f"入力値優先: {res_input['api_key']}")

# 2. 入力が欠損している場合は環境変数から取得
os.environ["MY_API_KEY"] = "env_secret_key"
res_env = validate({}, ENV_SCHEMA)
log_success(f"環境変数から取得: {res_env['api_key']}")

# --- 6.3 v.url() ---
print("\n[6.3 v.url() — URL フォーマット検証と制約]")
URL_SCHEMA = {
    "webhook": v.url().schemes(["https"]).domains(["discord.com"]).paths(["/api/webhooks"]),
    "profile_url": v.url().subdomains(["app"]).query_keys(["user_id"])
}

url_data = {
    "webhook": "https://discord.com/api/webhooks?token=abc",
    "profile_url": "https://app.example.com/view?user_id=123"
}
res_url = validate(url_data, URL_SCHEMA)
log_success(f"URLバリデーション成功: \n  - webhook: {res_url['webhook']}\n  - profile: {res_url['profile_url']}")

# ドメインエラーの確認
try:
    validate({"webhook": "https://evil.local/api/webhooks", "profile_url": "https://app.example.com/view?user_id=123"}, URL_SCHEMA)
except ValidationError as e:
    log_success(f"期待通りのエラー (ドメイン不一致): {e.message}")

# --- 6.4 v.enum() ---
print("\n[6.4 v.enum() — Enum 自動変換]")
ENUM_SCHEMA = {
    "role": v.enum(Role).coerce().default(Role.USER)
}

res_enum1 = validate({"role": "admin"}, ENUM_SCHEMA)
log_success(f"文字列からの自動変換成功: {res_enum1['role']} (type: {type(res_enum1['role']).__name__})")

res_enum2 = validate({}, ENUM_SCHEMA)
log_success(f"デフォルト値適用成功: {res_enum2['role']}")

header("すべてのデモが正常に終了しました。")
