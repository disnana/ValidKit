# ValidKit

[![CI](https://github.com/disnana/ValidKit/actions/workflows/ci.yml/badge.svg)](https://github.com/disnana/ValidKit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/validkit-py?label=PyPI)](https://pypi.org/project/validkit-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ValidKit は、<strong>「直感的なスキーマ定義」と「日本語キーへの完全対応」</strong>を特徴とする、Python 用の軽量バリデーションライブラリです。

複雑にネストされた設定ファイルや、Discord ボットのユーザー設定、外部 API からのレスポンスなどを、シンプルかつ堅牢に検証するために設計されました。Pydantic ほど重厚ではなく、しかし辞書ベースの柔軟性と強力なチェーンメソッドを提供します。

---

<a id="概要"></a>
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
  * [IDE 補完を効かせる（TypedDict + Schema）](#ide-補完を効かせるtypeddict--schema)
  * [部分更新とデフォルト値のマージ](#部分更新とデフォルト値のマージ)
  * [マイグレーション](#マイグレーション)
* [品質管理・セキュリティ](#品質管理セキュリティ)
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
* `.default(value)`: 値がない場合のデフォルト値を指定（自動的に `.optional()` 扱いとなる）
* `.examples(list)`: サンプル生成やドキュメント用の具体例を設定
* `.description(str)`: フィールドの説明文を設定
* `.regex(pattern)`: 正規表現チェック
* `.range(min, max)` / `.min(val)` / `.max(val)`: 範囲チェック
* `.custom(func)`: 独自の変換・検証ロジックを注入
* `.coerce()`: 入力値の型を自動的に変換（例: "123" -> 123）

---

## 高度な使い方

### IDE 補完を効かせる（TypedDict + Schema）

`Schema[T]` クラスを使うと、IDE（PyCharm / VS Code）での型補完が有効になります。

```python
from typing import TypedDict
from validkit import v, validate, Schema

# 1. TypedDict でキーと型を定義
class UserDict(TypedDict):
    name: str
    level: int

# 2. Schema[T] でスキーマをラップ
SCHEMA: Schema[UserDict] = Schema({
    "name": v.str(),
    "level": v.int().range(1, 100),
})

data = {"name": "nana_kit", "level": 50}

# 3. validate に渡すだけ — IDE が戻り値を UserDict として推論する
result = validate(data, SCHEMA)
print(result["name"])   # ← IDE が "name" / "level" を補完してくれる
```

注意:
- `collect_errors=True` を指定した場合、`validate` は `ValidationResult` を返します。そのため、`Schema[T]` を使っていても戻り値の型は `T` ではなく `ValidationResult` になります。

TypedDict を書くのが面倒な場合は、既存の辞書スキーマを渡す使い方もそのまま使えます。
型補完が不要なケースでは、変数側に型注釈を書くことで mypy / pyright に型を伝えられます。

```python
# 型付きスキーマなし（従来の辞書スキーマ）— 変数側にアノテーションを付ける方法
plain_schema = {"name": v.str(), "level": v.int()}
result: UserDict = validate(data, plain_schema)  # IDE への型ヒントは変数側で提供
```

### デフォルト値の自動補完 (`.default`)

スキーマ定義時にデフォルト値を設定しておくと、データにそのキーが含まれていない場合に自動的に補完されます。

```python
SCHEMA = {
    "host": v.str().default("localhost"),
    "port": v.int().default(5432)
}

# どちらも未指定でも、デフォルト値が補完される
result = validate({}, SCHEMA)
# -> {'host': 'localhost', 'port': 5432}
```

ネストされた辞書やリスト内でも同様に動作します。

### サンプルデータの自動生成 (`generate_sample`)

定義したスキーマから、仕様書の雛形や設定ファイルのテンプレートとして使えるサンプルデータを自動生成できます。

```python
SCHEMA = Schema({
    "app_name": v.str().examples(["MyAwesomeApp"]),
    "port": v.int().default(8080).description("待機ポート"),
    "debug": v.bool().default(False)
})

# スキーマからサンプルを辞書形式で取得
sample = SCHEMA.generate_sample()
# -> {'app_name': 'MyAwesomeApp', 'port': 8080, 'debug': False}
```

生成の優先順位:
1. `.default()` で設定された値
2. `.examples()` リストの最初の要素
3. 各型のダミー値（`str`: "example", `int`: 0, `bool`: False 等）

### 部分更新とデフォルト値のマージ (base引数)

既存の辞書データを「ベース」として、入力された不完全なデータをマージする場合に便利です。これは `.default()` よりも優先されます。

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

### 自動変換 (Coercion)

入力データの型が期待される型と異なる場合に、自動的に変換を試行します。

```python
# 文字列を整数へ、数値を真偽値へ自動変換
SCHEMA = {
    "id": v.int().coerce(),
    "is_active": v.bool().coerce()
}

data = {"id": "1001", "is_active": 1}
validated = validate(data, SCHEMA)
# -> {'id': 1001, 'is_active': True}
```

各バリデータの変換ルール：
- `v.str().coerce()`: `str(value)` による変換
- `v.int().coerce()`: `int(value)` による変換
- `v.float().coerce()`: `float(value)` による変換
- `v.bool().coerce()`: 
    - 文字列: `"true"`, `"1"`, `"yes"`, `"on"` -> `True` / `"false"`, `"0"`, `"no"`, `"off"` -> `False`
    - 数値: `1` -> `True` / `0` -> `False`

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

## ライセンス

本プロジェクトは **MIT ライセンス**の下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。
