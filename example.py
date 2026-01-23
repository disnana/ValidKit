import sys
import os

# Add src to path to import validkit
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from validkit import v, validate, ValidationError

# カスタムパース関数の例
def parse_time_str(s):
    if not any(s.endswith(unit) for unit in ['s', 'm', 'h', 'd']):
        raise ValueError("無効な時間形式です")
    return s

# カスタム型定義
TimeStr = v.str().regex(r'^\d+[smhd]$').custom(parse_time_str)
PunishmentList = v.list(v.oneof(['timeout', 'kick', 'ban', 'delete']))

# スキーマ定義
GUILD_SETTINGS_SCHEMA = {
    "token": {
        "検知": v.bool(),
        "検知レベル": v.int().range(1, 3),
        "処罰": PunishmentList,
        "期間": TimeStr,
        "違反回数に基づく処罰": v.dict(int, PunishmentList),
        "検知除外": {
            "ユーザー・ボット・webhook": v.list(int),
            "チャンネル": v.list(int)
        },
        "チェック": v.bool()
    },
    "権限": {
        "許可ユーザー": v.list(int),
        "許可ロール": v.list(int),
        "オーナーのみ変更を許可": v.bool()
    },
    "言語": v.oneof(["日本語", "English"]),
    "発言safety": {
        "検知": v.bool(),
        "検知対象カテゴリ": v.list(v.oneof([
            "TOXICITY", "SEVERE_TOXICITY", "IDENTITY_ATTACK", 
            "INSULT", "PROFANITY", "THREAT"
        ])),
        "スコア": v.float().range(0.0, 1.0),
        "カテゴリ毎の設定": v.dict(str, v.float().range(0.0, 1.0)),
        "処罰": v.dict(str, TimeStr).optional(),
        "違反回数に基づく加算処罰": v.bool(),
        "通知": v.bool(),
        "不適切なメッセージを表示": v.bool(),
        "処罰内容を表示": v.bool(),
        "処罰時間を表示": v.bool(),
        "送信者名を表示": v.bool(),
        "メッセージ種類": v.oneof(["text", "embed", "embed-webhook"]),
        "メッセージの遅延削除": v.bool(),
        "メッセージの遅延削除時間": TimeStr.when(
            lambda d: d.get("発言safety", {}).get("メッセージの遅延削除", False)
        ),
        "除外": {
            "ユーザー": v.list(int),
            "チャンネル": v.list(int),
            "ロール": v.list(int)
        }
    }
}

# テスト用データ
user_config = {
    "token": {
        "検知": True,
        "検知レベル": 2,
        "処罰": ["timeout", "ban"],
        "期間": "1h",
        "違反回数に基づく処罰": {3: ["kick"], 5: ["ban"]},
        "検知除外": {
            "ユーザー・ボット・webhook": [123456789],
            "チャンネル": []
        },
        "チェック": False
    },
    "権限": {
        "許可ユーザー": [],
        "許可ロール": [987654321],
        "オーナーのみ変更を許可": True
    },
    "言語": "日本語",
    "発言safety": {
        "検知": True,
        "検知対象カテゴリ": ["TOXICITY", "INSULT"],
        "スコア": 0.8,
        "カテゴリ毎の設定": {"TOXICITY": 0.7},
        "違反回数に基づく加算処罰": False,
        "通知": True,
        "不適切なメッセージを表示": True,
        "処罰内容を表示": True,
        "処罰時間を表示": True,
        "送信者名を表示": True,
        "メッセージ種類": "embed",
        "メッセージの遅延削除": True,
        "メッセージの遅延削除時間": "10s",
        "除外": {"ユーザー": [], "チャンネル": [], "ロール": []}
    }
}

print("--- 基本的な検証 ---")
try:
    validated = validate(user_config, GUILD_SETTINGS_SCHEMA)
    print("検証成功！")
except ValidationError as e:
    print(f"設定エラー: {e.path} - {e.message}")

print("\n--- 部分更新とデフォルト値マージ ---")
DEFAULT_CONFIG = {"言語": "English", "権限": {"オーナーのみ変更を許可": False}}
partial_config = {"言語": "日本語"}
updated = validate(
    partial_config, 
    GUILD_SETTINGS_SCHEMA, 
    partial=True,
    base=DEFAULT_CONFIG
)
print(f"更新後の言語: {updated['言語']}")
print(f"デフォルトから継承された権限: {updated['権限']['オーナーのみ変更を許可']}")

print("\n--- マイグレーション ---")
old_config = {"timeout": 60, "旧キー": "some_value"}
NEW_SCHEMA = {"timeout": v.str(), "新キー": v.str()}
migrated = validate(old_config, NEW_SCHEMA, partial=True, migrate={
    "旧キー": "新キー",
    "timeout": lambda v: f"{v}s"
})
print(f"マイグレーション後: {migrated}")

print("\n--- 詳細なエラー情報 ---")
invalid_config = {
    "token": {"検知レベル": 5, "期間": "invalid"},
    "言語": "フランス語"
}
result = validate(invalid_config, GUILD_SETTINGS_SCHEMA, partial=True, collect_errors=True)
if result.errors:
    for err in result.errors:
        print(f"エラー: {err}")
else:
    print("エラーが見つかりませんでした")
