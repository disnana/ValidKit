# ValidKit

[![CI](https://github.com/disnana/ValidKit/actions/workflows/ci.yml/badge.svg)](https://github.com/disnana/ValidKit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/validkit-py?label=PyPI)](https://pypi.org/project/validkit-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ValidKit は、**「直感的なスキーマ定義」と「日本語キーへの完全対応」**を特徴とする、Python 用の軽量バリデーションライブラリです。

複雑にネストされた設定ファイルや、Discord ボットのユーザー設定、外部 API からのレスポンスなどを、シンプルかつ堅牢に検証するために設計されました。Pydantic ほど重厚ではなく、しかし辞書ベースの柔軟性と強力なチェーンメソッドを提供します。

---

## 🚀 なぜ ValidKit なのか？

- **クラス定義不要**: 辞書そのものがスキーマになります。既存の JSON/YAML 構造をそのまま定義に落とし込めます。
- **日本語キーにフレンドリー**: `v.str()` や `v.int()` を日本語のキー名と組み合わせて、可読性の高いバリデーションを記述できます。
- **高度な検証をシンプルに**: 正規表現、数値範囲、カスタム関数、さらには「他のフィールドの値に応じた検証（条件付き検証）」も直感的に書けます。
- **モダンな開発フロー**: SLSA v3 準拠の来歴証明（provenance）に対応し、サプライチェーンの安全性を確保しています。

---

## 目次

* [概要](#概要)
* [特徴](#特徴)
* [インストール](#インストール)
* [クイックスタート](#クイックスタート)
* [API 例](#api-例)
* [高度な使い方](#高度な使い方)
* [品質管理・セキュリティ](#品質管理・セキュリティ)
* [貢献ガイドライン](#貢献ガイドライン)
* [ライセンス](#ライセンス)

---

## インストール

```bash
pip install validkit-py
```

---

## クイックスタート

わずか数行で、複雑なデータ構造を検証できます。

```python
from validkit import v, validate, ValidationError

# スキーマ定義：辞書の形がそのままバリデーション構造になります
SCHEMA = {
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
    # 検証実行
    validated = validate(data, SCHEMA)
    print(f"検証成功！レベル: {validated['レベル']}")
except ValidationError as e:
    # どこで何がエラーになったか、分かりやすいパスが表示されます
    print(f"エラー発生箇所: {e.path} - {e.message}")
```

---

## 特徴

* 📝 **直感的なチェインメソッド** — `v.int().range(1, 10).optional()` のように流れるように記述。
* 🌏 **日本語キー対応** — 日本語のキー名をそのまま扱えるため、仕様書に近いコードが書けます。
* 🔄 **強力な変換・マイグレーション** — 旧形式から新形式へのキー名変換や、値の動的変換を検証時に同時に行えます。
* 🛠️ **デフォルト値とマージ** — 不足している値をベース設定（デフォルト値）で自動補完します。
* 🔍 **全エラーの一括収集** — 最初のエラーで止まらず、すべての不備を洗い出すことが可能です。

---

## API 例

詳細なリファレンスは [docs/index.md](docs/index.md) を参照してください。

### 基本バリデータ
* `v.str()`: 文字列
* `v.int()` / `v.float()`: 数値
* `v.bool()`: 真偽値
* `v.list(schema)`: リスト（要素のスキーマを指定）
* `v.dict(key_type, value_schema)`: 辞書

### 修飾メソッド
* `.optional()`: 必須でないフィールドにする
* `.default(value)`: 値がない場合のデフォルト値を指定（※実装予定/ベースマージ推奨）
* `.regex(pattern)`: 正規表現チェック
* `.range(min, max)` / `.min(val)` / `.max(val)`: 範囲チェック
* `.custom(func)`: 独自の変換・検証ロジックを注入

---

## 高度な使い方

### 部分更新とデフォルト値のマージ

設定ファイルの一部だけをユーザーが変更した場合などに便利です。

```python
DEFAULT_CONFIG = {"言語": "English", "音量": 50}
user_input = {"音量": 80}

# partial=True で不足キーを許容し、base でデフォルト値を補完
updated = validate(user_input, SCHEMA, partial=True, base=DEFAULT_CONFIG)
# -> {'言語': 'English', '音量': 80}
```

### マイグレーション

古いバージョンの設定データを自動的に新しい形式へ変換します。

```python
old_data = {"旧設定": "on", "timeout": 30}

migrated = validate(
    old_data, 
    SCHEMA, 
    migrate={
        "旧設定": "通知",
        "timeout": lambda v: f"{v}s"
    }
)
```

---

## 品質管理・セキュリティ

### サプライチェーンセキュリティ
本プロジェクトは **in-toto / SLSA v3 準拠の provenance（来歴証明）** を公開しています。
PyPI に公開された成果物が、正しいソースコードから正しい手順でビルドされたことを数学的に証明できます。

```bash
# slsa-verifier を使った検証例
slsa-verifier verify-artifact dist/validkit-*.whl \
  --provenance multiple.intoto.jsonl \
  --source-uri github.com/disnana/ValidKit
```

### 開発品質
以下のツールを CI で常時実行し、高いコード品質を維持しています。
* **Ruff**: 高速な Lint & フォーマット
* **mypy**: 厳格な静的型チェック
* **pytest**: 網羅的な単体テスト

---

## 貢献ガイドライン

Issue の報告や Pull Request を歓迎します！詳細は [SECURITY.md](SECURITY.md) または Issue テンプレートを確認してください。

---
**MIT License**
