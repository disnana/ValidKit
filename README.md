# ValidKit

[![CI](https://github.com/disnana/ValidKit/actions/workflows/ci.yml/badge.svg)](https://github.com/disnana/ValidKit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/validkit-py?label=PyPI)](https://pypi.org/project/validkit-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ValidKit は、<strong>「直感的なスキーマ定義」と「日本語キーへの完全対応」</strong>を特徴とする、Python 用の軽量バリデーションライブラリです。

複雑にネストされた設定ファイルや、Discord ボットのユーザー設定、外部 API からのレスポンスなどを、シンプルかつ堅牢に検証するために設計されました。Pydantic ほど重厚ではなく、しかし辞書ベースの柔軟性と強力なチェーンメソッドを提供します。

最新リリースは `1.2.1` です。`Schema[T]` による IDE 補完、`.coerce()` による型変換、`.default()` / `.examples()` / `.description()`、`Schema.generate_sample()`、`v.auto_infer()` に対応しています。

---

<a id="概要"></a>
## 🚀 なぜ ValidKit なのか？

- **クラス定義不要**: 辞書そのものがスキーマになります。既存の JSON/YAML 構造をそのまま定義に落とし込めます。
- **日本語キーにフレンドリー**: `v.str()` や `v.int()` を日本語のキー名と組み合わせて、可読性の高いバリデーションを記述できます。
- **高度な検証をシンプルに**: 正規表現、数値範囲、カスタム関数、さらには「他のフィールドの値に応じた検証（条件付き検証）」も直感的に書けます。
- **仕様書づくりにも強い**: `Schema.generate_sample()` で設定テンプレートを生成し、`v.auto_infer()` で既存データからスキーマを逆生成できます。
- **モダンな開発フロー**: SLSA v3 準拠の来歴証明（provenance）に対応し、サプライチェーンの安全性を確保しています。

---

## 目次

* [最近のアップデート](#最近のアップデート)
* [特徴](#特徴)
* [インストール](#インストール)
* [クイックスタート](#クイックスタート)
* [API 例](#api-例)
* [高度な使い方](#高度な使い方)
  * [クラス記法によるスキーマ定義](#クラス記法によるスキーマ定義)
  * [IDE 補完を効かせる（TypedDict + Schema）](#ide-補完を効かせるtypeddict--schema)
  * [部分更新とデフォルト値のマージ](#部分更新とデフォルト値のマージ)
  * [マイグレーション](#マイグレーション)
* [品質管理・セキュリティ](#品質管理セキュリティ)
* [変更履歴](#変更履歴)
* [貢献ガイドライン](#貢献ガイドライン)
* [ライセンス](#ライセンス)

---

## 最近のアップデート

- **v1.2.1**
  - `v.auto_infer(data, type_map=None, schema_overrides=None)` を追加
  - `Schema.generate_sample()` の安全性を改善し、制約を満たせない候補は `ValueError` を返すように修正
  - `.range()` / `.min()` / `.max()` の境界矛盾を定義時に検出するよう改善
- **v1.2.0**
  - `.default()` / `.examples()` / `.description()` を追加
  - `Schema.generate_sample()` でスキーマからサンプル設定を生成可能に
- **v1.1.x**
  - `Schema[T]` と `validate()` の型補完対応を強化
  - `.coerce()` による自動型変換を追加

詳細は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。API の詳説は [`docs/index.md`](docs/index.md) にまとめています。

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
* 🏷️ **クラス記法対応** — Python クラスの型アノテーションをそのままスキーマとして使えます。`Optional[T]`・`List[T]`・`Dict[K,V]`・カスタム型にも対応。
* 🌏 **日本語キー対応** — 日本語のキー名をそのまま扱えるため、仕様書に近いコードが書けます。
* 🧠 **型補完に強い** — `Schema[T]` と TypedDict を組み合わせると、IDE / 型チェッカーが戻り値の形を推論できます。
* 🔄 **強力な変換・マイグレーション** — 旧形式から新形式へのキー名変換や、値の動的変換を検証時に同時に行えます。
* 🛠️ **デフォルト値とサンプル生成** — `.default()`・`.examples()`・`.description()` と `Schema.generate_sample()` で設定テンプレート作成にも向きます。
* 🔍 **全エラーの一括収集** — 最初のエラーで止まらず、すべての不備を洗い出すことが可能です。

---

## API 例

詳細なリファレンスは [`docs/index.md`](docs/index.md)、版ごとの変更点は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。

### 基本バリデータ
* `v.str()`: 文字列
* `v.int()` / `v.float()`: 数値
* `v.bool()`: 真偽値
* `v.list(schema)`: リスト（要素のスキーマを指定）
* `v.dict(key_type, value_schema)`: 辞書
* `v.instance(type_cls)`: 任意のクラスの isinstance チェック

### 修飾メソッド
* `.optional()`: 必須でないフィールドにする
* `.default(value)`: 値がない場合のデフォルト値を指定（自動的に `.optional()` 扱いとなる）
* `.examples(list)`: サンプル生成やドキュメント用の具体例を設定
* `.description(str)`: フィールドの説明文を設定
* `.regex(pattern)`: 正規表現チェック
* `.range(min, max)` / `.min(val)` / `.max(val)`: 範囲チェック（`min <= max` が必須。不正な境界は定義時に `ValueError`）
* `.custom(func)`: 独自の変換・検証ロジックを注入
* `.coerce()`: 入力値の型を自動的に変換（例: `"123" -> 123`）

---

## 高度な使い方

### クラス記法によるスキーマ定義

辞書スキーマに加えて、Python のクラス型アノテーションをそのままスキーマとして使えます。

#### 基本的なアノテーション

```python
from validkit import v, validate

class UserProfile:
    name: str
    age: int
    score: float
    active: bool

data = {"name": "Alice", "age": 30, "score": 9.5, "active": True}
result = validate(data, UserProfile)
# -> {"name": "Alice", "age": 30, "score": 9.5, "active": True}
```

#### `Optional` / `List` / `Dict` など typing モジュールの型

```python
from typing import Dict, List, Optional
from validkit import validate

class ServerConfig:
    host: str
    port: int
    tags: Optional[List[str]]   # 省略可能なリスト
    metadata: Dict[str, int]    # 辞書

# tags は省略してもエラーにならない
result = validate(
    {"host": "db.local", "port": 5432, "metadata": {"connections": 10}},
    ServerConfig,
)
# -> {"host": "db.local", "port": 5432, "metadata": {"connections": 10}}
```

Python 3.9 以降では `list[T]` / `dict[K, V]` の組み込みジェネリクス記法も使えます。

```python
class Report:
    scores: list[int]
    labels: dict[str, str]
```

#### カスタム型 (オリジナルクラス)

任意のクラスをアノテーションに使うと、`isinstance` チェックが自動的に行われます。

```python
from validkit import validate

class Timezone:
    def __init__(self, name: str) -> None:
        self.name = name

UTC = Timezone("UTC")

class Config:
    name: str
    age: int
    timezone: Timezone          # カスタム型 → isinstance チェック

result = validate({"name": "server1", "age": 5, "timezone": UTC}, Config)
```

`v.instance()` を使うと辞書スキーマ内でも同じチェックができます。

```python
from validkit import v, validate

schema = {
    "name": v.str(),
    "timezone": v.instance(Timezone).default(UTC),
}
result = validate({"name": "server1"}, schema)
# timezone は省略時に UTC が補完される
```

#### クラス属性によるデフォルト値と Validator の組み合わせ

クラス属性に具体的な値を設定するとデフォルト値として機能します。
Validator インスタンスを直接クラス属性にすることで、詳細な制約も記述できます。

```python
from typing import Optional
from validkit import v, validate

class Config:
    host: str                                    # 必須
    port: int = 5432                             # デフォルト値 5432
    ssl: bool = False                            # デフォルト値 False
    timeout: Optional[int] = 30                  # オプション + デフォルト
    role = v.str().default("worker")             # Validator で詳細に定義

result = validate({"host": "db.local"}, Config)
# -> {"host": "db.local", "port": 5432, "ssl": False, "timeout": 30, "role": "worker"}
```

#### 対応型ヒント一覧

| アノテーション | 動作 |
|---|---|
| `str` / `int` / `float` / `bool` | 型チェック |
| `Optional[T]` / `Union[T, None]` | 内部型をチェック・省略可能 |
| `List[T]` / `list[T]` | リスト要素の型チェック |
| `Dict[K, V]` / `dict[K, V]` | 辞書の値の型チェック |
| 任意のクラス | `isinstance` チェック |
| `Any` / 不明な型 | チェックなし（パススルー） |
| `Validator` インスタンス | ValidKit の完全なバリデーション |

> **注意**: `Union[int, str]` のように `None` を含まない非 Optional な Union 型は現在サポートされていません。`validate()` の呼び出し時（スキーマ変換フェーズ）に `TypeError` が送出されます。代わりに `Optional[T]`（= `Union[T, None]`）か具体的な単一型を使用してください。複数の型を受け付けたい場合は `v.instance(MyBaseClass)` などを検討してください。

### IDE 補完を効かせる（TypedDict + Schema）

`Schema[T]` クラスを使うと、IDE（PyCharm / VS Code）での型補完が有効になります。

```python
from typing import TypedDict
from validkit import v, validate

class UserDict(TypedDict):
    name: str
    level: int

data = {"name": "nana_kit", "level": 50}
plain_schema = {"name": v.str(), "level": v.int()}

result: UserDict = validate(data, plain_schema)  # IDE への型ヒントは変数側で提供
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
from validkit import v, validate

SCHEMA = {
    "host": v.str().default("localhost"),
    "port": v.int().default(5432),
}

# どちらも未指定でも、デフォルト値が補完される
result = validate({}, SCHEMA)
# -> {'host': 'localhost', 'port': 5432}
```

ネストされた辞書やリスト内でも同様に動作します。

### サンプルデータの自動生成 (`generate_sample`)

定義したスキーマから、仕様書の雛形や設定ファイルのテンプレートとして使えるサンプルデータを自動生成できます。生成された値は各バリデータで再検証されるため、`regex()` や `custom()` を満たせない不正なサンプルは返しません。

```python
from validkit import v, Schema

SCHEMA = Schema({
    "app_name": v.str().examples(["MyAwesomeApp"]),
    "port": v.int().default(8080).description("待機ポート"),
    "debug": v.bool().default(False),
})

# スキーマからサンプルを辞書形式で取得
sample = SCHEMA.generate_sample()
# -> {'app_name': 'MyAwesomeApp', 'port': 8080, 'debug': False}
```

生成の優先順位:
1. `.default()` で設定された値
2. `.examples()` リストの最初の要素
3. 各型のダミー値（`str`: `"example"`, `int`: `0`, `bool`: `False` 等）

`regex()` / `custom()` などで上記候補が制約を満たせない場合、`generate_sample()` は `ValueError` を送出します。その場合は妥当な `.default(...)` または `.examples([...])` を与えてください。

<a id="auto-infer"></a>
### スキーマを既存データから逆生成する (`v.auto_infer`)

既存の設定ファイルや API レスポンスがすでにある場合、`v.auto_infer()` で ValidKit スキーマのたたき台を作れます。

```python
from datetime import date
from validkit import v, validate

raw = {
    "name": "Alice",
    "age": 30,
    "active": True,
    "created_at": date(2026, 3, 1),
}

schema = v.auto_infer(
    raw,
    type_map={date: lambda value: value.isoformat()},
    schema_overrides={
        "age": v.int().range(0, 150),
    },
)

normalized = {
    "name": "Alice",
    "age": 30,
    "active": True,
    "created_at": "2026-03-01",
}

result = validate(normalized, schema)
```

使いどころ:
- 既存データからスキーマをブートストラップしたいとき
- カスタム型を `type_map` でプリミティブへ落として推論したいとき
- 一部のフィールドだけ `schema_overrides` で明示的に厳しくしたいとき

### スキーマ自動生成 (`v.auto_infer`)

既存データから ValidKit スキーマを逆生成できます。プロトタイピングや既存 JSON / dict からの移行時に便利です。

```python
import datetime
from validkit import v

data = {
    "name": "Alice",
    "score": 9.5,
    "created_at": datetime.date(2024, 1, 1),
}

schema = v.auto_infer(
    data,
    type_map={datetime.date: v.str()},
    schema_overrides={"score": v.float().range(0.0, 10.0)},
)
```

- `type_map` でカスタム型を処理できます
- `schema_overrides` でトップレベル dict の特定フィールドだけ推論結果を上書きできます
- `None` は `optional()` なバリデータとして推論されます

### 部分更新とデフォルト値のマージ (base引数)

既存の辞書データを「ベース」として、入力された不完全なデータをマージする場合に便利です。これは `.default()` よりも優先されます。

```python
from validkit import v, validate

SCHEMA = {
    "言語": v.oneof(["English", "日本語"]),
    "音量": v.int(),
}
DEFAULT_CONFIG = {"言語": "English", "音量": 50}
user_input = {"音量": 80}

# partial=True で不足キーを許容し、base でデフォルト値を補完
updated = validate(user_input, SCHEMA, partial=True, base=DEFAULT_CONFIG)
# -> {'言語': 'English', '音量': 80}
```

### マイグレーション

古いバージョンの設定データを自動的に新しい形式へ変換します。

```python
from validkit import v, validate

SCHEMA = {
    "通知": v.str(),
    "timeout": v.str(),
}
old_data = {"旧設定": "on", "timeout": 30}

migrated = validate(
    old_data,
    SCHEMA,
    migrate={
        "旧設定": "通知",
        "timeout": lambda value: f"{value}s",
    },
)
```

### 自動変換 (Coercion)

入力データの型が期待される型と異なる場合に、自動的に変換を試行します。

```python
from validkit import v, validate

SCHEMA = {
    "id": v.int().coerce(),
    "is_active": v.bool().coerce(),
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

<a id="changelog"></a>
## 変更履歴

- 版ごとの詳細な変更点は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。
- API の詳しい説明は [`docs/index.md`](docs/index.md) にあります。
- 現在の公開バージョンは `1.2.1` です。

---

## 貢献ガイドライン

Issue の報告や Pull Request を歓迎します！詳細は [SECURITY.md](SECURITY.md) または Issue テンプレートを確認してください。

---

## ライセンス

本プロジェクトは **MIT ライセンス**の下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。
