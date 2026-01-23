# ValidKit

ValidKit は、辞書ベースで簡潔に定義でき、日本語キーや複雑なネストに対応した Python バリデーションライブラリです。 Pydantic よりも軽量かつ、Discord ボットの設定管理などの複雑なデータ構造を直感的に扱うことができます。

## 特徴

- 📝 **辞書ベースのスキーマ**: クラス定義不要。データ構造をそのままスキーマとして定義可能
- 🌏 **日本語キー対応**: 日本語をキーにした設定データもそのまま検証
- 🔗 **チェイン可能なバリデータ**: `v.int().range(1, 10)` のように直感的に記述
- 🔄 **マイグレーション機能**: 古い形式のデータを検証と同時に新形式へ自動変換
- 🛠️ **部分更新・デフォルト値**: 足りないキーの補完や部分的な検証をサポート
- 🔍 **詳細なエラー収集**: 全エラーを一括で取得し、エラー箇所のパスを明確に表示

## インストール

```bash
pip install validkit
```
*(注: 現時点ではプレリリース版です)*

## クイックスタート

```python
from validkit import v, validate

# スキーマ定義
SCHEMA = {
    "ユーザー名": v.str().regex(r"^\w{3,15}$"),
    "レベル": v.int().range(1, 100),
    "スキル": v.list(v.oneof(["火", "水", "風"])),
    "設定": {
        "通知": v.bool(),
        "言語": v.oneof(["日本語", "English"])
    }
}

# 検証データ
data = {
    "ユーザー名": "nana_kit",
    "レベル": 50,
    "スキル": ["火", "風"],
    "設定": {
        "通知": True,
        "言語": "日本語"
    }
}

try:
    validated = validate(data, SCHEMA)
    print("検証成功！")
except ValidationError as e:
    print(f"エラー: {e.path} - {e.message}")
```

## 便利な高度な機能

### 部分更新とデフォルト値のマージ
```python
DEFAULT_CONFIG = {"言語": "English", "音量": 50}
partial_input = {"音量": 80}

updated = validate(
    partial_input, 
    SCHEMA, 
    partial=True,  # 不足キーを許可
    base=DEFAULT_CONFIG  # デフォルト値とマージ
)
```

### マイグレーション
```python
old_data = {"旧キー": "値", "timeout": 30}
migrated = validate(old_data, SCHEMA, migrate={
    "旧キー": "新キー",
    "timeout": lambda v: f"{v}s"  # 値の変換
})
```

## ライセンス

MIT
