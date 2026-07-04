# ValidKit

[![CI](https://github.com/disnana/ValidKit/actions/workflows/ci.yml/badge.svg)](https://github.com/disnana/ValidKit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/validkit-py?label=PyPI)](https://pypi.org/project/validkit-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ValidKit は、「直感的なスキーマ定義」と「日本語キーへの完全対応」を特徴とする、Python 用の軽量バリデーションライブラリです。

Pydantic ほどの重厚さを必要とせず、辞書ベースの柔軟性と強力なチェーンメソッドを維持しながら、堅牢な型安全環境を構築するために設計されました。

最新リリースは `1.3.2` です。事前コンパイル機能による超高速バリデーション、`Schema[T]` による IDE 補完、`.coerce()` による型自動変換、環境変数フォールバック、複数のエラー収集などの高度な機能に対応しています。

---

## 目次

- [特徴](#特徴)
- [インストール](#インストール)
- [クイックスタート](#クイックスタート)
- [スキーマの事前コンパイル (高速化)](#スキーマの事前コンパイル-高速化)
- [API 一覧](#api-一覧)
- [高度な機能](#高度な機能)
  - [クラス記法によるスキーマ定義](#クラス記法によるスキーマ定義)
  - [IDE 補完の有効化 (TypedDict + Schema)](#ide-補完の有効化-typeddict--schema)
  - [スキーマの逆生成 (v.auto_infer)](#スキーマの逆生成-vauto_infer)
  - [部分更新とデフォルト値のマージ](#部分更新とデフォルト値のマージ)
  - [データマイグレーション](#データマイグレーション)
- [品質管理とセキュリティ](#品質管理とセキュリティ)
- [ライセンス](#ライセンス)

---

## 特徴

- **クラス定義不要**: 辞書そのものがスキーマとして機能します。JSON や YAML の構造をそのまま定義に落とし込めます。
- **スキーマ事前コンパイル**: `compile(schema)` によりスキーマに最適化された検証コードを動的に生成し、超高速に動作します。
- **日本語キー完全対応**: 日本語のキー名をそのままバリデータと組み合わせて、可読性の高いバリデーションを記述できます。
- **高度な条件付き検証**: 正規表現、数値範囲、カスタム関数のほか、他のフィールドの状態に応じた条件付き検証も直感的に実装可能です。
- **モダンなサプライチェーンセキュリティ**: SLSA v3 準拠の来歴証明（provenance）に対応しています。

---

## インストール

```bash
pip install validkit-py
```

---

## クイックスタート

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
    "設定": {"通知": True}
}

try:
    # 検証実行
    validated = validate(data, SCHEMA)
    print(f"検証成功: {validated['レベル']}")
except ValidationError as e:
    # 発生箇所の階層パスとメッセージを取得可能
    print(f"エラー発生箇所: {e.path} - {e.message}")
```

---

## スキーマの事前コンパイル (高速化)

大規模なループや頻繁な API リクエストの検証など、パフォーマンスが重要視される場面では `compile` API を使用できます。
渡されたスキーマに対してインライン最適化された検証ロジックを事前に動的ビルドし、Python のネイティブな比較式に置き換えます。

```python
from validkit import compile, v

# 事前コンパイル (実行時に毎回発生するスキーマ走査やリフレクションを排除)
schema = compile({
    "id": v.int(),
    "name": v.str().min(3),
})

# 最適化された検証の実行
data = {"id": 1, "name": "Alice"}
validated = schema.validate(data)
```

> **パフォーマンス比較** (50,000回の検証ループ)
> - 通常の `validate()`: `0.155` 秒
> - 事前コンパイル `compile()`: `0.036` 秒 (**約 4.3 倍高速**)
>
> `collect_errors=True` も専用の生成関数で検証されますが、複数の `ErrorDetail` を作成するため通常検証より速度差は小さくなります。

---

## API 一覧

詳細な仕様は [`docs/index.md`](docs/index.md) を参照してください。

### 基本バリデータ
- `v.bool()`: 真偽値
- `v.datetime()`: 日時 (期限チェック対応)
- `v.uuid()`: UUID (バージョン検証対応)
- `v.mac()` / `v.sid()` / `v.hwid()`: 各種識別子・ハードウェア ID
- `v.ip()`: IP アドレス (IPv4/IPv6)
- `v.snowflake()`: Discord Snowflake
- `v.version()`: Semantic Versioning
- `v.url()`: URL フォーマット (プロトコル・ドメイン制限対応)
- `v.list(schema)`: 指定したスキーマを満たすリスト
- `v.dict(key_type, value_schema)`: 指定したキー型と値スキーマを満たす辞書
- `v.instance(type_cls)`: 指定したクラスの `isinstance` チェック
- `v.enum(enum_cls)`: Python `enum.Enum` (文字列からの自動変換対応)

### 共通修飾メソッド
- `.optional()`: フィールドを省略可能にする
- `.default(value)`: 欠損時のデフォルト値を設定する
- `.env(key, decryptor=None)`: 欠損時に環境変数から取得・復号して補完する
- `.secret()`: エラー時に元の値をマスク (`***`) する
- `.error_msg(msg)`: エラーメッセージを指定したテキストに上書きする
- `.custom(func)`: 独自の検証・変換ロジックを注入する
- `.when(condition_func)`: 親データ全体の状態に基づく条件付きバリデーション

---

## 高度な機能

### クラス記法によるスキーマ定義

```python
from typing import Optional, List, Dict
from validkit import validate

class ServerConfig:
    host: str
    port: int = 5432
    tags: Optional[List[str]]
    metadata: Dict[str, int]

result = validate(
    {"host": "db.local", "metadata": {"connections": 10}},
    ServerConfig,
)
```

### IDE 補完の有効化 (TypedDict + Schema)

```python
from typing import TypedDict
from validkit import v, validate, Schema

class UserDict(TypedDict):
    name: str
    level: int

# Schema[T] を使って IDE に型情報を伝える
SCHEMA: Schema[UserDict] = Schema({
    "name": v.str(),
    "level": v.int()
})

# 戻り値は UserDict として推論され、IDE による入力補完が有効になります
result = validate({"name": "nana_kit", "level": 50}, SCHEMA)
```

### スキーマの逆生成 (v.auto_infer)

```python
from validkit import v

raw_data = {"name": "Alice", "age": 30, "active": True}
schema = v.auto_infer(
    raw_data,
    schema_overrides={"age": v.int().range(0, 150)}
)
```

### 部分更新とデフォルト値のマージ

```python
from validkit import v, validate

SCHEMA = {"lang": v.str(), "volume": v.int()}
DEFAULT = {"lang": "English", "volume": 50}

# partial=True で不足キーを許容し、base でデフォルト値を補完
result = validate({"volume": 80}, SCHEMA, partial=True, base=DEFAULT)
# -> {"lang": "English", "volume": 80}
```

### データマイグレーション

```python
from validkit import v, validate

SCHEMA = {"notifications": v.str()}
old_data = {"old_notifications_key": "on"}

migrated = validate(
    old_data,
    SCHEMA,
    migrate={"old_notifications_key": "notifications"}
)
```

---

## 品質管理とセキュリティ

### サプライチェーンセキュリティ
本プロジェクトは **in-toto / SLSA v3 準拠の provenance（来歴証明）** を公開しています。
PyPI に公開されたパッケージ成果物が、正しいソースコードから正しい手順でビルドされたことを数学的に検証可能です。

### 開発品質
CI プロセスにおいて、以下の静的検証ツールおよびテストフレームワークを実行し、高いコード品質を維持しています。
- **Ruff**: 高速な Lint / フォーマット
- **mypy**: 厳格な型チェック
- **pytest**: 網羅的な単体テスト

---

## ライセンス

本プロジェクトは **MIT ライセンス** の下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。
